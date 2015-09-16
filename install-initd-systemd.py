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

import os
import sys
import re

# globals vars
systemddirectory = None
module = None
directory = None
user = None


# colorize output
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# systemd service unit generation
def installserviceunit():

    # create service unit name
    serviceunit = "smsgw-" + module + ".service"

    # prepare service unit content
    unit = """[Unit]
Description=smsgateway MODULE

[Service]
User=USER
WorkingDirectory=DIRECTORY
ExecStart=DIRECTORY/smsgw.py MODULE.py

[Install]
WantedBy=multi-user.target
"""

    # search replace service unit content
    unit = re.sub('MODULE', module, unit)
    unit = re.sub('DIRECTORY', current_dir, unit)
    unit = re.sub('USER', user, unit)

    # install to given path
    with open(systemddirectory + "/" + serviceunit, 'w') as f:
        f.write(unit)

    # print final messages
    print("To enable the service unit use:")
    print(bcolors.OKGREEN + "\tsystemctl enable " + serviceunit + bcolors.ENDC)

    print("To start the service unit use:")
    print(bcolors.OKGREEN + "\tsystemctl start " + serviceunit + bcolors.ENDC)


# initd generation
def installinitd():

    # create initd name
    initdname = "smsgw-" + module + ".sh"

    # prepare initd content
    initd = """#! /bin/bash
### BEGIN INIT INFO
# Provides:          smsgateway-XXXMODULE
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: This is the init.d script for smsgateway
# Description:       Please place a LINK from /etc/init.d to this file
#                    Do NOT move this file to /etc/init.d !
#                    Do NOT move the file outside the git checkout folder !
#                    Do NOT move the file away from its current location !
#                    e.g. ln - /path/to/smsgateway/git/checkout /etc/init.d/smsgateway
### END INIT INFO

# Author: Mario Kleinsasser <mario.kleinsasser@gmail.com>

MODULE=XXXMODULE
USER=XXXUSER

# No changes below this line !

SMSGATEWAYHOME=XXXDIRECTORY

MODULEBIN=$MODULE.py
SMSGATEWAYPID=$SMSGATEWAYHOME/run/$MODULE.pid
SMSGATEWAYBIN=$SMSGATEWAYHOME/smsgw.py

do_start()
{
    # Return
    #   0 if daemon has been started
    #   1 if daemon was already running
    #   2 if daemon could not be started
    start-stop-daemon --start --quiet --pidfile $SMSGATEWAYPID --startas $SMSGATEWAYBIN --test > /dev/null \
        || return 1
    start-stop-daemon --start --background --pidfile $SMSGATEWAYPID --make-pidfile --user $USER \
       --chuid smsgw --startas $SMSGATEWAYBIN -- $MODULEBIN \
        || return 2
}

do_stop()
{
start-stop-daemon --stop --pidfile $SMSGATEWAYPID
   rm -f $SMSGATEWAYPID
}

case "$1" in
   start)
    do_start
    ;;
    stop)
    do_stop
    ;;
    *)
    echo "Usage: $SCRIPTNAME {start|stop}" >&2
    exit 3
    ;;
esac
"""

    # search replace service unit content
    initd = re.sub('XXXMODULE', module, initd)
    initd = re.sub('XXXDIRECTORY', current_dir, initd)
    initd = re.sub('XXXUSER', user, initd)

    # install to given path
    with open(systemddirectory + "/" + initdname, 'w') as f:
        f.write(initd)

    # set file permission
    os.chmod(systemddirectory + "/" + initdname, 0o755)

    # print final messages
    print("To start the service unit use:")
    print(bcolors.OKGREEN + "\t" + systemddirectory + "/" + initdname + " start" + bcolors.ENDC)


# check if this script is running with root permissions
# e.g. sudo or as root user
if not os.getuid() == 0:
    print(bcolors.FAIL + "\tThis script must be run with root or root permissions (sudo)" + bcolors.ENDC)
    sys.exit(2)

# ask if used debian initd or systemd
system = input('Are you using Debin initd or general systemd (initd | systemd)? [systemd]? ')
systems = ['initd', 'systemd']
if not system:
    system = 'systemd'

if system not in systems:
    print(bcolors.FAIL + "\tPlease specify a valid system!" + bcolors.ENDC)
    sys.exit(3)

# Ask the user for the target DIRECTORY for systemd installation
systemddirectory = input('Specify systemd service unit install directory or initd directory [/etc/systemd/system]: ')

# Input validation
if not systemddirectory:
    systemddirectory = "/etc/systemd/system"

# check if given path is a directory
if not os.path.isdir(systemddirectory):
    print(bcolors.FAIL + "\tYou must specify a directory as target systemd service unit install directory!" + bcolors.ENDC)
    sys.exit(4)

# ask the user for the daemon user
user = input('Specify the the daemon user the smsgateway run with [smsgw]: ')
if not user:
    user = 'smsgw'

# ask the user which module to install
module = input('Which module should be installed (wis | pis | pid | all)? [all]: ')
if not module:
    module = 'all'

modules = ['wis', 'pis', 'pid', 'all']
if module not in modules:
    print(bcolors.FAIL + "\tPlease specify a valid module!" + bcolors.ENDC)
    sys.exit(5)

# get currentdir to use it for systemd.service exec parameter
current_dir = os.path.dirname(os.path.abspath(__file__))

# install the requested modules
if 'all' in module:
    modules.remove('all')
    for module in modules:
        if 'systemd' in system:
            installserviceunit()
        else:
            installinitd()
else:
    if 'systemd' in system:
        installserviceunit()
    else:
        installinitd()
