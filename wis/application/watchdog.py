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
from common import smsgwglobals
from common import database
from common import error
from common.helper import GlobalHelper
from datetime import datetime
from application import wisglobals
from application import smstransfer
from application.helper import Helper
import urllib.request
# import json
import socket


class Watchdog(threading.Thread):

    def __init__(self, threadID, name):
        super(Watchdog, self).__init__()
        wisglobals.watchdogThread = self
        wisglobals.watchdogThreadNotify = threading.Event()
        self.e = threading.Event()
        self.threadID = threadID
        self.name = name

    def send(self, smstrans, route):
        # encode to json
        jdata = json.dumps(smstrans.smsdict)
        data = GlobalHelper.encodeAES(jdata)

        request = \
            urllib.request.Request(
                route[0]["pisurl"] +
                "/sendsms")

        request.add_header("Content-Type",
                           "application/json;charset=utf-8")

        # smstrans = smstransfer.Smstransfer(**sms)

        try:
            smsgwglobals.wislogger.debug("WATCHDOG: " +
                                         "Sending VIA " +
                                         smstrans.smsdict["modemid"] +
                                         route[0]["pisurl"] +
                                         "/sendsms")
            f = urllib.request.urlopen(request, data, timeout=20)
            smsgwglobals.wislogger.debug("WATCHDOG: SMS send to PIS returncode:" + str(f.getcode()))
            # if all is OK set the sms status to SENT
            smstrans.smsdict["statustime"] = datetime.utcnow()
            if f.getcode() == 200:
                if smstrans.smsdict["status"] == 0:
                    smstrans.smsdict["status"] = 4
                    smsgwglobals.wislogger.debug("WATCHDOD: SEND direct:" + str(smstrans.smsdict))
                else:
                    smstrans.smsdict["status"] = 5
                    smsgwglobals.wislogger.debug("WATCHDOD: SEND deligated:" + str(smstrans.smsdict))
                smsgwglobals.wislogger.debug("WATCHDOD: SEND Update DB SUCCESS:" + str(smstrans.smsdict))
                smstrans.updatedb()
            else:
                if smstrans.smsdict["status"] == 0:
                    smstrans.smsdict["status"] = 104
                    smsgwglobals.wislogger.debug("WATCHDOD: SEND direct ERROR:" + str(smstrans.smsdict))
                else:
                    smstrans.smsdict["status"] = 105
                    smsgwglobals.wislogger.debug("WATCHDOD: SEND deligated ERROR:" + str(smstrans.smsdict))
                smsgwglobals.wislogger.debug("WATCHDOD: SEND Update DB ERROR:" + str(smstrans.smsdict))
                smstrans.updatedb()

        except urllib.error.URLError as e:
            if smstrans.smsdict["status"] == 0:
                smstrans.smsdict["status"] = 100
            else:
                smstrans.smsdict["status"] = 105
            smsgwglobals.wislogger.debug("WATCHDOG: SEND EXCEPTION " + str(smstrans.smsdict))
            smstrans.updatedb()
            # set SMS to not send!!!
            smsgwglobals.wislogger.debug(e)
            smsgwglobals.wislogger.debug("WATCHDOG: SEND Get peers NOTOK")
        except socket.timeout as e:
            smsgwglobals.wislogger.debug(e)
            smsgwglobals.wislogger.debug("WATCHDOG: SEND Socket connection timeout")

    def deligate(self, smstrans, route):
        # encode to json
        jdata = smstrans.getjson()
        data = GlobalHelper.encodeAES(jdata)

        request = \
            urllib.request.Request(
                route[0]["wisurl"] +
                "/smsgateway/api/deligatesms")

        request.add_header("Content-Type",
                           "application/json;charset=utf-8")

        try:
            smsgwglobals.wislogger.debug("WATCHDOG: " +
                                         "Deligate VIA " +
                                         route[0]["wisurl"] +
                                         "/smsgateway/api/deligate")
            f = urllib.request.urlopen(request, data, timeout=20)
            smsgwglobals.wislogger.debug("WATCHDOG: SMS deligate to PIS returncode:" + str(f.getcode()))
            # if all is OK set the sms status to SENT
            smstrans.smsdict["statustime"] = datetime.utcnow()
            if f.getcode() == 200:
                smstrans.smsdict["status"] = 3
                smsgwglobals.wislogger.debug("WATCHDOF: DELIGATE SUCCESS " + str(smstrans.smsdict))
                smsgwglobals.wislogger.debug("WATCHDOD: DELIGATE update  DB SUCCESS:" + str(smstrans.smsdict))
                smstrans.updatedb()
            else:
                smstrans.smsdict["status"] = 103
                smsgwglobals.wislogger.debug("WATCHDOF: DELIGATE ERROR " + str(smstrans.smsdict))
                smsgwglobals.wislogger.debug("WATCHDOD: DELIGATE update DB ERROR: " + str(smstrans.smsdict))
                smstrans.updatedb()
        except urllib.error.URLError as e:
            # set SMS to not send!!!
            smstrans.smsdict["status"] = 103
            smstrans.updatedb()
            smsgwglobals.wislogger.debug(e)
            smsgwglobals.wislogger.debug("WATCHDOG: DELIGATE Get peers NOTOK " + str(smstrans.smsdict))
        except socket.timeout as e:
            smsgwglobals.wislogger.debug(e)
            smsgwglobals.wislogger.debug("WATCHDOG: DELIGATE socket connection timeout " + str(smstrans.smsdict))

    def process(self):
        smsgwglobals.wislogger.debug("WATCHDOG: processing sms")

        # check if we have SMS to work on
        smscount = 0

        try:
            db = database.Database()

            # cleanup old sms
            db.delete_old_sms(wisglobals.cleanupseconds)

            smsen = db.read_sms(status=0)
            smsen = smsen + db.read_sms(status=1)
            smscount = len(smsen)
            if smscount == 0:
                smsgwglobals.wislogger.debug("WATCHDOG: " +
                                             "no SMS to process")
                return
        except error.DatabaseError as e:
            smsgwglobals.wislogger.debug(e.message)

        # we have sms, just process
        smsgwglobals.wislogger.debug("WATCHDOG: Count to process: %s", str(smscount))
        while smscount > 0:
            for sms in smsen:
                smsgwglobals.wislogger.debug("WATCHDOG: Process SMS: " + str(sms))

                # create smstrans object for easy handling
                smstrans = smstransfer.Smstransfer(**sms)

                # check if we have routes
                # if we have no routes, set error code and
                # continue with the next sms
                routes = wisglobals.rdb.read_routing()
                if routes is None or len(routes) == 0:
                    smstrans.smsdict["statustime"] = datetime.utcnow()
                    smstrans.smsdict["status"] = 100
                    smsgwglobals.wislogger.debug("WATCHDOG: NO routes to process SMS: " + str(smstrans.smsdict))
                    smstrans.updatedb()
                    continue

                # check if modemid exists in routing
                route = wisglobals.rdb.read_routing(
                    smstrans.smsdict["modemid"])
                if route is None or len(route) == 0:
                    smsgwglobals.wislogger.debug("WATCHDOG: " +
                                                 " ALERT ROUTE LOST")
                    # try to reprocess route
                    smstrans.smsdict["status"] = 106
                    smstrans.updatedb()
                    Helper.processsms(smstrans)
                elif route[0]["wisid"] != wisglobals.wisid:
                    self.deligate(smstrans, route)
                else:
                    # we have a route, this wis is the correct one
                    # therefore give the sms to the PIS
                    # this is a bad hack to ignore obsolete routes
                    # this may lead to an error, fixme
                    route[:] = [d for d in route if d['obsolete'] < 13]
                    smsgwglobals.wislogger.debug("WATCHDOG: process with route %s ", str(route))
                    smsgwglobals.wislogger.debug("WATCHDOG: Sending to PIS %s", str(sms))
                    # only continue if route contains data
                    if len(route) > 0:
                        self.send(smstrans, route)

            smsen = db.read_sms(status=0)
            smsen = smsen + db.read_sms(status=1)
            smscount = len(smsen)

    def run(self):
        smsgwglobals.wislogger.debug("WATCHDOG: starting")
        while not self.e.isSet():
            smsgwglobals.wislogger.debug("WATCHDOG: sleep for sms")
            wisglobals.watchdogThreadNotify.wait()
            smsgwglobals.wislogger.debug("WATCHDOG: running for sms")
            if self.e.is_set():
                continue

            # processing sms in database
            smsgwglobals.wislogger.debug("WATCHDOG: start processing sms")
            self.process()
            smsgwglobals.wislogger.debug("WATCHDOG: finished processing sms")

            wisglobals.watchdogThreadNotify.clear()
            smsgwglobals.wislogger.debug("WATCHDOG: clear for next sms run")

        smsgwglobals.wislogger.debug("WATCHDOG: stopped")

    def stop(self):
        self.e.set()

    def stopped(self):
        return self.e.is_set()

    def terminate(self):
        smsgwglobals.wislogger.debug("WATCHDOG: terminating")
        self.stop()
        wisglobals.watchdogThreadNotify.set()
