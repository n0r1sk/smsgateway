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
sys.path.insert(0, "..")
import re

from common import error
from common.config import SmsConfig
from common import smsgwglobals
from common.helper import GlobalHelper
from common.database import Database
from common.filelogger import FileLogger
from application.helper import Helper
from application import root
from application.smstransfer import Smstransfer
from application.watchdog import Watchdog
from application.router import Router
from application import wisglobals
from application import apperror
from application import routingdb

from lxml import etree
from ldap3 import Server, Connection, ALL

import ssl


# disable ssl check for unverified requests
# https://www.python.org/dev/peps/pep-0476/
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context


class XMLResponse(object):
    def successxml(self, number):
        root = etree.Element('SmsSendReturn')
        child = etree.Element('returnCode')
        child.text = "SUC" + number
        root.append(child)
        return etree.tostring(root, pretty_print=True, xml_declaration=True,
                              encoding='UTF-8', standalone="yes")

    def errorxml(self, number):
        root = etree.Element('SmsSendReturn')
        child = etree.Element('returnCode')
        child.text = "ERR" + number
        root.append(child)
        return etree.tostring(root, pretty_print=True, xml_declaration=True,
                              encoding='UTF-8', standalone="yes")


class Root(object):
    def triggerwatchdog(self):
        smsgwglobals.wislogger.debug("TRIGGER WATCHDOG")

        smsgwglobals.wislogger.debug("TRIGGER WATCHDOG ROUTER")
        if wisglobals.routerThread is None:
            smsgwglobals.wislogger.debug("Router died! Restarting it!")
            rt = Router(2, "Router")
            rt.daemon = True
            rt.start()
        elif not wisglobals.routerThread.isAlive():
            smsgwglobals.wislogger.debug("Router died! Restarting it!")
            rt = Router(2, "Router")
            rt.daemon = True
            rt.start()
        else:
            pass

        if wisglobals.watchdogThread is None:
            smsgwglobals.wislogger.debug("Watchdog died! Restarting it!")
            wd = Watchdog(1, "Watchdog")
            wd.daemon = True
            wd.start()
        elif not wisglobals.watchdogThread.isAlive():
            smsgwglobals.wislogger.debug("Watchdog died! Restarting it!")
            wd = Watchdog(1, "Watchdog")
            wd.daemon = True
            wd.start()
        else:
            smsgwglobals.wislogger.debug("TRIGGER WATCHDOG")
            smsgwglobals.wislogger.debug("Wakup watchdog")
            wisglobals.watchdogThreadNotify.set()

    @cherrypy.expose
    def viewmain(self):
        return root.ViewMain().view()

    @cherrypy.expose
    def index(self):
        if 'logon' not in cherrypy.session:
            return root.Login().view()
        elif cherrypy.session['logon'] is True:
            raise cherrypy.HTTPRedirect("/smsgateway/main")

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def checkpassword(self, **params):
        username = cherrypy.request.params.get('username').lower()
        password = cherrypy.request.params.get('password')

        if 'root' in username:
            smsgwglobals.wislogger.debug("FRONT: ROOT Login " + username)
            try:
                if Helper.checkpassword(username, password) is True:
                    cherrypy.session['logon'] = True
                    raise cherrypy.HTTPRedirect("/smsgateway/main")
                else:
                    raise cherrypy.HTTPRedirect("/smsgateway")
            except error.UserNotFoundError:
                raise cherrypy.HTTPRedirect("/smsgateway")
        else:
            try:
                smsgwglobals.wislogger.debug("FRONT: Ldap Login " + username)
                if wisglobals.ldapenabled is None or 'true' not in wisglobals.ldapenabled.lower():
                    smsgwglobals.wislogger.debug("FRONT: Ldap Login disabled " + username)
                    raise cherrypy.HTTPRedirect("/smsgateway")

                smsgwglobals.wislogger.debug("FRONT: Ldap Login " + username)
                smsgwglobals.wislogger.debug("FRONT: Ldap Users " + str(wisglobals.ldapusers))
                if username not in wisglobals.ldapusers:
                    smsgwglobals.wislogger.debug("FRONT: Ldap username not in ldapusers")
                    raise cherrypy.HTTPRedirect("/smsgateway")

                smsgwglobals.wislogger.debug("FRONT: Ldap Server " + wisglobals.ldapserver)
                s = Server(wisglobals.ldapserver, get_info=ALL)
                userdn = 'cn=' + username + ',' + wisglobals.ldapbasedn
                c = Connection(s, user=userdn, password=password)

                if c.bind():
                    cherrypy.session['logon'] = True
                    raise cherrypy.HTTPRedirect("/smsgateway/main")
                else:
                    raise cherrypy.HTTPRedirect("/smsgateway")
            except error.UserNotFoundError:
                raise cherrypy.HTTPRedirect("/smsgateway")

    @cherrypy.expose
    def main(self, **params):
        if 'logon' not in cherrypy.session:
            return root.Login().view()
        elif cherrypy.session['logon'] is True:
            return root.ViewMain().view()

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST', 'GET'])
    def ajax(self, arg, **params):
        if 'logon' not in cherrypy.session:
            raise cherrypy.HTTPRedirect("/smsgateway")

        smsgwglobals.wislogger.debug("AJAX: request with %s and %s ", str(arg), str(params))

        if "status" in arg:
            smsgwglobals.wislogger.debug("AJAX: called with %s and %s", str(arg), str(params))
            status = {}
            cherrypy.response.status = 200
            if wisglobals.routerThread is None:
                status['router'] = 'noobject'

            if wisglobals.routerThread.isAlive():
                status['router'] = 'alive'
            else:
                status['router'] = 'dead'

            if wisglobals.watchdogThread is None:
                status['watchdog'] = 'noobject'

            if wisglobals.watchdogThread.isAlive():
                status['watchdog'] = 'alive'
            else:
                status['watchdog'] = 'dead'

            data = json.dumps(status)
            return data

        if "getrouting" in arg:
            smsgwglobals.wislogger.debug("AJAX: called with %s and %s", str(arg), str(params))
            return root.Ajax().getrouting()

        if "getsms" in arg:
            smsgwglobals.wislogger.debug("AJAX: called with %s and %s", str(arg), str(params))
            if "all" in params:
                allflag = params['all']
                smsgwglobals.wislogger.debug("AJAX: all %s", str(allflag))
            else:
                allflag = False

            if "date" in params:
                date = params['date']
            else:
                date = None

            if allflag is not None and "true" in allflag:
                return root.Ajax().getsms(all=True, date=date)
            else:
                return root.Ajax().getsms(date=date)

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def api(self, arg, **params):
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl))
        smsgwglobals.wislogger.debug(rawbody)
        plaintext = GlobalHelper.decodeAES(rawbody)
        smsgwglobals.wislogger.debug(plaintext)
        data = json.loads(plaintext)

        if arg == "watchdog":

            if data["run"] == "True":
                self.triggerwatchdog()
            else:
                cherrypy.response.status = 400

        if arg == "heartbeat":
            if "routingid" in data:
                smsgwglobals.wislogger.debug(data["routingid"])
                try:
                    count = wisglobals.rdb.raise_heartbeat(data["routingid"])
                    if count == 0:
                        smsgwglobals.wislogger.debug("COUNT: " + str(count))
                        cherrypy.response.status = 400
                except error.DatabaseError:
                    cherrypy.response.status = 400
            else:
                cherrypy.response.status = 400

        if arg == "receiverouting":
            try:
                wisglobals.rdb.merge_routing(data)
            except error.DatabaseError as e:
                smsgwglobals.wislogger.debug(e.message)

        if arg == "requestrouting":
            if data["get"] != "peers":
                cherrypy.response.status = 400
                return

            smsgwglobals.wislogger.debug("Sending routing table to you")
            try:
                erg = wisglobals.rdb.read_routing()
                jerg = json.dumps(erg)
                data = GlobalHelper.encodeAES(jerg)
                return data

            except error.DatabaseError as e:
                smsgwglobals.wislogger.debug(e.message)

        if arg == "managemodem":
            try:
                if data["action"] == "register":
                    smsgwglobals.wislogger.debug("managemodem register")
                    smsgwglobals.wislogger.debug(wisglobals.wisid)

                    # add wisid to data object
                    data["wisid"] = wisglobals.wisid

                    # store date in routing table
                    wisglobals.rdb.write_routing(data)

                    # call receiverouting to distribute routing
                    Helper.receiverouting()

                elif data["action"] == "unregister":
                    smsgwglobals.wislogger.debug("managemodem unregister")
                    wisglobals.rdb.change_obsolete(data["routingid"], 14)
                    Helper.receiverouting()
                else:
                    return False
            except error.DatabaseError as e:
                smsgwglobals.wislogger.debug(e.message)

        if arg == "deligatesms":
            if "sms" in data:
                smsgwglobals.wislogger.debug(data["sms"])
                try:
                    sms = Smstransfer(**data["sms"])
                    sms.smsdict["status"] = 1
                    sms.writetodb()
                    self.triggerwatchdog()
                except error.DatabaseError:
                    cherrypy.response.status = 400
            else:
                cherrypy.response.status = 400

        if arg == "router":
            if data["action"] == "status":
                smsgwglobals.wislogger.debug("API: " + data["action"])
                if wisglobals.routerThread is None:
                    cherrypy.response.status = 200
                    data = GlobalHelper.encodeAES('{"ROUTER":"noobject"}')
                    return data

                if wisglobals.routerThread.isAlive():
                    cherrypy.response.status = 200
                    data = GlobalHelper.encodeAES('{"ROUTER":"alive"}')
                    return data
                else:
                    cherrypy.response.status = 200
                    data = GlobalHelper.encodeAES('{"ROUTER":"dead"}')
                    return data

        if arg == "getsms":
            if data["get"] != "sms":
                cherrypy.response.status = 400
                return

            if "date" in data:
                date = data["date"]
                smsgwglobals.wislogger.debug("API: " + date)
            else:
                date = None

            smsgwglobals.wislogger.debug("Sending SMS Table")
            smsgwglobals.wislogger.debug("Sending SMS Table date: " + str(date))
            try:
                db = Database()
                erg = db.read_sms_date(date=date)
                jerg = json.dumps(erg)
                data = GlobalHelper.encodeAES(jerg)
                return data

            except error.DatabaseError as e:
                smsgwglobals.wislogger.debug(e.message)

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['GET', 'POST'])
    def sendsms(self, **params):

        # this is used for parameter extraction
        # Create sms data object
        sms = Smstransfer(content=cherrypy.request.params.get('content'),
                          targetnr=cherrypy.request.params.get('mobile'),
                          priority=int(cherrypy.request.params.get('priority')),
                          appid=cherrypy.request.params.get('appid'),
                          sourceip=cherrypy.request.headers.get('Remote-Addr'),
                          xforwardedfor=cherrypy.request.headers.get(
                              'X-Forwarded-For'))

        # check if parameters are given
        resp = XMLResponse()
        if not sms.smsdict["content"]:
            self.triggerwatchdog()
            return resp.errorxml("0001")
        if not sms.smsdict["targetnr"]:
            self.triggerwatchdog()
            return resp.errorxml("0001")
        if not sms.smsdict["priority"]:
            self.triggerwatchdog()
            return resp.errorxml("0001")

        smsgwglobals.wislogger.debug(sms.getjson())

        # process sms to insert it into database
        try:
            Helper.processsms(sms)
        except apperror.NoRoutesFoundError:
            self.triggerwatchdog()
            return resp.errorxml("0001")

        self.triggerwatchdog()
        return resp.successxml("0001")


