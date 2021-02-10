import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def __init__(self, config, parent, dataset_schema, dataset_partitioning, partition_id, max_workers=5, batch_size=100):
        self.parent = parent
        self.config = config
        self.dataset_schema = dataset_schema
        self.dataset_partitioning = dataset_partitioning
        self.partition_id = partition_id
        self.buffer = []
        logger.info('init SharepointListWriter with {} workers and batch size of {}'.format(max_workers, batch_size))
        self.columns = dataset_schema[SharePointConstants.COLUMNS]
        self.sharepoint_column_ids = {}

        logger.info('flush:delete_list "{}"'.format(self.parent.sharepoint_list_title))
        self.parent.client.delete_list(self.parent.sharepoint_list_title)
        logger.info('flush:create_list "{}"'.format(self.parent.sharepoint_list_title))
        created_list = self.parent.client.create_list(self.parent.sharepoint_list_title)
        self.entity_type_name = created_list.get("EntityTypeName")
        self.list_item_entity_type_full_name = created_list.get("ListItemEntityTypeFullName")
        logger.info('New list "{}" created, type {}'.format(self.list_item_entity_type_full_name, self.entity_type_name))
        self.list_id = created_list.get("Id")
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.working_batch_size = max_workers * batch_size
        self.parent.get_read_schema()
        self.create_sharepoint_columns()

    def write_row(self, row):
        self.buffer.append(row)
        if len(self.buffer) >= self.working_batch_size:
            self.flush()
            self.buffer = []

    def flush(self):
        if self.max_workers > 1:
            self.upload_rows_multithreaded()
        else:
            self.upload_rows()

    def upload_rows_multithreaded(self):
        logger.info("Starting multithreaded rows adding")
        index = 0
        offset = 0
        kwargs = []
        futures = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as thread_pool_executor:
            for row in self.buffer:
                item = self.build_row_dictionary(row)
                kwargs.append(self.parent.client.get_add_list_item_kwargs(self.list_id, self.list_item_entity_type_full_name, item))
                index = index + 1
                if index >= self.batch_size:
                    futures.append(thread_pool_executor.submit(self.parent.client.process_batch, kwargs[offset:offset + index]))
                    offset += index
                    index = 0
            if offset < len(kwargs):
                futures.append(thread_pool_executor.submit(self.parent.client.process_batch, kwargs[offset:len(kwargs)]))
            for future in as_completed(futures):
                future_result = future.result()  # Necessary to raise any possible future's exception
        logger.info("{} items written".format(offset+index))

    def upload_rows(self):
        logger.info("Starting adding rows")
        kwargs = []
        for row in self.buffer:
            item = self.build_row_dictionary(row)
            kwargs.append(self.parent.client.get_add_list_item_kwargs(self.list_id, self.list_item_entity_type_full_name, item))
        self.parent.client.process_batch(kwargs)
        logger.info("{} items written".format(len(kwargs)))

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
