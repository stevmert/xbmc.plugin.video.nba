

import json
import datetime, time, calendar, re, sys, traceback, urllib, urllib2
from datetime import timedelta
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
from xml.dom.minidom import parseString
import common, utils
import vars


def get_game(video_id, video_type, video_ishomefeed, start_time, duration):
    utils.log("cookies: %s %s" % (video_type, vars.cookies), xbmc.LOGDEBUG)

    # video_type could be archive, live, condensed or oldseason
    if video_type not in ["live", "archive", "condensed"]:
        video_type = "archive"
    gt = 1
    if not video_ishomefeed:
        gt = 4
    if video_type == "condensed":
        gt = 8

    url = vars.config['publish_endpoint']
    headers = {
        'Cookie': vars.cookies,
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
    }
    body = {
        'type': 'game',
        'extid': str(video_id),
        'drmtoken': True,
        'token': vars.access_token,
        'deviceid': xbmc.getInfoLabel('Network.MacAddress'),  # TODO
        'gt': gt,
        'gs': vars.params.get('game_state', 3),
        'pcid': vars.player_id,
        'format': 'xml',
    }

    if video_type == "live":
        line1 = "Start from Beginning"
        line2 = "Go LIVE"
        ret = xbmcgui.Dialog().select("Game Options", [line1, line2])
        if ret == -1:
            return None
        elif ret == 0:
            if start_time:
                body['st'] = str(start_time)
                if duration:
                    body['dur'] = str(duration)
                else:
                    utils.log("No end time, can't start from beginning", xbmc.LOGERROR)
            else:
                utils.log("No start time can't start from beginning", xbmc.LOGERROR)
    else:
        if start_time:
            body['st'] = str(start_time)
            utils.log("start_time: %s" % start_time, xbmc.LOGDEBUG)

            if duration:
                body['dur'] = str(duration)
                utils.log("Duration: %s"% str(duration), xbmc.LOGDEBUG)
            else:
                utils.log("No end time for game", xbmc.LOGDEBUG)
        else:
            utils.log("No start time, can't start from beginning", xbmc.LOGERROR)

    if vars.params.get("camera_number"):
        body['cam'] = vars.params.get("camera_number")

    body = urllib.urlencode(body)
    utils.log("the body of publishpoint request is: %s" % body, xbmc.LOGDEBUG)

    try:
        request = urllib2.Request(url, body, headers)
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.HTTPError as err:
        utils.logHttpException(err, url)
        utils.littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50020))
        return None

    xml = parseString(str(content))
    url = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue
    utils.log("response URL from publishpoint: %s" % url, xbmc.LOGDEBUG)
    drm = xml.getElementsByTagName("drmToken")[0].childNodes[0].nodeValue
    utils.log(drm, xbmc.LOGDEBUG)

    selected_video_url = ''
    if video_type == "live":
        if '.mpd' in url:
            selected_video_url = url
        else:
            # Transform the url
            match = re.search('(https?)://([^:]+)/([^?]+?)\?(.+)$', url)
            protocol = match.group(1)
            domain = match.group(2)
            arguments = match.group(3)
            querystring = match.group(4)

            livecookies = "nlqptid=%s" % (querystring)
            livecookiesencoded = urllib.quote(livecookies)

            utils.log("live cookie: %s %s" % (querystring, livecookies), xbmc.LOGDEBUG)

            url = "%s://%s/%s?%s" % (protocol, domain, arguments, querystring)

            selected_video_url = "%s&Cookie=%s" % (url, livecookiesencoded)
    else:
        # Archive and condensed flow: We now work with HLS.
        # The cookies are already in the URL and the server will supply them to ffmpeg later.
        selected_video_url = url

    if selected_video_url:
        utils.log("the url of video %s is %s" % (video_id, selected_video_url), xbmc.LOGDEBUG)

    return {'url': selected_video_url, 'drm': drm}

