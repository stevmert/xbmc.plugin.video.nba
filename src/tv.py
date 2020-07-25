

import datetime
import time
import json
import sys
import urllib
import urllib2
from xml.dom.minidom import parseString

import pytz

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
        common.addListItem('Live', '', 'nba_tv_play_live', '')
        common.addListItem('Today\'s programming', '', 'nba_tv_episode_menu', '', isfolder=True)
        common.addListItem('Select date', '', 'nba_tv_episode_menu', '', isfolder=True, customparams={
            'custom_date': True
        })

    @staticmethod
    def episode_menu():
        et_tz = pytz.timezone('US/Eastern')
        date_et = common.get_date() if vars.params.get('custom_date', False) else utils.tznow(et_tz).date()

        # Avoid possible caching by using query string
        epg_url = 'https://nlnbamdnyc-a.akamaihd.net/fs/nba/feeds/epg/%d/%d_%d.js?t=%d' % (
            date_et.year, date_et.month, date_et.day, time.time())
        response = utils.fetch(epg_url)
        g_epg = json.loads(response[response.find('['):])

        for epg_item in g_epg:
            entry = epg_item['entry']

            start_et_hours, start_et_minutes = map(int, entry['start'].split(':'))
            duration_hours, duration_minutes = map(int, entry['duration'].split(':'))

            dt_et = et_tz.localize(datetime.datetime(date_et.year, date_et.month, date_et.day, start_et_hours, start_et_minutes))
            dt_utc = dt_et.astimezone(pytz.utc)

            start_timestamp = int((dt_utc - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()) * 1000  # in milliseconds
            duration = (duration_hours * 60 + duration_minutes) * 60 * 1000  # in milliseconds

            params = {
                'start_timestamp': start_timestamp,
                'duration': duration,
            }
            utils.log(params, xbmc.LOGDEBUG)

            name = '%s %s: %s' % (
                entry['start'], dt_et.tzname(), entry['showTitle'] if entry['showTitle'] else entry['title'])
            common.addListItem(name, '', 'nba_tv_play_episode', iconimage=entry['image'], customparams=params)

    @staticmethod
    def play_live():
        video_url = TV.get_live_url()
        if video_url is not None:
            shared_data = SharedData()
            shared_data.set('playing', {
                'what': 'nba_tv_live',
            })

            item = common.get_playable_item(video_url)
            if item is not None:
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)

    @staticmethod
    def play_episode():
        start_timestamp = vars.params.get('start_timestamp')
        duration = vars.params.get('duration')
        video_url = TV.get_episode_url(start_timestamp, duration)
        if video_url is not None:
            shared_data = SharedData()
            shared_data.set('playing', {
                'what': 'nba_tv_episode',
                'data': {
                    'start_timestamp': start_timestamp,
                    'duration': duration,
                },
            })

            item = common.get_playable_item(video_url)
            if item is not None:
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)

    @staticmethod
    def get_episode_url(start_timestamp, duration, force_login=False):
        if not vars.cookies or force_login:
            common.login()
        if not vars.cookies:
            return None

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
            'st': start_timestamp,
            'dur': duration,
            'pcid': vars.player_id,
            'format': 'xml',
        }

        body = urllib.urlencode(body)
        utils.log('the body of publishpoint request is: %s' % body, xbmc.LOGDEBUG)

        try:
            request = urllib2.Request(url, body, headers)
            response = urllib2.urlopen(request)
            content = response.read()
        except urllib2.HTTPError as err:
            utils.logHttpException(err, url)
            utils.littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50020))
            return None

        xml = parseString(str(content))
        url = xml.getElementsByTagName('path')[0].childNodes[0].nodeValue
        utils.log('response URL from publishpoint: %s' % url, xbmc.LOGDEBUG)
        drm = xml.getElementsByTagName('drmToken')[0].childNodes[0].nodeValue
        utils.log(drm, xbmc.LOGDEBUG)

        return {'url': url, 'drm': drm}

    @staticmethod
    def get_live_url(force_login=False):
        if not vars.cookies or force_login:
            common.login()
        if not vars.cookies:
            return None

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
        utils.log('the body of publishpoint request is: %s' % body, xbmc.LOGDEBUG)

        try:
            request = urllib2.Request(url, body, headers)
            response = urllib2.urlopen(request)
            content = response.read()
        except urllib2.HTTPError as err:
            utils.logHttpException(err, url)
            utils.littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50020))
            return None

        xml = parseString(str(content))
        url = xml.getElementsByTagName('path')[0].childNodes[0].nodeValue
        utils.log('response URL from publishpoint: %s' % url, xbmc.LOGDEBUG)
        drm = xml.getElementsByTagName('drmToken')[0].childNodes[0].nodeValue
        utils.log(drm, xbmc.LOGDEBUG)

        return {'url': url, 'drm': drm}
