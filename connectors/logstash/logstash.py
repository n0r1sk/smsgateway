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

import urllib.request
import json
import re
import sys
from common import database


class Sender():

    def tester(self):
        db = database.Database()
        smsen = db.read_sms(status=4)
        smsen = smsen + db.read_sms(status=5)

        for sms in smsen:
            datafieldsrow = {}
            datafieldsrow['smsintime'] = re.sub(' ', 'T', sms['smsintime'])
            datafieldsrow['statustime'] = re.sub(' ', 'T', sms['statustime'])
            datafieldsrow['targetnr'] = re.sub('.{3}$','XXX',sms['targetnr'])
            datafieldsrow['appid'] = sms['appid']
            datafieldsrow['modemid'] = sms['modemid']
            datafieldsrow['sourceip'] = sms['sourceip']
            datafieldsrow['xforwardedfor'] = sms['xforwardedfor']
            self.send(datafieldsrow=datafieldsrow,
                      timestamp=datafieldsrow['statustime'])

    def send(self, **kwargs):
        event = {}
        event['@source'] = 'wis'
        event['@type'] = 'smsgateway'
        event['@timestamp'] = kwargs['timestamp']
        event['@fields'] = kwargs['datafieldsrow']
        message = json.dumps(event)
        DATA = message.encode("utf-8")
        req = urllib.request.Request(url='http://10.200.30.231:31311', data=DATA, method='PUT')
        req.add_header('content-type', 'application/json')

        f = urllib.request.urlopen(req)
        print(f.status)
        print(f.reason)
