#!/usr/bin/env python
# 
# $Id: _testcase.py 3736 2010-12-06 22:57:26Z dhh1969 $
# 
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
# 

import re, unittest, sys

class TestCaseEx(unittest.TestCase):
    def printWithLineNums(self, txt, linesBefore = 0):
        lines = txt.split('\n')
        for i in range(len(lines)):
            line = lines[i]
            sys.stderr.write(str(i + 1 + linesBefore).rjust(4) + ' ' + line + '\n')
            
    def checkProp(self, obj, name, expected):
        assert(hasattr(obj, name))
        val = getattr(obj, name)
        if type(val) == _METHOD_TYPE:
            parens = '()'
            val = val()
        else:
            parens = ''
        val = str(val)
        pattern = re.compile(expected)
        if not pattern.match(val):
            sys.stderr.write('Bad property value for .%s%s:\n  expected "%s"\n  got      "%s"\n' % (name, parens, expected, val))
            return 1
        return 0

class __Bogus:
    def method(self):
        pass

_METHOD_TYPE = type(getattr(__Bogus(), 'method'))