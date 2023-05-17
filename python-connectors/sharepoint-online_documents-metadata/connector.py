from sharepoint_client import SharePointClient
from common import ItemsLimit
from dataiku.connector import Connector
from safe_logger import SafeLogger
from dss_constants import DSSConstants


logger = SafeLogger("sharepoint-online plugin", DSSConstants.SECRET_PARAMETERS_KEYS)


class SharePointDocumentsMetadataConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info('SharePoint Online plugin metadata dataset v{}'.format(DSSConstants.PLUGIN_VERSION))
        self.client = SharePointClient(config)

    def get_read_schema(self):
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = ItemsLimit(records_limit)
        for row in self.client.get_documents_medatada():
            yield row
            if limit.is_reached():
                break

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        raise NotImplementedError

    def get_partitioning(self):
        raise NotImplementedError

    def list_partitions(self, partitioning):
        return []

    def partition_exists(self, partitioning, partition_id):
        raise NotImplementedError

    def get_records_count(self, partitioning=None, partition_id=None):
        raise NotImplementedError


class CustomDatasetWriter(object):
    def __init__(self):
        pass

    def write_row(self, row):
        raise NotImplementedError

    def close(self):
        pass
