import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from sharepoint_constants import SharePointConstants
from dss_constants import DSSConstants
from safe_logger import SafeLogger


logger = SafeLogger("sharepoint-online plugin", DSSConstants.SECRET_PARAMETERS_KEYS)


def is_response_empty(response):
    return SharePointConstants.RESULTS_CONTAINER_V2 not in response or SharePointConstants.RESULTS not in response[SharePointConstants.RESULTS_CONTAINER_V2]


def extract_results(response):
    return response[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]


def get_dss_type(sharepoint_type):
    return SharePointConstants.TYPES.get(sharepoint_type, DSSConstants.FALLBACK_TYPE)


def get_sharepoint_type(dss_type):
    return DSSConstants.TYPES.get(dss_type, SharePointConstants.FALLBACK_TYPE)


def column_ids_to_names(convert_table, sharepoint_row):
    """ Replace the column ID used by SharePoint by their column names for use in DSS"""
    return {convert_table[key]: value for key, value in sharepoint_row.items() if key in convert_table}


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


def dss_to_sharepoint_date(date):
    return format_date(date, DSSConstants.DATE_FORMAT, SharePointConstants.DATE_FORMAT)


def sharepoint_to_dss_date(date):
    sharepoint_formats = ["%m/%d/%Y", "%m/%d/%Y %I:%M %p"]
    for sharepoint_format in sharepoint_formats:
        try:
            dss_date = format_date(date, sharepoint_format, DSSConstants.DATE_FORMAT)
        except ValueError as err:
            continue
        return dss_date
    return date


def format_date(date, from_format, to_format):
    if date:
        return datetime.datetime.strftime(
            datetime.datetime.strptime(date, from_format),
            to_format
        )
    else:
        return date


class SharePointListWriter(object):

    def __init__(self, config, parent, dataset_schema, dataset_partitioning, partition_id, max_workers=5, batch_size=100, write_mode="create"):
        self.parent = parent
        self.config = config
        self.dataset_schema = dataset_schema
        self.dataset_partitioning = dataset_partitioning
        self.partition_id = partition_id
        self.buffer = []
        logger.info('init SharepointListWriter with {} workers and batch size of {}'.format(max_workers, batch_size))
        self.columns = dataset_schema[SharePointConstants.COLUMNS]
        self.sharepoint_column_ids = {}
        self.sharepoint_existing_column_names = {}
        self.sharepoint_existing_column_entity_property_names = {}
        self.web_name = self.parent.sharepoint_list_title

        if write_mode == SharePointConstants.WRITE_MODE_CREATE:
            logger.info('flush:recycle_list "{}"'.format(self.parent.sharepoint_list_title))
            self.parent.recycle_list(self.parent.sharepoint_list_title)
            logger.info('flush:create_list "{}"'.format(self.parent.sharepoint_list_title))
            created_list = self.parent.create_list(self.parent.sharepoint_list_title)
            self.entity_type_name = created_list.get("EntityTypeName")
            self.list_item_entity_type_full_name = created_list.get("ListItemEntityTypeFullName")
            logger.info('New list "{}" created, type {}'.format(self.list_item_entity_type_full_name, self.entity_type_name))
            self.list_id = created_list.get("Id")
            self.web_name = self.parent.get_web_name(created_list) or self.parent.sharepoint_list_title
        else:
            list_metadata = self.parent.get_list_metadata(self.parent.sharepoint_list_title)
            self.web_name = self.parent.get_web_name(list_metadata)
            self.entity_type_name = list_metadata.get("EntityTypeName")
            self.list_item_entity_type_full_name = list_metadata.get("ListItemEntityTypeFullName")
            self.list_id = list_metadata.get("Id")
            logger.info('Existing list "{}" created, type {}'.format(self.list_item_entity_type_full_name, self.entity_type_name))
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.working_batch_size = max_workers * batch_size
        self.parent.get_read_schema()

        if write_mode != SharePointConstants.WRITE_MODE_CREATE:
            for column_id in self.parent.column_names:
                self.sharepoint_column_ids[column_id] = self.parent.column_names[column_id]
                self.sharepoint_existing_column_names[self.parent.column_names[column_id]] = column_id
                self.sharepoint_existing_column_entity_property_names[self.parent.column_names[column_id]] = self.parent.column_entity_property_name[column_id]
        self.create_sharepoint_columns()

    def write_row(self, row):
        self.buffer.append(row)
        if len(self.buffer) >= self.working_batch_size:
            self.flush()
            self.buffer = []

    def write_row_dict(self, row_dict):
        row = []
        for element in row_dict:
            row.append(str(row_dict.get(element)))
        self.write_row(row)

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
                kwargs.append(self.parent.get_add_list_item_kwargs(self.web_name, item))
                index = index + 1
                if index >= self.batch_size:
                    futures.append(thread_pool_executor.submit(self.parent.process_batch, kwargs[offset:offset + index]))
                    offset += index
                    index = 0
            if offset < len(kwargs):
                futures.append(thread_pool_executor.submit(self.parent.process_batch, kwargs[offset:len(kwargs)]))
            for future in as_completed(futures):
                future_result = future.result()  # Necessary to raise any possible future's exception
        logger.info("{} items written".format(offset+index))

    def upload_rows(self):
        logger.info("Starting adding items")
        kwargs = []
        for row in self.buffer:
            item = self.build_row_dictionary(row)
            kwargs.append(self.parent.get_add_list_item_kwargs(self.web_name, item))
        self.parent.process_batch(kwargs)
        logger.info("{} items written".format(len(kwargs)))

    def create_sharepoint_columns(self):
        """ Create the list's columns on SP, retrieve their SP id and map it to their DSS column name """
        logger.info("create_sharepoint_columns")
        for column in self.columns:
            dss_type = column.get(SharePointConstants.TYPE_COLUMN, DSSConstants.FALLBACK_TYPE)
            sharepoint_type = get_sharepoint_type(dss_type)
            dss_column_name = column[SharePointConstants.NAME_COLUMN]
            existing_sharepoint_type = self.parent.column_sharepoint_type.get(dss_column_name)
            if existing_sharepoint_type:
                sharepoint_type = existing_sharepoint_type

            if dss_column_name not in self.parent.column_ids and dss_column_name not in self.sharepoint_existing_column_names:
                logger.info("Creating column '{}' with type {}".format(dss_column_name, sharepoint_type))
                response = self.parent.create_custom_field_via_id(
                    self.list_id,
                    dss_column_name,
                    field_type=sharepoint_type
                )
                json = response.json()
                self.sharepoint_column_ids[dss_column_name] = \
                    json[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.STATIC_NAME]
                self.parent.add_column_to_list_default_view(dss_column_name, self.parent.sharepoint_list_title)
            elif dss_column_name in self.sharepoint_existing_column_names:
                self.sharepoint_column_ids[dss_column_name] = self.sharepoint_existing_column_entity_property_names[dss_column_name]
            else:
                self.sharepoint_column_ids[dss_column_name] = dss_column_name

    def build_row_dictionary(self, row):
        ret = {}
        for column, structure in zip(row, self.columns):
            key_to_use = self.sharepoint_existing_column_names.get(
                structure[SharePointConstants.NAME_COLUMN],
                self.sharepoint_column_ids[structure[SharePointConstants.NAME_COLUMN]]
            )
            if column and structure.get("type") == "date":
                ret[key_to_use] = dss_to_sharepoint_date(column)
            else:
                ret[key_to_use] = column
        return ret

    def close(self):
        self.flush()