def getHighlightGameUrl(video_id):
    url = 'https://watch.nba.com/service/publishpoint'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': "AppleCoreMedia/1.0.0.8C148a (iPad; U; CPU OS 6_2_1 like Mac OS X; en_us)",
    }

    body = urllib.urlencode({
        'extid': str(video_id),
        'plid': vars.player_id,
        'gt': "64",
        'type': 'game',
        'bitrate': "1600"
    })

    utils.log("the body of publishpoint request is: %s" % body, xbmc.LOGDEBUG)

    try:
        request = urllib2.Request(url, body, headers)
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.HTTPError as ex:
        utils.log("Highlight url not found. Error: %s - body: %s" % (str(ex), ex.read()), xbmc.LOGERROR)
        return ''

    xml = parseString(str(content))
    url = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue

    # Remove everything after ? otherwise XBMC fails to read the rtpm stream
    #url, _,_ = url.partition("?")

    utils.log("highlight video url: %s" % url, xbmc.LOGDEBUG)
    return url

def process_key(dictionary, key, processed_keys):
    processed_keys.add(key)
    return dictionary.get(key)

def addGamesLinks(date='', video_type="archive"):
    try:
        now_datetime_est = utils.nowEST()
        schedule = 'https://nlnbamdnyc-a.akamaihd.net/fs/nba/feeds_s2019/schedule/%04d/%d_%d.js?t=%d' % \
            (date.year, date.month, date.day, time.time())
        utils.log('Requesting %s' % schedule, xbmc.LOGDEBUG)

        schedule_request = urllib2.Request(schedule, None)
        schedule_response = str(urllib2.urlopen(schedule_request).read())
        schedule_json = json.loads(schedule_response[schedule_response.find("{"):])

        unknown_teams = {}
        for index, daily_games in enumerate(schedule_json['games']):
            utils.log("daily games for day %d are %s" % (index, daily_games), xbmc.LOGDEBUG)

            for game in daily_games:
                processed_keys = set()

                v = process_key(game, 'v', processed_keys)
                h = process_key(game, 'h', processed_keys)
                vr = process_key(game, 'vr', processed_keys)
                hr = process_key(game, 'hr', processed_keys)
                vs = process_key(game, 'vs', processed_keys)
                hs = process_key(game, 'hs', processed_keys)

                if v is None or h is None:  # TODO
                    utils.log(json.dumps(game), xbmc.LOGDEBUG)
                    continue

                game_id = process_key(game, 'id', processed_keys)
                game_start_date_est = process_key(game, 'd', processed_keys)

                name = process_key(game, 'name', processed_keys)
                image = process_key(game, 'image', processed_keys)
                seo_name = process_key(game, 'seoName', processed_keys)

                video = process_key(game, 'video', processed_keys)
                has_video = video is not None
                has_condensed_video = has_video and bool(video.get('c'))
                has_away_feed = has_video and bool(video.get('af'))

                # Try to convert start date to datetime
                try:
                    game_start_datetime_est = datetime.datetime.strptime(game_start_date_est, "%Y-%m-%dT%H:%M:%S.%f")
                except:
                    game_start_datetime_est = datetime.datetime.fromtimestamp(time.mktime(time.strptime(game_start_date_est, "%Y-%m-%dT%H:%M:%S.%f")))

                #Set game start date in the past if python can't parse the date
                #so it doesn't get flagged as live or future game and you can still play it
                #if a video is available
                if type(game_start_datetime_est) is not datetime.datetime:
                    game_start_datetime_est = now_datetime_est + timedelta(-30)

                # Guess end date by adding 4 hours to start date
                game_end_datetime_est = game_start_datetime_est + timedelta(hours=4)

                # Get playoff game number, if available
                playoff_game_number = 0
                playoff_status = ""

                if 'playoff' in game:
                    playoff_home_wins = int(game['playoff']['hr'].split("-")[0])
                    playoff_visitor_wins = int(game['playoff']['vr'].split("-")[0])
                    playoff_status = "%d-%d" % (playoff_visitor_wins, playoff_home_wins)
                    playoff_game_number = playoff_home_wins + playoff_visitor_wins

                if game_id is not None:
                    # Get pretty names for the team names
                    [visitor_name, host_name] = [vars.config['teams'].get(t.lower(), t) for t in [v, h]]
                    [unknown_teams.setdefault(t, []).append(game_start_datetime_est.strftime("%Y-%m-%d"))
                        for t in [v, h] if t.lower() not in vars.config['teams']]

                    future_video = game_start_datetime_est > now_datetime_est and \
                        game_start_datetime_est.date() == now_datetime_est.date()
                    live_video = game_start_datetime_est < now_datetime_est < game_end_datetime_est

                    name = game_start_datetime_est.strftime("%Y-%m-%d")
                    if video_type == "live":
                        name = utils.toLocalTimezone(game_start_datetime_est).strftime("%Y-%m-%d (at %I:%M %p)")

                    name += " %s%s vs %s%s" % (visitor_name,
                                               " (%s)" % vr if vars.show_records_and_scores else '',
                                               host_name,
                                               " (%s)" % hr if vars.show_records_and_scores else '')

                    if playoff_game_number != 0:
                        name += ' (game %d)' % (playoff_game_number)
                    if vars.show_records_and_scores and not future_video:
                        name += ' %s:%s' % (vs, hs)

                        if playoff_status:
                            name += " (series: %s)" % playoff_status

                    thumbnail_url = utils.generateCombinedThumbnail(v, h)

                    if video_type == "live":
                        if future_video:
                            name = "UPCOMING: " + name
                        elif live_video:
                            name = "LIVE: " + name

                    add_link = True
                    if video_type == "live" and not (live_video or future_video):
                        add_link = False
                    elif video_type != "live" and (live_video or future_video):
                        add_link = False
                    elif not future_video and not has_video:
                        add_link = False


                    if add_link:
                        params = {
                            'video_id': game_id,
                            'video_type': video_type,
                            'seo_name': seo_name,
                            'visitor_team': visitor_name,
                            'home_team': host_name,
                            'has_away_feed': 1 if has_away_feed else 0,
                            'has_condensed_game': 1 if has_condensed_video else 0,
                        }

                        if 'st' in game:
                            start_time = calendar.timegm(time.strptime(game['st'], '%Y-%m-%dT%H:%M:%S.%f')) * 1000
                            params['start_time'] = start_time
                            if 'et' in game:
                                end_time = calendar.timegm(time.strptime(game['et'], '%Y-%m-%dT%H:%M:%S.%f')) * 1000
                                params['end_time'] = end_time
                                params['duration'] = end_time - start_time
                            else:
                                # create my own et for game (now)
                                end_time = str(datetime.datetime.now()).replace(' ', 'T')
                                end_time = calendar.timegm(time.strptime(end_time, '%Y-%m-%dT%H:%M:%S.%f')) * 1000
                                params['end_time'] = end_time
                                params['duration'] = end_time - start_time

                        # Add a directory item that contains home/away/condensed items
                        common.addListItem(name, url="", mode="gamechoosevideo", iconimage=thumbnail_url, isfolder=True, customparams=params)

                remaining_keys = set(game.keys()).difference(processed_keys)
                utils.log('Remaining keys: {}'.format(remaining_keys), xbmc.LOGDEBUG)

        if unknown_teams:
            utils.log("Unknown teams: %s" % str(unknown_teams), xbmc.LOGWARNING)

    except Exception, e:
        utils.littleErrorPopup("Error: %s" % str(e))
        utils.log(traceback.format_exc(), xbmc.LOGDEBUG)
        pass

