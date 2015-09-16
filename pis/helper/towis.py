#!/usr/bin/python
# Copyright 2015 Neuhold Markus and Kleinsasser Mario
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import time
import urllib.request

import pisglobals
# from common import error
from common import smsgwglobals
from common.helper import GlobalHelper


class WIS(object):
    """ Class used to handle communication to WIS
    """
    @staticmethod
    def unregister(modemlist):
        try:
            for modem in modemlist:
                data = {}
                data['action'] = "unregister"
                data['routingid'] = modem['routingid']

                wisurl = {}
                wisurl['url'] = pisglobals.activewisurl
                smsgwglobals.pislogger.debug("/ws: UNREGISTER - " +
                                             str(wisurl['url']) +
                                             " - " +
                                             str(data))
                httpcode = WIS.request_managemodem(wisurl, data)

                # if no Wis work raise an exception
                if httpcode != 200:
                    raise
            return True

        except Exception as e:
            smsgwglobals.pislogger.warning("/ws: unable to UNregister at any " +
                                           "configured WIS: " +
                                           "httpcode = " + str(httpcode) +
                                           str(e))
            return False

    @staticmethod
    def register(modemlist):
        try:
            # for each modem try to register
            for modem in modemlist:
                data = {}
                data['action'] = "register"
                data['modemid'] = modem['modemid']
                data['regex'] = modem['regex']
                data['modemname'] = modem['modemname']
                data['pisurl'] = pisglobals.pisurl
                data['lbcount'] = 0
                data['lbfactor'] = modem['lbfactor']
                data['obsolete'] = 0
                data['routingid'] = modem['routingid']

                httpcode = WIS.loopwis(data)

                # if no Wis work raise an exception
                if httpcode != 200:
                    raise
            return True

        except Exception as e:
            smsgwglobals.pislogger.warning("/ws: Unable to Register at any " +
                                           "configured WIS: " +
                                           str(e))
            return False

    @staticmethod
    def loopwis(data):
        for wisurl in pisglobals.wisurllist:
            # Retry Modem registration
            maxretries = pisglobals.retrywisurl
            for run in range(maxretries):
                data['wisurl'] = wisurl['url']

                httpcode = WIS.request_managemodem(wisurl, data)

                if httpcode == 200:
                    break
                else:
                    # wait some secondes for retry
                    time.sleep(pisglobals.retrywait)

            if httpcode == 200:
                # keep url to wis in globals and leave loopwis
                pisglobals.activewisurl = wisurl['url']
                break
            else:
                pass
                # try next wis

        return httpcode

    @staticmethod
    def request_managemodem(wisurl, data):
        asjson = json.dumps(data)
        smsgwglobals.pislogger.info("/ws: Call /managemodem: " +
                                    str(asjson) + " at WIS " +
                                    wisurl['url'])

        tosend = GlobalHelper.encodeAES(asjson)

        request = urllib.request.Request(wisurl['url'] +
                                         "/smsgateway/api/managemodem")
        request.add_header("Content-Type",
                           "application/json;charset=utf-8")
        try:
            f = urllib.request.urlopen(request, tosend, timeout=5)
            httpcode = f.getcode()
        except Exception as e:
            httpcode = 500  # Internal Server error
            smsgwglobals.pislogger.warning("/ws: WIS managemodem error: "
                                           + str(e))

        smsgwglobals.pislogger.debug("/ws: WIS managemodem response: " +
                                     str(httpcode))

        return httpcode

    @staticmethod
    def request_heartbeat(data):
        asjson = json.dumps(data)
        smsgwglobals.pislogger.debug("/ws: Call WIS /heartbeat: " +
                                     str(asjson) + " at WIS " +
                                     str(pisglobals.activewisurl))

        tosend = GlobalHelper.encodeAES(asjson)

        request = urllib.request.Request(pisglobals.activewisurl +
                                         "/smsgateway/api/heartbeat")
        request.add_header("Content-Type",
                           "application/json;charset=utf-8")
        try:
            f = urllib.request.urlopen(request, tosend, timeout=5)
            httpcode = f.getcode()
        except Exception as e:
            httpcode = 500  # Internal Server error
            smsgwglobals.pislogger.warning("/ws: WIS heartbeat error: " +
                                           str(e))

        smsgwglobals.pislogger.debug("/ws: WIS heartbeat response: " +
                                     str(httpcode))

        return httpcode
