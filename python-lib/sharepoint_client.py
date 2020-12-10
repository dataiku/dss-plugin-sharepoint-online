import os
import requests
import sharepy
import urllib.parse
import logging

from sharepoint_constants import SharePointConstants
from dss_constants import DSSConstants
from common import is_email_address


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint-online plugin %(levelname)s - %(message)s')


class SharePointClientError(ValueError):
    pass


class SharePointClient():

    def __init__(self, config):
        self.sharepoint_root = None
        self.sharepoint_tenant = None
        self.sharepoint_url = None
        self.sharepoint_origin = None
        if config.get('auth_type') == DSSConstants.AUTH_OAUTH:
            login_details = config.get('sharepoint_oauth')
            self.assert_login_details(DSSConstants.OAUTH_DETAILS, login_details)
            self.setup_login_details(login_details)
            self.setup_sharepoint_online_url(login_details)
            self.sharepoint_access_token = login_details['sharepoint_oauth']
            self.session = SharePointSession(
                None,
                None,
                self.sharepoint_tenant,
                self.sharepoint_site,
                sharepoint_access_token=self.sharepoint_access_token
            )
        elif config.get('auth_type') == DSSConstants.AUTH_LOGIN:
            login_details = config.get('sharepoint_sharepy')
            self.assert_login_details(DSSConstants.LOGIN_DETAILS, login_details)
            self.setup_login_details(login_details)
            username = login_details['sharepoint_username']
            password = login_details['sharepoint_password']
            self.assert_email_address(username)
            self.setup_sharepoint_online_url(login_details)
            self.session = sharepy.connect(self.sharepoint_url, username=username, password=password)
        elif config.get('auth_type') == DSSConstants.AUTH_SITE_APP:
            login_details = config.get('site_app_permissions')
            self.assert_login_details(DSSConstants.SITE_APP_DETAILS, login_details)
            self.setup_sharepoint_online_url(login_details)
            self.setup_login_details(login_details)
            self.tenant_id = login_details.get("tenant_id")
            self.client_secret = login_details.get("client_secret")
            self.client_id = login_details.get("client_id")
            self.sharepoint_tenant = login_details.get('sharepoint_tenant')
            self.sharepoint_access_token = self.get_site_app_access_token()
            self.session = SharePointSession(
                None,
                None,
                self.sharepoint_tenant,
                self.sharepoint_site,
                sharepoint_access_token=self.sharepoint_access_token
            )
        else:
            raise SharePointClientError("The type of authentication is not selected")
        self.sharepoint_list_title = config.get("sharepoint_list_title")

    def assert_email_address(self, username):
        if not is_email_address(username):
            raise SharePointClientError("Sharepoint-Online's username should be an email address")

    def setup_login_details(self, login_details):
        self.sharepoint_site = login_details['sharepoint_site']
        if 'sharepoint_root' in login_details:
            self.sharepoint_root = login_details['sharepoint_root'].strip("/")
        else:
            self.sharepoint_root = "Shared Documents"

    def setup_sharepoint_online_url(self, login_details):
        self.sharepoint_tenant = login_details['sharepoint_tenant']
        self.sharepoint_url = self.sharepoint_tenant + ".sharepoint.com"
        self.sharepoint_origin = "https://" + self.sharepoint_url

    def get_folders(self, path):
        response = self.session.get(self.get_sharepoint_item_url(path) + "/Folders")
        self.assert_response_ok(response)
        return response.json()

    def get_files(self, path):
        response = self.session.get(self.get_sharepoint_item_url(path) + "/Files")
        self.assert_response_ok(response)
        return response.json()

    def get_sharepoint_item_url(self, path):
        if path == '/':
            path = ""
        return SharePointConstants.GET_FOLDER_URL_STRUCTURE.format(
            self.sharepoint_origin,
            self.sharepoint_site,
            self.sharepoint_root,
            path
        )

    def get_file_content(self, full_path):
        response = self.session.get(
            self.get_file_content_url(full_path)
        )
        self.assert_response_ok(response, no_json=True)
        return response

    def write_file_content(self, full_path, data):
        full_path_parent, file_name = os.path.split(full_path)
        headers = {
            "Content-Length": "{}".format(len(data))
        }
        response = self.session.post(
            self.get_file_add_url(
                full_path_parent,
                file_name
            ),
            headers=headers,
            data=data
        )
        self.assert_response_ok(response)
        return response

    def create_folder(self, full_path):
        response = self.session.post(
            self.get_add_folder_url(full_path)
        )
        self.assert_response_ok(response)
        return response

    def move_file(self, full_from_path, full_to_path):
        get_move_url = self.get_move_url(
            full_from_path,
            full_to_path
        )
        response = self.session.post(get_move_url)
        self.assert_response_ok(response)
        return response.json()

    def delete_file(self, full_path):
        headers = {
            "X-HTTP-Method": "DELETE"
        }
        response = self.session.post(
            self.get_file_url(full_path),
            headers=headers
        )
        self.assert_response_ok(response)

    def delete_folder(self, full_path):
        headers = {
            "X-HTTP-Method": "DELETE"
        }
        response = self.session.post(
            self.get_folder_url(full_path),
            headers=headers
        )
        self.assert_response_ok(response)

    def get_list_fields(self, list_title):
        response = self.session.get(
            self.get_list_fields_url(list_title)
        )
        self.assert_response_ok(response)
        return response.json()

    def get_list_all_items(self, list_title, column_to_expand=None):
        items = self.get_list_items(list_title, column_to_expand)
        buffer = items
        while SharePointConstants.RESULTS_CONTAINER_V2 in items and SharePointConstants.NEXT_PAGE in items[SharePointConstants.RESULTS_CONTAINER_V2]:
            items = self.session.get(items[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.NEXT_PAGE]).json()
            buffer[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS].extend(
                items[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]
            )
        return buffer

    def get_list_items(self, list_title, columns_to_expand=None):
        if columns_to_expand is not None:
            select = []
            expand = []
            for column_to_expand in columns_to_expand:
                if columns_to_expand.get(column_to_expand) is None:
                    select.append("{}".format(column_to_expand))
                else:
                    select.append("{}/{}".format(column_to_expand, columns_to_expand.get(column_to_expand)))
                    expand.append(column_to_expand)
            params = {
                "$select": ",".join(select),
                "$expand": ",".join(expand)
            }
        else:
            params = None
        response = self.session.get(
            self.get_list_items_url(list_title),
            params=params
        )
        self.assert_response_ok(response)
        return response.json()

    def create_list(self, list_name):
        headers = {
            "content-type": DSSConstants.APPLICATION_JSON,
            'Accept': 'application/json; odata=nometadata'
        }
        data = {
            '__metadata': {
                'type': 'SP.List'
            },
            'AllowContentTypes': True,
            'BaseTemplate': 100,
            'ContentTypesEnabled': True,
            'Title': list_name
        }
        response = self.session.post(
            self.get_lists_url(),
            headers=headers,
            json=data
        )
        self.assert_response_ok(response)
        return response

    def delete_list(self, list_name):
        headers = {
            "X-HTTP-Method": "DELETE",
            "IF-MATCH": "*"
        }
        response = self.session.post(
            self.get_lists_by_title_url(list_name),
            headers=headers
        )
        return response

    def create_custom_field(self, list_title, field_title, field_type=None):
        field_type = SharePointConstants.FALLBACK_TYPE if field_type is None else field_type
        body = {
            'parameters': {
                '__metadata': {'type': 'SP.XmlSchemaFieldCreationInformation'},
                'SchemaXml': "<Field DisplayName='{0}' Format='Dropdown' MaxLength='255' Type='{1}'></Field>".format(self.amp_escape(field_title), field_type)
            }
        }
        headers = {
            "content-type": DSSConstants.APPLICATION_JSON
        }
        response = self.session.post(
            self.get_lists_add_field_url(list_title),
            headers=headers,
            json=body
        )
        self.assert_response_ok(response)
        return response

    @staticmethod
    def amp_escape(to_format):
        to_convert = {'"': '&quot;', "'": "&apos;", "<": "&lt;", ">": "&gt;", "&": "&amp;", "/": "&#x2F;"}
        for key in to_convert:
            to_format = to_format.replace(key, to_convert[key])
        return to_format

    def add_list_item(self, list_title, item):
        item["__metadata"] = {
            "type": "SP.Data.{}ListItem".format(list_title.capitalize().replace(" ", "_x0020_"))
        }
        headers = {
            "Content-Type": DSSConstants.APPLICATION_JSON
        }
        response = self.session.post(
            self.get_list_items_url(list_title),
            json=item,
            headers=headers
        )
        self.assert_response_ok(response)
        return response

    def get_base_url(self):
        return "{}/{}/_api/Web".format(
            self.sharepoint_origin, self.sharepoint_site
        )

    def get_lists_url(self):
        return self.get_base_url() + "/lists"

    def get_lists_by_title_url(self, list_title):
        return self.get_lists_url() + "/GetByTitle('{}')".format(urllib.parse.quote(list_title))

    def get_list_items_url(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/Items"

    def get_list_fields_url(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/fields"

    def get_lists_add_field_url(self, list_title):
        return self.get_base_url() + "/GetList(@a1)/Fields/CreateFieldAsXml?@a1='/{}/Lists/{}'".format(
            self.sharepoint_site,
            list_title
        )

    def get_folder_url(self, full_path):
        return self.get_base_url() + "/GetFolderByServerRelativeUrl({})".format(
            self.get_site_path(full_path)
        )

    def get_file_url(self, full_path):
        return self.get_base_url() + "/GetFileByServerRelativeUrl({})".format(
            self.get_site_path(full_path)
        )

    def get_file_content_url(self, full_path):
        return self.get_file_url(full_path) + "/$value"

    def get_move_url(self, from_path, to_path):
        return self.get_file_url(from_path) + "/moveto(newurl={},flags=1)".format(
            self.get_site_path(to_path)
        )

    def get_site_path(self, full_path):
        return "'/{}/{}{}'".format(self.sharepoint_site, self.sharepoint_root, full_path)

    def get_add_folder_url(self, full_path):
        return self.get_base_url() + "/Folders/add('{}{}')".format(
            self.sharepoint_root,
            full_path
        )

    def get_file_add_url(self, full_path, file_name):
        return self.get_folder_url(full_path) + "/Files/add(url='{}',overwrite=true)".format(file_name)

    @staticmethod
    def assert_login_details(required_keys, login_details):
        if login_details is None or login_details == {}:
            raise SharePointClientError("Login details are empty")
        for key in required_keys:
            if key not in login_details.keys():
                raise SharePointClientError(required_keys[key])

    def assert_response_ok(self, response, no_json=False):
        status_code = response.status_code
        if status_code >= 400:
            enriched_error_message = self.get_enriched_error_message(response)
            if enriched_error_message is not None:
                raise SharePointClientError("Error: {}".format(enriched_error_message))
        if status_code == 400:
            raise SharePointClientError("{}".format(response.text))
        if status_code == 404:
            raise SharePointClientError("Not found. Please check tenant, site type or site name.")
        if status_code == 403:
            raise SharePointClientError("Forbidden. Please check your account credentials.")
        if not no_json:
            self.assert_no_error_in_json(response)

    @staticmethod
    def get_enriched_error_message(response):
        try:
            json_response = response.json()
            enriched_error_message = json_response.get("error").get("message").get("value")
            return enriched_error_message
        except SharePointClientError as error:
            logger.info("Error trying to extract error message :{}".format(error))
            return None

    @staticmethod
    def assert_no_error_in_json(response):
        if len(response.content) == 0:
            raise SharePointClientError("Empty response from SharePoint. Please check user credentials.")
        json_response = response.json()
        if "error" in json_response:
            if "message" in json_response["error"] and "value" in json_response["error"]["message"]:
                raise SharePointClientError("Error: {}".format(json_response["error"]["message"]["value"]))
            else:
                raise SharePointClientError("Error: {}".format(json_response))

    def get_site_app_access_token(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": "{client_id}@{tenant_id}".format(client_id=self.client_id, tenant_id=self.tenant_id),
            "client_secret": self.client_secret,
            "resource": "{resource}/{sharepoint_tenant}.sharepoint.com@{tenant_id}".format(
                resource=SharePointConstants.SHAREPOINT_ONLINE_RESSOURCE,
                sharepoint_tenant=self.sharepoint_tenant,
                tenant_id=self.tenant_id
            )
        }
        response = requests.post(
            SharePointConstants.GET_SITE_APP_TOKEN_URL.format(tenant_id=self.tenant_id),
            headers=headers,
            data=data
        )
        self.assert_response_ok(response)
        json_response = response.json()
        return json_response.get("access_token")


class SharePointSession():

    def __init__(self, sharepoint_user_name, sharepoint_password, sharepoint_tenant, sharepoint_site, sharepoint_access_token=None):
        self.sharepoint_tenant = sharepoint_tenant
        self.sharepoint_site = sharepoint_site
        self.sharepoint_access_token = sharepoint_access_token

    def get(self, url, headers=None, params=None):
        headers = {} if headers is None else headers
        headers["accept"] = DSSConstants.APPLICATION_JSON
        headers["Authorization"] = self.get_authorization_bearer()
        return requests.get(url, headers=headers, params=params)

    def post(self, url, headers=None, json=None, data=None):
        headers = {} if headers is None else headers
        headers["accept"] = DSSConstants.APPLICATION_JSON
        headers["Authorization"] = self.get_authorization_bearer()
        return requests.post(url, headers=headers, json=json, data=data)

    def get_authorization_bearer(self):
        return "Bearer {}".format(self.sharepoint_access_token)
