class SharePointConstants(object):
    HIDDEN_COLUMN = 'Hidden'
    READ_ONLY_FIELD = 'ReadOnlyField'
    TITLE_COLUMN = 'Title'
    NAME_COLUMN = 'name'
    TYPE_COLUMN = 'type'
    COLUMNS = 'columns'
    TYPE_AS_STRING = 'TypeAsString'
    RESULTS_CONTAINER_V2 = 'd'
    RESULTS = 'results'
    ERROR_CONTAINER = 'error'
    MESSAGE = 'message'
    VALUE = 'value'
    TIME_LAST_MODIFIED = 'TimeLastModified'
    NEXT_PAGE = '__next'
    LENGTH = 'Length'
    NAME = 'Name'
    MOVE_TO = "MoveTo"
    FORM_DIGEST_VALUE = "FormDigestValue"
    TYPES = {
        "Text": "string",
        "Number": "string",
        "DateTime": "date",
        "Boolean": "string",
        "URL": "object",
        "Location": "object",
        "Computed": None,
        "Attachments": None
    }
    TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    GET_FOLDER_URL_STRUCTURE = "{0}/{1}/_api/Web/GetFolderByServerRelativeUrl('/{1}/{2}{3}')"
