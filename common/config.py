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

import configparser
import ast
import sys
sys.path.insert(0, "..")

from common import error


# Default: Sections are case sensitive but keys are not.
# See also: https://docs.python.org/3/library/configparser.html
class SmsConfig(object):
    """Base class for reading the configuration file

    Attributes:
        configfile -- path to configuration file.
    """
    __config = None

    # Constructor
    def __init__(self, configfile='conf/smsgw.conf'):
        try:
            self.__config = configparser.ConfigParser()
            self.__config.read(configfile, encoding='utf-8')
        except Exception as e:
            raise error.ConfigError("Config file '" + configfile +
                                    "' not found!", e)
        # check if config file is valid
        sectionsfound = self.getsections()
        sectionsneeded = ['db', 'pis', 'pid', 'wis']
        if len(set(sectionsfound) & set(sectionsneeded)) != 4:
            self.errorandexit("Missing or wrong sections in config file!")

    def getsections(self):
        return (self.__config.sections())
#    return ([section for section in self.__config.items()])

    def getsectionoptions(self, section='DEFAULT'):
        return [option for option in self.__config[section]]

    def getsectionvalues(self, section='DEFAULT'):
        return [value for value in self.__config[section].values()]

    def getoptionsandvalues(self, section='DEFAULT'):
        return ([sects for sects in self.__config.items(section)])

    def getvalue(self, option=None, fback=None, section='DEFAULT'):
        return (self.__config.get(section, option, fallback=fback))

    def getlist(self, option=None, fback=None, section='DEFAULT'):
        return (self.__config.get(section, option,
                                  fallback=fback)).split(',')

    def getdict(self, option=None, fback=None, section='DEFAULT'):
        try:
            retval = (ast.literal_eval
                      (self.__config.get(section, option, fallback=fback)))
        except Exception as e:
            raise error.ConfigError("Value for '" + option + "' has to be " +
                                    "a dictionary! e.g. {'a':'b', 'c':'d'}", e)
        else:
            return retval

    def errorandexit(self, option):
        errortext = "ERROR in conf/smsgw.cfg at option: " + str(option) + "\n"
        sys.stderr.write(errortext)
        # System errorcode 1 ... is defined as config error
        sys.exit(1)
