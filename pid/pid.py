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
import time
from datetime import datetime
import urllib.request
import urllib.error
from os import path
from ws4py.client.threadedclient import WebSocketClient
import json
sys.path.insert(0, "..")

import pidglobals
# from common import error
from common import smsgwglobals
from common.config import SmsConfig
from common.helper import GlobalHelper
from common.filelogger import FileLogger
from helper.gammumodem import USBModem
from helper.heartbeat import Heartbeat


class PidWsClient(WebSocketClient):
    def opened(self):
        # as we are connected set the time when it was done
        self.lastprimcheck = datetime.now()

        smsgwglobals.pidlogger.info(pidglobals.pidid + ": " +
                                    "Opened connection to " +
                                    str(self.bind_addr))
        data = {}
        data['action'] = 'register'
        data['pidid'] = pidglobals.pidid
        data['modemlist'] = pidglobals.modemlist
        data['pidprotocol'] = pidglobals.pidprotocol

        # if modemlist is not [] register at PIS
        if data['modemlist']:
            asjson = json.dumps(data)
            smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                         "Registration data: " +
                                         asjson)
            tosend = GlobalHelper.encodeAES(asjson)
            self.send(tosend)
        else:
            # close connection to PIS
            closingreason = "Unable to connect to modem(s)"
            pidglobals.closingcode = 4000
            self.close(code=4000, reason=closingreason)
            # if >= 4000 the pid.py endlessloop will exit

    def closed(self, code, reason=None):
        smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                     "Closed down with code: " + str(code) +
                                     " - reason: " + str(reason))
        # signal heartbeat to stop
        if pidglobals.heartbeatdaemon is not None:
            pidglobals.heartbeatdaemon.stop()
        # set the closing reason in globals
        pidglobals.closingcode = code

    def received_message(self, msg):
        plaintext = GlobalHelper.decodeAES(str(msg))

        smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                     "Message received: " +
                                     str(plaintext))
        data = json.loads(plaintext)

        if data['action'] == "sendsms":
            tosend = Modem.sendsms(data)

            plaintext = json.dumps(tosend)
            smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                         "Message delivery status: " +
                                         str(plaintext))
            message = GlobalHelper.encodeAES(plaintext)
            # reply sms-status to PIS
            self.send(message)

            # calculate difference time to last primary PIS check
            diff = datetime.now() - self.lastprimcheck

            # only if 5 mins are passed (= 300 sec)
            if diff.seconds > 300:
                if self.check_primpid() == "reconnect":
                    # close Websocket to reconnect!
                    # fixes #25 wait a bit to let pis fetch the smsstatus first
                    time.sleep(1)

                    closingreason = "Primary PID is back! Reinit now!"
                    pidglobals.closingcode = 4001
                    self.close(code=4001, reason=closingreason)

        if data['action'] == "register":
            if data['status'] == "registered":
                # Start Heartbeat to connected PID
                hb = Heartbeat(data['modemlist'], self)
                hb.daemon = True
                hb.start()

        if data['action'] == "heartbeat":
            # connection to PIS is OK but
            # Response from WIS is NOT OK
            if data['status'] != 200:
                # close Connection to PIS and retry initialisation
                self.close()

    def check_primpid(self):
        # Do a simple URL-check and denn close Websocket connection.
        # Set the closing code to 4001 Going back to Primary
        # This will result in a reconnect on first URL.

        status = "none"
        if pidglobals.curpisurl == pidglobals.primpisurl:
            status = "nothing to do"
        else:
            request = urllib.request.Request(pidglobals.primpisurl)
            try:
                urllib.request.urlopen(request, timeout=5)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    status = "reconnect"
                    smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                                 "PRIMPIS is back!")
            except Exception as e:
                status = "primPID not back!"
                smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                             "PRIMPIS not available - "
                                             "Error: " + str(e))

        self.lastprimcheck = datetime.now()
        return status


class Modem(object):
    """Class used to handle GAMMU modem requests
    """
    @staticmethod
    def connectmodems(modemlist, gammucfg):
        # init empty modemlist and connection dictionaries in pisglobals
        pidglobals.modemlist = []
        pidglobals.modemcondict = {}

        # init USBmodem connection
        # and remove modem if connection makes trouble...
        for modem in modemlist:
            smsgwglobals.pidlogger.info(pidglobals.pidid + ": " +
                                        "Trying to init Modem: " +
                                        str(modem))
            usbmodem = USBModem(gammucfg,
                                modem['gammusection'],
                                modem['pin'],
                                modem['ctryexitcode'])
            # for each modemid persist the object and the modemn pidglobals
            if usbmodem.get_status():
                pidglobals.modemcondict[modem['modemid']] = usbmodem
                pidglobals.modemlist.append(modem)
            else:
                smsgwglobals.pidlogger.error(pidglobals.pidid + ": " +
                                             "Unable to init USBModem: " +
                                             str(modem))

    @staticmethod
    def sendsms(sms):
        smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                     "Sending SMS: " + str(sms))
        status = {}
        status['smsid'] = sms['smsid']
        status['action'] = "status"

        if pidglobals.testmode:
            # special answers if testmode is true!
            if (sms['content'] == "ERROR" or
               sms['content'] == "SUCCESS"):
                time.sleep(2)
                status['status'] = sms['content']

            elif sms['content'] == "LONGWAIT":
                # has to be longer than maxwaitpid in smsgw.conf
                time.sleep(130)
                status['status'] = "SUCCESS"

            elif sms['content'] == "TESTMARIO":
                status['status'] = "SUCCESS"

        if "status" in status:
            # exit if testmode sms was sent
            return status

        # normal operation
        sentstatus = False
        if sms['modemid'] in pidglobals.modemcondict:
            usbmodem = pidglobals.modemcondict[sms['modemid']]
            sentstatus = usbmodem.send_SMS(sms['content'],
                                           sms['targetnr'])
        if sentstatus:
            status['status'] = "SUCCESS"
        else:
            status['status'] = "ERROR"

        return status


