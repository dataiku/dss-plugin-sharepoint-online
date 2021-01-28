import logging

from sharepoint_constants import SharePointConstants
from dss_constants import DSSConstants

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint plugin %(levelname)s - %(message)s')


def is_response_empty(response):
    return SharePointConstants.RESULTS_CONTAINER_V2 not in response or SharePointConstants.RESULTS not in response[SharePointConstants.RESULTS_CONTAINER_V2]


def extract_results(response):
    return response[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]


def get_dss_type(sharepoint_type):
    return SharePointConstants.TYPES.get(sharepoint_type, DSSConstants.FALLBACK_TYPE)


def get_sharepoint_type(dss_type):
    return DSSConstants.TYPES.get(dss_type, SharePointConstants.FALLBACK_TYPE)


def column_ids_to_names(column_ids, column_names, sharepoint_row):
    """ Replace the column ID used by SharePoint by their column names for use in DSS"""
    return {column_names[key]: value for key, value in sharepoint_row.items() if key in column_ids}


def is_error(response):
    return _has_error(response) and _has_message(response) and _has_value(response)


def _has_error(response):
    return SharePointConstants.ERROR_CONTAINER in response


def _has_message(response):
    return SharePointConstants.MESSAGE in response[SharePointConstants.ERROR_CONTAINER]


def _has_value(response):
    return SharePointConstants.VALUE in response[SharePointConstants.ERROR_CONTAINER][SharePointConstants.MESSAGE]


def assert_list_title(list_title):
    """ Asserts that the list title does not contain any character forbidden by the list creation API call """
    """ (currently just '?') """

    if "?" in list_title:
        raise ValueError("The list title contains a '?' characters")


class SharePointListWriter(object):

    def __init__(self, config, parent, dataset_schema, dataset_partitioning, partition_id):
        self.parent = parent
        self.config = config
        self.dataset_schema = dataset_schema
        self.dataset_partitioning = dataset_partitioning
        self.partition_id = partition_id
        self.buffer = []
        logger.info('init SharepointListWriter')
        self.columns = dataset_schema[SharePointConstants.COLUMNS]
        self.sharepoint_column_ids = {}

    def write_row(self, row):
        self.buffer.append(row)

    def flush(self):
        logger.info('flush:delete_list "{}"'.format(self.parent.sharepoint_list_title))
        self.parent.client.delete_list(self.parent.sharepoint_list_title)
        logger.info('flush:create_list "{}"'.format(self.parent.sharepoint_list_title))
        created_list = self.parent.client.create_list(self.parent.sharepoint_list_title)
        self.entity_type_name = created_list.get("EntityTypeName")
        self.list_item_entity_type_full_name = created_list.get("ListItemEntityTypeFullName")
        logger.info('New list "{}" created, type {}'.format(self.list_item_entity_type_full_name, self.entity_type_name))
        self.list_id = created_list.get("Id")

        self.parent.get_read_schema()
        self.create_sharepoint_columns()

        logger.info("Starting adding rows")
        for row in self.buffer:
            item = self.build_row_dictionary(row)
            self.parent.client.add_list_item_by_id(self.list_id, self.list_item_entity_type_full_name, item)
        logger.info("All rows added")

    def create_sharepoint_columns(self):
        """ Create the list's columns on SP, retrieve their SP id and map it to their DSS column name """
        logger.info("create_sharepoint_columns")
        for column in self.columns:
            dss_type = column.get(SharePointConstants.TYPE_COLUMN, DSSConstants.FALLBACK_TYPE)
            sharepoint_type = get_sharepoint_type(dss_type)
            dss_column_name = column[SharePointConstants.NAME_COLUMN]
            if dss_column_name not in self.parent.column_ids:
                logger.info("Creating column '{}'".format(dss_column_name))
                response = self.parent.client.create_custom_field_via_id(
                    self.list_id,
                    dss_column_name,
                    field_type=sharepoint_type
                )
                json = response.json()
                self.sharepoint_column_ids[dss_column_name] = \
                    json[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.ENTITY_PROPERTY_NAME]
                self.parent.client.add_column_to_list_default_view(dss_column_name, self.parent.sharepoint_list_title)
            else:
                self.sharepoint_column_ids[dss_column_name] = dss_column_name

    def build_row_dictionary(self, row):
        ret = {}
        for column, structure in zip(row, self.columns):
            ret[self.sharepoint_column_ids[structure[SharePointConstants.NAME_COLUMN]]] = column
        return ret

    def close(self):
        self.flush()
