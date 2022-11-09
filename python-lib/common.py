import re
import datetime
import time
try:
    import urlparse
except:
    import urllib.parse as urlparse
from safe_logger import SafeLogger
from sharepoint_constants import SharePointConstants
from dss_constants import DSSConstants

logger = SafeLogger("sharepoint-online plugin", DSSConstants.SECRET_PARAMETERS_KEYS)


def get_rel_path(path):
    if len(path) > 0 and path[0] == '/':
        path = path[1:]
    return path


def get_lnt_path(path):
    if len(path) == 0 or path == '/':
        return '/'
    elts = path.split('/')
    elts = [e for e in elts if len(e) > 0]
    return '/' + '/'.join(elts)


def is_email_address(address):
    return bool(re.match("^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$", address))


def get_value_from_path(dictionary, path, default_reply=None):
    ret = dictionary
    for key in path:
        if key in ret:
            ret = ret.get(key)
        else:
            return default_reply
    return ret


def get_value_from_paths(dictionary, paths, default_reply=None):
    ret = None
    for path in paths:
        ret = get_value_from_path(dictionary, path, default_reply)
        if ret:
            return ret
    return default_reply


def parse_query_string_to_dict(query_string):
    return dict(
        urlparse.parse_qsl(
            list(
                urlparse.urlparse(query_string)
            )[4]
        )
    )


def parse_url(tenant_name):
    url_tokens = urlparse.urlparse(tenant_name.strip('/'))
    return url_tokens.scheme, url_tokens.netloc, url_tokens.path


def is_request_performed(response):
    if response is None:
        return False
    if response.status_code in [429, 503]:
        logger.warning("Error {}, headers = {}".format(response.status_code, response.headers))
        if response.status_code == 503:
            # SP 503 errors tend to generate html error message, so we dump it in the logs
            logger.warning("dumping content: {}".format(response.content))
        seconds_before_retry = decode_retry_after_header(response)
        logger.warning("Sleeping for {} seconds".format(seconds_before_retry))
        time.sleep(seconds_before_retry)
        return False
    return True


def decode_retry_after_header(response):
    seconds_before_retry = SharePointConstants.DEFAULT_WAIT_BEFORE_RETRY
    raw_header_value = response.headers.get("Retry-After", str(SharePointConstants.DEFAULT_WAIT_BEFORE_RETRY))
    if raw_header_value.isdigit():
        seconds_before_retry = int(raw_header_value)
    else:
        # Date format, "Wed, 21 Oct 2015 07:28:00 GMT"
        try:
            datetime_now = datetime.datetime.now()
            datetime_header = datetime.datetime.strptime(raw_header_value, '%a, %d %b %Y %H:%M:%S GMT')
            if datetime_header.timestamp() > datetime_now.timestamp():
                # target date in the future
                seconds_before_retry = (datetime_header - datetime_now).seconds
        except Exception as err:
            logger.error("decode_retry_after_header error {}".format(err))
            seconds_before_retry = SharePointConstants.DEFAULT_WAIT_BEFORE_RETRY
    return seconds_before_retry


def is_empty_path(path):
    if not path:
        return True
    if path.strip("/") == "":
        return True
    return False


def merge_paths(first_path, second_path):
    path_1 = first_path or ""
    path_2 = second_path or ""
    path_1 = path_1.strip("/")
    path_2 = path_2.strip("/")
    joined_path = "/".join([path_1, path_2])
    return joined_path.strip("/")
    

class ItemsLimit():
    def __init__(self, records_limit=-1):
        self.has_no_limit = (records_limit == -1)
        self.records_limit = records_limit
        self.counter = 0

    def is_reached(self, number_of_new_records=None):
        if self.has_no_limit:
            return False
        self.counter += number_of_new_records or 1
        return self.counter > self.records_limit

    def add_record(self):
        self.counter += 1
