from safe_logger import SafeLogger

logger = SafeLogger("sharepoint-online plugin")


class WhiteList():
    def __init__(self, config=None):
        self.config = config or {}
        self.activate_white_list = self.config.get("activate_whitelist", False)
        self.libraries_whitelist = {}
        self.lists_whitelist = {}
        libraries_whitelist = self.config.get("libraries_whitelist", [])
        for library in libraries_whitelist:
            library_path = library.get("whitelist_name", "").strip("/").lower()
            library_rights = library.get("whitelist_rights", [])
            self.libraries_whitelist[library_path] = library_rights
        lists_whitelist = self.config.get("lists_whitelist", [])
        for list_item in lists_whitelist:
            list_name = list_item.get("whitelist_name", "").lower()
            list_rights = list_item.get("whitelist_rights", [])
            self.lists_whitelist[list_name] = list_rights
        if self.activate_white_list:
            logger.info("Whitelisting with libraries:{} and lists:{}".format(self.libraries_whitelist, self.lists_whitelist))

    def assert_can_read_path(self, path):
        if not self.can_read_path(path):
            raise Exception("This preset does not have read access to '{}'".format(path))

    def assert_can_write_path(self, path):
        if not self.can_write_path(path):
            raise Exception("This preset does not have write access to '{}'".format(path))

    def assert_can_read_list(self, list_name):
        if not self.can_read_list(list_name):
            raise Exception("This preset does not have read access to the list '{}'".format(list_name))

    def assert_can_write_list(self, list_name):
        if not self.can_write_list(list_name):
            raise Exception("This preset does not have write access to the list '{}'".format(list_name))

    def can_read_path(self, path):
        return self.can_do("read", self.libraries_whitelist, path.strip("/").lower().split("/"))

    def can_write_path(self, path):
        return self.can_do("write", self.libraries_whitelist, path.strip("/").lower().split("/"))

    def can_read_list(self, list_name):
        return self.can_do("read", self.lists_whitelist, list_name.lower())

    def can_write_list(self, list_name):
        return self.can_do("write", self.lists_whitelist, list_name.lower())

    def can_do(self, required_right, rights, path_to_test):
        if not self.activate_white_list:
            return True
        if isinstance(path_to_test, list):
            for path_size in range(len(path_to_test) + 1, 0, -1):
                tokens_in_path = path_to_test[0:path_size]
                path_chunk_to_test = "/".join(tokens_in_path)
                right_for_path = rights.get(path_chunk_to_test, [])
                if required_right in right_for_path:
                    return True
            return False
        else:
            right_for_path = rights.get(path_to_test, [])
            return required_right in right_for_path
