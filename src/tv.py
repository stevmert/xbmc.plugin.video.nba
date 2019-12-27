

import calendar
import datetime
import time
import json
import re
import sys
import urllib
import urllib2
from xml.dom.minidom import parseString

import xbmc
import xbmcaddon
import xbmcplugin

import common
from shareddata import SharedData
import utils
import vars


class TV:

    @staticmethod
    def menu():
        common.addListItem('Live', '', 'nbatvlive', '')
        common.addListItem('Today\'s programming', '', 'nbatvliveepisodemenu', '', isfolder=True)
        common.addListItem('Select date', '', 'nbatvliveepisodemenu', '', isfolder=True, customparams={
            'custom_date': True
        })

    @staticmethod
    def episodeMenu():
        if vars.params.get("custom_date", False):
            date = datetime.datetime.combine(common.getDate(), datetime.time(hour=4, minute=0, second=0))
        else:
            date = utils.nowEST().replace(hour=4, minute=0, second=0)

        utils.log("date for episodes: %s (from %s)" % (date, utils.nowEST()), xbmc.LOGDEBUG)
        schedule = 'https://nlnbamdnyc-a.akamaihd.net/fs/nba/feeds/epg/2019/%s_%s.js?t=%d' % (
            date.month, date.day, time.time())
        utils.log('Requesting %s' % schedule, xbmc.LOGDEBUG)

        now_timestamp = int(calendar.timegm(date.timetuple()))
        now_timestamp_milliseconds = now_timestamp * 1000

        req = urllib2.Request(schedule, None)
        response = str(urllib2.urlopen(req).read())
        json_response = json.loads(response[response.find("["):])

        for entry in json_response:
            entry = entry['entry']

            start_hours, start_minutes = entry['start'].split(':')
            start_timestamp_milliseconds = now_timestamp_milliseconds + (int(start_hours) * 60 * 60 + int(start_minutes) * 60) * 1000

            utils.log("date for episode %s: %d (from %d)" % (entry['title'], start_timestamp_milliseconds, now_timestamp_milliseconds), xbmc.LOGDEBUG)

            duration_hours, duration_minutes = entry['duration'].split(":")
            duration_milliseconds = (int(duration_hours) * 60 * 60 + int(duration_minutes) * 60) * 1000

            params = {
                'duration': duration_milliseconds,
                'start_timestamp': start_timestamp_milliseconds
            }

            name = "%s - %s (%s)" % (entry['start'], entry['title'], entry['duration'])
            common.addListItem(name, '', 'nbatvliveepisode', iconimage=entry['image'], customparams=params)

    @staticmethod
    def playLive():
        video_url = TV.getLiveUrl()
        if video_url:
            shared_data = SharedData()
            shared_data.set('playing', {
                'what': 'nba_tv_live',
            })

            item = common.getPlayableItem(video_url)
            if item is not None:
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)

    @staticmethod
    def playEpisode():
        start_timestamp = vars.params.get('start_timestamp')
        duration = vars.params.get('duration')
        video_url = TV.getEpisodeUrl(start_timestamp, duration)
        if video_url:
            shared_data = SharedData()
            shared_data.set('playing', {
                'what': 'nba_tv_episode',
                'data': {
                    'start_timestamp': start_timestamp,
                    'duration': duration,
                },
            })

            item = common.getPlayableItem(video_url)
            if item is not None:
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)

    @staticmethod
    def getEpisodeUrl(start_timestamp, duration, force_login=False):
        if not vars.cookies or force_login:
            common.login()
        if not vars.cookies:
            return ''

        url = vars.config['publish_endpoint']
        headers = {
            'Cookie': vars.cookies,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'iPad'
        }
        body = urllib.urlencode({
            'id': "1",
            'type': 'channel',
            'ppid': vars.player_id,
            'nt': "1",
            'st': start_timestamp,
            'dur': duration,
        })

        utils.log("nba tv live: the body of publishpoint request is: %s" % body, xbmc.LOGDEBUG)

        try:
            request = urllib2.Request(url, body, headers)
            response = urllib2.urlopen(request)
            content = response.read()
        except urllib2.HTTPError as err:
            utils.log("nba live tv: failed getting url: %s %s" % (url, err.read()), xbmc.LOGDEBUG)
            utils.littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50020))
            return ''

        # Get the adaptive video url
        xml = parseString(str(content))
        video_temp_url = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue
        utils.log("nba live tv: temp video url is %s" % video_temp_url, xbmc.LOGDEBUG)

        # transform the link
        match = re.search('http://([^:]+)/([^?]+?)\?(.+)$', video_temp_url)
        domain = match.group(1)
        arguments = match.group(2)
        querystring = match.group(3)

        livecookies = "nlqptid=%s" % (querystring)
        livecookiesencoded = urllib.quote(livecookies)
        utils.log("live cookie: %s %s" % (querystring, livecookies), xbmc.LOGDEBUG)

        video_url = "http://%s/%s?%s|User-Agent=%s&Cookie=%s" % (domain, arguments, querystring, vars.useragent, livecookiesencoded)
        return video_url

    @staticmethod
    def getLiveUrl(force_login=False):
        if not vars.cookies or force_login:
            common.login()
        if not vars.cookies:
            return ''

        url = vars.config['publish_endpoint']
        headers = {
            'Cookie': vars.cookies,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        }
        body = {
            'type': 'channel',
            'id': 1,
            'drmtoken': True,
            'deviceid': xbmc.getInfoLabel('Network.MacAddress'),
            'pcid': vars.player_id,
            'format': 'xml',
        }

        body = urllib.urlencode(body)
        utils.log("the body of publishpoint request is: %s" % body, xbmc.LOGDEBUG)

        try:
            request = urllib2.Request(url, body, headers)
            response = urllib2.urlopen(request)
            content = response.read()
        except urllib2.HTTPError as err:
            utils.logHttpException(err, url)
            utils.littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50020))
            return ''

        xml = parseString(str(content))
        url = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue
        utils.log("response URL from publishpoint: %s" % url, xbmc.LOGDEBUG)
        drm = xml.getElementsByTagName("drmToken")[0].childNodes[0].nodeValue
        utils.log(drm, xbmc.LOGDEBUG)

        return {'url': url, 'drm': drm}
