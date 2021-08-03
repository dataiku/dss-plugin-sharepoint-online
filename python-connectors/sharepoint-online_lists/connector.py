from dataiku.connector import Connector
import logging

from sharepoint_client import SharePointClient
from sharepoint_constants import SharePointConstants
from sharepoint_lists import assert_list_title, get_dss_type
from sharepoint_lists import SharePointListWriter, column_ids_to_names, sharepoint_to_dss_date
from common import parse_query_string_to_dict


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint-online plugin %(levelname)s - %(message)s')


class SharePointListsConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info('SharePoint Online plugin connector v1.0.9b1')
        self.sharepoint_list_title = self.config.get("sharepoint_list_title")
        self.auth_type = config.get('auth_type')
        logger.info('init:sharepoint_list_title={}, auth_type={}'.format(self.sharepoint_list_title, self.auth_type))
        self.column_ids = {}
        self.column_names = {}
        self.column_entity_property_name = {}
        self.columns_to_format = []
        self.dss_column_name = {}
        self.column_sharepoint_type = {}
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
            self.sharepoint_list_view_id = self.get_view_id(self.sharepoint_list_title, self.sharepoint_list_view_title)

    def get_view_id(self, list_title, view_title):
        if not list_title:
            return None
        views = self.client.get_list_views(list_title)
        for view in views:
            if view.get("Title") == view_title:
                return view.get("Id")
        raise ValueError("View '{}' does not exist in list '{}'.".format(view_title, list_title))

    def get_read_schema(self):
        logger.info('get_read_schema')
        sharepoint_columns = self.client.get_list_fields(self.sharepoint_list_title)
        dss_columns = []
        self.column_ids = {}
        self.column_names = {}
        self.column_entity_property_name = {}
        self.columns_to_format = []
        for column in sharepoint_columns:
            logger.info("get_read_schema:{}/{}/{}/{}/{}/{}".format(
                column[SharePointConstants.TITLE_COLUMN],
                column[SharePointConstants.TYPE_AS_STRING],
                column[SharePointConstants.STATIC_NAME],
                column[SharePointConstants.INTERNAL_NAME],
                column[SharePointConstants.ENTITY_PROPERTY_NAME],
                self.is_column_displayable(column)
            ))
            if self.is_column_displayable(column):
                sharepoint_type = get_dss_type(column[SharePointConstants.TYPE_AS_STRING])
                self.column_sharepoint_type[column[SharePointConstants.STATIC_NAME]] = column[SharePointConstants.TYPE_AS_STRING]
                if sharepoint_type is not None:
                    dss_columns.append({
                        SharePointConstants.NAME_COLUMN: column[SharePointConstants.TITLE_COLUMN],
                        SharePointConstants.TYPE_COLUMN: sharepoint_type
                    })
                    self.column_ids[column[SharePointConstants.STATIC_NAME]] = sharepoint_type
                    self.column_names[column[SharePointConstants.STATIC_NAME]] = column[SharePointConstants.TITLE_COLUMN]
                    self.column_entity_property_name[column[SharePointConstants.STATIC_NAME]] = column[SharePointConstants.ENTITY_PROPERTY_NAME]
                    self.dss_column_name[column[SharePointConstants.STATIC_NAME]] = column[SharePointConstants.TITLE_COLUMN]
                    self.dss_column_name[column[SharePointConstants.ENTITY_PROPERTY_NAME]] = column[SharePointConstants.TITLE_COLUMN]
                if sharepoint_type == "date":
                    self.columns_to_format.append((column[SharePointConstants.STATIC_NAME], sharepoint_type))
        logger.info("get_read_schema: Schema updated with {}".format(dss_columns))
        return {
            SharePointConstants.COLUMNS: dss_columns
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

        logger.info('generate_row:dataset_schema={}, dataset_partitioning={}, partition_id={}, records_limit={}'.format(
            dataset_schema, dataset_partitioning, partition_id, records_limit
        ))

        page = {}
        record_count = 0
        is_first_run = True
        is_record_limit = records_limit > 0
        while is_first_run or self.is_not_last_page(page):
            is_first_run = False
            page = self.client.get_list_items(
                self.sharepoint_list_title,
                params=self.get_requests_params(page)
            )
            rows = self.get_page_rows(page)
            for row in rows:
                row = self.format_row(row)
                yield column_ids_to_names(self.dss_column_name, row)
            record_count += len(rows)
            if is_record_limit and record_count >= records_limit:
                break

    @staticmethod
    def is_not_last_page(page):
        return "Row" in page and "NextHref" in page

    def get_requests_params(self, page):
        next_page_query_string = page.get("NextHref", "")
        next_page_requests_params = parse_query_string_to_dict(next_page_query_string)
        if self.sharepoint_list_view_id:
            next_page_requests_params.update(
                {
                    "View": self.sharepoint_list_view_id
                }
            )
        return next_page_requests_params

    @staticmethod
    def get_page_rows(page):
        return page.get("Row", "")

    def format_row(self, row):
        for column_to_format, type_to_process in self.columns_to_format:
            value = row.get(column_to_format)
            if value:
                row[column_to_format] = sharepoint_to_dss_date(value)
        return row

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        assert_list_title(self.sharepoint_list_title)
        return SharePointListWriter(
            self.config,
            self,
            dataset_schema,
            dataset_partitioning,
            partition_id,
            max_workers=self.max_workers,
            batch_size=self.batch_size,
            write_mode=self.write_mode
        )

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
