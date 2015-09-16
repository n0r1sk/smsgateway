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
from os import path
from common.config import SmsConfig


class GlobalHelper(object):

    @staticmethod
    def encodeAES(plaintext):
        from Crypto.Cipher import AES
        import base64

        BLOCK_SIZE = 32

        PADDING = '{'

        abspath = path.abspath(path.join(path.dirname(__file__), path.pardir))
        configfile = abspath + '/conf/smsgw.conf'
        cfg = SmsConfig(configfile)
        key = cfg.getvalue('key', '7D8FAA235238F8C2')
        cipher = AES.new(key)

        # in AES the plaintext has to be padded to fit the blocksize
        # therefore create a pad

        plaintextbase64 = \
            base64.b64encode(plaintext.encode('utf-8')).decode('utf-8')

        def pad(s):
            return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING

        # pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING

        def encAES(c, s):
            return base64.b64encode(c.encrypt(pad(s)))

        # EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))

        encoded = encAES(cipher, plaintextbase64)

        return encoded

    @staticmethod
    def decodeAES(ciphertext):
        from Crypto.Cipher import AES
        import base64

        PADDING = '{'

        abspath = path.abspath(path.join(path.dirname(__file__), path.pardir))
        configfile = abspath + '/conf/smsgw.conf'
        cfg = SmsConfig(configfile)
        key = cfg.getvalue('key', '7D8FAA235238F8C2')
        cipher = AES.new(key)

        def decAES(c, e):
            try:
                ret = c.decrypt(base64.b64decode(e.encode("ASCII"))).decode("UTF-8") \
                    .rstrip(PADDING)
            except AttributeError:
                ret = c.decrypt(base64.b64decode(e)).decode("UTF-8") \
                    .rstrip(PADDING)

            return ret

        # DecodeAES = lambda c, e:
        # c.decrypt(base64.b64decode(e)).decode("UTF-8").rstrip(PADDING)

        decoded = decAES(cipher, ciphertext)

        try:
            ciphertextbase64 = base64.b64decode(decoded.encode("ASCII")).decode('utf-8')
        except AttributeError:
            ciphertextbase64 = base64.b64decode(decoded).decode('utf-8')

        return ciphertextbase64
