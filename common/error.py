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


class Error(Exception):
    """Base class for exceptions"""
    pass


class UserNotFoundError(Error):
    pass


class ConfigError(Error):
    """Exception raised for errors in configuration handinling.

    Attributes:
        message -- explanation of the error
        baseexception -- forwarding the base excepton cached
    """
    def __init__(self, message, baseexception):
        self.message = message
        self.baseexcepton = baseexception


class DatabaseError(Error):
    """Exception raised for errors in database handinling.

    Attributes:
        message -- explanation of the error
        baseexception -- forwarding the base excepton cached
    """
    def __init__(self, message, baseexception):
        self.message = message
        self.baseexcepton = baseexception