def play_game():
    if not common.authenticate():
        return

    currentvideo_id = vars.params.get("video_id")
    currentvideo_type = vars.params.get("video_type")
    start_time = vars.params.get("start_time")
    duration = vars.params.get("duration")
    currentvideo_ishomefeed = vars.params.get("video_ishomefeed", "1")
    currentvideo_ishomefeed = currentvideo_ishomefeed == "1"

    # Authentication is needed over this point!
    game = get_game(currentvideo_id, currentvideo_type, currentvideo_ishomefeed, start_time, duration)
    if game is not None:
        common.play(game)

def chooseGameVideoMenu():
    video_id = vars.params.get("video_id")
    video_type = vars.params.get("video_type")
    seo_name = vars.params.get("seo_name")
    has_away_feed = vars.params.get("has_away_feed", "0") == "1"
    has_condensed_game = vars.params.get("has_condensed_game", "0") == "1"
    start_time = vars.params.get("start_time")
    duration = vars.params.get("duration")
    game_data_json = json.loads(utils.fetch(vars.config['game_data_endpoint'] % seo_name))
    game_state = game_data_json['gameState']
    game_home_team = vars.params.get("home_team")
    game_visitor_team = vars.params.get("visitor_team")
    game_cameras = []
    if 'multiCameras' in game_data_json:
        game_cameras = game_data_json['multiCameras'].split(",")

    nba_config = json.loads(utils.fetch(vars.config['config_endpoint']))
    nba_cameras = {}
    for camera in nba_config['content']['cameras']:
        nba_cameras[camera['number']] = camera['name']

    if has_away_feed:
        # Create the "Home" and "Away" list items
        for ishomefeed in [True, False]:
            listitemname = "Full game, " + ("away feed" if not ishomefeed else "home feed")

            # Show actual team names instead of 'home feed' and 'away feed'
            if game_home_team and game_visitor_team:
                if ishomefeed:
                    listitemname += " (" + game_home_team + ")"
                else:
                    listitemname += " (" + game_visitor_team + ")"

            params = {
                'video_id': video_id,
                'video_type': video_type,
                'video_ishomefeed': 1 if ishomefeed else 0,
                'game_state': game_state,
                'start_time': start_time,
                'duration': duration,
            }
            common.addListItem(listitemname, url="", mode="playgame", iconimage="", customparams=params)
    else:
        # Add a "Home" list item
        params = {
            'video_id': video_id,
            'video_type': video_type,
            'game_state': game_state,
            'start_time': start_time,
            'duration': duration,
        }
        common.addListItem("Full game", url="", mode="playgame", iconimage="", customparams=params)

    if vars.show_cameras:
        utils.log(nba_cameras, xbmc.LOGDEBUG)
        utils.log(game_cameras, xbmc.LOGDEBUG)

        # Add all the cameras available
        for camera_number in game_cameras:
            camera_number = int(camera_number)

            # Skip camera number 0 (broadcast?) - the full game links are the same
            if camera_number == 0:
                continue

            params = {
                'video_id': video_id,
                'video_type': video_type,
                'game_state': game_state,
                'camera_number': camera_number,
                'start_time': start_time,
                'duration': duration,
            }

            name = "Camera %d: %s" % (camera_number, nba_cameras.get(camera_number, 'Unknown'))
            common.addListItem(name, url="", mode="playgame", iconimage="", customparams=params)

    # Live games have no condensed or highlight link
    if video_type != "live":
        # Create the "Condensed" list item
        if has_condensed_game:
            params = {
                'video_id': video_id,
                'video_type': 'condensed',
                'game_state': game_state
            }
            common.addListItem("Condensed game", url="", mode="playgame", iconimage="", customparams=params)

        # Get the highlights video if available
        highlights_url = getHighlightGameUrl(video_id)
        if highlights_url:
            common.addVideoListItem("Highlights", highlights_url, iconimage="")

    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

