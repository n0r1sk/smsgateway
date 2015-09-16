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
import argparse


def main(argv):
    parser = argparse.ArgumentParser(
        description='SMS-Gateway start script.')

    parser.add_argument('module',
                        help='module to start, one of wis.py, pis.py, pid.py')

    args = parser.parse_args()

    modules = ['pis.py', 'wis.py', 'pid.py']

    if args.module not in modules:
        parser.print_help()
        sys.exit(2)

    if 'pis.py' in args.module:
        from pis import pis
        pis.main(argv)

    if 'wis.py' in args.module:
        from wis import wis
        wis.main(argv)

    if 'pid.py' in args.module:
        from pid import pid
        pid.main(argv)

# Called when running from command line
if __name__ == '__main__':
    main(sys.argv[1:])
