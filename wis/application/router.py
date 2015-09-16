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
from application.helper import Helper
from common import smsgwglobals
from application import wisglobals


class Router(threading.Thread):

    def __init__(self, threadID, name):
        super(Router, self).__init__()
        wisglobals.routerThread = self
        self.e = threading.Event()
        self.threadID = threadID
        self.name = name

    def run(self):
        # counter to timeout split horzion
        checkround = 0

        # the follwing is like the RIP protocol
        # like Bellman-Ford-Algorithmus
        smsgwglobals.wislogger.debug("ROUTER: Starting")

        # 1. request routing
        # if we could not get anything, shit happens
        Helper.requestrouting(initial=True)

        # 2. startup update timer
        while not self.e.isSet():

            # starting router run
            smsgwglobals.wislogger.debug("ROUTER: Starting router run")

            # raise timeouts
            smsgwglobals.wislogger.debug("ROUTER: Starting raise obsolete")
            wisglobals.rdb.raise_obsolete()

            # check local table if there are obsoletes
            smsgwglobals.wislogger.debug("ROUTER: Starting delete obsolete")
            wisglobals.rdb.delete_routing()

            # send out table
            smsgwglobals.wislogger.debug("ROUTER: Starting sending table")
            Helper.receiverouting()

            # remove dead direcly connected
            smsgwglobals.wislogger.debug("ROUTER: Starting delete directly")
            if checkround == 4:
                checkround == 0
                Helper.checkrouting()
            else:
                checkround = checkround + 1

            smsgwglobals.wislogger.debug("ROUTER: Starting sleep")

            time.sleep(25)

            smsgwglobals.wislogger.debug("ROUTER: Finishing router run")

        smsgwglobals.wislogger.debug("ROUTER: Stopped")

    def stop(self):
        self.e.set()

    def stopped(self):
        return self.e.is_set()

    def terminate(self):
        smsgwglobals.wislogger.debug("ROUTER: terminating")
        self.stop()