class Wisserver(object):

    def run(self):
        # load the configuration
        # Create default root user
        db = Database()

        abspath = path.abspath(path.join(path.dirname(__file__), path.pardir))
        configfile = abspath + '/conf/smsgw.conf'
        cfg = SmsConfig(configfile)

        readme = open(abspath + '/README.md', 'r')
        readmecontent = readme.read()
        version = re.compile(r"(?<=## Version)(.*v.\..*)", re.S).findall(readmecontent)
        if version:
            wisglobals.version = version[0].strip('\n')

        smsgwglobals.wislogger.debug("WIS: Version: " + str(wisglobals.version))

        wisglobals.wisid = cfg.getvalue('wisid', 'nowisid', 'wis')
        wisglobals.wisipaddress = cfg.getvalue('ipaddress', '127.0.0.1', 'wis')
        wisglobals.wisport = cfg.getvalue('port', '7777', 'wis')
        wisglobals.cleanupseconds = cfg.getvalue('cleanupseconds', '86400', 'wis')

        wisglobals.ldapserver = cfg.getvalue('ldapserver', None, 'wis')
        wisglobals.ldapbasedn = cfg.getvalue('ldapbasedn', None, 'wis')
        wisglobals.ldapenabled = cfg.getvalue('ldapenabled', None, 'wis')
        ldapusers = cfg.getvalue('ldapusers', '[]', 'wis')
        wisglobals.ldapusers = json.loads(ldapusers)
        wisglobals.ldapusers = [item.lower() for item in wisglobals.ldapusers]
        smsgwglobals.wislogger.debug("WIS:" + str(wisglobals.ldapusers))

        password = cfg.getvalue('password', '20778ba41791cdc8ac54b4f1dab8cf7602a81f256cbeb9e782263e8bb00e01794d47651351e5873f9ac82868ede75aa6719160e624f02bba4df1f94324025058', 'wis')
        salt = cfg.getvalue('salt', 'changeme', 'wis')

        # write the default user on startup
        db.write_users('root', password, salt)

        # check if ssl is enabled
        wisglobals.sslenabled = cfg.getvalue('sslenabled', None, 'wis')
        wisglobals.sslcertificate = cfg.getvalue('sslcertificate', None, 'wis')
        wisglobals.sslprivatekey = cfg.getvalue('sslprivatekey', None, 'wis')
        wisglobals.sslcertificatechain = cfg.getvalue('sslcertificatechain', None, 'wis')

        smsgwglobals.wislogger.debug("WIS: SSL " + str(wisglobals.sslenabled))

        if wisglobals.sslenabled is not None and 'true' in wisglobals.sslenabled.lower():
            smsgwglobals.wislogger.debug("WIS: STARTING SSL")
            cherrypy.config.update({'server.ssl_module':
                                    'builtin'})
            cherrypy.config.update({'server.ssl_certificate':
                                    wisglobals.sslcertificate})
            cherrypy.config.update({'server.ssl_private_key':
                                    wisglobals.sslprivatekey})
            if wisglobals.sslcertificatechain is not None:
                cherrypy.config.update({'server.ssl_certificate_chain':
                                        wisglobals.sslcertificatechain})

        cherrypy.config.update({'server.socket_host':
                                wisglobals.wisipaddress})
        cherrypy.config.update({'server.socket_port':
                                int(wisglobals.wisport)})
        cherrypy.quickstart(Root(), '/smsgateway',
                            'wis-web.conf')


def main(argv):

    # in any case redirect stdout and stderr
    std = FileLogger(smsgwglobals.wislogger)
    sys.stderr = std
    sys.stdout = std

    # Create the routingdb
    wisglobals.rdb = routingdb.Database()
    wisglobals.rdb.create_table_routing()
    wisglobals.rdb.read_routing()

    # Start the router
    rt = Router(2, "Router")
    rt.daemon = True
    rt.start()

    # Start the watchdog
    wd = Watchdog(1, "Watchdog")
    wd.daemon = True
    wd.start()

    # After startup let the watchdog run to clean database
    wisglobals.watchdogThreadNotify.set()

    wisserver = Wisserver()
    wisserver.run()


# Called when running from command line
if __name__ == '__main__':
    main(sys.argv[1:])
