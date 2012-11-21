#!/usr/bin/env python
# -*- coding: utf8 -*-
# $Id: CodeStatTest.py 4165 2010-12-30 12:04:29Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest
import sys
from text_diff import *
from testsupport import checkin

@checkin
class TextDiffTest(unittest.TestCase):
    def test_texts_differ(self):
        self.assertTrue(texts_differ('a', 'b'))
        self.assertFalse(texts_differ('a', 'a'))
        self.assertFalse(texts_differ('a', u'a'))
    def test_texts_differ_ignore_case(self):
        self.assertTrue(texts_differ_ignore_case('a', 'b'))
        self.assertFalse(texts_differ_ignore_case('a', 'a'))
        self.assertFalse(texts_differ_ignore_case('A', u'A'))
        self.assertFalse(texts_differ_ignore_case('A', 'a'))
        self.assertFalse(texts_differ_ignore_case('a', u'A'))
    def test_texts_differ_ignore_whitespace(self):
        self.assertTrue(texts_differ_ignore_whitespace('ab', ' a b\t\r\nx'))
        self.assertFalse(texts_differ_ignore_whitespace('ab', ' a b\t\r\n'))
        self.assertFalse(texts_differ_ignore_whitespace(u'A\t', u'\rA'))
        self.assertTrue(texts_differ_ignore_whitespace('A', u'\ra'))
    def test_texts_differ_ignore_case_and_whitespace(self):
        self.assertTrue(texts_differ_ignore_case_and_whitespace('ab', ' a b\t\r\nx'))
        self.assertFalse(texts_differ_ignore_case_and_whitespace('ab', ' a b\t\r\n'))
        self.assertFalse(texts_differ_ignore_case_and_whitespace(u'A\t', u'\rA'))
        self.assertFalse(texts_differ_ignore_case_and_whitespace('A', u'\ra'))
        self.assertTrue(texts_differ_ignore_case_and_whitespace('aB', ' a b\t\r\nx'))
        self.assertFalse(texts_differ_ignore_case_and_whitespace('aB', ' a b\t\r\n'))
        self.assertFalse(texts_differ_ignore_case_and_whitespace(u'a\t', u'\rA'))

if __name__ == '__main__':
    unittest.main()
