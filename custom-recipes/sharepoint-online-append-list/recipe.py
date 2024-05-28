import dataiku
import pandas
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
from safe_logger import SafeLogger
from dss_constants import DSSConstants
from sharepoint_client import SharePointClient


logger = SafeLogger("sharepoint-online plugin", DSSConstants.SECRET_PARAMETERS_KEYS)
logger.info('SharePoint Online append to list recipe v{}'.format(DSSConstants.PLUGIN_VERSION))


def convert_date_format(json_row):
    #  Convert pandas timestamps to iso
    for key in json_row:
        value = json_row.get(key)
        if pandas.isna(value):
            json_row[key] = ""
        elif type(value) == pandas.Timestamp:
            json_row[key] = str(value.strftime(DSSConstants.DATE_FORMAT))
    return json_row


input_dataset_names = get_input_names_for_role('input_dataset')
input_dataset = dataiku.Dataset(input_dataset_names[0])
input_dataframe = input_dataset.get_dataframe()
input_schema = input_dataset.read_schema()
output_dataset_names = get_output_names_for_role('api_output')
output_dataset = dataiku.Dataset(output_dataset_names[0])
output_dataset.write_schema(input_schema)
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

sharepoint_list_title = config.get("sharepoint_list_title")
auth_type = config.get('auth_type')
logger.info('init:sharepoint_list_title={}, auth_type={}'.format(sharepoint_list_title, auth_type))
column_ids = {}
column_names = {}
column_entity_property_name = {}
columns_to_format = []
dss_column_name = {}
column_sharepoint_type = {}
expand_lookup = config.get("expand_lookup", False)
metadata_to_retrieve = config.get("metadata_to_retrieve", [])
advanced_parameters = config.get("advanced_parameters", False)
write_mode = config.get("write_mode", "append")
columns_to_update = config.get("columns_to_update", [])
if columns_to_update and "ID" not in columns_to_update:
    columns_to_update.append("ID")

if not advanced_parameters:
    max_workers = 1  # no multithread per default
    batch_size = 100
    sharepoint_list_view_title = ""
else:
    max_workers = config.get("max_workers", 1)
    batch_size = config.get("batch_size", 100)
    sharepoint_list_view_title = config.get("sharepoint_list_view_title", "")
logger.info("init:advanced_parameters={}, max_workers={}, batch_size={}".format(advanced_parameters, max_workers, batch_size))
metadata_to_retrieve.append("Title")
display_metadata = len(metadata_to_retrieve) > 0
client = SharePointClient(config)

sharepoint_writer = client.get_writer({"columns": input_schema}, None, None, max_workers,
                                      batch_size, write_mode, columns_to_update)


with output_dataset.get_writer() as writer:
    for index, input_parameters_row in input_dataframe.iterrows():
        straighten_json_row = sharepoint_writer.pandas_row_to_json(input_parameters_row)
        sharepoint_writer.write_row_dict(straighten_json_row)
        writer.write_row_dict(sharepoint_writer.fix_dates_for_pandas_output(input_parameters_row))
    sharepoint_writer.close()
