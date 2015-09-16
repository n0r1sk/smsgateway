#!/usr/bin/python
# Copyright 2015 Bernhard Rausch and Mario Kleinsasser
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

# import cherrypy
import collections
import urllib.request
import json
import socket
from common.helper import GlobalHelper
from application import wisglobals
from common import smsgwglobals
from .html import Htmlpage


class ViewMain(Htmlpage):
    def __init__(self):
        Htmlpage.__init__(self)
        self.setBody()

    def setBody(self):
        str_list = []
        str_list.append('<body>\n')
        str_list.append('''<script>

        function setActDate(){
            var today = new Date();
            var dd = today.getDate();
            var mm = today.getMonth()+1; //January is 0!
            var yyyy = today.getFullYear();

            if(dd<10) {
                dd='0'+dd
            }

            if(mm<10) {
                mm='0'+mm
            }

            today = yyyy + '-' + mm + '-' + dd + '%';

            $("#getsms input[name=date]").val(today)
        }

         $.tablesorter.addParser({
             id: "customDate",
             is: function(s) {
                 //return false;
                 //use the above line if you don't want table
                 //sorter to auto detected this parser
                 //else use the below line.
                 //attention: doesn't check for invalid stuff
                 //2009-77-77 77:77:77.0 would also be matched
                 //if that doesn't suit you alter the regex to
                 //be more restrictive
                 return /\d{1,4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2}\.\d+/.test(s);
             },
             format: function(s) {
                 s = s.replace(/\-/g," ");
                 s = s.replace(/:/g," ");
                 s = s.replace(/\./g," ");
                 s = s.split(" ");
                 return $.tablesorter.formatFloat(new Date(s[0], s[1]-1, s[2], s[3], s[4], s[5]).getTime()+parseInt(s[6]));
             },
             type: "numeric"
         });

         window.onload = function() {
         getRouting();
         };
         function getAllSms(){
                        var datum = $("#getsms input[name=date]").val();
                        $('div.sms').load('ajax/getsms', {all : "true", date: datum}, function(){
         $("#smsTable").tablesorter(
                        {headers: { 4: { sorter:'customDate' }, 8: { sorter:'customDate' }},
                        sortList: [[4,1], [8,1]],
                        theme: 'blue',
                        widgets: ["zebra", "filter"],
                        widthFixed: true });
             });
         }
         function getSms(){
                        var datum = $("#getsms input[name=date]").val();
                        $('div.sms').load('ajax/getsms', {all : "false", date: datum}, function(){
         $("#smsTable").tablesorter(
             {headers: { 4: { sorter:'customDate' }, 8: { sorter:'customDate' }},
             sortList: [[4,1], [8,1]],
             theme: 'blue',
             widgets: ["zebra", "filter"],
             widthFixed: true });
             });
         }

         function getStatus(){

            $.post( "ajax/status", function( data ) {

            var status = JSON.parse(data);

            $( "#routerstatus" ).html(status['router']);
                if (status['router'] == 'alive'){
                    $( "#routerstatus" ).css( "background", "#669933" );
                } else {
                    $( "#routerstatus" ).css( "background", "#E24C34" );
                }
                $( "#watchdogstatus" ).html(status['watchdog']);
                if (status['watchdog'] == 'alive'){
                    $( "#watchdogstatus" ).css( "background", "#669933" );
                } else {
                    $( "#watchdogstatus" ).css( "background", "#E24C34" );
                }
            });
         }


         function getRouting() {
         $('div.routing').load('ajax/getrouting', function(){
            $("#routingTable").tablesorter(
                {headers: { 0: { sorter:'customDate' }},
                sortList: [[0,1], [9,1]],
                theme: 'blue' });
                });
            getStatus();
         }
         $(document).ready(function(){
            setActDate();

            $( "#getsms" ).submit(function( event ) {
            // Stop form from submitting normally
            event.preventDefault();

            // Get some values from elements on the page:
            var $form = $( this ),
            dat = $form.find( "input[name='date']" ).val(),
            mob = $form.find( "input[name='mobile']" ).val(),
            url = $form.attr( "action" );

            // Send the data using post
            var posting = $.post( url, { date: dat, mobile: mob } );

            // Put the results in a div
            posting.done(function( data ) {
            $("div.sms").empty().append(data);
            $("#smsTable").tablesorter(
                {headers: { 4: { sorter:'customDate' }, 8: { sorter:'customDate' }},
                sortList: [[4,1], [8,1]],
                theme: 'blue',
                widgets: ["zebra", "filter"] });
                });
            });
         });
         </script>''')
        str_list.append('''
        <table>
            <tbody><tr>
            <td>
            <button class="btn" type="button" onclick="getRouting()">Refresh Routing</button>
            </td>
            <td>
                Router status:
            </td>
            <td id="routerstatus"></td>
            <td>
                Watchdog status:
            </td>
            <td id="watchdogstatus"></td>
            </tr>
            </tbody>
        </table>
        ''')
        str_list.append('<div class="routing">')
        str_list.append('</div>')
        str_list.append('<hr>')
        str_list.append('<form id="getsms" action="ajax/getsms">\n')
        str_list.append('Date:<input type="text" name="date">\n')
        str_list.append('<button class="btn" type="button"' +
                        ' onclick="getSms()">Read from local</button>&nbsp;')
        str_list.append('<button class="btn" type="button"' +
                        ' onclick="getAllSms()">Read from routing</button>')
        str_list.append('</form>')
        str_list.append('<div class="sms">\n')
        str_list.append('</div>')
        str_list.append('</body>\n')
        Htmlpage.body = ''.join(str_list)


