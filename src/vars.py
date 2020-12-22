

import xbmc, xbmcaddon
import json
import os, binascii


try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

__addon_name__ = "NBA League Pass"
__addon_id__ = "plugin.video.nba"

# Global variables
settings = xbmcaddon.Addon(id=__addon_id__)
show_scores = json.loads(settings.getSetting(id="scores"))
debug = json.loads(settings.getSetting(id="debug"))
use_cached_thumbnails = json.loads(settings.getSetting(id="cached_thumbnails"))
use_local_timezone = json.loads(settings.getSetting(id="local_timezone"))
show_cameras = json.loads(settings.getSetting(id="cameras"))
useragent = "iTunes-AppleTV/4.1"

cache = StorageServer.StorageServer("nbaleaguepass", 1)
cache.table_name = "nbaleaguepass"

cookies = None
access_token = None

player_id = binascii.b2a_hex(os.urandom(16))
addon_dir = xbmc.translatePath(settings.getAddonInfo('path')).decode('utf-8')

# the default fanart image
fanart_image = os.path.join(addon_dir, "fanart.jpg")
setting_fanart_image = settings.getSetting("fanart_image")
if setting_fanart_image != '':
    fanart_image = setting_fanart_image

try:
    config_path = os.path.join(addon_dir, "config", "config.json")
    config_json = open(config_path).read()
    config = json.loads(config_json)
except:
    root_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(root_path, "..", "config", "config.json")
    config_json = open(config_path).read()
    config = json.loads(config_json)
    pass

fav_team_abbrs = None
