import os
import requests
import sharepy
import urllib.parse
import logging
import uuid
import time
import json
import re

from xml.etree.ElementTree import Element, tostring
from xml.dom import minidom
from robust_session import RobustSession
from sharepoint_constants import SharePointConstants
from dss_constants import DSSConstants
from common import is_email_address, get_value_from_path, parse_url, get_value_from_paths, is_request_performed
from safe_logger import SafeLogger


logger = SafeLogger("sharepoint-online plugin", ["Authorization", "sharepoint_username", "sharepoint_password", "client_secret"])


class SharePointClientError(ValueError):
    pass


class SharePointClient():

    def __init__(self, config):
        self.sharepoint_root = None
        self.sharepoint_url = None
        self.sharepoint_origin = None
        attempt_session_reset_on_403 = config.get("advanced_parameters", False) and config.get("attempt_session_reset_on_403", False)
        self.session = RobustSession(status_codes_to_retry=[429], attempt_session_reset_on_403=attempt_session_reset_on_403)
        self.number_dumped_logs = 0
        self.username_for_namespace_diag = None
        if config.get('auth_type') == DSSConstants.AUTH_OAUTH:
            logger.info("SharePointClient:sharepoint_oauth")
            login_details = config.get('sharepoint_oauth')
            self.assert_login_details(DSSConstants.OAUTH_DETAILS, login_details)
            self.setup_login_details(login_details)
            self.apply_paths_overwrite(config)
            self.setup_sharepoint_online_url(login_details)
            self.sharepoint_access_token = login_details['sharepoint_oauth']
            self.session.update_settings(session=SharePointSession(
                    None,
                    None,
                    self.sharepoint_url,
                    self.sharepoint_site,
                    sharepoint_access_token=self.sharepoint_access_token
                ),
                max_retries=SharePointConstants.MAX_RETRIES,
                base_retry_timer_sec=SharePointConstants.WAIT_TIME_BEFORE_RETRY_SEC
            )
        elif config.get('auth_type') == DSSConstants.AUTH_LOGIN:
            logger.info("SharePointClient:sharepoint_sharepy")
            login_details = config.get('sharepoint_sharepy')
            self.assert_login_details(DSSConstants.LOGIN_DETAILS, login_details)
            self.setup_login_details(login_details)
            username = login_details['sharepoint_username']
            password = login_details['sharepoint_password']
            self.assert_email_address(username)
            self.username_for_namespace_diag = username  # stored for possible 403 diagnostic
            self.setup_sharepoint_online_url(login_details)
            # Throttling is harsher for username/password authenticated users
            # https://www.netwoven.com/2021/01/27/how-to-avoid-throttling-or-getting-blocked-in-sharepoint-online-using-sharepoint-app-authentication/
            self.session.update_settings(max_retries=5, base_retry_timer_sec=120)  # Yeah !
            # If several python workers are on the job, opening the session in itslef could be an issue
            self.session.connect(
                connection_library=sharepy,
                site=self.sharepoint_url,
                username=username,
                password=password
            )
        elif config.get('auth_type') == DSSConstants.AUTH_SITE_APP:
            logger.info("SharePointClient:site_app_permissions")
            login_details = config.get('site_app_permissions')
            self.assert_login_details(DSSConstants.SITE_APP_DETAILS, login_details)
            self.setup_sharepoint_online_url(login_details)
            self.setup_login_details(login_details)
            self.apply_paths_overwrite(config)
            self.tenant_id = login_details.get("tenant_id")
            self.client_secret = login_details.get("client_secret")
            self.client_id = login_details.get("client_id")
            self.sharepoint_access_token = self.get_site_app_access_token()
            self.session.update_settings(session=SharePointSession(
                    None,
                    None,
                    self.sharepoint_url,
                    self.sharepoint_site,
                    sharepoint_access_token=self.sharepoint_access_token
                ),
                max_retries=SharePointConstants.MAX_RETRIES,
                base_retry_timer_sec=SharePointConstants.WAIT_TIME_BEFORE_RETRY_SEC
            )
        else:
            raise SharePointClientError("The type of authentication is not selected")
        self.sharepoint_list_title = config.get("sharepoint_list_title")
        try:
            from urllib3.connectionpool import log
            log.addFilter(SuppressFilter())
        except Exception as err:
            logging.warning("Error while adding filter to urllib3.connectionpool logs: {}".format(err))

    def assert_email_address(self, username):
        if not is_email_address(username):
            raise SharePointClientError("Sharepoint-Online's username should be an email address")

    def setup_login_details(self, login_details):
        self.sharepoint_site = login_details.get('sharepoint_site', "").strip("/")
        logger.info("SharePointClient:sharepoint_site={}".format(self.sharepoint_site))
        if 'sharepoint_root' in login_details:
            self.sharepoint_root = login_details['sharepoint_root'].strip("/")
        else:
            self.sharepoint_root = "Shared Documents"
        logger.info("SharePointClient:sharepoint_root={}".format(self.sharepoint_root))

    def apply_paths_overwrite(self, config):
        advanced_parameters = config.get("advanced_parameters", False)
        sharepoint_root_overwrite = config.get("sharepoint_root_overwrite", "").strip("/")
        sharepoint_site_overwrite = config.get("sharepoint_site_overwrite", "").strip("/")
        if advanced_parameters and sharepoint_root_overwrite:
            self.sharepoint_root = sharepoint_root_overwrite
        if advanced_parameters and sharepoint_site_overwrite:
            self.sharepoint_site = sharepoint_site_overwrite

    def setup_sharepoint_online_url(self, login_details):
        scheme, domain, tenant = parse_url(login_details['sharepoint_tenant'])
        if scheme:
            self.sharepoint_url = domain
            self.sharepoint_origin = scheme + "://" + domain
        elif tenant.endswith(".sharepoint.com"):
            self.sharepoint_url = tenant
            self.sharepoint_origin = "https://" + tenant
        else:
            self.sharepoint_url = tenant + ".sharepoint.com"
            self.sharepoint_origin = "https://" + self.sharepoint_url
        logger.info("SharePointClient:sharepoint_tenant={}, url={}, origin={}".format(
                login_details['sharepoint_tenant'],
                self.sharepoint_url,
                self.sharepoint_origin
            )
        )

    def get_folders(self, path):
        response = self.session.get(self.get_folder_url(path) + "/Folders")
        self.assert_response_ok(response, calling_method="get_folders")
        return response.json()

    def get_files(self, path):
        response = self.session.get(self.get_folder_url(path) + "/Files")
        self.assert_response_ok(response, calling_method="get_files")
        return response.json()

    def get_item_fields(self, path):
        response = self.session.get(self.get_folder_url(path) + "/ListItemAllFields")
        self.assert_response_ok(response, calling_method="get_item_fields")
        return response.json()

    def get_start_upload_url(self, path, upload_id):
        return self.get_file_url(path) + "/startupload(uploadId=guid'{}')".format(upload_id)

    def get_continue_upload_url(self, path, upload_id, file_offset):
        return self.get_file_url(path) + "/continueupload(uploadId=guid'{}',fileOffset={})".format(upload_id, file_offset)

    def get_finish_upload_url(self, path, upload_id, file_offset):
        return self.get_file_url(path) + "/finishupload(uploadId=guid'{}',fileOffset={})".format(upload_id, file_offset)

    def is_file(self, path):
        item_fields = self.get_item_fields(path)
        file_system_object_type = item_fields.get(SharePointConstants.RESULTS_CONTAINER_V2, {}).get(SharePointConstants.FILE_SYSTEM_OBJECT_TYPE)
        return (file_system_object_type == SharePointConstants.FILE)

    def get_file_content(self, full_path):
        response = self.session.get(
            self.get_file_content_url(full_path)
        )
        self.assert_response_ok(response, no_json=True, calling_method="get_file_content")
        return response

    def write_file_content(self, full_path, data):
        self.file_size = len(data)
        if self.file_size < SharePointConstants.MAX_FILE_SIZE_CONTINUOUS_UPLOAD:
            # below 262MB, the file can be uploaded in one go
            self.write_full_file_content(full_path, data)
        else:
            # Start by creating an empty file. Thanks, MS doc, not.
            self.write_full_file_content(full_path, [])
            self.write_chunked_file_content(full_path, data)

    def write_full_file_content(self, full_path, data):
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
        self.assert_response_ok(response, calling_method="write_file_content")
        return response

    def write_chunked_file_content(self, full_path, data):
        is_initial_chunk = True
        is_last_chunk = False
        chunk_size = SharePointConstants.FILE_UPLOAD_CHUNK_SIZE
        save_upload_offset = 0
        upload_id = self.get_random_guid()
        while save_upload_offset < self.file_size:
            next_save_upload_offset = save_upload_offset + chunk_size
            if next_save_upload_offset >= self.file_size:
                is_last_chunk = True
                next_save_upload_offset = self.file_size
            if is_initial_chunk:
                is_initial_chunk = False
                logger.info("write_chunked_file_content:start_upload")
                url = self.get_start_upload_url(full_path, upload_id)
            elif is_last_chunk:
                logger.info("write_chunked_file_content:finish_upload")
                url = self.get_finish_upload_url(full_path, upload_id, save_upload_offset)
            else:
                logger.info("write_chunked_file_content:continue_upload")
                url = self.get_continue_upload_url(full_path, upload_id, save_upload_offset)
            logger.info("write_chunked_file_content from {} to {}".format(save_upload_offset, next_save_upload_offset))
            response = self.session.post(
                url,
                data=data[save_upload_offset:next_save_upload_offset]
            )
            save_upload_offset = next_save_upload_offset
            self.assert_response_ok(response, calling_method="write_chunked_file_content")
        return response

    def create_folder(self, full_path):
        response = self.session.post(
            self.get_add_folder_url(full_path)
        )
        self.assert_response_ok(response, calling_method="create_folder")
        return response

    def move_file(self, full_from_path, full_to_path):
        get_move_url = self.get_move_url(
            full_from_path,
            full_to_path
        )
        response = self.session.post(get_move_url)
        self.assert_response_ok(response, calling_method="move_file")
        return response.json()

    def check_in_file(self, full_path):
        logger.info("Checking in {}.".format(full_path))
        file_check_in_url = self.get_file_check_in_url(full_path)
        self.session.post(file_check_in_url)
        return

    def recycle_file(self, full_path):
        recycle_file_url = self.get_recycle_file_url(full_path)
        response = self.session.post(recycle_file_url)
        self.assert_response_ok(response, calling_method="recycle_file")

    def recycle_folder(self, full_path):
        recycle_folder_url = self.get_recycle_folder_url(full_path)
        response = self.session.post(recycle_folder_url)
        self.assert_response_ok(response, calling_method="recycle_folder")

    def get_list_fields(self, list_title):
        list_fields_url = self.get_list_fields_url(list_title)
        response = self.session.get(
            list_fields_url
        )
        self.assert_response_ok(response, calling_method="get_list_fields")
        json_response = response.json()
        if self.is_response_empty(json_response):
            return None
        return self.extract_results(json_response)

    @staticmethod
    def is_response_empty(response):
        return SharePointConstants.RESULTS_CONTAINER_V2 not in response or SharePointConstants.RESULTS not in response[SharePointConstants.RESULTS_CONTAINER_V2]

    @staticmethod
    def extract_results(response):
        return response[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]

    def get_list_items(self, list_title, params=None):
        params = params or {}
        data = {
            "parameters": {
                "__metadata": {
                    "type": "SP.RenderListDataParameters"
                },
                "RenderOptions": SharePointConstants.RENDER_OPTIONS,
                "AllowMultipleValueFilterForTaxonomyFields": True,
                "AddRequiredFields": True
            }
        }
        headers = DSSConstants.JSON_HEADERS
        response = self.session.post(
            self.get_list_data_as_stream(list_title),
            params=params,
            headers=headers,
            json=data
        )
        self.assert_response_ok(response, calling_method="get_list_items")
        return response.json().get("ListData", {})

    def create_list(self, list_name):
        headers = DSSConstants.JSON_HEADERS
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
        self.assert_response_ok(response, calling_method="create_list")
        json = response.json()
        return json.get(SharePointConstants.RESULTS_CONTAINER_V2, {})

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

    def recycle_list(self, list_name):
        headers = DSSConstants.JSON_HEADERS
        response = self.session.post(
            self.get_lists_by_title_url(list_name)+"/recycle()",
            headers=headers
        )
        return response

    def get_list_metadata(self, list_name):
        headers = DSSConstants.JSON_HEADERS
        response = self.session.get(
            self.get_lists_by_title_url(list_name),
            headers=headers
        )
        self.assert_response_ok(response, calling_method="get_list_default_view")
        json_response = response.json()
        return json_response.get(SharePointConstants.RESULTS_CONTAINER_V2, {})

    def get_web_name(self, created_list):
        root_folder_url = get_value_from_path(created_list, ['RootFolder', '__deferred', 'uri'])
        headers = DSSConstants.JSON_HEADERS
        response = self.session.get(
            root_folder_url,
            headers=headers
        )
        json_response = response.json()
        return get_value_from_path(json_response, [SharePointConstants.RESULTS_CONTAINER_V2, "Name"])

    def create_custom_field_via_id(self, list_id, field_title, field_type=None):
        field_type = SharePointConstants.FALLBACK_TYPE if field_type is None else field_type
        schema_xml = self.get_schema_xml(field_title, field_type)
        body = {
            'parameters': {
                '__metadata': {'type': 'SP.XmlSchemaFieldCreationInformation'},
                'SchemaXml': schema_xml
            }
        }
        headers = DSSConstants.JSON_HEADERS
        guid_lists_add_field_url = self.get_guid_lists_add_field_url(list_id)
        response = self.session.post(
            guid_lists_add_field_url,
            headers=headers,
            json=body
        )
        self.assert_response_ok(response, calling_method="create_custom_field_via_id")
        return response

    def get_list_default_view(self, list_name):
        list_default_view_url = self.get_list_default_view_url(list_name)
        response = self.session.get(
            list_default_view_url
        )
        if response.status_code == 404:
            return []
        self.assert_response_ok(response, calling_method="get_list_default_view")
        json_response = response.json()
        return json_response.get(SharePointConstants.RESULTS_CONTAINER_V2, {"Items": {"results": []}}).get("Items", {"results": []}).get("results", [])

    def add_column_to_list_default_view(self, column_name, list_name):
        escaped_column_name = self.escape_path(column_name)
        list_default_view_url = os.path.join(
            self.get_list_default_view_url(list_name),
            "addviewfield('{}')".format(urllib.parse.quote(escaped_column_name))
        )
        response = self.session.post(
            list_default_view_url
        )
        return response

    @staticmethod
    def get_schema_xml(encoded_field_title, field_type):
        field = Element('Field')
        field.set('encoding', 'UTF-8')
        field.set('DisplayName', encoded_field_title)
        field.set('Format', 'Dropdown')
        field.set('MaxLength', '255')
        field.set('Type', field_type)
        rough_string = tostring(field, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml()

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
        self.assert_response_ok(response, calling_method="add_list_item")
        return response

    def add_list_item_by_id(self, list_id, list_item_full_name, item):
        item["__metadata"] = {
            "type": "{}".format(list_item_full_name)
        }
        headers = {
            "Content-Type": DSSConstants.APPLICATION_JSON
        }
        list_items_url = self.get_list_items_url_by_id(list_id)

        response = self.session.post(
            list_items_url,
            json=item,
            headers=headers
        )
        self.assert_response_ok(response, calling_method="add_list_item_by_id")
        return response

    def get_add_list_item_kwargs(self, list_title, item):
        headers = DSSConstants.JSON_HEADERS

        list_items_url = self.get_list_add_item_using_path_url(list_title)
        item_structure = self.get_item_structure(list_title, item)

        kwargs = {
            "verb": "post",
            "url": list_items_url,
            "json": item_structure,
            "headers": headers
        }

        return kwargs

    def get_item_structure(self, list_title, item):
        list_item_create_info = self.get_list_item_create_info(list_title)
        form_values = []
        for field_name in item:
            if item[field_name] is not None and item[field_name] != "":
                #  Some columns (Title) can't be field with None or ""
                form_values.append(self.get_form_value(field_name, item[field_name]))
        form_values.append(self.get_form_value("ContentType", "Item"))
        return {
            "listItemCreateInfo": list_item_create_info,
            "formValues": form_values,
            "bNewDocumentUpdate": False,
            "checkInComment": None
        }

    @staticmethod
    def get_form_value(field_name, field_value):
        return {
            "FieldName": field_name,
            "FieldValue": field_value,
            "HasException": False,
            "ErrorMessage": None
        }

    def get_list_item_create_info(self, list_title):
        return {
            "__metadata": {
                "type": "SP.ListItemCreationInformationUsingPath"
            },
            "FolderPath": {
                "__metadata": {
                    "type": "SP.ResourcePath"
                },
                "DecodedUrl": "/{}/Lists/{}".format(self.sharepoint_site, list_title)
            }
        }

    def process_batch(self, kwargs_array):
        batch_id = self.get_random_guid()
        change_set_id = self.get_random_guid()

        headers = {
            "Content-Type": "multipart/mixed;boundary=\"batch_{}\"".format(batch_id),
            "Accept": "multipart/mixed"
        }
        url = "{}/{}/_api/$batch".format(self.sharepoint_origin, self.sharepoint_site)
        body_elements = []
        body_elements.append("--batch_{}".format(batch_id))
        body_elements.append("Content-Type: multipart/mixed; boundary=changeset_{}".format(change_set_id))
        body_elements.append("")

        for kwargs in kwargs_array:
            body_elements.append("--changeset_{}".format(change_set_id))
            body_elements.append("Content-Type: application/http")
            body_elements.append("Content-Transfer-Encoding: binary")
            body_elements.append("")
            body_elements.append("{} {} HTTP/1.1".format(kwargs["verb"].upper(), kwargs["url"]))
            for header in kwargs["headers"]:
                body_elements.append("{}: {}".format(header, kwargs["headers"][header]))
            body_elements.append("Accept-Charset: UTF-8")
            body_elements.append("")
            body_elements.append(json.dumps(kwargs["json"]))
        body_elements.append("--changeset_{}--".format(change_set_id))
        body_elements.append('--batch_{}--'.format(batch_id))
        body = "\r\n".join(body_elements)
        successful_post = False
        attempt_number = 0
        while not successful_post and attempt_number <= SharePointConstants.MAX_RETRIES:
            try:
                attempt_number += 1
                logger.info("Posting batch of {} items".format(len(kwargs_array)))
                response = self.session.post(
                    url,
                    dku_rs_off=True,
                    headers=headers,
                    data=body.encode('utf-8')
                )
                logger.info("Batch post status: {}".format(response.status_code))
                if response.status_code >= 400:
                    logger.error("Responnse={}".format(response.content))
                successful_post = True
            except requests.exceptions.Timeout as err:
                #  Necessary to raise since timed out items may or may not be uploaded
                #  possibly resulting in duplicated items
                logger.error("Timeout error:{}".format(err))
                raise SharePointClientError("Timeout error: {}".format(err))
            except Exception as err:
                logger.warning("ERROR:{}".format(err))
                logger.warning("on attempt #{}".format(attempt_number))
                if attempt_number == SharePointConstants.MAX_RETRIES:
                    raise SharePointClientError("Error in batch processing on attempt #{}: {}".format(attempt_number, err))
                time.sleep(SharePointConstants.WAIT_TIME_BEFORE_RETRY_SEC)

        self.log_batch_errors(response, kwargs_array)

        return response

    def log_batch_errors(self, response, kwargs_array):
        logger.info("Batch error analysis")
        statuses = re.findall('HTTP/1.1 (.*?) ', str(response.content))
        dump_response_content = False
        for status, kwarg in zip(statuses, kwargs_array):
            if not status.startswith("20"):
                if dump_response_content:
                    logger.warning("Error {}".format(status))
                else:
                    logger.warning("Error {} with kwargs={}".format(status, logger.filter_secrets(kwarg)))
                dump_response_content = True
        json_chains = re.findall('\r\n\r\n{"d":(.*?)}\r\n--batchresponse_', str(response.content))
        for json_chain in json_chains:
            errors = re.findall('"ErrorCode":(.*?),"', json_chain)
            for error in errors:
                if error != "0":
                    dump_response_content = True
        error_messages = re.findall('"ErrorMessage":"(.*?)}', str(response.content))
        for error_message in error_messages:
            logger.warning("Error:'{}'".format(error_message))
        if dump_response_content:
            if self.number_dumped_logs == 0:
                logger.warning("response.content={}".format(response.content))
            else:
                logger.warning("Batch error analysis KO ({})".format(self.number_dumped_logs))    
            self.number_dumped_logs += 1
        else:
            logger.info("Batch error analysis OK")

    def get_base_url(self):
        return "{}/{}/_api/Web".format(
            self.sharepoint_origin, self.sharepoint_site
        )

    def get_lists_url(self):
        return self.get_base_url() + "/lists"

    def get_lists_by_title_url(self, list_title):
        # Sharepoint's API escapes single quotes in titles by doubling them. "McDonald's" -> 'McDonald''s'
        # https://sharepoint.stackexchange.com/questions/246685/sharepoint-rest-api-update-metadata-document-library-item-when-value-string-in
        escaped_list_title = self.escape_path(list_title)
        return self.get_lists_url() + "/GetByTitle('{}')".format(urllib.parse.quote(escaped_list_title))

    def get_lists_by_id_url(self, list_id):
        return self.get_lists_url() + "('{}')".format(list_id)

    def get_list_items_url(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/Items"

    def get_list_data_as_stream(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/RenderListDataAsStream"

    def get_list_items_url_by_id(self, list_id):
        return self.get_lists_by_id_url(list_id) + "/Items"

    def get_list_views_url(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/Views"

    def get_list_add_item_using_path_url(self, list_title):
        # https://ikuiku.sharepoint.com/sites/dssplugin/_api/web/GetList(@a1)/AddValidateUpdateItemUsingPath()?@a1=%27%2Fsites%2Fdssplugin%2FLists%2FTypeLocation%27
        return self.get_base_url() + "/GetList(@a1)/AddValidateUpdateItemUsingPath()?@a1='/{}/Lists/{}'".format(
            self.sharepoint_site,
            self.escape_path(list_title)
        )

    def get_list_fields_url(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/fields"

    def get_lists_add_field_url(self, list_title):
        return self.get_base_url() + "/GetList(@a1)/Fields/CreateFieldAsXml?@a1='/{}/Lists/{}'".format(
            self.sharepoint_site,
            self.escape_path(list_title)
        )

    def get_guid_lists_add_field_url(self, list_id):
        return self.get_base_url() + "/lists('{}')/Fields/CreateFieldAsXml".format(
            list_id
        )

    def get_folder_url(self, full_path):
        if full_path == '/':
            full_path = ""
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

    def get_recycle_file_url(self, full_path):
        return self.get_file_url(full_path) + "/recycle()"

    def get_recycle_folder_url(self, full_path):
        return self.get_folder_url(full_path) + "/recycle()"

    def get_file_check_in_url(self, full_path):
        return self.get_file_url(full_path) + "/CheckIn()"

    def get_site_path(self, full_path):
        return "'/{}/{}{}'".format(
            self.escape_path(self.sharepoint_site),
            self.escape_path(self.sharepoint_root),
            self.escape_path(full_path)
        )

    def get_add_folder_url(self, full_path):
        return self.get_base_url() + "/Folders/add('{}{}')".format(
            self.sharepoint_root,
            full_path
        )

    def get_file_add_url(self, full_path, file_name):
        return self.get_folder_url(full_path) + "/Files/add(url='{}',overwrite=true)".format(self.escape_path(file_name))

    def get_list_default_view_url(self, list_title):
        return os.path.join(
            self.get_lists_by_title_url(list_title),
            SharePointConstants.DEFAULT_VIEW_ENDPOINT
        )

    @staticmethod
    def assert_login_details(required_keys, login_details):
        if login_details is None or login_details == {}:
            raise SharePointClientError("Login details are empty")
        for key in required_keys:
            if key not in login_details.keys():
                raise SharePointClientError(required_keys[key])

    def assert_response_ok(self, response, no_json=False, calling_method=""):
        status_code = response.status_code
        if status_code >= 400:
            logger.error("Error {} in method {}".format(status_code, calling_method))
            enriched_error_message = self.get_enriched_error_message(response)
            if enriched_error_message is not None:
                raise SharePointClientError("Error ({}): {}".format(calling_method, enriched_error_message))
            if status_code == 400:
                raise SharePointClientError("({}){}".format(calling_method, response.text))
            if status_code == 404:
                raise SharePointClientError("Not found. Please check tenant, site type or site name. ({})".format(calling_method))
            if status_code == 403:
                logger.error("403 error. Checking for federated namespace.")
                self.assert_non_federated_namespace()
                logger.error("User does not belong to federated namespace.")
                raise SharePointClientError("403 Forbidden. Please check your account credentials. ({})".format(calling_method))
            raise SharePointClientError("Error {} ({})".format(status_code, calling_method))
        if not no_json:
            self.assert_no_error_in_json(response, calling_method=calling_method)

    def assert_non_federated_namespace(self):
        # Called following 403 error
        if self.username_for_namespace_diag:
            # username / password login was used to login
            # we check if the email used as username belongs to a federated namespace
            json_response = ""
            try:
                response = self.session.get(
                    "https://login.microsoftonline.com/GetUserRealm.srf",
                    params={
                        "login": "{}".format(self.username_for_namespace_diag)
                    }
                )
                json_response = response.json()
            except Exception as err:
                logger.info("Error while testing for federated namespace: {}".format(err))
            if json_response.get("NameSpaceType", "").lower() == "federated":
                logger.error("User email address belongs to a federated namespace.")
                raise SharePointClientError(
                    "403 Forbidden. The '{}' account belongs to a federated namespace. ".format(self.username_for_namespace_diag)
                    + "Dataiku might not be able to use it to access SharePoint-Online. "
                    + "Please contact your administrator to configure a Single Sign On or an App token access."
                )

    @staticmethod
    def get_enriched_error_message(response):
        try:
            json_response = response.json()
            error_message = get_value_from_paths(
                json_response,
                [
                    ["error", "message", "value"],
                    ["error_description"]
                ]
            )
            if error_message:
                return "{}".format(error_message)
        except Exception as error:
            logger.info("Error trying to extract error message: {}".format(error))
            logger.info("Response.content={}".format(response.content))
            return None

    @staticmethod
    def assert_no_error_in_json(response, calling_method=""):
        if len(response.content) == 0:
            raise SharePointClientError("Empty response from SharePoint ({}). Please check user credentials.".format(calling_method))
        json_response = response.json()
        if "error" in json_response:
            if "message" in json_response["error"] and "value" in json_response["error"]["message"]:
                raise SharePointClientError("Error ({}): {}".format(calling_method, json_response["error"]["message"]["value"]))
            else:
                raise SharePointClientError("Error ({}): {}".format(calling_method, json_response))

    def get_site_app_access_token(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": "{client_id}@{tenant_id}".format(client_id=self.client_id, tenant_id=self.tenant_id),
            "client_secret": self.client_secret,
            "resource": "{resource}/{sharepoint_url}@{tenant_id}".format(
                resource=SharePointConstants.SHAREPOINT_ONLINE_RESSOURCE,
                sharepoint_url=self.sharepoint_url,
                tenant_id=self.tenant_id
            )
        }
        response = requests.post(
            SharePointConstants.GET_SITE_APP_TOKEN_URL.format(tenant_id=self.tenant_id),
            headers=headers,
            data=data
        )
        self.assert_response_ok(response, calling_method="get_site_app_access_token")
        json_response = response.json()
        return json_response.get("access_token")

    def get_list_views(self, list_title):
        response = self.session.get(
            self.get_list_views_url(list_title),
            params={
                "$select": "ID,ServerRelativeUrl,Title"
            }
        )
        self.assert_response_ok(response, calling_method="get_list_views_ids")
        json_response = response.json()
        views = get_value_from_path(json_response, [SharePointConstants.RESULTS_CONTAINER_V2, "results"])
        logger.info("get_list_views:available views:{}".format(views))
        return views

    @staticmethod
    def get_random_guid():
        return str(uuid.uuid4())

    @staticmethod
    def escape_path(path):
        return path.replace("'", "''")


class SharePointSession():

    def __init__(self, sharepoint_user_name, sharepoint_password, sharepoint_url, sharepoint_site, sharepoint_access_token=None, max_retry=10):
        self.sharepoint_url = sharepoint_url
        self.sharepoint_site = sharepoint_site
        self.sharepoint_access_token = sharepoint_access_token
        requests.adapters.DEFAULT_RETRIES = max_retry
        self.form_digest_value = self.get_form_digest_value()

    def get(self, url, headers=None, params=None):
        headers = headers or {}
        headers["Accept"] = DSSConstants.APPLICATION_JSON
        headers["Authorization"] = self.get_authorization_bearer()
        response = None
        while not is_request_performed(response):
            response = requests.get(url, headers=headers, params=params)
        return response

    def post(self, url, headers=None, json=None, data=None, params=None):
        headers = headers or {}
        default_headers = {
           "Accept": DSSConstants.APPLICATION_JSON_NOMETADATA,
           "Content-Type": DSSConstants.APPLICATION_JSON_NOMETADATA,
           "Authorization": self.get_authorization_bearer()
        }
        if self.form_digest_value:
            default_headers.update({"X-RequestDigest": self.form_digest_value})
        default_headers.update(headers)
        response = None
        while not is_request_performed(response):
            response = requests.post(url, headers=default_headers, json=json, data=data, params=params, timeout=SharePointConstants.TIMEOUT_SEC)
        return response

    @staticmethod
    def close():
        logger.info("Closing SharePointSession.")

    def get_authorization_bearer(self):
        return "Bearer {}".format(self.sharepoint_access_token)

    def get_form_digest_value(self):
        logger.info("Getting form digest value")
        session = RobustSession(session=requests, status_codes_to_retry=[429])
        session.update_settings(
            max_retries=SharePointConstants.MAX_RETRIES,
            base_retry_timer_sec=SharePointConstants.WAIT_TIME_BEFORE_RETRY_SEC
        )
        headers = {**DSSConstants.JSON_HEADERS, **{"Authorization": self.get_authorization_bearer()}}
        response = session.post(
            url=self.get_contextinfo_url(),
            headers=headers
        )
        form_digest_value = get_value_from_path(
            response.json(),
            [
                SharePointConstants.RESULTS_CONTAINER_V2,
                SharePointConstants.GET_CONTEXT_WEB_INFORMATION,
                SharePointConstants.FORM_DIGEST_VALUE
            ]
        )
        logger.info("Form digest value {}".format(form_digest_value))
        return form_digest_value

    def get_contextinfo_url(self):
        return "https://{}/{}/_api/contextinfo".format(
            self.sharepoint_url, self.sharepoint_site
        )


class SuppressFilter(logging.Filter):
    # Avoid poluting logs with redondant warnings
    # https://github.com/diyan/pywinrm/issues/269
    def filter(self, record):
        return 'Failed to parse headers' not in record.getMessage()