class Pid(object):
    def run(self):
        # load the configuration
        abspath = path.abspath(path.join(path.dirname(__file__), path.pardir))
        configfile = abspath + '/conf/smsgw.conf'
        gammucfg = abspath + '/conf/gammu.conf'
        print(configfile)
        cfg = SmsConfig(configfile)

        pidglobals.pidid = cfg.getvalue('pidid', 'pid-dummy', 'pid')
        smsgwglobals.pidlogger.debug("PisID: " + pidglobals.pidid)

        testmode = cfg.getvalue('testmode', 'Off', 'pid')
        if testmode == "On":
            # set testmode - content "ERROR" "SUCCESS" and "LONGWAIT" is
            # handled in a special way now
            pidglobals.testmode = True
        else:
            pidglobals.testmode = False
        smsgwglobals.pidlogger.debug("TestMode: " +
                                     str(pidglobals.testmode))

        retrypisurl = cfg.getvalue('retrypisurl', '2', 'pid')
        smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                     "RetryPisUrl: " + retrypisurl)

        retrywait = cfg.getvalue('retrywait', '5', 'pid')
        smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                     "RetryWait: " + retrywait)

        modemcfg = cfg.getvalue('modemlist', '[{}]', 'pid')

        # convert json to list of dictionary entries
        modemlist = json.loads(modemcfg)
        # check if modemcfg is set
        if 'modemid' not in modemlist[0]:
            # if len(modemlist) == 0:
            cfg.errorandexit("modemlist - not set!!!")

        # connect to USBModems and persist in pidglobals
        Modem.connectmodems(modemlist, gammucfg)

        smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                     "ModemList: " +
                                     str(pidglobals.modemlist))

        pisurlcfg = cfg.getvalue('pisurllist',
                                 '[{"url": "ws://127.0.0.1:7788"}]',
                                 'pid')
        # convert json to list of dictionary entries
        pisurllist = json.loads(pisurlcfg)
        smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                     "PisUrlList: " +
                                     str(pisurllist))

        # endless try to connect to configured PIS
        # error: wait for some secs, then 1 retry, then next PID  in list
        curpis = 0
        tries = 1
        while True:
            try:
                if pidglobals.closingcode:
                    raise

                baseurl = pisurllist[curpis]['url']
                pisurl = baseurl + "/ws"
                smsgwglobals.pidlogger.info(pidglobals.pidid + ": " +
                                            "Try " + str(tries) + ": " +
                                            "Connecting to: " +
                                            pisurl)
                # init websocket client with heartbeat, 30 is fixed in all
                # modules wis/pis/pid
                ws = PidWsClient(pisurl,
                                 protocols=['http-only', 'chat'],
                                 heartbeat_freq=30)
                ws.connect()
                # set values for primary check in Websocket connection!
                # trim ws out of ws:/.. and add http:/
                pidglobals.curpisurl = "http" + baseurl[2:]
                pidglobals.primpisurl = "http" + pisurllist[0]['url'][2:]
                ws.run_forever()
            except KeyboardInterrupt:
                ws.close()
                # leave while loop
                break
            except Exception as e:
                # do retry except there is no more modem to communicate
                if (pidglobals.closingcode is None or
                   pidglobals.closingcode < 4000):

                    # try to reconnect
                    smsgwglobals.pidlogger.info(pidglobals.pidid + ": " +
                                                "Got a problem will reconnect "
                                                "in " + retrywait + " seconds.")
                    smsgwglobals.pidlogger.debug(pidglobals.pidid + ": " +
                                                 "Problem is: " + str(e))
                    try:
                        time.sleep(int(retrywait))
                    except:
                        break

                    if tries < int(retrypisurl):
                        tries = tries + 1
                    else:
                        tries = 1
                        curpis = curpis + 1
                        if curpis == len(pisurllist):
                            curpis = 0
                    pidglobals.closingcode = None

                elif pidglobals.closingcode == 4001:
                    # go back to inital PID
                    # reset while parameter for pis and retries
                    smsgwglobals.pidlogger.info(pidglobals.pidid + ": " +
                                                "Going back to Prim PID")
                    curpis = 0
                    tries = 1
                    pidglobals.closingcode = None

                elif pidglobals.closingcode == 4000:
                    # leave while loop
                    # no connection to modem found!
                    break


def main(argv):

    # in any case redirect stdout and stderr
    std = FileLogger(smsgwglobals.pidlogger)
    sys.stderr = std
    sys.stdout = std

    pid = Pid()
    pid.run()


# Called when running from command line
if __name__ == '__main__':
    main(sys.argv[1:])
