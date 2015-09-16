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

import threading
import time
import json
import urllib.request

from common import smsgwglobals
# from common import error
import pidglobals
from common.helper import GlobalHelper


class Heartbeat(threading.Thread):

    def __init__(self, modemlist, handler):
        super(Heartbeat, self).__init__()
        pidglobals.heartbeatdaemon = self
        self.e = threading.Event()
        self.modemlist = modemlist
        # addin websocket connection object
        self.handler = handler

    def process(self):
        # smsgwglobals.pidlogger.debug("HEARTBEAT: PROCESSING - " +
        #                              str(self.modemlist) + "-" +
        #                              str(self.handler))
        # send heartbeat to PID
        # PID will forward it to WIS
        self.wis_heartbeat()

    def wis_heartbeat(self):
        # sending 1 heartbeat for each Modem (routingid)
        for modem in self.modemlist:
            data = {}
            data['routingid'] = modem['routingid']
            data['action'] = "heartbeat"
            data['status'] = "sent"

            asjson = json.dumps(data)
            smsgwglobals.pidlogger.debug("HEARTBEAT: SENT heartbeat msg: " +
                                         str(self.handler))
            #                             str(asjson) + " to handler " +

            tosend = GlobalHelper.encodeAES(asjson)
            try:
                # sending heartbeat message to PID
                # returncodes are handled in PidWsClient.received_message
                self.handler.send(tosend)
            except Exception as e:
                # at any error with communication to PID end heartbeat
                smsgwglobals.pidlogger.warning("HEARTBEAT: ERROR at " +
                                               "wis_heartbeat: "
                                               + str(e))
                self.stop()

    def run(self):
        smsgwglobals.pidlogger.debug("HEARTBEAT: STARTING - " +
                                     str(self.modemlist) + "-" +
                                     str(self.handler))
        while not self.e.isSet():
            # processing WIS heartbeat
            self.process()
            # sleep for 30 seconds
            time.sleep(30)

        smsgwglobals.pidlogger.debug("HEARTBEAT: STOPPED! - " +
                                     str(self.modemlist) + "-" +
                                     str(self.handler))

    def stop(self):
        self.e.set()

    def stopped(self):
        return self.e.is_set()

    def terminate(self):
        smsgwglobals.pidlogger.debug("HEARTBEAT: " +
                                     str(self.modemlist) + "-" +
                                     str(self.handler) + " terminating!")
        self.stop()
