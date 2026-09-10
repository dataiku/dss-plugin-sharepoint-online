import time
import logging
import calendar
from dataiku.customtrigger import get_plugin_config
from dataiku.scenario import Trigger
from sharepoint_client import SharePointClient
from dss_constants import DSSConstants


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint-online plugin %(levelname)s - %(message)s')


class ProjectVariable():
    def __init__(self, variable_name, variable_type=None, default_value=None):
        from dataiku import Project
        self.variable_name = variable_name
        self.project = Project()
        self.variable_type = variable_type or "standard"
        self.default_value = default_value

    def is_not_set(self):
        project_variables = self.project.get_variables()
        project_variable = project_variables.get(self.variable_type, {}).get(self.variable_name)
        if project_variable is None:
            return True
        return False

    def get_value(self):
        project_variables = self.project.get_variables()
        project_variable = project_variables.get(self.variable_type, {}).get(self.variable_name, self.default_value)
        return project_variable

    def set_value(self, value):
        project_variables = self.project.get_variables()
        project_variables[self.variable_type][self.variable_name] = value
        self.project.set_variables(project_variables)


def pretty_epoch(epoch_time):
    return time.strftime('%Y-%m-%d %H:%M:%S%z', time.gmtime(epoch_time/1000))


def find_sharepoint_item(sharepoint_path):
    sharepoint_path = sharepoint_path.strip("/")
    sharepoint_path = "/" + sharepoint_path
    sharepoint_path_tokens = sharepoint_path.split("/")
    item_path = "/".join(sharepoint_path_tokens[:-1])
    item_name = "/".join(sharepoint_path_tokens[-1:])

    # 1 - get files folders for path-1
    # 2 - scan these files then folders for Name=path[last] !!files get priority
    # 3 - returns TimeLastModified. Format is 2024-01-18T14:41:46Z
    files = client.get_files(item_path)
    files = files.get("d", {}).get("results", [])
    # print("ALX:files={}".format(files))
    for file in files:
        file_name = file.get("Name")
        if file_name == item_name:
            return file
    folders = client.get_folders(item_path)
    folders = folders.get("d", {}).get("results", [])
    for folder in folders:
        folder_name = folder.get("Name")
        if folder_name == item_name:
            return folder


logger.info('SharePoint Online plugin fs trigger v{}'.format(DSSConstants.PLUGIN_VERSION))
plugin_config = get_plugin_config()
config = plugin_config.get("config", {})
sharepoint_path = config.get("sharepoint_path")

trigger = Trigger()
project_variable_name = "sharepoint-online-fs-trigger_{}".format(sharepoint_path)
last_modified = ProjectVariable(project_variable_name, default_value=0)
client = SharePointClient(config)

sharepoint_item = find_sharepoint_item(sharepoint_path)
if not sharepoint_item:
    raise Exception("Sharepoint item not found")

remote_file_last_modified = sharepoint_item.get("TimeLastModified")

remote_file_last_modified_epoch = calendar.timegm(
                    time.strptime(remote_file_last_modified, "%Y-%m-%dT%H:%M:%SZ")
                ) * 1000

last_modified_epoch = last_modified.get_value()
logger.info("Trigger.{}.lastLocalTime: {} ({})".format(
        project_variable_name,
        last_modified_epoch,
        pretty_epoch(last_modified_epoch)
    )
)
logger.info("Trigger.{}.remoteTime: {} ({})".format(
        project_variable_name,
        remote_file_last_modified_epoch,
        pretty_epoch(remote_file_last_modified_epoch)
    )
)
if last_modified.is_not_set() or (remote_file_last_modified_epoch > last_modified_epoch):
    logger.info("remote epoch {} > local epoch {}, firing the trigger".format(remote_file_last_modified_epoch, last_modified_epoch))
    remote_file_last_modified_epoch = int(time.time()) * 1000
    last_modified.set_value(remote_file_last_modified_epoch)
    trigger.fire()
else:
    logger.info("Remote file has not been modified")
