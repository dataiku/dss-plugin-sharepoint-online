class DSSConstants(object):
    APPLICATION_JSON = "application/json;odata=verbose"
    APPLICATION_JSON_NOMETADATA = "application/json; odata=nometadata"
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
    LOGIN_DETAILS = {
        "sharepoint_tenant" : "The tenant name is missing",
        "sharepoint_site" : "The site name is missing",
        "sharepoint_username" : "The account's username is missing",
        "sharepoint_password" : "The account's password is missing"
    }
    OAUTH_DETAILS = {
        "sharepoint_tenant" : "The tenant name is missing",
        "sharepoint_site" : "The site name is missing",
        "sharepoint_oauth" : "The access token is missing"
    }
