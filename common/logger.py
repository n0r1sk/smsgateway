#!/usr/bin/python
# Copyright 2014-2015 Neuhold Markus and Kleinsasser Mario
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

import logging
import logging.handlers

import sys
sys.path.insert(0, "..")

from os import path

from common.config import SmsConfig


# Default: Sections are case sensitive but keys are not
# See also: https://docs.python.org/3/library/configparser.html
class SmsLogger(object):
    """Base class for Log handling. Creates a log-handler for each section
    in config file.

    Attributes:
        configfile -- absolut path to configuration file
                      to read relevant optionsi out of all sections..

                      loglevel = CRITICAL | ERROR | WARNING | INFO | DEBUG
                      logdirectory = absolut path to log directory
                                     fallback is local \logs directory
                      logfile = smsgw.log
    """
    __smsconfig = None
    __abspath = path.abspath(path.join(path.dirname(__file__), path.pardir))

    # Constructor
    def __init__(self, configfile=__abspath + '/conf/smsgw.conf'):
        # read SmsConfigs
        self.__smsconfig = SmsConfig(configfile)
        sections = self.__smsconfig.getsections()
        # print (type(sections))
        # print (sections)

        # prepare inital logger for each section in config file
        for section in sections:
            # print (section)
            # configer logger per section
            # handler values are -> 'console'
            #                    -> 'file'
            self.addHandler(section, 'console')
            self.addHandler(section, 'file')

    def addHandler(self, section, forhandler='console'):
        # set logger per section
        smslogger = logging.getLogger(section)

        # prepare format
        logFormatter = logging.Formatter("%(asctime)s [%(name)s:%(levelname)-5.5s]  %(message)s")

        # choose the right handler
        if forhandler == 'file':
            todir = self.__smsconfig.getvalue('logdirectory', self.__abspath + '/logs/', section)
            fbacktofile = section + '.log'
            tofile = self.__smsconfig.getvalue('logfile', fbacktofile, section)
            logfile = todir + tofile
            daysback = int(self.__smsconfig.getvalue('logfiledaysback', 7, section))
            handler = logging.handlers.TimedRotatingFileHandler(logfile,
                                                                when='midnight',
                                                                backupCount=daysback,
                                                                encoding='utf-8',
                                                                utc=True)
            # handler = logging.FileHandler(logfile, 'a', 'utf-8')
        # double ensure that default handler is StreamHandler
        else:
            handler = logging.StreamHandler()

        # set the format to the Handler
        handler.setFormatter(logFormatter)

        # add handler
        smslogger.addHandler(handler)

        # set log level
        loglevel = self.__smsconfig.getvalue('loglevel', 'WARNING', section)
        try:
            nummeric_level = getattr(logging, loglevel)
            smslogger.setLevel(nummeric_level)
            smslogger.debug('addHandler for (%s) handler (%s) done!', section, forhandler)
        except Exception:
            self.__smsconfig.errorandexit('loglevel')
