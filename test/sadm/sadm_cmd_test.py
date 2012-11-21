#!/usr/bin/env python
#
# $Id: PromptTest.py 3593 2010-11-30 23:01:06Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, os, tempfile, sys
from testsupport import checkin, RUNROOT
sys.path.append(RUNROOT)
from lib.sadm_cmd import *


@checkin
class CommandTest(unittest.TestCase):
    def by_verb(self, verb):
        x = [x for x in commands() if x.verb == verb]
        self.assertEqual(1, len(x))
        return x[0]
    def test_many_commands(self):
        self.assertTrue(len(commands()) > 10)
    def test_all_commands_come_back_with_valid_abbrev(self):
        x = self.by_verb('start')
        self.assertEquals('star', x.abbrev)
    def test_operates_on_sandbox(self):
        x = self.by_verb('stop')
        self.assertTrue(x.operates_on_sandbox())
        x = self.by_verb('setup')
        self.assertFalse(x.operates_on_sandbox())
    def test_syntax_vs_verb(self):
        x = self.by_verb('foreach')
        self.assertEqual('foreach sandbox do cmd', x.syntax)
    def test_find_command(self):
        x = find_command('his')
        self.assertEqual('history', x.verb)
        x = find_command('historyish')
        self.assertFalse(x)
        x = find_command('hi')
        self.assertEqual('history', x.verb)

if __name__ == '__main__':
    unittest.main()
