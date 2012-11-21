#!/usr/bin/env python
# $Id: CodescanTest.py 4165 2010-12-30 12:04:29Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import sys, platform, os, codecs
from unittest2 import TestCase
from xmail import *
from testsupport import checkin


class TestMailer:
    def connect(self):
        pass
    def quit(self):
        pass
    def starttls(self, *args):
        pass
    def login(self, *args):
        pass
    def sendmail(self, sender, to, msg):
        self.sender = sender
        self.to = ', '.join(to)
        self.msg = msg

@checkin
class XmailTest(TestCase):
    def assertContains(self, txt, lines):
        if type(lines) == type(''):
            lines = [l.strip() for l in lines.split('\n') if l.strip()]
        missing = []
        for l in lines:
            if txt.find(l) == -1:
                missing.append(l)
        if missing:
            msg = 'The following lines were missing:\n    "' + '"\n    "'.join(missing) + '"'
            msg += '\n\nScanned "%s"' % txt
            self.fail(msg)
    def test_sendmail(self):
        ml = TestMailer()
        sendmail('test body', 'From <f@x.com>', 'test subject',
            to='a@x.com, B <b@x.com>', cc='a@x.com,c@x.com;d@x.com;d@x.com',
            mailer=ml)
        self.assertEqual(ml.sender, 'From <f@x.com>')
        self.assertEqual(ml.to, 'a@x.com, b@x.com, c@x.com, d@x.com')
        self.assertContains(ml.msg, '''To: B <b@x.com>, a@x.com
From: From <f@x.com>
CC: c@x.com, d@x.com
Subject: test subject
X-Mailer: xmail.py
test body''')
        #print(ml.msg)
    def test_sendmail_ISO8859_1_body(self):
        ml = TestMailer()
        sendmail('espa\xA4ol', 'From <f@x.com>', 'test subject',
            to='a@x.com, B <b@x.com>', cc='a@x.com,c@x.com;d@x.com;d@x.com',
            mailer=ml)
        self.assertEqual(ml.sender, 'From <f@x.com>')
        self.assertEqual(ml.to, 'a@x.com, b@x.com, c@x.com, d@x.com')
        self.assertContains(ml.msg, '''To: B <b@x.com>, a@x.com
From: From <f@x.com>
CC: c@x.com, d@x.com
Subject: test subject
X-Mailer: xmail.py
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: base64
ZXNwYcKkb2w=
''')
        #print(ml.msg)

if __name__ == '__main__':
    interactive = False
    if len(sys.argv) > 1:
        interactive = bool(sys.argv[1] == 'interactive')
    if interactive:
        import time
        def prompt(txt, defaultValue):
            sys.stdout.write(txt)
            if defaultValue:
                sys.stdout.write(' (%s)' % str(defaultValue))
            sys.stdout.write(': ')
            answer = sys.stdin.readline().strip()
            if not answer:
                answer = defaultValue
            return answer

        fromaddr = 'example@example.com' ## TODO FIX EMAIL
        msg = u'Can I send data? Yes I can.\n\nI can even send extended chars: espa\u00F1ol!'
        toaddrs = prompt('TO', 'example <example@example.com>') ## TODO FIX EMAIL ???
        attach = prompt('Attach files',__file__)
        host = prompt('SMTP server', 'smtp.gmail.com')
        if host == 'localhost':
            port = None
            uname = None
            pwd = None
            host = None
        else:
            port = prompt('port', 587)
            uname = prompt('username on SMTP server', 'example@example.com') ##TODO FIX email??
            pwd = prompt('password on SMTP server','')
        sendmail(fromaddr, 'interactive test (espa\xF1ol) at ' + time.asctime(), msg, to=toaddrs,
            host=host, port=port, username=uname, password=pwd, attach=attach)
