

import xbmc, xbmcaddon
import json
import os, binascii


try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

__addon_name__ = "NBA League Pass II"
__addon_id__ = "video.nba.leaguepass.sm"

# Global variables
settings = xbmcaddon.Addon(id=__addon_id__)
show_records_and_scores = json.loads(settings.getSetting(id="records_and_scores"))
use_alternative_archive_menu = json.loads(settings.getSetting(id="alternative_archive_menu"))
enable_playlists = json.loads(settings.getSetting(id="enable_playlists"))
team_preferences = {}
for t in ['Hawks', 'Celtics', 'Nets', 'Hornets', 'Bulls', 'Cavaliers', 'Mavericks', 'Nuggets', 'Pistons', 'Warriors', 'Rockets', 'Pacers', 'Clippers', 'Lakers', 'Grizzlies', 'Heat', 'Bucks', 'Timberwolves', 'Pelicans', 'Knicks', 'Thunder', 'Magic', '76ers', 'Suns', 'Trail Blazers', 'Kings', 'Spurs', 'Raptors', 'Jazz', 'Wizards']:
    try:
        value = int(json.loads(settings.getSetting(id=t)))
        if value < 0:
            value = 0
        if value > 4:
            value = 4
        team_preferences[t] = value
    except:
        team_preferences[t] = 0
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
