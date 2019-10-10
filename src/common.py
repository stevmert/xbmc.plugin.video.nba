import json
import datetime
import urllib,urllib2
import xbmc,xbmcaddon
import re
from xml.dom.minidom import parseString

import vars
from utils import *

def updateFavTeam():
    vars.fav_team_abbrs = None

    settings = xbmcaddon.Addon(id=vars.__addon_id__)
    fav_team_name = settings.getSetting(id="fav_team")
    if fav_team_name:
        for franchise, abbrs in vars.config['franchises'].items():
            if fav_team_name == franchise:
                vars.fav_team_abbrs = abbrs
                xbmc.log(msg="fav_team_abbrs set to %s" % str(vars.fav_team_abbrs), level=xbmc.LOGWARNING)

def getGameUrlWithBitrate(url, video_type):
    return url

def getFanartImage():
    # get the feed url
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

def getDate( default= '', heading='Please enter date (YYYY/MM/DD)', hidden=False ):
    now = datetime.datetime.now()
    default = "%04d" % now.year + '/' + "%02d" % now.month + '/' + "%02d" % now.day
    keyboard = xbmc.Keyboard( default, heading, hidden )
    keyboard.doModal()
    ret = datetime.date.today()
    if keyboard.isConfirmed():
        sDate = unicode( keyboard.getText(), "utf-8" )
        temp = sDate.split("/")
        ret = datetime.date(int(temp[0]),  int(temp[1]), int(temp[2]))
    return ret

def login():
    username = vars.settings.getSetting( id="username")
    password = vars.settings.getSetting( id="password")
    
    if not username or not password:
        littleErrorPopup( xbmcaddon.Addon().getLocalizedString(50024) )
        return ''
    
    try:
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        body = urllib.urlencode({
            'username': username,
            'password': password
        })

        request = urllib2.Request(vars.config['login_endpoint'], body, headers)
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.HTTPError as e:
        log("Login failed with code: %d and content: %s" % (e.getcode(), e.read()))
        littleErrorPopup( xbmcaddon.Addon().getLocalizedString(50022) )
        return ''

    # Check the response xml
    xml = parseString(str(content))
    if xml.getElementsByTagName("code")[0].firstChild.nodeValue == "loginlocked":
        littleErrorPopup( xbmcaddon.Addon().getLocalizedString(50021) )
        return ''
    else:
        # logged in
        vars.cookies = response.info().getheader('Set-Cookie').partition(';')[0]

    """try:
        body = urllib.urlencode({
            'format': 'json'
        })

        request = urllib2.Request('https://watch.nba.com/account/subscriptions?', body, headers)
        subscriptions = urllib2.urlopen(request).read()
    except urllib2.HTTPError as e:
        log("Login failed with code: %d and content: %s" % (e.getcode(), e.read()))
        littleErrorPopup( xbmcaddon.Addon().getLocalizedString(50022) )
        return ''

    subscription_json = json.loads(subscriptions)
    log("Subscription json: %s" % (subscription_json), xbmc.LOGNOTICE)
    if subscription_json['code'] != "noaccess":
        subscription_sku = subscription_json["subs"][0]["sku"]
        log("Subscription sku: %s" % (subscription_sku), xbmc.LOGNOTICE)
        if subscription_sku == "LPP2015":
            vars.subscriptions = ["season", "playoffs", "nbatvlive"]"""

    return vars.cookies
