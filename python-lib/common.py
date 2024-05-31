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


def update_dict_in_kwargs(kwargs, key_to_update, update):
    if not update:
        return kwargs
    if isinstance(update, dict) and isinstance(kwargs, dict):
        updated_kwargs = {}
        updated_dict = {}
        updated_dict.update(kwargs.get(key_to_update, {}))
        updated_dict.update(update)
        updated_kwargs.update(kwargs)
        updated_kwargs[key_to_update] = updated_dict
        return updated_kwargs
    logger.warning("The update is not a dict")
    return kwargs


def run_oauth_diagnosis(jwt_token):
    censored_token = diagnose_jwt(jwt_token)
    kernel_external_ip = get_kernel_external_ip()
    ip_in_jwt = censored_token.get("ipaddr", "")
    if ip_in_jwt != kernel_external_ip:
        logger.error("The plugin external IP address ({}) does not match the IP allowed in the SSO token ({})".format(
            ip_in_jwt,
            kernel_external_ip
        ))


def diagnose_jwt(jwt_token):
    keys_to_report = ["aud", "exp", "app_displayname", "appid", "ipaddr", "name", "scp", "unique_name", "upn"]
    decoded_token = decode_jwt(jwt_token)
    censored_token = {}
    for key_to_report in keys_to_report:
        censored_token[key_to_report] = decoded_token.get(key_to_report)
    logger.info("Decoded token: {}".format(censored_token))
    return censored_token


def decode_jwt(jwt_token):
    try:
        import base64
        import json
        sub_tokens = jwt_token.split('.')
        if len(sub_tokens)<2:
            logger.error("JWT format is wrong")
            return {}
        token_of_interest = sub_tokens[1]
        padded_token = token_of_interest + "="*divmod(len(token_of_interest),4)[1]
        decoded_token = base64.urlsafe_b64decode(padded_token.encode('utf-8'))
        json_token = json.loads(decoded_token)
        return json_token
    except Exception as error:
        logger.error("Could not decode JWT token ({})".format(error))
    return {}


def get_kernel_external_ip():
    try:
        import requests
        response = requests.get("https://api64.ipify.org?format=json")
        if response.status_code >= 400:
            logger.error("Error {} trying to check kernel's external ip:{}".format(response.status_code, response.content))
        json_response = response.json()
        kernel_external_ip = json_response.get("ip", "")
        return kernel_external_ip
    except Exception as error:
        logger.error("Could not fetch kernel's remote ip ({})".format(error))
    return ""


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
