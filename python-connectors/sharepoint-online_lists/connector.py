from dataiku.connector import Connector
import logging

from sharepoint_client import SharePointClient

from sharepoint_constants import SharePointConstants
from sharepoint_lists import assert_list_title, is_response_empty, extract_results, get_dss_types, is_error, matched_item
from sharepoint_lists import SharePointListWriter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint-online plugin %(levelname)s - %(message)s')


class SharePointListsConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        self.sharepoint_list_title = self.config.get("sharepoint_list_title")
        self.auth_type = config.get('auth_type')
        logger.info('init:sharepoint_list_title={}, auth_type={}'.format(self.sharepoint_list_title, self.auth_type))
        self.column_ids = {}
        self.column_names = {}
        self.client = SharePointClient(config)

    def get_read_schema(self):
        logger.info('get_read_schema')
        response = self.client.get_list_fields(self.sharepoint_list_title)
        if is_response_empty(response) or len(response[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]) < 1:
            return None
        columns = []
        self.column_ids = {}
        self.column_names = {}
        for column in extract_results(response):
            if (not column[SharePointConstants.HIDDEN_COLUMN]) and (not column[SharePointConstants.READ_ONLY_FIELD]):
                sharepoint_type = get_dss_types(column[SharePointConstants.TYPE_AS_STRING])
                if sharepoint_type is not None:
                    columns.append({
                        SharePointConstants.NAME_COLUMN: column[SharePointConstants.TITLE_COLUMN],
                        SharePointConstants.TYPE_COLUMN: sharepoint_type
                    })
                    self.column_ids[column[SharePointConstants.ENTITY_PROPERTY_NAME]] = sharepoint_type
                    self.column_names[column[SharePointConstants.ENTITY_PROPERTY_NAME]] = column[SharePointConstants.TITLE_COLUMN]
        return {
            SharePointConstants.COLUMNS: columns
        }

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        if self.column_ids == {}:
            self.get_read_schema()

        logger.info('generate_row:dataset_schema={}, dataset_partitioning={}, partition_id={}'.format(
            dataset_schema, dataset_partitioning, partition_id
        ))

        response = self.client.get_list_all_items(self.sharepoint_list_title)
        if is_response_empty(response):
            if is_error(response):
                raise Exception("Error: {}".format(response[SharePointConstants.ERROR_CONTAINER][SharePointConstants.MESSAGE][SharePointConstants.VALUE]))
            else:
                raise Exception("Error when interacting with SharePoint")

        for item in extract_results(response):
            yield matched_item(self.column_ids, self.column_names, item)

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        assert_list_title(self.sharepoint_list_title)
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
