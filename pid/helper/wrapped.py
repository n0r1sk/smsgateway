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

import subprocess
import os
import time

from common import smsgwglobals
import pidglobals


class WrappedUSBModem(object):
    __status = None
    __config = None
    __section = None
    __ctryexitcode = None
    __basecommand = None
    __command_env = None

    def __init__(self, command, config, section=0, pin=None, ctryexitcode="00"):
        self.__config = config
        self.__section = section
        self.__ctryexitcode = ctryexitcode
        self.__basecommand = [command,
                              "-c", self.__config,
                              "-s", str(self.__section)]
        if pidglobals.gammudebug:
            self.__basecommand.append("-d")
            self.__basecommand.append("textalldate")
            self.__basecommand.append("-f")
            self.__basecommand.append(pidglobals.gammudebugfile)

        # copy os environment and set lang to en to be sure on returned output
        self.__command_env = os.environ.copy()
        self.__command_env['LANG'] = 'en_US.UTF-8'

        status = self.get_secstatus()

        if status is False:
            if pin is not None:
                self.set_pin(pin)
                # wait 5 seconds as setting the pin takes some time a litte bit
                time.sleep(5)
                status = self.get_secstatus()

        self.__status = status

    def get_status(self):
        return self.__status

    def set_pin(self, pin):
        # gammu -c conf/gammu.conf entersecuritycode PIN 1234
        command = list(self.__basecommand)
        command.append("entersecuritycode")
        command.append("PIN")
        command.append(pin)

        with subprocess.Popen(command, stdout=subprocess.PIPE,
                              env=self.__command_env) as proc:
            out = proc.stdout.read()
            output = out.decode('UTF-8')
        smsgwglobals.pidlogger.debug("MODEM: Set PIN (" + pin +
                                     ") with message '" +
                                     output + "' "
                                     )

    def get_secstatus(self):
        # Will react on PIN only!!! no PUK nothing else
        # gammu -c conf/gammu.conf getsecuritystatus
        command = list(self.__basecommand)
        command.append("getsecuritystatus")

        with subprocess.Popen(command, stdout=subprocess.PIPE,
                              env=self.__command_env) as proc:
            out = proc.stdout.read()
            output = out.decode('UTF-8')

        if 'Nothing to enter.' in output:
            smsgwglobals.pidlogger.info("MODEM: initialized!")
            retval = True
        else:
            smsgwglobals.pidlogger.debug("MODEM: getsecuritystatus, output = "
                                         + output)
            retval = False
        return retval

    def transform_targetnr(self, targetnr):
        # trim leading '+' and add ctryexitcode
        tonr = self.__ctryexitcode + targetnr.lstrip('+')
        return tonr

    def send_SMS(self, content, targetnr):
        # gammu -c conf/gammu.conf -s 0 sendsms
        #       TEXT 00436805064962 -autolen 20 -text "123456789♣"
        command = list(self.__basecommand)
        command.append("sendsms")
        command.append("TEXT")
        tonr = self.transform_targetnr(targetnr)
        command.append(tonr)
        command.append("-autolen")
        command.append(str(len(content)))
        command.append("-text")
        command.append(content)

        with subprocess.Popen(command, stdout=subprocess.PIPE,
                              env=self.__command_env) as proc:
            out = proc.stdout.read()
            output = out.decode('UTF-8')

        smsgwglobals.pidlogger.debug("MODEM: send_SMS to " + tonr + " " +
                                     output)
        if 'Error' in output or 'Failed' in output or 'error' in output:
            smsgwglobals.pidlogger.error("MODEM: Unable to send sms to " +
                                         tonr + " !")
            retval = False
        else:
            retval = True

        return retval
