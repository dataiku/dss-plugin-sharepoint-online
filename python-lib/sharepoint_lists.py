import logging

from sharepoint_constants import *

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint plugin %(levelname)s - %(message)s')

def is_response_empty(response):
    return SHAREPOINT_RESULTS_CONTAINER_V2 not in response or SHAREPOINT_RESULTS not in response[SHAREPOINT_RESULTS_CONTAINER_V2]

def result_loop(response):
    return response[SHAREPOINT_RESULTS_CONTAINER_V2][SHAREPOINT_RESULTS]

def get_dss_types(sharepoint_type):
    if sharepoint_type in SHAREPOINT_TYPES:
        return SHAREPOINT_TYPES[sharepoint_type]
    else:
        return "string"

def matched_item(columns, item):
    ret = {}
    for key, value in item.items():
        if key in columns:
            ret[key] = value
    return ret

def is_error(response):
    return SHAREPOINT_ERROR_CONTAINER in response and SHAREPOINT_MESSAGE in response[SHAREPOINT_ERROR_CONTAINER] and SHAREPOINT_VALUE in response[SHAREPOINT_ERROR_CONTAINER][SHAREPOINT_MESSAGE]


class SharePointListWriter(object):

    def __init__(self, config, parent, dataset_schema, dataset_partitioning, partition_id):
        self.parent = parent
        self.config = config
        self.dataset_schema = dataset_schema
        self.dataset_partitioning = dataset_partitioning
        self.partition_id = partition_id
        self.buffer = []
        logger.info('init SharepointListWriter')
        self.columns = dataset_schema[SHAREPOINT_COLUMNS]

    def write_row(self, row):
        logger.info('write_row:row={}'.format(row))
        self.buffer.append(row)

    def flush(self):
        self.parent.client.delete_list(self.parent.sharepoint_list_title.lower())
        self.parent.client.create_list(self.parent.sharepoint_list_title.lower())

        self.parent.get_read_schema()
        for column in self.columns:
            if column[SHAREPOINT_NAME_COLUMN] not in self.parent.columns:
                self.parent.client.create_custom_field(self.parent.sharepoint_list_title, column[SHAREPOINT_NAME_COLUMN])

        for row in self.buffer:
            item = self.build_row_dictionary(row)
            self.parent.client.add_list_item(self.parent.sharepoint_list_title, item)

    def build_row_dictionary(self, row):
        ret = {}
        for column, structure in zip(row, self.columns):
            ret[structure[SHAREPOINT_NAME_COLUMN].replace(" ", "_x0020_")] = column
        return ret

    def close(self):
        self.flush()
