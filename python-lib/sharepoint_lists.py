import logging

from sharepoint_constants import SharePointConstants

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint plugin %(levelname)s - %(message)s')


def is_response_empty(response):
    return SharePointConstants.RESULTS_CONTAINER_V2 not in response or SharePointConstants.RESULTS not in response[SharePointConstants.RESULTS_CONTAINER_V2]


def result_loop(response):
    return response[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]


def get_dss_types(sharepoint_type):
    if sharepoint_type in SharePointConstants.TYPES:
        return SharePointConstants.TYPES[sharepoint_type]
    else:
        return "string"


def matched_item(columns, item):
    ret = {}
    for key, value in item.items():
        if key in columns:
            ret[key] = value
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
        raise Exception("The list title contains non alphanumerical characters")


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

    def write_row(self, row):
        logger.info('write_row:row={}'.format(row))
        self.buffer.append(row)

    def flush(self):
        self.parent.client.delete_list(self.parent.sharepoint_list_title.lower())
        self.parent.client.create_list(self.parent.sharepoint_list_title.lower())

        self.parent.get_read_schema()
        for column in self.columns:
            if column[SharePointConstants.NAME_COLUMN] not in self.parent.columns:
                self.parent.client.create_custom_field(self.parent.sharepoint_list_title, column[SharePointConstants.NAME_COLUMN])

        for row in self.buffer:
            item = self.build_row_dictionary(row)
            self.parent.client.add_list_item(self.parent.sharepoint_list_title, item)

    def build_row_dictionary(self, row):
        ret = {}
        for column, structure in zip(row, self.columns):
            ret[structure[SharePointConstants.NAME_COLUMN].replace(" ", "_x0020_")] = column
        return ret

    def close(self):
        self.flush()