class Ajax():

    def getsms(self, all=False, date=None):
        smsgwglobals.wislogger.debug("AJAX: " + str(all))
        smsgwglobals.wislogger.debug("AJAX: " + str(date))

        str_list = []
        smsen = []

        if all is False:
            smsgwglobals.wislogger.debug("AJAX: " + str(all))
            try:
                if date is None:
                    data = GlobalHelper.encodeAES('{"get": "sms"}')
                else:
                    data = GlobalHelper.encodeAES('{"get": "sms", "date": "' + str(date) + '"}')

                if wisglobals.sslenabled is not None and 'true' in wisglobals.sslenabled.lower():
                    request = urllib.request.Request('https://' +
                                                     wisglobals.wisipaddress +
                                                     ':' +
                                                     wisglobals.wisport +
                                                     "/smsgateway/api/getsms")
                else:
                    request = urllib.request.Request('http://' +
                                                     wisglobals.wisipaddress +
                                                     ':' +
                                                     wisglobals.wisport +
                                                     "/smsgateway/api/getsms")
                request.add_header("Content-Type",
                                   "application/json;charset=utf-8")
                f = urllib.request.urlopen(request, data, timeout=5)
                resp = f.read().decode('utf-8')
                respdata = GlobalHelper.decodeAES(resp)
                smsen = json.loads(respdata)

            except urllib.error.URLError as e:
                smsgwglobals.wislogger.debug(e)
                smsgwglobals.wislogger.debug("AJAX: getsms connect error")
            except socket.timeout as e:
                smsgwglobals.wislogger.debug(e)
                smsgwglobals.wislogger.debug("AJAX: getsms socket connection timeout")
        else:
            smsgwglobals.wislogger.debug("AJAX: " + str(all))
            entries = wisglobals.rdb.read_wisurls_union()
            if len(entries) == 0:
                return "No Wis Urls"
            else:
                for entry in entries:
                    try:
                        if date is None:
                            data = GlobalHelper.encodeAES('{"get": "sms"}')
                        else:
                            data = GlobalHelper.encodeAES('{"get": "sms", "date": "' + str(date) + '"}')

                        request = urllib.request.Request(entry["wisurl"] +
                                                         "/smsgateway/api/getsms")
                        request.add_header("Content-Type",
                                           "application/json;charset=utf-8")
                        f = urllib.request.urlopen(request, data, timeout=5)
                        resp = f.read().decode('utf-8')
                        respdata = GlobalHelper.decodeAES(resp)
                        smsen = smsen + json.loads(respdata)

                    except urllib.error.URLError as e:
                        smsgwglobals.wislogger.debug(e)
                        smsgwglobals.wislogger.debug("AJAX: getsms connect error")
                    except socket.timeout as e:
                        smsgwglobals.wislogger.debug(e)
                        smsgwglobals.wislogger.debug("AJAX: getsms socket connection timeout")

        if smsen is None or len(smsen) == 0:
            return "No SMS in Tables found"

        th = []
        tr = []

        if len(smsen) > 0:
            od = collections.OrderedDict(sorted(smsen[0].items()))
            for k, v in od.items():
                th.append(k)

        for sms in smsen:
            od = collections.OrderedDict(sorted(sms.items()))
            td = []
            for k, v in od.items():
                td.append(v)

            tr.append(td)

        str_list.append('<table id="smsTable" class="tablesorter">\n')

        str_list.append('<thead>\n')
        str_list.append('<tr>\n')
        for h in th:
            str_list.append('<th>' + h + '</th>\n')

        str_list.append('</tr>\n')
        str_list.append('</thead>\n')

        str_list.append('<tbody>\n')
        for r in tr:
            str_list.append('<tr>\n')
            for d in r:
                str_list.append('<td>' + str(d) + '</td>\n')

            str_list.append('</tr>')

        str_list.append('</tbody>\n')
        str_list.append('</table>\n')
        return ''.join(str_list)

    def getrouting(self):
        str_list = []
        th = []
        tr = []

        rows = wisglobals.rdb.read_routing()

        if len(rows) == 0:
            return "No routes - press button to reload!"

        if len(rows) > 0:
            od = collections.OrderedDict(sorted(rows[0].items()))
            for k, v in od.items():
                th.append(k)

        for row in rows:
            od = collections.OrderedDict(sorted(row.items()))
            td = []
            for k, v in od.items():
                td.append(v)

            tr.append(td)

        str_list.append('<table id="routingTable" class="tablesorter">\n')

        str_list.append('<thead>\n')
        str_list.append('<tr>\n')
        for h in th:
            str_list.append('<th>' + h + '</th>\n')

        str_list.append('</tr>\n')
        str_list.append('</thead>\n')

        str_list.append('<tbody>\n')
        for r in tr:
            str_list.append('<tr>\n')
            for d in r:
                txt = None
                if "http" in str(d):
                    txt = '<a href="' + str(d) + '/smsgateway" target="_blank">' + str(d) + '</a>'
                else:
                    txt = str(d)
                str_list.append('<td>' + txt + '</td>\n')

            str_list.append('</tr>')

        str_list.append('</tbody>\n')
        str_list.append('</table>\n')
        return ''.join(str_list)


class Login(Htmlpage):

    def __init__(self):
        Htmlpage.__init__(self)
        self.setBody()

    def setBody(self):
        str_list = """<body>
<div id="pageBody">
  <div id="logo">
    <img src="images/application_logo.png">
  </div>
  <div id="loginform">
    <form method="post" action="checkpassword">
  <table class="logintable">
    <tbody>
      <tr>
      <td class="label">
        Username:
      </td>
      <td class="form">
        <input name="username" type="text">
      </td>
    </tr>
    <tr>
      <td class="label">
        Password:
      </td>
      <td class="form">
        <input name="password" type="password">
      </td>
    </tr>
        <tr>
      <td class="label">
        </td>
      <td class="form">
        <input value="Login" type="submit">
      </td>
    </tr>
  </tbody>
      </table>
  </form></div>
  </div>
</body>
"""
        Htmlpage.body = str_list
