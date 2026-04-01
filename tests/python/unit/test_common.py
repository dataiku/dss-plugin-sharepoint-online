from common import get_value_from_path, is_request_performed, decode_retry_after_header
from sharepoint_whitelist import WhiteList
from sharepoint_constants import SharePointConstants
import pytest


class MockResponse:
    def __init__(self, status_code, headers):
        self.status_code = status_code
        self.headers = headers
        self.content = '{"a": 1}'
        self.url = 'https://test.com/test'


class TestCommonMethods:
    def setup_class(self):
        self.dictionary_to_search = {
            "a": {
                "b": {
                    "c": "ok1"
                },
                "d": "ok2"
            }
        }
        self.ok_path_1 = ["a", "b", "c"]
        self.ok_path_2 = ["a", "d"]
        self.ko_path = ["a", "c"]
        self.mock_response_none = None
        self.mock_response_http_200 = MockResponse(200, {"Retry-After": "1"})
        self.mock_response_http_429_digit_1s = MockResponse(429, {"Retry-After": "1"})
        self.mock_response_http_429_no_header = MockResponse(429, {})
        self.mock_response_http_503_digit_1s = MockResponse(503, {"Retry-After": "1"})
        self.mock_response_http_429_date_in_past = MockResponse(429, {"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"})
        self.mock_response_http_429_date_in_future = MockResponse(429, {"Retry-After": "Wed, 21 Oct 9999 07:28:00 GMT"})
        self.mock_response_http_429_garbage = MockResponse(429, {"Retry-After": "blablablabla"})
        self.app_certificate = {
            'libraries_whitelist': [
                {
                    '$$hashKey': 'object:540',
                    'whitelist_rights': ['read'],
                    'whitelist_name': 'site/Path/Shared Documents 1'
                },
                {
                    '$$hashKey': 'object:540',
                    'whitelist_rights': ['read'],
                    'whitelist_name': '/site/Path/Shared Documents 2'
                },
                {
                    '$$hashKey': 'object:540',
                    'whitelist_rights': ['read'],
                    'whitelist_name': 'site/Path/Shared Documents 3/'
                },
                {
                    '$$hashKey': 'object:540',
                    'whitelist_rights': ['read'],
                    'whitelist_name': '/site/Path/Shared Documents 4/'
                }
            ],
            'lists_whitelist': [
                {
                    '$$hashKey': 'object:540',
                    'whitelist_rights': ['read'],
                    'whitelist_name': 'CanRead'
                }, {
                    '$$hashKey': 'object:540',
                    'whitelist_rights': ['read', 'write'],
                    'whitelist_name': 'Can write'
                }
            ],
            'activate_whitelist': True
        }

    def test_get_value_from_path_long_path(self):
        key = get_value_from_path(self.dictionary_to_search, self.ok_path_1)
        assert key == "ok1"

    def test_get_value_from_path_short_path(self):
        key = get_value_from_path(self.dictionary_to_search, self.ok_path_2)
        assert key == "ok2"

    def test_get_value_from_path_wrong_path(self):
        key = get_value_from_path(self.dictionary_to_search, self.ko_path)
        assert key is None

    def test_get_value_from_path_wrong_path_custom_reply(self):
        key = get_value_from_path(self.dictionary_to_search, self.ko_path, default_reply="ko")
        assert key == "ko"

    def test_is_request_performed_none(self):
        mock_response = None
        response = is_request_performed(mock_response)
        assert response is False

    def test_is_request_performed_error_200(self):
        response = is_request_performed(self.mock_response_http_200)
        assert response is True

    def test_is_request_performed_error_429(self):
        response = is_request_performed(self.mock_response_http_429_digit_1s)
        assert response is False

    def test_is_request_performed_error_503(self):
        response = is_request_performed(self.mock_response_http_503_digit_1s)
        assert response is False

    def test_decode_retry_after_header_seconds(self):
        seconds_before_retry = decode_retry_after_header(self.mock_response_http_429_digit_1s)
        assert seconds_before_retry == 1

    def test_decode_retry_after_header_future_date(self):
        seconds_before_retry = decode_retry_after_header(self.mock_response_http_429_date_in_future)
        assert seconds_before_retry >= 4000

    def test_decode_retry_after_header_past_date(self):
        seconds_before_retry = decode_retry_after_header(self.mock_response_http_429_date_in_past)
        assert seconds_before_retry == SharePointConstants.DEFAULT_WAIT_BEFORE_RETRY

    def test_decode_retry_after_header_garbage(self):
        seconds_before_retry = decode_retry_after_header(self.mock_response_http_429_garbage)
        assert seconds_before_retry == SharePointConstants.DEFAULT_WAIT_BEFORE_RETRY

    def test_decode_retry_after_header_no_header(self):
        seconds_before_retry = decode_retry_after_header(self.mock_response_http_429_no_header)
        assert seconds_before_retry == SharePointConstants.DEFAULT_WAIT_BEFORE_RETRY

    def test_whitelist_read_start_slash_series_1(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_read_path("site/Path/Shared Documents 1") is True
        assert whitelist.can_read_path("/site/Path/Shared Documents 1") is True
        assert whitelist.can_read_path("site/Path/Shared Documents 1/subfolder") is True
        assert whitelist.can_read_path("/site/Path/Shared Documents 1/subfolder") is True

    def test_whitelist_read_start_slash_series_2(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_read_path("site/Path/Shared Documents 2") is True
        assert whitelist.can_read_path("/site/Path/Shared Documents 2") is True
        assert whitelist.can_read_path("site/Path/Shared Documents 2/subfolder") is True
        assert whitelist.can_read_path("/site/Path/Shared Documents 2/subfolder") is True

    def test_whitelist_read_start_slash_series_3(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_read_path("site/Path/Shared Documents 3") is True
        assert whitelist.can_read_path("/site/Path/Shared Documents 3") is True
        assert whitelist.can_read_path("site/Path/Shared Documents 3/subfolder") is True
        assert whitelist.can_read_path("/site/Path/Shared Documents 3/subfolder") is True

    def test_whitelist_read_start_slash_series_4(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_read_path("site/Path/Shared Documents 4") is True
        assert whitelist.can_read_path("/site/Path/Shared Documents 4") is True
        assert whitelist.can_read_path("site/Path/Shared Documents 4/subfolder") is True
        assert whitelist.can_read_path("/site/Path/Shared Documents 4/subfolder") is True

    def test_whitelist_read_start_slash_series_5(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_read_path("site/Path/Shared Documents 5") is False
        assert whitelist.can_read_path("/site/Path/Shared Documents 5") is False
        assert whitelist.can_read_path("site/Path/Shared Documents 5/subfolder") is False
        assert whitelist.can_read_path("/site/Path/Shared Documents 5/subfolder") is False

    def test_whitelist_read_casing(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_read_path("Site/path/shared documents 4/subFolder") is True

    def test_whitelist_read_list(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_read_list("CanRead") is True

    def test_whitelist_cannot_write_list(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_write_list("CanRead") is False

    def test_whitelist_list_casing_cannot(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_write_list("canread") is False

    def test_whitelist_list_casing(self):
        whitelist = WhiteList(self.app_certificate)
        assert whitelist.can_read_list("canread") is True
