from dataiku.fsprovider import FSProvider

import os
import shutil
import logging

from sharepoint_client import SharePointClient
from dss_constants import DSSConstants
from sharepoint_items import loop_sharepoint_items, has_sharepoint_items, extract_item_from, get_size, get_last_modified, get_name, assert_path_is_not_root
from sharepoint_items import create_path
from common import get_rel_path, get_lnt_path

try:
    from BytesIO import BytesIO  # for Python 2
except ImportError:
    from io import BytesIO  # for Python 3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint-online plugin %(levelname)s - %(message)s')


# based on https://docs.microsoft.com/fr-fr/sharepoint/dev/sp-add-ins/working-with-folders-and-files-with-rest

class SharePointFSProvider(FSProvider):
    def __init__(self, root, config, plugin_config):
        """
        :param root: the root path for this provider
        :param config: the dict of the configuration of the object
        :param plugin_config: contains the plugin settings
        """
        if len(root) > 0 and root[0] == '/':
            root = root[1:]
        self.root = root
        self.provider_root = "/"
        logger.info('SharePoint Online plugin fs v1.0.10')
        logger.info('init:root={}'.format(self.root))

        self.client = SharePointClient(config)

    # util methods
    def get_full_path(self, path):
        path_elts = [self.provider_root, get_rel_path(self.root), get_rel_path(path)]
        path_elts = [e for e in path_elts if len(e) > 0]
        return os.path.join(*path_elts)

    def close(self):
        logger.info('close')

    def stat(self, path):
        full_path = get_lnt_path(self.get_full_path(path))
        logger.info('stat:path="{}", full_path="{}"'.format(path, full_path))
        files = self.client.get_files(full_path)
        folders = self.client.get_folders(full_path)

        if has_sharepoint_items(files) or has_sharepoint_items(folders):
            return {
                DSSConstants.PATH: get_lnt_path(path),
                DSSConstants.SIZE: 0,
                DSSConstants.IS_DIRECTORY: True
            }

        path_to_item, item_name = os.path.split(full_path)
        files = self.client.get_files(path_to_item)
        folders = self.client.get_folders(path_to_item)

        file = extract_item_from(item_name, files)
        folder = extract_item_from(item_name, folders)

        if folder is not None:
            return {
                DSSConstants.PATH: get_lnt_path(path),
                DSSConstants.SIZE: 0,
                DSSConstants.LAST_MODIFIED: get_last_modified(folder),
                DSSConstants.IS_DIRECTORY: True
            }
        if file is not None:
            return {
                DSSConstants.PATH: get_lnt_path(path),
                DSSConstants.SIZE: get_size(file),
                DSSConstants.LAST_MODIFIED: get_last_modified(file),
                DSSConstants.IS_DIRECTORY: False
            }
        return None

    def set_last_modified(self, path, last_modified):
        full_path = self.get_full_path(path)
        logger.info('set_last_modified: path="{}", full_path="{}"'.format(path, full_path))
        return False

    def browse(self, path):
        path = get_rel_path(path)
        full_path = get_lnt_path(self.get_full_path(path))
        logger.info('browse:path="{}", full_path="{}"'.format(path, full_path))

        folders = self.client.get_folders(full_path)
        files = self.client.get_files(full_path)
        children = []

        for file in loop_sharepoint_items(files):
            children.append({
                DSSConstants.FULL_PATH: get_lnt_path(os.path.join(path, get_name(file))),
                DSSConstants.EXISTS: True,
                DSSConstants.DIRECTORY: False,
                DSSConstants.SIZE: get_size(file),
                DSSConstants.LAST_MODIFIED: get_last_modified(file)
            })
        for folder in loop_sharepoint_items(folders):
            children.append({
                DSSConstants.FULL_PATH: get_lnt_path(os.path.join(path, get_name(folder))),
                DSSConstants.EXISTS: True,
                DSSConstants.DIRECTORY: True,
                DSSConstants.SIZE: 0,
                DSSConstants.LAST_MODIFIED: get_last_modified(folder)
            })

        if len(children) > 0:
            return {
                DSSConstants.FULL_PATH: get_lnt_path(path),
                DSSConstants.EXISTS: True,
                DSSConstants.DIRECTORY: True,
                DSSConstants.CHILDREN: children
            }
        path_to_file, file_name = os.path.split(full_path)

        files = self.client.get_files(path_to_file)

        for file in loop_sharepoint_items(files):
            if get_name(file) == file_name:
                return {
                    DSSConstants.FULL_PATH: get_lnt_path(path),
                    DSSConstants.EXISTS: True, DSSConstants.SIZE: get_size(file),
                    DSSConstants.LAST_MODIFIED: get_last_modified(file),
                    DSSConstants.DIRECTORY: False
                }

        parent_path, item_name = os.path.split(full_path)
        folders = self.client.get_folders(parent_path)
        folder = extract_item_from(item_name, folders)
        if folder is None:
            ret = {
                DSSConstants.FULL_PATH: None,
                DSSConstants.EXISTS: False
            }
        else:
            ret = {
                DSSConstants.FULL_PATH: get_lnt_path(path),
                DSSConstants.EXISTS: True,
                DSSConstants.DIRECTORY: True,
                DSSConstants.SIZE: 0
            }
        return ret

    def enumerate(self, path, first_non_empty):
        full_path = get_lnt_path(self.get_full_path(path))
        logger.info('enumerate:path="{}",fullpath="{}", first_non_empty="{}"'.format(path, full_path, first_non_empty))
        path_to_item, item_name = os.path.split(full_path)
        is_file = self.client.is_file(full_path)
        if is_file:
            return [{
                DSSConstants.PATH: path
            }]
        ret = self.list_recursive(path, full_path, first_non_empty)
        return ret

    def list_recursive(self, path, full_path, first_non_empty):
        paths = []
        folders = self.client.get_folders(full_path)
        for folder in loop_sharepoint_items(folders):
            paths.extend(
                self.list_recursive(
                    get_lnt_path(os.path.join(path, get_name(folder))),
                    get_lnt_path(os.path.join(full_path, get_name(folder))),
                    first_non_empty
                )
            )
        files = self.client.get_files(full_path)
        for file in loop_sharepoint_items(files):
            paths.append({
                DSSConstants.PATH: get_lnt_path(os.path.join(path, get_name(file))),
                DSSConstants.LAST_MODIFIED: get_last_modified(file),
                DSSConstants.SIZE: get_size(file)
            })
            if first_non_empty:
                return paths
        return paths

    def delete_recursive(self, path):
        full_path = self.get_full_path(path)
        logger.info('delete_recursive:path={},fullpath={}'.format(path, full_path))
        assert_path_is_not_root(full_path)
        path_to_item, item_name = os.path.split(full_path.rstrip("/"))
        files = self.client.get_files(path_to_item)
        folders = self.client.get_folders(path_to_item)
        file = extract_item_from(item_name, files)
        folder = extract_item_from(item_name, folders)

        if file is not None and folder is not None:
            raise Exception("Ambiguous naming with file / folder {}".format(item_name))

        if file is not None:
            self.client.recycle_file(get_lnt_path(full_path))
            return 1

        if folder is not None:
            self.client.recycle_folder(get_lnt_path(full_path))
            return 1

        return 0

    def move(self, from_path, to_path):
        full_from_path = self.get_full_path(from_path)
        full_to_path = self.get_full_path(to_path)
        logger.info('move:from={},to={}'.format(full_from_path, full_to_path))

        self.client.move_file(full_from_path, full_to_path)
        # SP Online now returns {'odata.null': True}
        return True

    def read(self, path, stream, limit):
        full_path = self.get_full_path(path)
        logger.info('read:full_path={}'.format(full_path))
        response = self.client.get_file_content(full_path)
        bio = BytesIO(response.content)
        shutil.copyfileobj(bio, stream)

    def write(self, path, stream):
        full_path = self.get_full_path(path)
        logger.info('write:path="{}", full_path="{}"'.format(path, full_path))
        bio = BytesIO()
        shutil.copyfileobj(stream, bio)
        bio.seek(0)
        data = bio.read()
        create_path(self.client, full_path)
        response = self.client.write_file_content(full_path, data)
        logger.info("write:response={}".format(response))
        self.client.check_in_file(full_path)
