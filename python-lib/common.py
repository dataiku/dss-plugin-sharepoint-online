import re
try:
    import urlparse
except:
    import urllib.parse as urlparse


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
