from dku_plugin_test_utils import dss_scenario

TEST_PROJECT_KEY = "PLUGINTESTSHAREPOINTONLINE"


def test_run_sharepoint_online_regular_list_write(user_clients):
    dss_scenario.run(user_clients, project_key=TEST_PROJECT_KEY, scenario_id="RegularListWrite")


def test_run_sharepoint_online_read_calculated_columns(user_clients):
    dss_scenario.run(user_clients, project_key=TEST_PROJECT_KEY, scenario_id="ReadCalculatedColumns")


def test_run_sharepoint_online_read_long_list(user_clients):
    dss_scenario.run(user_clients, project_key=TEST_PROJECT_KEY, scenario_id="ReadLongList")


def test_run_sharepoint_online_documents(user_clients):
    dss_scenario.run(user_clients, project_key=TEST_PROJECT_KEY, scenario_id="SharePointDocuments")


def test_run_sharepoint_online_authentication_modes(user_clients):
    dss_scenario.run(user_clients, project_key=TEST_PROJECT_KEY, scenario_id="AuthenticationModes")
