#!/usr/bin/python
# Copyright 2014 Neuhold Markus and Kleinsasser Mario
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
import atexit
import logging


class Daemon:

    pid = None

    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def run(self):
        logging.debug("Parent Run")
        "method to overwrite"

    def start(self):
        logging.debug("START DEAMON SEQUENZE")
        self.daemonize()
        self.run()

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            self.pid = os.fork()
            if self.pid > 0:
                logging.debug("FIRST FORK")
                # exit first parent
                sys.exit(0)
        except OSError as e:
                sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
                sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            self.pid = os.fork()
            if self.pid > 0:
                logging.debug("SECOND FORK " + str(self.pid))
                # exit from second parent
                sys.exit(0)
        except OSError as e:
                sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
                sys.exit(1)

        # redirect standard file descriptors
        logging.debug("DAEMON STARTED " + str(self.pid))
        sys.stdin.flush()
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # start main run
        logging.debug("START RUN SEQUENZE")
        self.pid = str(os.getpid())
