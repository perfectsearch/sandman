#
# $Id: MailoutTest.py 8824 2011-06-01 22:55:43Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys, unittest, os, codecs, subprocess
from mailout import *
from testsupport import checkin, RUNROOT


@checkin
class MailoutTest(unittest.TestCase):
    def test_options(self):
        probs = subprocess.Popen(['python', RUNROOT + 'buildscripts/mailout.py', '--to', 'none', '--sender', 'none', '--subject', 'none'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = probs.stdout.read()
        self.assertTrue(probs.pid)

