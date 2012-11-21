#!/usr/bin/env python
#
# $Id: AnsiTest.py 9319 2011-06-10 02:59:43Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, os, sys
from ioutil import FakeFile
from nose.tools import istest, nottest
from nose.plugins.attrib import attr
from textui.ansi import *

@attr('interactive')
class AnsiTest(unittest.TestCase):
    def setUp(self):
        self.use_colors = ansi.get_use_colors()
    def tearDown(self):
        ansi.set_use_colors(self.use_colors)

    def test_interactive(self):
        printc('\n' + BOLD_RED + 'C' + BOLD_YELLOW + 'o' + BOLD_BLUE + 'l' +
               BOLD_GREEN + 'o' + WHITE + 'r' + NORMTXT + 's Enabled\n---------------')
        for i in range(len(COLORS)):
            printc(str(i) + ' ' + cwrap(COLOR_NAMES[i], COLORS[i]))
        printc('')
        printc('... checking leakage; should be default color...')
        eprintc('written to stderr', BOLD_RED)
        printc('... checking leakage; should be default color...')
        ansi.set_use_colors(False)
        printc('\n' + BOLD_RED + 'C' + BOLD_YELLOW + 'o' + BOLD_BLUE + 'l' +
               BOLD_GREEN + 'o' + WHITE + 'r' + NORMTXT + 's Disabled\n---------------')
        for i in range(len(COLORS)):
            printc(str(i) + ' ' + cwrap(COLOR_NAMES[i], COLORS[i]))
        while True:
            sys.stdout.write('''
Do you see colors in the "Colors Enabled" section, plain text in the "Colors
Disabled" section, and plain text surrounding the red line that says "written
to stderr"? (Y/n) ''')
            answer = sys.stdin.readline().strip().lower()
            if answer.startswith('n'):
                self.fail('Ansi color support isn\'t working.')
            elif answer.startswith('y'):
                return
            else:
                print("Please enter 'y' or 'n'.")
