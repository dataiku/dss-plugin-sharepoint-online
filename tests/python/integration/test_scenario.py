import pytest
import logging

from dku_plugin_test_utils import dss_scenario


pytestmark = pytest.mark.usefixtures("plugin", "dss_target")


test_kwargs = {
    "user": "user1",
    "project_key": "PLUGINTESTSHAREPOINTONLINE",
    "logger": logging.getLogger("dss-plugin-test.sharepoint-online.test_scenario"),
}


def test_run_sharepoint_online_regular_list_write(user_clients):
    test_kwargs["client"] = user_clients[test_kwargs["user"]]
    dss_scenario.run(scenario_id="RegularListWrite", **test_kwargs)


def test_run_sharepoint_online_read_calculated_columns(user_clients):
    dss_scenario.run(scenario_id="ReadCalculatedColumns", **test_kwargs)


def test_run_sharepoint_online_read_long_list(user_clients):
    dss_scenario.run(scenario_id="ReadLongList", **test_kwargs)


def test_run_sharepoint_online_documents(user_clients):
    dss_scenario.run(scenario_id="SharePointDocuments", **test_kwargs)
