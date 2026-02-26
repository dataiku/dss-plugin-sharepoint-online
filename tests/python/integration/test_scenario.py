from dku_plugin_test_utils import dss_scenario

TEST_PROJECT_KEY = "PLUGINTESTSHAREPOINTONLINE"


def test_run_sharepoint_online_regular_list_write(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="RegularListWrite")


def test_run_sharepoint_online_read_calculated_columns(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="ReadCalculatedColumns")


def test_run_sharepoint_online_read_long_list(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="ReadLongList")


def test_run_sharepoint_online_documents(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="SharePointDocuments")


def test_run_sharepoint_online_authentication_modes(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="AuthenticationModes")


def test_run_sharepoint_online_site_root_overwrite(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="SiteRootOverwrite")


def test_run_sharepoint_online_write_on_empty_root_path(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="WRITEONEMPTYROOTPATH")


def test_run_sharepoint_online_file_overwrite(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="FILEOVERWRITE")


def test_run_sharepoint_online_append_to_list_recipe(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="APPENDTOLISTRECIPE")


def test_run_sharepoint_online_write_file_in_path_w_ro_parent(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="SC169288_WRITE_FILE_WITH_RO_PARENT_FOLDER")


def test_run_sharepoint_online_certificate_auth(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="CERTIFICATEAUTH")


def test_run_sharepoint_online_encrypted_certificate_auth(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="ENCRYPTEDCERTIFICATEAUTH")


def test_run_sharepoint_online_write_preset_without_root_folder(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="SC194128NOROOTFOLDERPRESETS")


def test_run_sharepoint_online_256_plus_chars_strings(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="SC196085_256_CHARS_BUG")


def test_run_sharepoint_online_app_username_password_auth(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="APPUSERNAMEPASSWORDAUTH")


def test_run_sharepoint_online_app_basic_auth(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="APPBASICAUTH")
