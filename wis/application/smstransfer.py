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

import sys
sys.path.insert(0, "..")
from common.database import Database
from common import smsgwglobals
from common import error
import json
import re


class Smstransfer(object):
    smstransfer = {}
    smsdict = {}

    # def __init__(self, content, targetnr, priority,
    #             appid, sourceip, xforwardedfor):
    def __init__(self, **kwargs):
        self.smsdict["content"] = kwargs["content"]
        self.smsdict["priority"] = kwargs["priority"]
        self.smsdict["appid"] = kwargs["appid"]
        self.smsdict["sourceip"] = kwargs["sourceip"]
        self.smsdict["targetnr"] = kwargs["targetnr"]
        self.smsdict["xforwardedfor"] = kwargs["xforwardedfor"]

        if "smsid" in kwargs:
            self.smsdict["smsid"] = kwargs["smsid"]
        else:
            self.smsdict["smsid"] = ""

        if "modemid" in kwargs:
            self.smsdict["modemid"] = kwargs["modemid"]
        else:
            self.smsdict["modemid"] = ""

        if "smsintime" in kwargs:
            self.smsdict["smsintime"] = kwargs["smsintime"]
        else:
            self.smsdict["smsintime"] = ""

        if "status" in kwargs:
            self.smsdict["status"] = kwargs["status"]
        else:
            self.smsdict["status"] = ""

        if "appid" in kwargs:
            self.smsdict["appid"] = kwargs["appid"]
        else:
            self.smsdict["appid"] = ""

        if not self.smsdict["appid"]:
            self.smsdict["appid"] = "legacy"

        if "statustime" in kwargs:
            self.smsdict["statustime"] = kwargs["statustime"]
        else:
            self.smsdict["statustime"] = ""

        # xforwardedfor None fix
        if self.smsdict["xforwardedfor"] is None:
            if self.smsdict["sourceip"] is not None:
                self.smsdict["xforwardedfor"] = self.smsdict["sourceip"]
            else:
                self.smsdict["xforwardedfor"] = "null"

        # BRVZ Fix
        self.smsdict["targetnr"] = self.smsdict["targetnr"].lstrip("0")
        p = re.compile('^[0\+]')
        if (p.match(self.smsdict["targetnr"]) is None):
            self.smsdict["targetnr"] = "+" + self.smsdict["targetnr"]
        else:
            self.smsdict["targetnr"] = self.smsdict["targetnr"]

        self.smstransfer["sms"] = self.smsdict

    def appendroutes(self, routes):
        self.smstransfer["routes"] = routes

    def getjson(self):
        self.smstransfer["sms"] = self.smsdict
        return json.dumps(self.smstransfer)

    def writetodb(self):
        try:
            db = Database()
            db.insert_sms(self.smsdict["modemid"],
                          self.smsdict["targetnr"],
                          self.smsdict["content"],
                          self.smsdict["priority"],
                          self.smsdict["appid"],
                          self.smsdict["sourceip"],
                          self.smsdict["xforwardedfor"],
                          self.smsdict["smsintime"],
                          self.smsdict["status"],
                          self.smsdict["statustime"])
        except error.DatabaseError as e:
            smsgwglobals.wislogger.debug(e.message)

    def updatedb(self):
        try:
            db = Database()
            smsen = []
            smsen.append(self.smsdict)
            smsgwglobals.wislogger.debug("WATCHDOG: " +
                                         "UPDATING")
            db.update_sms(smsen)
        except error.DatabaseError as e:
            smsgwglobals.wislogger.debug(e.message)
