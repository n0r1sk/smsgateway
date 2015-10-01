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

from application import wisglobals
from common.config import SmsConfig
from common import smsgwglobals
from common import database
import json
import urllib
import re


class Logstash():

    testcnt = 0
    logstashstatstoken = None
    logstashstatstoken = None

    def __init__(self, token):
        configfile = wisglobals.smsgatewayabspath + '/conf/smsgw.conf'
        cfg = SmsConfig(configfile)
        self.logstashstatstoken = cfg.getvalue('logstashstatstoken', '', 'wis')
        self.logstashstatsserver = cfg.getvalue('logstashserver', '', 'wis')

        if not self.logstashstatstoken:
            smsgwglobals.wislogger.debug("STATS: Logstash token not configured")
            raise RuntimeError('Logstash token not configured')

        if not self.logstashstatsserver:
            smsgwglobals.wislogger.debug("STATS: Logstash server not configured")
            raise RuntimeError('Logstash server not configured')

        if not (token == self.logstashstatstoken):
            smsgwglobals.wislogger.debug("STATS: Logstash server token not valid")
            raise RuntimeError('Logstash server token not valid')

    def report(self):
        smsgwglobals.wislogger.debug("STATS: Logstash reporter running")
        smsgwglobals.wislogger.debug("STATS: Logstash reporter token: " + self.logstashstatstoken)
        smsgwglobals.wislogger.debug("STATS: Logstash reporter server " + self.logstashstatsserver)

        db = database.Database()
        timestamp = db.read_statstimestamp()
        smsgwglobals.wislogger.debug("STATS: Logstash last timestamp " + str(timestamp))

        smsen = None

        if len(timestamp) == 0:
            smsen = db.read_sucsmsstats()
        else:
            smsen = db.read_sucsmsstats(timestamp[0]['lasttimestamp'])

        retval = {}
        retval['all'] = len(smsen)
        retval['pro'] = 0
        smsgwglobals.wislogger.debug("STATS: Logstash data count to process " + str(len(smsen)))

        datafieldsrow = {}

        for sms in smsen:
            datafieldsrow['smsintime'] = re.sub(' ', 'T', sms['smsintime'])
            datafieldsrow['statustime'] = re.sub(' ', 'T', sms['statustime'])
            datafieldsrow['targetnr'] = re.sub('.{3}$', 'XXX', sms['targetnr'])
            datafieldsrow['appid'] = sms['appid']
            datafieldsrow['modemid'] = sms['modemid']
            datafieldsrow['sourceip'] = sms['sourceip']
            datafieldsrow['xforwardedfor'] = sms['xforwardedfor']

            try:
                self.send(datafieldsrow=datafieldsrow, timestamp=datafieldsrow['statustime'])
            except RuntimeError as e:
                smsgwglobals.wislogger.debug("STATS: Logstash reporter send exeption " + str(e))
                break

            db.write_statstimestamp(sms['statustime'])
            retval['pro'] += 1

        return retval

    def send(self, **kwargs):
        event = {}
        event['@source'] = 'wis'
        event['@type'] = 'smsgateway'
        event['@timestamp'] = kwargs['timestamp']
        event['@fields'] = kwargs['datafieldsrow']
        message = json.dumps(event)
        DATA = message.encode("utf-8")

        smsgwglobals.wislogger.debug("STATS: Logstash reporter send data " + str(DATA))

        req = urllib.request.Request(url=self.logstashstatsserver, data=DATA, method='PUT')
        req.add_header('content-type', 'application/json')

        try:
            f = urllib.request.urlopen(req)
            smsgwglobals.wislogger.debug("STATS: Logstash reporter send status %s, %s ", str(f.status), str(f.reason) )
        except:
            raise RuntimeError('STATS: Problem in submitting data to logstash')

        if f.status != 200:
            raise RuntimeError('STATS: Logstash send wrong wrong HTML status code')
