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


def matched_item(column_ids, column_names, item, column_to_expand=None):
    ret = {}
    for key, value in item.items():
        if key in column_ids:
            name = column_names[key]
            ret[name] = value
    return ret


def expand_matched_item(column_ids, column_names, item, column_to_expand=None):
    ret = {}
    column_to_expand = {} if column_to_expand is None else column_to_expand
    for key, value in item.items():
        if key in column_ids:
            name = column_names[key]
            key_to_return = column_to_expand.get(key)
            if key_to_return:
                ret[name] = value.get(key_to_return)
            else:
                ret[name] = value
    return ret


def is_error(response):
    return _has_error(response) and _has_message(response) and _has_value(response)


def _has_error(response):
    return SharePointConstants.ERROR_CONTAINER in response


def _has_message(response):
    return SharePointConstants.MESSAGE in response[SharePointConstants.ERROR_CONTAINER]


def _has_value(response):
    return SharePointConstants.VALUE in response[SharePointConstants.ERROR_CONTAINER][SharePointConstants.MESSAGE]


def assert_list_title(list_title):
    if not list_title.isalnum():
        raise ValueError("The list title contains non alphanumerical characters")


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
        logger.info('write_row')
        self.buffer.append(row)

    def flush(self):
        logger.info('flush:delete_list "{}"'.format(self.parent.sharepoint_list_title.lower()))
        self.parent.client.delete_list(self.parent.sharepoint_list_title.lower())
        logger.info('flush:create_list "{}"'.format(self.parent.sharepoint_list_title.lower()))
        self.parent.client.create_list(self.parent.sharepoint_list_title.lower())

        self.parent.get_read_schema()
        self.create_sharepoint_columns()

        for row in self.buffer:
            item = self.build_row_dictionary(row)
            self.parent.client.add_list_item(self.parent.sharepoint_list_title, item)

    def create_sharepoint_columns(self):
        """ Create the list's columns on SP, retrieve their SP id and map it to their DSS column name """
        for column in self.columns:
            dss_type = column.get(SharePointConstants.TYPE_COLUMN, DSSConstants.FALLBACK_TYPE)
            sharepoint_type = get_sharepoint_type(dss_type)
            dss_column_name = column[SharePointConstants.NAME_COLUMN]
            if dss_column_name not in self.parent.column_ids:
                response = self.parent.client.create_custom_field(
                    self.parent.sharepoint_list_title,
                    dss_column_name,
                    field_type=sharepoint_type
                )
                json = response.json()
                self.sharepoint_column_ids[dss_column_name] = \
                    json[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.ENTITY_PROPERTY_NAME]
            else:
                self.sharepoint_column_ids[dss_column_name] = dss_column_name

    def build_row_dictionary(self, row):
        ret = {}
        for column, structure in zip(row, self.columns):
            ret[self.sharepoint_column_ids[structure[SharePointConstants.NAME_COLUMN]]] = column
        return ret

    def close(self):
        self.flush()
