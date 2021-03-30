import re


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

def get_date_time_format_from_regional_settings(regional_settings):
    date_patterns = {
        0: ["%m", "%d", "%Y"],
        1: ["%d", "%m", "%Y"],
        2: ["%Y", "%m", "%d"]
    }
    time_patterns = {
        False: ["%I","%M %p"],
        True: ["%H","%M"]
    }
    date_format = regional_settings.get("DateFormat")
    if date_format is None:
        #return "%Y-%m-%dT%H:%M:%S.%fZ"
        return None
    datetime_pattern = ""
    datetime_pattern = regional_settings.get("DateSeparator", "/").join(date_patterns.get(regional_settings.get("DateFormat", 0)))
    datetime_pattern += " "
    datetime_pattern += regional_settings.get("TimeSeparator", ":").join(time_patterns.get(regional_settings.get("Time24", False)))
    return datetime_pattern
