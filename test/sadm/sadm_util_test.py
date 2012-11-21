#!/usr/bin/env python
#
# $Id: UtilTest.py 9424 2011-06-13 18:42:04Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, os, tempfile, sys
from testsupport import RUNROOT, checkin
sys.path.append(RUNROOT)
from lib.sadm_util import *


@checkin
class MiscTest(unittest.TestCase):
    def test_get_float_from_version(self):
        self.assertAlmostEqual(2.8, get_float_from_version('abc 2.8.19'))
        self.assertAlmostEqual(2.8, get_float_from_version('abc 2.8.19 1.2'))
        self.assertAlmostEqual(2.8, get_float_from_version('2.8.19'))
        self.assertAlmostEqual(2.819, get_float_from_version('2.819'))
    def test_quote_if_needed(self):
        self.assertEqual("test", quote_if_needed("test"))
        self.assertEqual('"a test"', quote_if_needed('a test'))

if __name__ == '__main__':
    unittest.main()
