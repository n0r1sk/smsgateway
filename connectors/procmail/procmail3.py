#!/usr/bin/python3
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
import os
import urllib.request
import urllib.parse
import urllib.error
import logging
import logging.handlers
import email
import json
import configparser
from email.header import decode_header


class Smsmail(object):
    smsdict = {}

    def __init__(self, **kwargs):
        if "maintype" in kwargs:
            self.smsdict["maintype"] = kwargs["maintype"]

        if "to" in kwargs:
            self.smsdict["to"] = kwargs["to"]

        if "frm" in kwargs:
            self.smsdict["frm"] = kwargs["frm"]

        if "subject" in kwargs:
            self.smsdict["subject"] = kwargs["subject"]
            if not self.smsdict["subject"]:
                self.smsdict["subject"] = "nosubject"
        else:
            self.smsdict["subject"] = "nosubject"

        if "decodedsubject" in kwargs:
            self.smsdict["decodedsubject"] = kwargs["decodedsubject"]
            if not self.smsdict["decodedsubject"]:
                self.smsdict["decodedsubject"] = "nosubject"
        else:
            self.smsdict["decodedsubject"] = "nosubject"

        if "bodycharset" in kwargs:
            self.smsdict["bodycharset"] = kwargs["bodycharset"]

        if "body" in kwargs:
            self.smsdict["body"] = kwargs["body"]

        if "appid" in kwargs:
            self.smsdict["appid"] = kwargs["appid"]
        else:
            self.smsdict["appid"] = "mailserver"

        if "prio" in kwargs:
            self.smsdict["prio"] = kwargs["prio"]
        else:
            self.smsdict["prio"] = "1"

        # call prepare
        self.prepare()

    def show(self):
        print(json.dumps(self.smsdict))

    def prepare(self):
        # prepare the mobilenumber for ditribution
        self.smsdict["to"] = email.utils.unquote(self.smsdict["to"])
        self.smsdict["mobile"] = self.smsdict["to"].split('@')[0]
        logging.debug("msg prepared to: %s", self.smsdict["mobile"])

        # read smsgateway from config
        config = configparser.RawConfigParser()
        config.read('procmail3.conf')

        self.smsdict["smsgateway"] = config['general']['smsgateway']

        logging.debug("smsdict: %s", json.dumps(self.smsdict))

    def send(self):
        # decode utf8 !!!
        logging.debug(self.smsdict["decodedsubject"])
        encsubject = self.smsdict['decodedsubject'].encode("utf-8")
        data = urllib.parse.urlencode({"content": encsubject,
                                       "priority": self.smsdict["prio"],
                                       "mobile": self.smsdict["mobile"],
                                       "appid": self.smsdict["appid"]})

        logging.debug(data)
        data = data.encode('utf-8')

        request = urllib.request.Request(self.smsdict["smsgateway"] +
                                         "/smsgateway/sendsms")

        request.add_header("Content-Type",
                           "application/x-www-form-urlencoded;charset=utf-8")

        f = urllib.request.urlopen(request, data)

        logging.info(f.read().decode('utf-8'))


def main(argv):
    # check python version
    print(sys.version_info[0])
    if sys.version_info[0] < 3:
        sys.exit(1)

    # get script path
    path = os.path.dirname(__file__)

    # read config file
    config = configparser.RawConfigParser()
    config.read(path + '/procmail3.conf')

    loglevel = config['general']['loglevel']
    logfile = config['general']['logfile']
    priority = config['general']['priority']

    # set current working directory
    os.chdir('/srv/scripts')

    # configure logger
    # get the root logger
    rootLogger = logging.getLogger()

    # prepare format
    logFormatter = logging.Formatter("%(asctime)s" +
                                     " [%(levelname)-5.5s] %(message)s")

    # get stream handler for console and set format
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)

    # add console handler to root logger
    rootLogger.addHandler(consoleHandler)

    # prepare file handle and add formatter
    fileHandler = logging.handlers.TimedRotatingFileHandler(path + "/"
                                                            + logfile,
                                                            "H",
                                                            1,
                                                            14,
                                                            "utf-8")
    fileHandler.setFormatter(logFormatter)

    # add file handle with format to root logger
    rootLogger.addHandler(fileHandler)

    numeric_level = getattr(logging, loglevel, None)
    rootLogger.setLevel(numeric_level)

    # start sending
    logging.info("start sms send")

    full_msg = sys.stdin.read()
    logging.debug(full_msg)

    msg = email.message_from_string(full_msg)

    maintype = msg.get_content_maintype()

    if 'X-Original-To' in msg:
        logging.debug("msg x-original-to: True")
        to = msg['X-Original-To']
    else:
        logging.debug("msg x-original-to: False")
        to = msg['to']

    if not to:
        logging.debug("No TO in mail header - aborting!")
        sys.exit(0)

    frm = msg['from']
    subject = msg['subject']

    bodycharset = ""
    body = ""

    if maintype == 'multipart':
        for part in msg.get_payload():
            if part.get_content_type() == 'text/plain':
                bodycharset = part.get_content_charset()
                body = part.get_payload(decode=1).decode(bodycharset)
            elif maintype == 'text':
                bodycharset = msg.get_charset()
                body = msg.get_payload(decode=1).decode(bodycharset)

    logging.debug("msg maintype: %s", str(maintype))
    logging.debug("msg to: %s", str(to))
    logging.debug("msg from: %s", str(frm))
    logging.debug("msg subject: %s", str(subject))

    decodedsubject = decode_header(subject)

    # decode and choose server
    if (decodedsubject[0][1] is None):
        decodedsubject = decodedsubject[0][0]
    else:
        decodedsubject = decodedsubject[0][0].decode(decodedsubject[0][1])

    logging.debug("msg decoded subject: %s", decodedsubject)
    logging.debug("msg bodycharset: %s", str(bodycharset))
    logging.debug("msg body: %s", body)

    sm = Smsmail(to=to,
                 frm=frm,
                 maintype=maintype,
                 subject=subject,
                 prio=priority,
                 decodedsubject=decodedsubject,
                 bodycharset=bodycharset,
                 body=body)
    sm.send()

# Called when running from command line
if __name__ == '__main__':
    main(sys.argv[1:])
