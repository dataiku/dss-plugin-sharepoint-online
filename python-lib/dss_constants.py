class DSSConstants(object):
    APPLICATION_JSON = "application/json;odata=verbose"
    APPLICATION_JSON_NOMETADATA = "application/json;odata=nometadata"
    PATH = 'path'
    FULL_PATH = 'fullPath'
    EXISTS = 'exists'
    DIRECTORY = 'directory'
    IS_DIRECTORY = 'isDirectory'
    SIZE = 'size'
    LAST_MODIFIED = 'lastModified'
    CHILDREN = 'children'
    AUTH_OAUTH = "oauth"
    AUTH_LOGIN = "login"
    AUTH_SITE_APP = "site-app-permissions"
    LOGIN_DETAILS = {
        "sharepoint_tenant": "The tenant name is missing",
        "sharepoint_site": "The site name is missing",
        "sharepoint_username": "The account's username is missing",
        "sharepoint_password": "The account's password is missing"
    }
    OAUTH_DETAILS = {
        "sharepoint_tenant": "The tenant name is missing",
        "sharepoint_site": "The site name is missing",
        "sharepoint_oauth": "The access token is missing"
    }
    SITE_APP_DETAILS = {
        "sharepoint_tenant": "The tenant name is missing",
        "sharepoint_site": "The site name is missing",
        "tenant_id": "The tenant ID is missing. See documentation on how to obtain this information",
        "client_id": "The client ID is missing",
        "client_secret": "The client secret is missing"
    }
    TYPES = {
        "string": "Text",
        "map": "Note",
        "array": "Note",
        "object": "Note",
        "double": "Number",
        "float": "Number",
        "int": "Integer",
        "bigint": "Integer",
        "smallint": "Integer",
        "tinyint": "Integer",
        "date": "DateTime"
    }
    FALLBACK_TYPE = "string"
