from common import get_value_from_path
import pytest


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
