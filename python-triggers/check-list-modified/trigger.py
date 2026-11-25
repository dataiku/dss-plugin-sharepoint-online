import time
import logging
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


logger.info('SharePoint Online plugin list trigger v{}'.format(DSSConstants.PLUGIN_VERSION))
plugin_config = get_plugin_config()
config = plugin_config.get("config", {})
sharepoint_list_title = config.get("sharepoint_list_title")

trigger = Trigger()
project_variable_name = "sharepoint-online-list-trigger_{}".format(sharepoint_list_title)
last_modified = ProjectVariable(project_variable_name, default_value=0)
client = SharePointClient(config)
remote_file_last_modified_epoch = client.get_list_last_modified(
    sharepoint_list_title
)
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
    logger.info("Remote spreadsheet has not been modified")
