#!/usr/bin/env python
#
# $Id: DisabledUnitTestTest.py 4193 2011-01-04 23:19:42Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import sys, os, _testcase
from unittest2 import TestCase, skip
from codescan.disabled_unit_test import *
from testsupport import checkin, officialbuild

# We're beginning the string constant in an odd way so we don't
# cause this file to show up in the list of those containing
# a disabled unit test.
DESC = '/' + '''*
UNIT TEST TEMPORARILY DISABLED
By: your name
When: 2011-02-27
Ticket: #295
Which: testFoo
Where: all 32-bit platforms
Owner: fred@flintstones.org, barney@rubble.org
Why: description of problem, including copy-and-paste
    from error log
*/'''
PREFIX = '''
#if 0
this is inactive text
    #if 1
        this is also inactive
    #endif
#endif
/**
* some more text that's inactive
*/
''' + DESC

OFFSET = PREFIX.find(DESC)

CPP_SUFFIX1 = '''
// a comment
SIMPLE_TEST(foo)'''

CPP_SUFFIX2 = '''/*
SOME MORE COMMENTS
*/
    class SpecialTest: public SomethingTest {
    }'''

JAVA_SUFFIX = '''//@Test
public void testSomething() {
}'''

@skip("9/16/2011 this test can't be run until we finish work on the test runner -- Julie Jones")
@officialbuild
class DisabledUnitTestTest(_testcase.TestCaseEx):
    def validateDut(self, dut, errors):
        errors += self.checkProp(dut, 'ticket', '295')
        errors += self.checkProp(dut, 'which', 'testFoo')
        errors += self.checkProp(dut, 'where', 'all 32-bit platforms')
        errors += self.checkProp(dut, 'when', '2011-02-27')
        errors += self.checkProp(dut, 'by', 'your name')
        errors += self.checkProp(dut, 'owner', 'fred@flintstones.org, barney@rubble.org')
        errors += self.checkProp(dut, 'why', 'description of problem, including copy-and-paste from error log')
        errorsX = self.checkProp(dut, 'lineNum', '11')
        if errorsX:
            self.printWithLineNums(txt)
        self.assertEquals(0, errors)

    def testDisabledUnitTestPropertiesCppSuffix1(self):
        txt = PREFIX + CPP_SUFFIX1
        dut = DisabledUnitTest('bar/footest.cpp', txt, OFFSET, OFFSET + len(DESC))
        errors = self.checkProp(dut, 'path', 'bar/footest.cpp')
        self.validateDut(dut, errors)

    def testDisabledUnitTestPropertiesCppSuffix2(self):
        txt = PREFIX + CPP_SUFFIX2
        dut = DisabledUnitTest('bar/footest.cpp', txt, OFFSET, OFFSET + len(DESC))
        errors = self.checkProp(dut, 'path', 'bar/footest.cpp')
        self.validateDut(dut, errors)

    def testDisabledUnitTestPropertiesJavaSuffix(self):
        txt = PREFIX + JAVA_SUFFIX
        dut = DisabledUnitTest('bar/footest.java', txt, OFFSET, OFFSET + len(DESC))
        errors = self.checkProp(dut, 'path', 'bar/footest.java')
        self.validateDut(dut, errors)

