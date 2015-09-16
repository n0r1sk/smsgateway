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

import cherrypy
import json
from os import path
import sys
import time
import uuid
from datetime import datetime
from datetime import timedelta
from ws4py.server.cherrypyserver import WebSocketTool, WebSocketPlugin
from ws4py.websocket import WebSocket

sys.path.insert(0, "..")

import pisglobals
from helper.towis import WIS
from helper.topid import PID
# from common import error
from common import smsgwglobals
from common.config import SmsConfig
from common.helper import GlobalHelper
from common.filelogger import FileLogger


class Root(object):
    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def sendsms(self, **params):
        """ json before encoding
        {
        "smsid":"uuid.uuid1()",
        "modemid":"00436762222222",
        "targetnr":"+43200200200",
        "content":"test_sendsms200 ♠ ♣ ♥ ♦ ↙ ↺ ↻ ⇒ ä"}
        """
        # for receiving sms from WIS
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl))
        # smsgwglobals.pislogger.debug("/sendsms: rawbody: " + str(rawbody))
        plaintext = GlobalHelper.decodeAES(rawbody)

        try:
            # smsgwglobals.pislogger.debug("/sendsms: plaintext: " + plaintext)
            data = json.loads(plaintext)
            # adding action switch for message to PID
            data['action'] = "sendsms"
            smsgwglobals.pislogger.debug("/sendsms: dictionary: " +
                                         str(data))

        except Exception as e:
            smsgwglobals.pislogger.warning("/sendsms: Invalid data received! "
                                           + str(e))
            cherrypy.response.status = 400  # Bad Request
            return

        try:
            address = PID.getclientaddress(data['modemid'])

            if address:
                # sending SMS to Pid
                PID.sendtopid(address, data)
                PID.addclientsms(address, data['smsid'])

                # Poll PIDsmstatus every 0.20 second till maxwait
                maxwaitpid = pisglobals.maxwaitpid
                now = datetime.utcnow()
                until = now + timedelta(seconds=maxwaitpid)

                while now < until:
                    status = PID.getclientsmsstatus(address, data['smsid'])

                    if status == 'SUCCESS':
                        cherrypy.response.status = 200
                        PID.removeclientsms(address, data['smsid'])
                        return

                    if status == 'ERROR':
                        cherrypy.response.status = 500
                        PID.removeclientsms(address, data['smsid'])
                        return

                    # wait for next run
                    time.sleep(0.50)
                    now = datetime.utcnow()

                # maxwaitpid reached so raise an error
                smsgwglobals.pislogger.warning("/sendsms: maxwaitpid " +
                                               "of " + str(maxwaitpid) +
                                               " seconds reached!")
                cherrypy.response.status = 500
                PID.removeclientsms(address, data['smsid'])
                return

            else:
                smsgwglobals.pislogger.warning("/sendsms: No PID for " +
                                               "modem " +
                                               data['modemid'] +
                                               " found!")
                cherrypy.response.status = 500  # Internal Server Error
                return

        except Exception as e:
            smsgwglobals.pislogger.debug("/sendsms: Internal Server "
                                         "Error! " +
                                         str(e))
            cherrypy.response.status = 500  # Internal Server Error
            return

    @cherrypy.expose
    def ws(self, *channels):
        # Open WebSocket server for PID communication
        handler = cherrypy.request.ws_handler
        smsgwglobals.pislogger.debug("/ws: using " + str(type(handler))
                                     + " handler.")


