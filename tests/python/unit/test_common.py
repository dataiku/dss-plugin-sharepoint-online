from common import get_value_from_path, get_date_time_format_from_regional_settings
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
        self.us_regional_settings = {
            "odata.metadata": "https://ikuiku.sharepoint.com/sites/dssplugin/_api/$metadata#SP.ApiData.RegionalSettingss/@Element",
            "odata.type": "SP.RegionalSettings",
            "odata.id": "https://ikuiku.sharepoint.com/sites/dssplugin/_api/web/RegionalSettings",
            "odata.editLink": "web/RegionalSettings",
            "AdjustHijriDays": 0,
            "AlternateCalendarType": 0,
            "AM": "AM",
            "CalendarType": 1,
            "Collation": 25,
            "CollationLCID": 2070,
            "DateFormat": 0,
            "DateSeparator": "/",
            "DecimalSeparator": ".",
            "DigitGrouping": "3;0",
            "FirstDayOfWeek": 0,
            "FirstWeekOfYear": 0,
            "IsEastAsia": False,
            "IsRightToLeft": False,
            "IsUIRightToLeft": False,
            "ListSeparator": ",",
            "LocaleId": 1033,
            "NegativeSign": "-",
            "NegNumberMode": 1,
            "PM": "PM",
            "PositiveSign": "",
            "ShowWeeks": False,
            "ThousandSeparator": ",",
            "Time24": False,
            "TimeMarkerPosition": 0,
            "TimeSeparator": ":",
            "WorkDayEndHour": 1020,
            "WorkDays": 62,
            "WorkDayStartHour": 480
        }
        self.eu_regional_settings = {
            "AM": "AM",
            "CalendarType": 1,
            "DateFormat": 1,
            "DateSeparator": "/",
            "DecimalSeparator": ".",
            "DigitGrouping": "3;0",
            "ListSeparator": ",",
            "NegativeSign": "-",
            "NegNumberMode": 1,
            "PM": "PM",
            "PositiveSign": "",
            "ShowWeeks": False,
            "ThousandSeparator": ",",
            "Time24": True,
            "TimeMarkerPosition": 0,
            "TimeSeparator": ":",
            "WorkDayEndHour": 1020,
            "WorkDays": 62,
            "WorkDayStartHour": 480
        }
        self.no_regional_settings = {}

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

    def test_get_time_format_us(self):
        date_format = get_date_time_format_from_regional_settings(self.us_regional_settings)
        assert date_format == "%m/%d/%Y %I:%M %p"

    def test_get_time_format_none(self):
        date_format = get_date_time_format_from_regional_settings(self.no_regional_settings)
        assert date_format == "%Y-%m-%dT%H:%M:%S.%fZ"
