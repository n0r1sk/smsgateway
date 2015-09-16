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
import sqlite3
from datetime import datetime
from datetime import timedelta
from common import smsgwglobals
from application import wisglobals
from common import error
import threading

rdblock = threading.Lock()


class Database(object):

    con = None
    cur = None

    # check_same_thread is only documented online
    # it is needed if the memory database is used and also
    # created in another thread
    def __init__(self):
        self.con = sqlite3.connect(":memory:", check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        self.create_table_routing()

    # Create table and index for table routing
    def create_table_routing(self):
        smsgwglobals.wislogger.debug("ROUTERDB: Create table 'routing'")
        query = ("CREATE TABLE IF NOT EXISTS routing (" +
                 "wisid TEXT, " +
                 "modemid TEXT, " +
                 "regex TEXT, " +
                 "lbcount INTEGER, " +
                 "lbfactor INTEGER, " +
                 "wisurl TEXT, " +
                 "pisurl TEXT, " +
                 "modemname TEXT, " +
                 "routingid TEXT, " +
                 "obsolete INTEGER, " +
                 "changed TIMESTAMP, " +
                 "PRIMARY KEY (routingid))")
        self.cur.execute(query)

    # Read routing entries
    def read_routing(self, modemid=None):
        smsgwglobals.wislogger.debug("ROUTERDB: Read routing entries")
        query = ("SELECT " +
                 "wisid, " +
                 "modemid, " +
                 "regex, " +
                 "lbcount, " +
                 "lbfactor, " +
                 "wisurl, " +
                 "pisurl, " +
                 "modemname, " +
                 "routingid, " +
                 "obsolete, " +
                 "changed " +
                 "FROM routing")
        try:
            if modemid is None:
                rdblock.acquire()
                result = self.cur.execute(query)
            else:
                query = query + " WHERE modemid = ?"
                rdblock.acquire()
                result = self.cur.execute(query, [modemid])

        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to SELECT FROM routing! ", e)
        else:
            # convert rows to dict
            routes = [dict(row) for row in result]
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(len(routes)) +
                                         " routing entries selected.")
            return routes
        finally:
            rdblock.release()

    # Read routing entries
    def read_lbcount(self, routingid):
        smsgwglobals.wislogger.debug("ROUTERDB: Read routing entries")
        query = ("SELECT " +
                 "lbcount " +
                 "FROM routing " +
                 "WHERE routingid = ?")
        try:
            rdblock.acquire()
            result = self.cur.execute(query, [routingid])

        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to SELECT FROM routing! ", e)
        else:
            # convert rows to dict
            routes = [dict(row) for row in result]
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(len(routes)) +
                                         " routing entries selected.")
            return routes
        finally:
            rdblock.release()

    # Read routing wisurls entries union
    def read_wisurls_union(self):
        smsgwglobals.wislogger.debug("ROUTERDB: Read wisurls union")
        query = ("SELECT DISTINCT " +
                 "wisurl " +
                 "FROM routing")
        try:
            rdblock.acquire()
            result = self.cur.execute(query)

        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to SELECT FROM routing! ", e)
        else:
            # convert rows to dict
            routes = [dict(row) for row in result]
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(len(routes)) +
                                         " wis entries selected.")
            return routes
        finally:
            rdblock.release()

    # Insert or replaces a list of routing entries
    def write_routing(self, route, changed=None):
        """Insert or replace a routing entry
        Attributes: wisid ... text-1st of primary key
        modemid ... text-serving modem number-2nd of primary key
        regex ... text-regex to match numbers for modem
        lbcount ... int-number of sms delivered
        lbfactor ... int-factor if different contingets
        wisurl ... text-url of wis
        obsolete ... route got flag for deletion
        modemname ... text-longtext of modem
        changed ... datetime.utcnow-when changed
        """
        query = ("INSERT OR REPLACE INTO routing " +
                 "(wisid, modemid, regex, lbcount, lbfactor, wisurl, " +
                 "pisurl, obsolete, modemname, routingid, changed) " +
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ")

        # read lbcount if exist
        lbcount = 0
        r = self.read_lbcount(route["routingid"])
        if r is None or len(r) == 0:
            self.reset_lbcount()
        else:
            lbcount = r[0]["lbcount"]

        if changed is None:
            changed = datetime.utcnow()

        try:
            smsgwglobals.wislogger.debug("ROUTERDB: Write into routing" +
                                         " :wisid: " + route["wisid"] +
                                         " :modemid: " + route["modemid"] +
                                         " :regex: " + route["regex"] +
                                         " :lbcount: " + str(lbcount) +
                                         " :lbfactor: " +
                                         str(route["lbfactor"]) +
                                         " :wisurl: " + route["wisurl"] +
                                         " :pisurl: " + route["pisurl"] +
                                         " :obsolete: " +
                                         str(route["obsolete"]) +
                                         " :modemname: " + route["modemname"] +
                                         " :routingid: " + route["routingid"] +
                                         " :changed: " + str(changed))
            rdblock.acquire()
            self.cur.execute(query, (route["wisid"],
                                     route["modemid"],
                                     route["regex"],
                                     lbcount,
                                     route["lbfactor"],
                                     route["wisurl"],
                                     route["pisurl"],
                                     route["obsolete"],
                                     route["modemname"],
                                     route["routingid"],
                                     changed))
            self.con.commit()
            smsgwglobals.wislogger.debug("ROUTERDB: INSERT!")

        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to INSERT routing entry! ", e)
        finally:
            rdblock.release()

    # Delete routing entry by wisurl
    def delete_routing_wisurl(self, wisurl):
        smsgwglobals.wislogger.debug("ROUTERDB: Deleting" +
                                     " routing entries...")

        try:
            query = ("UPDATE routing SET " +
                     "obsolete = 14 " +
                     "WHERE wisurl = ? " +
                     "AND obsolete < 14")

            rdblock.acquire()
            result = self.cur.execute(query, [wisurl])
            count = result.rowcount
            self.con.commit()
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(count) +
                                         " routing DELETE WISURL!")
        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to DELETE from routing! ", e)
        finally:
            rdblock.release()

    # Delete routing entry by routingid or obsolete
    def delete_routing(self, routingid=None):
        smsgwglobals.wislogger.debug("ROUTERDB: Deleting" +
                                     " routing entries...")

        try:
            if (routingid is None):
                query = ("DELETE FROM routing " +
                         "WHERE obsolete = ?")
                rdblock.acquire()
                result = self.cur.execute(query, [16])
            else:
                query = ("DELETE FROM routing " +
                         "WHERE routingid = ?")
                rdblock.acquire()
                result = self.cur.execute(query, routingid)

            count = result.rowcount
            self.con.commit()
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(count) +
                                         " routing DELETE MAIN!")
        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to DELETE from routing! ", e)
        finally:
            rdblock.release()

    # Update all routing entries set lbcount = 0
    def reset_lbcount(self):
        smsgwglobals.wislogger.debug("ROUTERDB: Reset lbcount")

        try:
            query = ("UPDATE routing SET " +
                     "lbcount = ? "
                     )

            rdblock.acquire()
            result = self.cur.execute(query, [0])
            count = result.rowcount
            self.con.commit()
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(count) +
                                         " lbcount CHANGED!")
        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to reset lbcount! ", e)
        finally:
            rdblock.release()

    # Directoy change obsolete entry by routingid
    def change_obsolete(self, routingid, obsolete):
        smsgwglobals.wislogger.debug("ROUTERDB: Changing" +
                                     " routing entries...")

        try:
            query = ("UPDATE routing SET " +
                     "obsolete = ? " +
                     "WHERE routingid = ?"
                     )

            rdblock.acquire()
            result = self.cur.execute(query, (obsolete, routingid))
            count = result.rowcount
            self.con.commit()
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(count) +
                                         " routing OBSOLETE CHANGEG!")
        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to change obsolete! ", e)
        finally:
            rdblock.release()

    # Raise obsolte on timeout in routing
    def raise_obsolete(self):
        smsgwglobals.wislogger.debug("ROUTERDB: Raising Obsolete" +
                                     " routing entries...")

        try:
            now = datetime.utcnow()
            older = now - timedelta(0, 30)

            smsgwglobals.wislogger.debug("ROUTER " + str(now))
            smsgwglobals.wislogger.debug("ROUTER " + str(older))

            query = ("UPDATE routing SET " +
                     "obsolete = obsolete + 1 " +
                     "WHERE changed < ?"
                     )

            rdblock.acquire()
            result = self.cur.execute(query, [older])
            counta = result.rowcount

            query = ("UPDATE routing SET " +
                     "obsolete = 14 " +
                     "WHERE obsolete = 3"
                     )

            result = self.cur.execute(query)
            countb = result.rowcount

            self.con.commit()
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(counta) +
                                         str(countb) +
                                         " routing OBSOLETE RAISED!")
        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to change obsolete! ", e)
        finally:
            rdblock.release()

    # Raise obsolte on timeout in routing
    def raise_lbcount(self, modemid):
        smsgwglobals.wislogger.debug("ROUTERDB: Raising lbcount")

        try:
            query = ("UPDATE routing SET " +
                     "lbcount = lbcount + 1 " +
                     "WHERE modemid = ? "
                     )

            rdblock.acquire()
            result = self.cur.execute(query, [modemid])
            count = result.rowcount
            self.con.commit()
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(count) +
                                         " lbcount updated!")
            return count
        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to change lbcount! ", e)
        finally:
            rdblock.release()

    # Raise obsolte on timeout in routing
    def raise_heartbeat(self, routingid):
        smsgwglobals.wislogger.debug("ROUTERDB: Raising Heartbeat" +
                                     " routing entries...")

        try:
            now = datetime.utcnow()

            smsgwglobals.wislogger.debug("ROUTERDB: NEW HEARTBEAT" + str(now))

            query = ("UPDATE routing SET " +
                     "changed = ? ," +
                     "obsolete = 0 " +
                     "WHERE routingid = ? " +
                     "AND obsolete < 14"
                     )

            rdblock.acquire()
            result = self.cur.execute(query, [now, routingid])
            count = result.rowcount
            self.con.commit()
            smsgwglobals.wislogger.debug("ROUTERDB: " + str(count) +
                                         " routing HEARTBEAT updated!")
            return count
        except Exception as e:
            smsgwglobals.wislogger.critical("ROUTERDB: " + query +
                                            " failed! [EXCEPTION]:%s", e)
            raise error.DatabaseError("Unable to change obsolete! ", e)
        finally:
            rdblock.release()

    # merge received routing entries
    def merge_routing(self, routes):
        # clean received routes, remove routes
        # that have wisid of me
        smsgwglobals.wislogger.debug("MERGE: Start")
        for route in list(routes):
            if route["wisid"] == wisglobals.wisid:
                smsgwglobals.wislogger.debug("MERGE: OWN WISID DELETE")
                routes.remove(route)

        # read local routes
        localroutes = self.read_routing()

        # for all received routes
        for route in routes:
            # check if received route is in local routes
            # found flag
            found = False
            for r in localroutes:
                # if it is
                if route["routingid"] == r["routingid"]:
                    smsgwglobals.wislogger.debug("MERGE: Found")
                    found = True
                    # and if it es 0 vs < 3
                    if route["obsolete"] == 0 and r["obsolete"] < 3:
                        # overwrite
                        smsgwglobals.wislogger.debug("ROUTER MERDED")
                        smsgwglobals.wislogger.debug("ROUTER " +
                                                     route["changed"])
                        self.write_routing(route, route["changed"])
                        # if route is obsolete, overwrite
                    # elif route["obsolete"] >= 14:
                        # overwrite
                    #    self.write_routing(route, route["changed"])
                    else:
                        pass
                    # nothing to change
                else:
                    pass
            # nothing to change
            # leave found flag False
            # check if route was not found
            # just add
            if found is False:
                # add route to local
                if route["obsolete"] < 14:
                    smsgwglobals.wislogger.debug("MERGE: Writing route")
                    self.write_routing(route, route["changed"])
