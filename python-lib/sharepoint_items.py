import os.path

from sharepoint_constants import SharePointConstants
from datetime import datetime
from common import get_lnt_path, get_rel_path


def loop_sharepoint_items(items):
    if SharePointConstants.RESULTS_CONTAINER_V2 not in items or SharePointConstants.RESULTS not in items[SharePointConstants.RESULTS_CONTAINER_V2]:
        yield
    for item in items[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]:
        yield item


def extract_item_from(item_name, items):
    for item in loop_sharepoint_items(items):
        if SharePointConstants.NAME in item and item[SharePointConstants.NAME] == item_name:
            return item
    return None


def has_sharepoint_items(items):
    if SharePointConstants.RESULTS_CONTAINER_V2 not in items or SharePointConstants.RESULTS not in items[SharePointConstants.RESULTS_CONTAINER_V2]:
        return False
    if len(items[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]) > 0:
        return True
    else:
        return False


def get_last_modified(item):
    if SharePointConstants.TIME_LAST_MODIFIED in item:
        return int(format_date(item[SharePointConstants.TIME_LAST_MODIFIED]))


def format_date(date):
    if date is not None:
        utc_time = datetime.strptime(date, SharePointConstants.TIME_FORMAT)
        epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
        return int(epoch_time) * 1000
    else:
        return None


def get_size(item):
    if SharePointConstants.LENGTH in item:
        return int(item[SharePointConstants.LENGTH])
    else:
        return 0


def get_name(item):
    if SharePointConstants.NAME in item:
        return item[SharePointConstants.NAME]
    else:
        return None


def assert_path_is_not_root(path):
    if path is None:
        raise ValueError("Cannot delete root path")
    path = get_rel_path(path)
    if path == "" or path == "/":
        raise ValueError("Cannot delete root path")


def create_path(client, file_full_path):
    full_path, filename = os.path.split(file_full_path)
    tokens = full_path.split("/")
    path = ""
    for token in tokens:
        path = get_lnt_path(path + "/" + token)
        client.create_folder(path)