class WebSocketHandler(WebSocket):
    def received_message(self, msg):
        # smsgwglobals.pislogger.debug("/ws: " + str(self.peer_address) +
        #                              " - Got message: '" + str(msg) + "'")
        try:
            plaintext = GlobalHelper.decodeAES(str(msg))
            # smsgwglobals.pislogger.debug("/ws: plaintext: " + plaintext)
            data = json.loads(plaintext)
            smsgwglobals.pislogger.debug("/ws: message-dictionary: " +
                                         str(data))

            # check the protocol version of pid and pis if transmitted
            if ('pidprotocol' in data) and (data['pidprotocol'] != pisglobals.pisprotocol):
                closingreason = ('PID protocol ' + data['pidprotocol'] +
                                 " does not fit " +
                                 'PIS protocol ' + pisglobals.pisprotocol)
                # setting defined closing reasion for shutdown PID
                self.close(1011, closingreason)
            else:
                self.process_msg(data)
        except Exception as e:
            smsgwglobals.pislogger.debug("/ws: ERROR at WebSocektHandler " +
                                         "received_message: " + str(e))

    def process_msg(self, data):
        if (data['action'] == "register"):
            # adding fresh routingids to modemlist
            modemlist = []
            for modem in data['modemlist']:
                modem['routingid'] = str(uuid.uuid1())
                modemlist.append(modem)

            if WIS.register(modemlist):
                PID.addclientinfo(self.peer_address, data['pidid'],
                                  modemlist)

                data['status'] = "registered"
                # replace modemlist to have routingids in it
                data['modemlist'] = modemlist
                smsgwglobals.pislogger.debug("/ws: reply registered - " +
                                             str(data))
                # respond registation status
                PID.sendtopid(str(self.peer_address), data)
            else:
                closingreason = 'Unable to register to any WIS!'
                # tell PID to close and retry initialisation
                self.close(1011, closingreason)

        if data['action'] == "status":
            # set sms status to globals for handling in /sendsms
            PID.setclientsmsstatus(self.peer_address,
                                   data['smsid'],
                                   data['status'])

        if data['action'] == "heartbeat":
            # forward heartbeat to WIS
            httpcode = WIS.request_heartbeat(data)
            data['status'] = httpcode
            PID.sendtopid(str(self.peer_address), data)

    def opened(self):
        PID.addclient(self.peer_address, self)

    def closed(self, code, reason=None):
        modemlist = PID.getclientmodemlist(self.peer_address)
        PID.delclient(self.peer_address, code, reason)
        # Try to unregister
        WIS.unregister(modemlist)


class MyWebSocketPlugin(WebSocketPlugin):
    def stop(self):
        # Unregister all Modems at WIS
        modemlist = PID.getclientmodemlist()
        PID.delclient()
        WIS.unregister(modemlist)


class PisServer(object):
    def run(self):
        # load the configuration
        abspath = path.abspath(path.join(path.dirname(__file__), path.pardir))
        configfile = abspath + '/conf/smsgw.conf'
        cfg = SmsConfig(configfile)

        pisglobals.pisid = cfg.getvalue('pisid', 'pis-dummy', 'pis')
        ipaddress = cfg.getvalue('ipaddress', '127.0.0.1', 'pis')
        pisport = cfg.getvalue('port', '7788', 'pis')
        pisglobals.pisurl = ("http://" + ipaddress + ":" + pisport)
        wisurlcfg = cfg.getvalue('wisurllist',
                                 '[{"url": "http://127.0.0.1:7777"}]',
                                 'pis')

        # convert json to list of dictionary entriesi
        pisglobals.wisurllist = json.loads(wisurlcfg)

        pisglobals.maxwaitpid = int(cfg.getvalue('maxwaitpid', '10', 'pis'))
        pisglobals.retrywisurl = int(cfg.getvalue('retrywisurl', '2', 'pis'))
        pisglobals.retrywait = int(cfg.getvalue('retrywait', '5', 'pis'))

        # prepare ws4py
        cherrypy.config.update({'server.socket_host':
                                ipaddress})
        cherrypy.config.update({'server.socket_port':
                                int(pisport)})
        MyWebSocketPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()

        # come back to config as dictionary as i was not able to bind web
        # socket class unsing the pis-web-conf file
        cfg = {'/': {},
               '/ws': {'tools.websocket.on': True,
                       'tools.websocket.handler_cls': WebSocketHandler}
               }
        cherrypy.quickstart(Root(), '/', cfg)


def main(argv):

    # in any case redirect stdout and stderr
    std = FileLogger(smsgwglobals.pislogger)
    sys.stderr = std
    sys.stdout = std

    pisserver = PisServer()
    pisserver.run()


# Called when running from command line
if __name__ == '__main__':
    main(sys.argv[1:])
