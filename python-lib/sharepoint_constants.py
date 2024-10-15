class SharePointConstants(object):
    CLEAR_KEY_END = "-----END PRIVATE KEY-----"
    CLEAR_KEY_START = "-----BEGIN PRIVATE KEY-----"
    COLUMNS = 'columns'
    COMMENT_COLUMN = 'comment'
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    DEFAULT_VIEW_ENDPOINT = "DefaultView/ViewFields"
    DEFAULT_WAIT_BEFORE_RETRY = 60
    ENCRYPTED_KEY_END = "-----END ENCRYPTED PRIVATE KEY-----"
    ENCRYPTED_KEY_START = "-----BEGIN ENCRYPTED PRIVATE KEY-----"
    ENTITY_PROPERTY_NAME = 'EntityPropertyName'
    ERROR_CONTAINER = 'error'
    EXPENDABLES_FIELDS = {"Author": "Title", "Editor": "Title"}
    FALLBACK_TYPE = "Text"
    FILE = 0
    FILE_SYSTEM_OBJECT_TYPE = "FileSystemObjectType"
    FILE_UPLOAD_CHUNK_SIZE = 131072000
    FORBIDDEN_PATH_CHARS = ['"', '*', ':', '<', '>', '?', '\\', '|']
    FORM_DIGEST_VALUE = "FormDigestValue"
    GET_CONTEXT_WEB_INFORMATION = "GetContextWebInformation"
    GET_FOLDER_URL_STRUCTURE = "{0}/{1}/_api/Web/GetFolderByServerRelativeUrl('/{1}/{2}{3}')"
    GET_SITE_APP_TOKEN_URL = "https://accounts.accesscontrol.windows.net/{tenant_id}/tokens/OAuth/2"
    HIDDEN_COLUMN = 'Hidden'
    INTERNAL_NAME = 'InternalName'
    LENGTH = 'Length'
    LOOKUP_FIELD = 'LookupField'
    MAX_FILE_SIZE_CONTINUOUS_UPLOAD = 262144000
    MAX_RETRIES = 5
    MESSAGE = 'message'
    MOVE_TO = "MoveTo"
    NAME = 'Name'
    NAME_COLUMN = 'name'
    NEXT_PAGE = '__next'
    READ_ONLY_FIELD = 'ReadOnlyField'
    RENDER_OPTIONS = 5707271
    RESULTS = 'results'
    RESULTS_CONTAINER_V2 = 'd'
    SHAREPOINT_ONLINE_RESSOURCE = "00000003-0000-0ff1-ce00-000000000000"
    STATIC_NAME = 'StaticName'
    TIME_LAST_MODIFIED = 'TimeLastModified'
    TITLE_COLUMN = 'Title'
    TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    TIMEOUT_SEC = 300
    TYPES = {
        "Text": "string",
        "Number": "string",
        "DateTime": "date",
        "Boolean": "string",
        "URL": "object",
        "Location": "object",
        "Computed": None,
        "Attachments": None,
        "Calculated": "string",
        "User": "array",
        "Thumbnail": "object"
    }
    TYPE_AS_STRING = 'TypeAsString'
    TYPE_COLUMN = 'type'
    VALUE = 'value'
    WRITE_MODE_CREATE = "create"
    WAIT_TIME_BEFORE_RETRY_SEC = 2
