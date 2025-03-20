from dataiku.llm.agent_tools import BaseAgentTool
from sharepoint_client import SharePointClient
from safe_logger import SafeLogger
from dss_constants import DSSConstants

logger = SafeLogger("sharepoint-online plugin", DSSConstants.SECRET_PARAMETERS_KEYS)


class WriteToSharePointListTool(BaseAgentTool):

    def set_config(self, config, plugin_config):
        logger.info('SharePoint Online plugin list write tool v{}'.format(DSSConstants.PLUGIN_VERSION))
        self.sharepoint_list_title = config.get("sharepoint_list_title")
        self.auth_type = config.get('auth_type')
        logger.info('init:sharepoint_list_title={}, auth_type={}'.format(self.sharepoint_list_title, self.auth_type))
        self.expand_lookup = config.get("expand_lookup", False)
        self.metadata_to_retrieve = config.get("metadata_to_retrieve", [])
        advanced_parameters = config.get("advanced_parameters", False)
        self.write_mode = "create"
        if not advanced_parameters:
            self.max_workers = 1  # no multithread per default
            self.batch_size = 100
            self.sharepoint_list_view_title = ""
        else:
            self.max_workers = config.get("max_workers", 1)
            self.batch_size = config.get("batch_size", 100)
            self.sharepoint_list_view_title = config.get("sharepoint_list_view_title", "")
        logger.info("init:advanced_parameters={}, max_workers={}, batch_size={}".format(advanced_parameters, self.max_workers, self.batch_size))
        self.metadata_to_retrieve.append("Title")
        self.display_metadata = len(self.metadata_to_retrieve) > 0
        self.client = SharePointClient(config)
        self.sharepoint_list_view_id = None
        if self.sharepoint_list_view_title:
            self.sharepoint_list_view_id = self.client.get_view_id(self.sharepoint_list_title, self.sharepoint_list_view_title)
        self.sharepoint_column_of_interest = config.get("sharepoint_column_of_interest")
        self.output_schema = None

    def get_descriptor(self, tool):
        schema = self.client.get_read_schema(display_metadata=self.display_metadata, metadata_to_retrieve=self.metadata_to_retrieve, add_description=True)
        columns = schema.get("columns", [])
        properties = {}
        required = []
        output_columns = []
        for column in columns:
            column_description = column.get("description")
            if column_description:
                properties[column.get("name")] = {
                    "type": column.get("type"),
                    "name": column.get("name")
                }
                required.append(column.get("name"))  # For now...
                output_columns.append({
                    "type": column.get("type"),
                    "name": column.get("name")
                })
        self.output_schema = {
            "columns": output_columns
        }
        return {
            "description": "This tool can be used to access lists on SharePoint Online. The input to this tool is a dictionary containing the new issue summary and description, e.g. '{'summary':'new issue summary', 'description':'new issue description'}'",
            "inputSchema" : {
                "$id": "https://dataiku.com/agents/tools/search/input",
                "title": "Add an item to a SharePoint Online list tool",
                "type": "object",
                "properties" : properties
            }
        }

    def invoke(self, input, trace):
        sharepoint_writer = self.client.get_writer(
            self.output_schema,
            None, None, 1, 1,
            "append"
        )
        row = input.get("input", {})
        sharepoint_writer.write_row_dict(row)
        sharepoint_writer.close()
        
        return { 
            "output" : 'The record was added'
        }