def chooseGameMenu(mode, video_type, date2Use=None):
    try:
        if mode == "selectdate":
            date = common.get_date()
        elif mode == "oldseason":
            date = date2Use
        else:
            date = utils.nowEST()
            utils.log("current date (america timezone) is %s" % str(date), xbmc.LOGDEBUG)

        # Starts on mondays
        day = date.isoweekday()#2 = tuesday
        date = date - timedelta(day-1)

        if vars.use_alternative_archive_menu:
            if mode == 'last4-10days':
                if day <= 5:
                    date = date - timedelta(7)
                addGamesLinks(date, video_type)
                if day <= 5 and day > 1:#no need to query empty list when day < 2
                    date = date + timedelta(7)
                    addGamesLinks(date, video_type)
            else:
                #to counter empty list on mondays for 'this week'
                if day == 1:
                    date = date - timedelta(7)

                if mode == "last2weeks":
                    date = date - timedelta(7)
                if mode == "last3weeks":
                    date = date - timedelta(7)

                addGamesLinks(date, video_type)

                if mode == "last2weeks":
                    date = date + timedelta(7)
                    addGamesLinks(date, video_type)
                if mode == "last3weeks":
                    date = date + timedelta(7)
                    addGamesLinks(date, video_type)
                    date = date + timedelta(7)
                    addGamesLinks(date, video_type)
        else:
            if mode == "lastweek":
                date = date - timedelta(7)

            addGamesLinks(date, video_type)

        # Can't sort the games list correctly because XBMC treats file items and directory
        # items differently and puts directory first, then file items (home/away feeds
        # require a directory item while only-home-feed games is a file item)
        #xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_DATE)
    except:
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=False)
        return None
