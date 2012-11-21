#
# $Id: ToolCheckTest.py 9263 2011-06-09 17:49:19Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys, platform, unittest, os, codecs
import sandbox
from testsupport import checkin

@checkin
class CheckToolsTest(unittest.TestCase):
    def test_check_tools(self):
        self.assertEqual(0, sandbox.current.check_tools(quiet=True))
