

import json

import xbmc
import xbmcaddon
import xbmcvfs


class SharedData:

    DEFAULT_FILE_CONTENT = "{}"  # TODO

    def __init__(self):
        self.folder = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode("utf-8")
        if not xbmcvfs.exists(self.folder):
            xbmcvfs.mkdir(self.folder)
        self.file_path = self.folder + "shared_data.json"
        with open(self.file_path, 'w') as file_obj:
            file_obj.write(self.DEFAULT_FILE_CONTENT)

    def __getFileContent(self):  # TODO
        try:
            with open(self.file_path) as file_obj:
                file_content = file_obj.read()
        except:  # TODO
            file_content = self.DEFAULT_FILE_CONTENT

        json_content = json.loads(file_content)
        return json_content

    def set(self, path, value):
        json_content = self.__getFileContent()

        # Simple "json-path"-like set algorithm #  TODO
        keys = path.split('.')
        keys_length = len(keys)
        item = json_content
        for index, key in enumerate(keys):
            if key not in item:
                item[key] = {}

            if index + 1 < keys_length:
                if not isinstance(item[key], dict):
                    item[key] = {}
                item = item[key]
            else:
                item[key] = value

        file_content = json.dumps(json_content)
        with open(self.file_path, 'w') as file_obj:
            file_obj.write(file_content)

    def get(self, path):
        json_content = self.__getFileContent()

        # Simple "json-path"-like get algorithm #  TODO
        keys = path.split('.')
        item = json_content
        try:
            for key in keys:
                item = item.get(key, {})
        except:  # TODO
            return None

        return item
