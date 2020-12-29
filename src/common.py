

import json
import datetime
import urllib
import urllib2
import xbmc
import xbmcaddon
import xbmcgui
from xml.dom.minidom import parseString

import vars
from utils import *


PROTOCOLS = {
    'mpd': {'extensions': ['mpd'], 'mimetype': 'application/dash+xml'},
    'hls': {'extensions': ['m3u8', 'm3u'], 'mimetype': 'application/vnd.apple.mpegurl'},
}
DRM = 'com.widevine.alpha'  # TODO Handle other DRM_SCHEMES
LICENSE_URL = 'https://shield-twoproxy.imggaming.com/proxy'


def play(video):
    item = None
    if 'url' in video:
        item = xbmcgui.ListItem(path=video['url'])
        for protocol, protocol_info in PROTOCOLS.items():
            if any(".%s" % extension in video['url'] for extension in protocol_info['extensions']):
                from inputstreamhelper import Helper
                is_helper = Helper(protocol, drm=DRM)
                if is_helper.check_inputstream():
                    item.setMimeType(protocol_info['mimetype'])
                    item.setContentLookup(False)
                    item.setProperty('inputstreamaddon', is_helper.inputstream_addon)  # TODO Kodi version dep
                    item.setProperty('inputstream.adaptive.manifest_type', protocol)
                    item.setProperty('inputstream.adaptive.license_type', DRM)
                    item.setProperty('inputstream.adaptive.manifest_update_parameter', 'full')
                    license_key = '%s|authorization=bearer %s|R{SSM}|' % (LICENSE_URL, video['drm'])
                    item.setProperty('inputstream.adaptive.license_key', license_key)

    if item is not None:
        xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)

def updateFavTeam():
    vars.fav_team_abbrs = None

    settings = xbmcaddon.Addon(id=vars.__addon_id__)
    fav_team_name = settings.getSetting(id="fav_team")
    if fav_team_name:
        for franchise, abbrs in vars.config['franchises'].items():
            if fav_team_name == franchise:
                vars.fav_team_abbrs = abbrs
                xbmc.log(msg="fav_team_abbrs set to %s" % str(vars.fav_team_abbrs), level=xbmc.LOGWARNING)

def getFanartImage():
    # Get the feed url
    feed_url = "https://nlnbamdnyc-a.akamaihd.net/fs/nba/feeds/common/dl.js"
    xbmc.log(feed_url, xbmc.LOGINFO)
    req = urllib2.Request(feed_url, None)
    response = str(urllib2.urlopen(req).read())

    try:
        # Parse
        js = json.loads(response[response.find("{"):])
        dl = js["dl"]

        # for now only chose the first fanart
        first_id = dl[0]["id"]
        fanart_image = "https://nbadsdmt.akamaized.net/media/nba/nba/thumbs/dl/%s_pc.jpg" % first_id
        xbmc.log(fanart_image, xbmc.LOGINFO)
        vars.settings.setSetting("fanart_image", fanart_image)
    except:
        # I don't care
        pass

def get_date(default='', heading='Please enter date (YYYY/MM/DD)', hidden=False):
    now = datetime.datetime.now()
    default = "%04d" % now.year + '/' + "%02d" % now.month + '/' + "%02d" % now.day
    keyboard = xbmc.Keyboard(default, heading, hidden)
    keyboard.doModal()
    ret = datetime.date.today()
    if keyboard.isConfirmed():
        sDate = unicode(keyboard.getText(), 'utf-8')
        temp = sDate.split("/")
        ret = datetime.date(int(temp[0]), int(temp[1]), int(temp[2]))
    return ret

def authenticate():
    email = vars.settings.getSetting(id="email")
    password = vars.settings.getSetting(id="password")

    if not email or not password:
        littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50024))
        return False

    try:
        headers = {
            'Content-Type': 'application/json',
            'X-Client-Platform': 'web',
        }
        body = json.dumps({
            'email': email,
            'password': password,
            'rememberMe': True,
        })

        request = urllib2.Request('https://identity.nba.com/api/v1/auth', body, headers)
        response = urllib2.urlopen(request)
        content = response.read()
        content_json = json.loads(content)
        vars.cookies = response.info()['Set-Cookie'].partition(';')[0]
    except urllib2.HTTPError as err:
        littleErrorPopup(err)
        return False

    try:
        headers = {
            'Cookie': vars.cookies,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        }
        body = {
            'format': 'json',
            'accesstoken': 'true',
            'ciamlogin': 'true',
        }
        body = urllib.urlencode(body)

        request = urllib2.Request('https://watch.nba.com/secure/authenticate', body, headers)
        response = urllib2.urlopen(request)
        content = response.read()
        content_json = json.loads(content)
        vars.access_token = content_json['data']['accessToken']
    except urllib2.HTTPError as err:
        littleErrorPopup(err)
        return False

    return True
