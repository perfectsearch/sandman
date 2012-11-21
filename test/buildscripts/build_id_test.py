#!/usr/bin/env python
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import unittest
import sys
import os
from build_id import *
from testsupport import checkin

@checkin
class BuildIDTest(unittest.TestCase):
    def test_str(self):
        b = BuildID('a', 'b', 1, 2, '', '')
        self.assertEquals('a.b.1.2..', str(b))
    def test_cmp_component_case_insensitive(self):
        b1 = BuildID('a', 'b', 1, 2, '', '')
        b2 = BuildID('A', 'b', 1, 2, '', '')
        # Should compare component in case-insensitive fashion.
        self.assertEquals(0, cmp(b1, b2))
        self.assertEquals(b1, b2)
    def test_cmp_branch_case_insensitive(self):
        b1 = BuildID('a', 'b', 1, 2, '', '')
        b2 = BuildID('a', 'B', 1, 2, '', '')
        # Should compare component in case-insensitive fashion.
        self.assertEquals(0, cmp(b1, b2))
        self.assertEquals(b1, b2)
    def test_cmp_code_revno_numeric(self):
        b1 = BuildID('a', 'b', 2, 1, '', '')
        b2 = BuildID('a', 'b', 10, 1, '', '')
        # Should compare component in case-insensitive fashion.
        self.assertTrue(b1 < b2)
        self.assertTrue(cmp(b1, b2) < 0)
    def test_cmp_test_revno_numeric(self):
        b1 = BuildID('a', 'b', 1, 2, '', '')
        b2 = BuildID('a', 'b', 1, 10, '', '')
        # Should compare component in case-insensitive fashion.
        self.assertTrue(b1 < b2)
        self.assertTrue(cmp(b1, b2) < 0)
    def test_from_str(self):
        b1 = build_id_from_str('a.PSA-3.0.49.27')
        self.assertEqual('a', b1.component)
        self.assertEqual('PSA-3.0', b1.branch)
        self.assertEqual(49, b1.code_revno)
        self.assertEqual(27, b1.test_revno)

if __name__ == '__main__':
    unittest.main()
