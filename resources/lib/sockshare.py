'''
    sockshare XBMC Plugin
    Copyright (C) 2013 dmdsoftware

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


'''

import os
import re
import urllib, urllib2
import cookielib


import xbmc, xbmcaddon, xbmcgui, xbmcplugin

# global variables
addon = xbmcaddon.Addon(id='plugin.video.sockshare')

# helper methods
def log(msg, err=False):
    if err:
        xbmc.log(addon.getAddonInfo('name') + ': ' + msg, xbmc.LOGERROR)
    else:
        xbmc.log(addon.getAddonInfo('name') + ': ' + msg, xbmc.LOGDEBUG)


#
#
#
class sockshare:

    # magic numbers
    MEDIA_TYPE_MUSIC = 1
    MEDIA_TYPE_VIDEO = 2
    MEDIA_TYPE_FOLDER = 0

    CACHE_TYPE_MEMORY = 0
    CACHE_TYPE_DISK = 1
    CACHE_TYPE_STREAM = 2

    ##
    # initialize (setting 1) username, 2) password, 3) authorization token, 4) user agent string
    ##
    def __init__(self, user, password, auth, user_agent):
        self.user = user
        self.password = password
        self.auth = auth
        self.user_agent = user_agent
        self.cookiejar = cookielib.CookieJar()


        # if we have an authorization token set, try to use it
        if auth != '':
          log('using token')

          return
        else:
          log('no token - logging in')
          self.login();
          return



    ##
    # perform login
    ##
    def login(self):

        self.auth = ''

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        # default User-Agent ('Python-urllib/2.6') will *not* work
        opener.addheaders = [('User-Agent', self.user_agent)]

        url = 'http://www.sockshare.com/authenticate.php?login'

        try:
            response = opener.open(url)

        except urllib2.URLError, e:
            log(str(e), True)
            return
        response_data = response.read()
        response.close()

        # fetch captcha url
        for r in re.finditer('<td>(CAPTCHA)</td>.*?<td><img src="([^\"]+)\"',
                             response_data, re.DOTALL):
            ceptchaType,captchaURL = r.groups()

        url = 'http://www.sockshare.com' + captchaURL

        try:
            response = opener.open(url)
        except urllib2.URLError, e:
                log(str(e), True)

        captchaFile = xbmc.translatePath(os.path.join('special://profile/addon_data/plugin.video.sockshare', 'captcha.png'))

        try:
            os.remove(captchaFile)
        except:
            pass


        output = open(captchaFile,'wb')
        output.write(response.read())
        output.close()
        response.close()


        img = xbmcgui.ControlImage(450,15,400,130,captchaFile)
        wdlg = xbmcgui.WindowDialog()
        wdlg.addControl(img)
        wdlg.show()

        xbmc.sleep(3000)

        kb = xbmc.Keyboard('', addon.getLocalizedString(30012), False)
        kb.doModal()
        capcode = kb.getText()

        if (kb.isConfirmed()):
           userInput = kb.getText()
           if userInput != '':
               solution = kb.getText()
           elif userInput == '':
               raise Exception (addon.getLocalizedString(30011))
        else:
           raise Exception ('Captcha Error')
        wdlg.close()

        try:
            os.remove(captchaFile)
        except:
            pass

        url = 'http://www.sockshare.com/authenticate.php?login'

        values = {
                  'pass' : self.password,
                  'user' : self.user,
                  'remember' : 1,
                  'captcha_code' : solution,
                  'login_submit' : 'Login',
        }

        log('logging in')

        # try login
        try:
            response = opener.open(url,urllib.urlencode(values))

        except urllib2.URLError, e:
            if e.code == 403:
                #login denied
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(30000), ADDON.getLocalizedString(30017))
            log(str(e), True)
            return
        response_data = response.read()
        response.close()


        loginResult = 0
        #validate successful login
        for r in re.finditer('class="(header-right-auth)"><strong>([^\<]+)</strong>',
                             response_data, re.DOTALL):
            loginType,loginResult = r.groups()

        if (loginResult == 0 or loginResult != self.user):
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(30000), ADDON.getLocalizedString(30017))
            log('login failed', True)
            return

        for cookie in self.cookiejar:
            for r in re.finditer(' ([^\=]+)\=([^\s]+)\s',
                        str(cookie), re.DOTALL):
                cookieType,cookieValue = r.groups()
                if cookieType == 'auth':
                    self.auth = cookieValue


        return



    ##
    # return the appropriate "headers" for FireDrive requests that include 1) user agent, 2) authorization cookie
    #   returns: list containing the header
    ##
    def getHeadersList(self):
        if (self.auth != '' or self.auth != 0):
            return { 'User-Agent' : self.user_agent, 'Cookie' : 'auth='+self.auth+'; exp=1' }
        else:
            return { 'User-Agent' : self.user_agent }

    ##
    # return the appropriate "headers" for FireDrive requests that include 1) user agent, 2) authorization cookie
    #   returns: URL-encoded header string
    ##
    def getHeadersEncoded(self):
        return urllib.urlencode(self.getHeadersList())

    ##
    # retrieve a list of videos, using playback type stream
    #   parameters: prompt for video quality (optional), cache type (optional)
    #   returns: list of videos
    ##
    def getVideosList(self, folderID=0, cacheType=0):

        # retrieve all documents
        if folderID == 0:
            url = 'http://www.sockshare.com/cp.php'
        else:
            url = 'http://www.sockshare.com/cp.php?folder='+folderID

        videos = {}
        if True:
            log('url = %s header = %s' % (url, self.getHeadersList()))
            req = urllib2.Request(url, None, self.getHeadersList())

            # if action fails, validate login
            try:
              response = urllib2.urlopen(req)
            except urllib2.URLError, e:
              if e.code == 403 or e.code == 401:
                self.login()
                req = urllib2.Request(url, None, self.getHeadersList())
                try:
                  response = urllib2.urlopen(req)
                except urllib2.URLError, e:
                  log(str(e), True)
                  return
              else:
                log(str(e), True)
                return

            response_data = response.read()
            response.close()


            # parsing page for videos
            # video-entry
            for r in re.finditer('<tr>.*?input name="file_\d+" type="checkbox" value="([^\"]+)"></td>.*?<strong><a href="[^\"]+">(.*?)</a>.*?</tr>' ,
                                 response_data, re.DOTALL):
                fileID,title = r.groups()

                title = re.sub('<.*?>', '', title)
                title = re.sub('\/\* <\!\[CDATA\[ \*/', '[' + fileID + '] (invalid name;rename it on the website)', title)

                log('found video %s %s' % (title, fileID))

                # streaming
                videos[title] = {'mediaType' : self.MEDIA_TYPE_VIDEO, 'url': 'plugin://plugin.video.sockshare?mode=streamVideo&filename=' + fileID, 'thumbnail' : None}


            for r in re.finditer('<a href="\/cp.php\?folder=([^\"]+)" class="folder_link">([^\<]+)</a>' ,
                                 response_data, re.DOTALL):
                folderID,folderName = r.groups()

                log('found folder %s %s' % (folderID, folderName))

                videos[folderName] = {'mediaType' : self.MEDIA_TYPE_FOLDER, 'url': 'plugin://plugin.video.sockshare?mode=folder&foldername=' + folderID, 'thumbnail' : None}


        return videos


    ##
    # retrieve a video link
    #   parameters: title of video, whether to prompt for quality/format (optional), cache type (optional)
    #   returns: list of URLs for the video or single URL of video (if not prompting for quality)
    ##
    def getVideoLink(self,fileID='',url='',cacheType=0):

        cacheType = (int)(cacheType)

        if fileID != '':
            url = 'http://www.sockshare.com/file/'+ fileID


        log('url = %s header = %s' % (url, self.getHeadersList()))
        req = urllib2.Request(url, None, self.getHeadersList())

        # if action fails, validate login
        try:
            response = urllib2.urlopen(req)
        except urllib2.URLError, e:
            if e.code == 403 or e.code == 401:
                self.login()
                req = urllib2.Request(url, None, self.getHeadersList())
                try:
                  response = urllib2.urlopen(req)
                except urllib2.URLError, e:
                  log(str(e), True)
                  return
            else:
                log(str(e), True)
                return

        response_data = response.read()
        response.close()


        # retrieve request hash
        for r in re.finditer('<input type="hidden" value="([^\"]+)" name="(hash)">' ,
                                 response_data, re.DOTALL):
            hashValue,hashType = r.groups()


        values = {
                  'hash' : hashValue,
                  'confirm' : 'Please wait for 0 seconds',
        }

        log('url = %s header = %s' % (url, self.getHeadersList()))
        req = urllib2.Request(url, urllib.urlencode(values), self.getHeadersList())

        # if action fails, validate login
        try:
            response = urllib2.urlopen(req)
        except urllib2.URLError, e:
            if e.code == 403 or e.code == 401:
                self.login()
                req = urllib2.Request(url, urllib.urlencode(values), self.getHeadersList())
                try:
                  response = urllib2.urlopen(req)
                except urllib2.URLError, e:
                  log(str(e), True)
                  return
            else:
                log(str(e), True)
                return

        response_data = response.read()
        response.close()

        streamURL = ''


        # video stream
        if cacheType == self.CACHE_TYPE_STREAM:

          for r in re.finditer('(playlist): \'([^\']+)' ,
                                 response_data, re.DOTALL):
            streamType,streamURL = r.groups()

            log('found video stream %s' % (streamURL))

            # streaming
            streamURL = 'http://www.sockshare.com/'+ streamURL

            log('url = %s header = %s' % (streamURL, self.getHeadersList()))
            req = urllib2.Request(streamURL, None, self.getHeadersList())

            # if action fails, validate login
            try:
                response = urllib2.urlopen(req)
            except urllib2.URLError, e:
                if e.code == 403 or e.code == 401:
                    self.login()
                    req = urllib2.Request(streamURL, None, self.getHeadersList())
                    try:
                        response = urllib2.urlopen(req)
                    except urllib2.URLError, e:
                        log(str(e), True)
                        return
                else:
                    log(str(e), True)
                    return

            response_data = response.read()
            response.close()

            # retrieve request hash
            for r in re.finditer('<media:(content) url="([^\"]+)"' ,
                                 response_data, re.DOTALL):
                streamType,streamURL = r.groups()

            streamURL = re.sub('&amp;', '&', streamURL)
            return streamURL + '|'+self.getHeadersEncoded()
        else:
          for r in re.finditer('href="([^\"]+)" class="(download_file_link)"' ,
                                 response_data, re.DOTALL):
            streamURL,streamType = r.groups()

            log('found video download %s' % (streamURL))

            # streaming
            streamURL = 'http://www.sockshare.com/'+ streamURL


        # audio download
        for r in re.finditer('"(setFile)", "([^\"]+)"' ,
                                 response_data, re.DOTALL):
            streamType,streamURL = r.groups()

            log('found audio %s' % (streamURL))

            # streaming
            streamURL = 'http://www.sockshare.com/'+ streamURL

        return streamURL + '|'+self.getHeadersEncoded()






