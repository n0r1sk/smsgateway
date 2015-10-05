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

import time
import gammu
from common import smsgwglobals
import pidglobals


class USBModem(object):
    __status = None
    __config = None
    __section = None
    __ctryexitcode = None
    __statemachine = None

    def __init__(self, config, section=0, pin=None, ctryexitcode="00"):
        self.__config = config
        self.__section = section
        self.__ctryexitcode = ctryexitcode

        # Get Connection to Modem
        self.__statemachine = gammu.StateMachine()

        status = self.init_usbmodem(config, section, pin)

        self.__status = status

    def init_usbmodem(self, config, section, pin):
        try:
            # Read config file
            self.__statemachine.ReadConfig(Section=section, Filename=config)

            # Connect to USBModem
            self.__statemachine.Init()

            # Enable debugging if configured
            if pidglobals.gammudebug:
                self.__statemachine.SetDebugFile(pidglobals.gammudebugfile)
                self.__statemachine.SetDebugLevel("textalldate")

            # Set_Pin
            status = self.set_pin(pin)
            return status

        except Exception as e:
            smsgwglobals.pidlogger.warning("MODEM: Error at connect - " +
                                           str(e))
            return False

    def get_status(self):
        return self.__status

    def set_pin(self, pin):
        # Check if PIN is needed
        secstatus = self.__statemachine.GetSecurityStatus()

        if secstatus is None:
            # No Pin is needed
            status = True

        elif secstatus == 'PIN':
            # PIN is needed
            self.__statemachine.EnterSecurityCode('PIN', pin)
            # Wait 5 seconds to get PIN set
            time.sleep(5)

            # Recheck security status
            secstatus_again = self.__statemachine.GetSecurityStatus()
            if secstatus_again is None:
                status = True
            else:
                status = False
        else:
            # unhandled status
            status = False

        smsgwglobals.pidlogger.debug("MODEM: Set PIN (" + pin +
                                     ") with status '" +
                                     str(status) + "' ")
        return status

    def transform_targetnr(self, targetnr):
        # trim leading '+' and add ctryexitcode
        tonr = self.__ctryexitcode + targetnr.lstrip('+')
        return tonr

    def send_SMS(self, content, targetnr):

        # Check if String holds only ASCII characters or is Unicode
        try:
            content.encode('ascii')
            isUnicode = False
        except UnicodeEncodeError:
            isUnicode = True

        smsgwglobals.pidlogger.debug("MODEM: isUnicode = " + str(isUnicode))

        # if content fits in a short sms send a standard Text message else
        # send a ConcatenatedTextLong message
        lencontent = len(content)

        if (isUnicode and lencontent <= 70):
            whichID = 'Text'
        elif (not isUnicode and lencontent <= 160):
            whichID = 'Text'
        else:
            whichID = 'ConcatenatedTextLong'

        # Fixes issue #43 - changing to not setting a SMS Class
        smsinfo = {
            'Class': -1,
            'Unicode': isUnicode,
            'Entries': [
                {
                    'ID': whichID,
                    'Buffer': content
                }
            ]}

        # Encode message
        encoded = gammu.EncodeSMS(smsinfo)

        # Replace + with country exit code of Modem
        tonr = self.transform_targetnr(targetnr)

        # Send message
        for message in encoded:
            message['SMSC'] = {'Location': 1}
            message['Number'] = tonr

            try:
                msgref = self.__statemachine.SendSMS(message)
                status = True
            except:
                msgref = 'Error'
                status = False

        smsgwglobals.pidlogger.debug("MODEM: send_SMS to " + str(targetnr) +
                                     " has status: " + str(status) + " and " +
                                     "msgref (" + str(msgref) + ")")
        return status
