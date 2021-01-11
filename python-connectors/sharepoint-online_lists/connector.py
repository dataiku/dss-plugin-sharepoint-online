from dataiku.connector import Connector
import logging

from sharepoint_client import SharePointClient

from sharepoint_constants import SharePointConstants
from sharepoint_lists import assert_list_title, is_response_empty, extract_results, get_dss_type, is_error
from sharepoint_lists import SharePointListWriter, matched_item, expand_matched_item

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
        self.expand_lookup = config.get("expand_lookup", False)
        self.column_to_expand = {}
        self.metadata_to_retrieve = config.get("metadata_to_retrieve", [])
        self.metadata_to_retrieve.append("Title")
        self.display_metadata = len(self.metadata_to_retrieve) > 0
        self.client = SharePointClient(config)

    def get_read_schema(self):
        logger.info('get_read_schema')
        response = self.client.get_list_fields(self.sharepoint_list_title)
        if is_response_empty(response) or len(response[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]) < 1:
            return None
        columns = []
        self.column_ids = {}
        self.column_names = {}
        has_expandable_columns = False
        for column in extract_results(response):
            if self.is_column_displayable(column):
                sharepoint_type = get_dss_type(column[SharePointConstants.TYPE_AS_STRING])
                if sharepoint_type is not None:
                    columns.append({
                        SharePointConstants.NAME_COLUMN: column[SharePointConstants.TITLE_COLUMN],
                        SharePointConstants.TYPE_COLUMN: sharepoint_type
                    })
                    self.column_ids[column[SharePointConstants.ENTITY_PROPERTY_NAME]] = sharepoint_type
                    self.column_names[column[SharePointConstants.ENTITY_PROPERTY_NAME]] = column[SharePointConstants.TITLE_COLUMN]
                if self.expand_lookup and (self.is_column_expendable(column) or self.must_column_display_be_forced(column)):
                    if column[SharePointConstants.TYPE_AS_STRING] == "Lookup" and self.is_column_expendable(column):
                        self.column_to_expand.update({column[SharePointConstants.STATIC_NAME]: column[SharePointConstants.LOOKUP_FIELD]})
                        has_expandable_columns = True
                    else:
                        self.column_to_expand.update({
                            column[SharePointConstants.STATIC_NAME]: self.get_column_lookup_field(column[SharePointConstants.STATIC_NAME])
                        })
                if self.display_metadata and (column['StaticName'] in self.metadata_to_retrieve):
                    self.column_to_expand.update({
                        column[SharePointConstants.STATIC_NAME]: self.get_column_lookup_field(column[SharePointConstants.STATIC_NAME])
                    })
        if not has_expandable_columns:
            self.column_to_expand = {}
        return {
            SharePointConstants.COLUMNS: columns
        }

    @staticmethod
    def get_column_lookup_field(column_static_name):
        if column_static_name in SharePointConstants.EXPENDABLES_FIELDS:
            return SharePointConstants.EXPENDABLES_FIELDS.get(column_static_name)
        return None

    def is_column_displayable(self, column):
        if self.display_metadata and (column['StaticName'] in self.metadata_to_retrieve):
            return True
        return (not column[SharePointConstants.HIDDEN_COLUMN])

    @staticmethod
    def must_column_display_be_forced(column):
        return column[SharePointConstants.TYPE_AS_STRING] in ["Calculated"]

    @staticmethod
    def is_column_expendable(column):
        return (not column[SharePointConstants.HIDDEN_COLUMN]) \
            and (not column[SharePointConstants.READ_ONLY_FIELD])

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        if self.column_ids == {}:
            self.get_read_schema()

        logger.info('generate_row:dataset_schema={}, dataset_partitioning={}, partition_id={}'.format(
            dataset_schema, dataset_partitioning, partition_id
        ))

        response = self.client.get_list_all_items(self.sharepoint_list_title, self.column_to_expand)
        if is_response_empty(response):
            if is_error(response):
                raise Exception("Error: {}".format(response[SharePointConstants.ERROR_CONTAINER][SharePointConstants.MESSAGE][SharePointConstants.VALUE]))
            else:
                raise Exception("Error when interacting with SharePoint")
        if self.column_to_expand == {}:
            for item in extract_results(response):
                yield matched_item(self.column_ids, self.column_names, item)
        else:
            for item in extract_results(response):
                yield expand_matched_item(self.column_ids, self.column_names, item, column_to_expand=self.column_to_expand)

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
