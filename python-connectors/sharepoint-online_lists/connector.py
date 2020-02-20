from six.moves import xrange
from dataiku.connector import Connector
import sharepy, logging

from sharepoint_client import SharePointClient, SharePointSession

from sharepoint_client import *
from dss_constants import *
from sharepoint_lists import *

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint-online plugin %(levelname)s - %(message)s')

class SharePointListsConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        self.sharepoint_list_title = self.config.get("sharepoint_list_title")
        assert_list_title(self.sharepoint_list_title)
        self.auth_type = config.get('auth_type')
        logger.info('init:sharepoint_list_title={}, auth_type={}'.format(self.sharepoint_list_title, self.auth_type))
        self.columns={}
        self.client = SharePointClient(config)

    def get_read_schema(self):
        logger.info('get_read_schema ')
        response = self.client.get_list_fields(self.sharepoint_list_title)
        if is_response_empty(response) or len(response[SHAREPOINT_RESULTS_CONTAINER_V2][SHAREPOINT_RESULTS]) < 1:
            return None
        columns = []
        self.columns={}
        for column in result_loop(response):
            if column[SHAREPOINT_HIDDEN_COLUMN] == False and column[SHAREPOINT_READ_ONLY_FIELD]==False:
                sharepoint_type = get_dss_types(column[SHAREPOINT_TYPE_AS_STRING])
                if sharepoint_type is not None:
                    columns.append({
                        SHAREPOINT_NAME_COLUMN : column[SHAREPOINT_TITLE_COLUMN],
                        SHAREPOINT_TYPE_COLUMN : get_dss_types(column[SHAREPOINT_TYPE_AS_STRING])
                    })
                    self.columns[column[SHAREPOINT_TITLE_COLUMN]] = sharepoint_type
        return {
            SHAREPOINT_COLUMNS : columns
        }

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                            partition_id=None, records_limit = -1):
        if self.columns=={}:
            self.get_read_schema()

        logger.info('generate_row:dataset_schema={}, dataset_partitioning={}, partition_id={}'.format(
            dataset_schema, dataset_partitioning, partition_id
        ))

        response = self.client.get_list_all_items(self.sharepoint_list_title)
        if is_response_empty(response):
            if is_error(response):
                raise Exception ("Error: {}".format(response[SHAREPOINT_ERROR_CONTAINER][SHAREPOINT_MESSAGE][SHAREPOINT_VALUE]))
            else:
                raise Exception("Error when interacting with SharePoint")

        for item in result_loop(response):
            yield matched_item(self.columns, item)

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                         partition_id=None):
        return SharePointListWriter(self.config, self, dataset_schema, dataset_partitioning, partition_id)


    def get_partitioning(self):
        logger.info('get_partitioning')
        raise Exception("Unimplemented")


    def list_partitions(self, partitioning):
        logger.info('list_partitions:partitioning={}'.format(partitioning))
        return []


    def partition_exists(self, partitioning, partition_id):
        logger.info('partition_exists:partitioning={}, partition_id={}'.format(partitioning, partition_id))
        raise Exception("unimplemented")


    def get_records_count(self, partitioning=None, partition_id=None):
        logger.info('get_records_count:partitioning={}, partition_id={}'.format(partitioning, partition_id))
        raise Exception("unimplemented")
