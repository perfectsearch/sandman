#!/usr/bin/env python
#
# $Id: CodescanTest.py 7630 2011-05-06 18:21:04Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, sys, os
from codescan.codescan import *
from testsupport import checkin, officialbuild

_BUG_TXT = '''//void TestQuickLoaderRead()
//{
//  PCC8 hs3FilePath = "\\five.hs3";
//  QuickLoader qloader;
//  qloader.SetFilePath(hs3FilePath);
//  bool success = qloader.ReadLookupTable();
//  Test(success, "Failed to read lookup table");
//  success = qloader.ReadAbbreviatedPatternIndex();
//  Test(success, "Failed to read abbreviated pattern index");
//}

#if 0
SIMPLE_TEST(test_HVAuxFileMaker)
{
//PCC16 hs3FilePath = L"J:\\ExptBuild\\ExptIndex.i1.fixed.hs3";
PCC16 hs3FilePath = L"J:\\ExptBuild\\StructExtractsIndex.i1.fixed.hs3";
PCC16 dbRecMapFile = L"J:\\ExptBuild\\Expt-DB-configs7.txt";
const U32 triggerSOCT = 512;
U64 memLimit = 100000;
HVAuxFileMaker auxMaker;
auxMaker.SetFilePath(hs3FilePath);
auxMaker.InitMaker(triggerSOCT);
auxMaker.InitDBSumFactory(dbRecMapFile);
auxMaker.BuildAuxFiles(memLimit);
}

SIMPLE_TEST(test_HVSetFinder)
{
//PCC16 hs3FilePath = L"J:\\ExptBuild\\ExptIndex.i1.fixed.hs3";
PCC16 hs3FilePath = L"J:\\ExptBuild\\StructExtractsIndex.i1.fixed.hs3";
HVSetFinder setFinder;
setFinder.InitFromAuxFiles(hs3FilePath);
assertEqual(0, setFinder.CheckHVDir());
}

#endif

SIMPLE_TEST(test_HMap)
{
#define NUM_TEST_LINKS 64
PsDeleteFile(_T("HmapTest.h1d"));
PCTCHAR fileName = _T("HmapTest.h1m");
PsDeleteFile(fileName);
unsigned n;
HMap hmap;
hmap.HMapInit(fileName, 100, 18);
}
'''

@officialbuild
class CodescanTest(unittest.TestCase):
    def test_getLineNumForOffset(self):
        self.assertEquals(1, getLineNumForOffset("", 0))
        self.assertEquals(1, getLineNumForOffset("", 100))
        self.assertEquals(2, getLineNumForOffset("abc\nxyz", 4))
        self.assertEquals(1, getLineNumForOffset("abc\nxyz", 3))
    def test_getNextCStyleBlockComment(self):
        self.assertEquals(None, getNextCStyleBlockComment("abc", 0))
        self.assertEquals(None, getNextCStyleBlockComment("abc", 100))
        self.assertEquals((0,11), getNextCStyleBlockComment("/* comment */xyz", 0))
        self.assertEquals((3,14), getNextCStyleBlockComment("abc/* comment */xyz", 1))
        self.assertEquals((3,14), getNextCStyleBlockComment("abc/* comment */xyz", 3))
        self.assertEquals(None, getNextCStyleBlockComment("abc/* comment */xyz", 4))
        self.assertEquals(None, getNextCStyleBlockComment("abc/*/xyz", 0))
    def test_getNextIfZero(self):
        self.assertEquals(-1, getNextIfZero("abc", 0))
        self.assertEquals(-1, getNextIfZero("abc", 100))
        self.assertEquals(3, getNextIfZero("ab\n#if 0\nsomething\n\nsomething else\n #endif", 1))
        self.assertEquals(3, getNextIfZero("ab\n#if false\nsomething\n\nsomething else\n #endif", 0))
        self.assertEquals(3, getNextIfZero("ab\n#if FALSE\nsomething\n\nsomething else\n #endif", 2))
        self.assertEquals(3, getNextIfZero("ab\n#if 0\nsomething\n\nsomething else\n #endif", 3))
        self.assertEquals(3, getNextIfZero("ab\n\t\t   \t#if 0\nsomething\n\nsomething else\n \t #endif", 3))
        self.assertEquals(-1, getNextIfZero("ab\n#if 0\nsomething\n\nsomething else\n #endif", 4))
        self.assertEquals(-1, getNextIfZero("ab\n//#if FALSE\nsomething\n\nsomething else\n #endif", 0))
    def test_bug_where_we_didnt_find_endif(self):
        txt = _BUG_TXT
        #print("at offset 348, txt=" + txt[348:355])
        #print("at offset 1081, txt=" + txt[1075:1100])
        self.assertEquals((348,1081), getNextInactiveCppBlock(txt, 0))
    def test_getNextInactiveJavaBlock(self):
        self.assertEquals(None, getNextInactiveJavaBlock("abc", 0))
        self.assertEquals(None, getNextInactiveJavaBlock("abc", 100))
        self.assertEquals((3,8), getNextInactiveJavaBlock("abc/*.*/xyz", 1))
        self.assertEquals((3,8), getNextInactiveJavaBlock("abc/*\n*/xyz", 3))
        self.assertEquals(None, getNextInactiveJavaBlock("abc/*\t*/xyz", 4))
        self.assertEquals((3,7), getNextInactiveJavaBlock("abc/**/xyz", 3))
        self.assertEquals((3,9), getNextInactiveJavaBlock("abc/*/xyz", 0))
    def test_findEndif(self):
        self.assertEquals(-1, findEndif("abc", 0))
        self.assertEquals(-1, findEndif("abc", 100))
        self.assertEquals(10, findEndif("abc\n#endif", 1))
        self.assertEquals(16, findEndif("#if 1\nabc\n#endif\n#endif", 1))
        self.assertEquals(23, findEndif("#if 1\nabc\n#endif\n#endif", 0))
    def test_getNextInactiveCppBlock(self):
        # We are ignoring the possibility that C-style block comments could contain #ifdefs,
        # and vice-versa. Although such things are possible, they are quite uncommon, and
        # parsing such nested blocks correctly isn't worth the effort.
        self.assertEquals(None, getNextInactiveCppBlock("abc", 0))
        self.assertEquals(None, getNextInactiveCppBlock("abc", 100))
        self.assertEquals((3,8), getNextInactiveCppBlock("abc/*.*/xyz", 1))
        self.assertEquals((3,8), getNextInactiveCppBlock("abc/*\n*/xyz", 3))
        self.assertEquals(None, getNextInactiveCppBlock("abc/*\t*/xyz", 4))
        self.assertEquals((3,7), getNextInactiveCppBlock("abc/**/xyz", 3))
        self.assertEquals((3,9), getNextInactiveCppBlock("abc/*/xyz", 0))
        self.assertEquals((4,16), getNextInactiveCppBlock("abc\n#if 0\n#endif\nxyz", 1))
        self.assertEquals((4,21), getNextInactiveCppBlock("abc\n#if false\n\n#endif\nxyz", 3))
        self.assertEquals(None, getNextInactiveCppBlock("abc\n#ifdef X\n#endif\n#endif\nxyz", 0))
        self.assertEquals((4,36), getNextInactiveCppBlock("abc\n#if FALSE\n#ifdef X\n#endif\n#endif\nxyz", 0))
    def test_getNextInactiveCppBlockWithQuotedStrings(self):
        # We shouldn't see anything other than a quoted string here...'
        self.assertEquals(None, getNextInactiveCppBlock('\"/*\" */', 0))
        # Here, we should go to the end of the comment even though it appears to be in the middle of a quoted str;
        # that's what a C++ compiler would do.'
        self.assertEquals((0,11), getNextInactiveCppBlock('/*abc, "\"*/\" xyz*/', 0))
        self.assertEquals((9,15), getNextInactiveCppBlock('\"/*\" abc /*hi*/', 0))
    def test_getNextInactiveJavaBlockWithQuotedStrings(self):
        # We shouldn't see anything other than a quoted string here...'
        self.assertEquals(None, getNextInactiveJavaBlock('\"/*\" */', 0))
        # Here, we should go to the end of the comment even though it appears to be in the middle of a quoted str;
        # that's what a C++ compiler would do.'
        self.assertEquals((0,11), getNextInactiveJavaBlock('/*abc, "\"*/\" xyz*/', 0))
        self.assertEquals((9,15), getNextInactiveJavaBlock('\"/*\" abc /*hi*/', 0))
    def test_matchPairs(self):
        self.assertEquals([], matchPairs('[{(\'""\')}]'))
        self.assertFalse(matchPairs('"{}["]') == [])
        self.assertFalse(matchPairs('\'') == [])
        self.assertFalse(matchPairs('{') == [])
        self.assertFalse(matchPairs('[') == [])
        self.assertFalse(matchPairs('(') == [])
        self.assertFalse(matchPairs('"') == [])
        self.assertFalse(matchPairs('}') == [])
        self.assertFalse(matchPairs(']') == [])
        self.assertFalse(matchPairs(')') == [])
        self.assertEquals(['No closing for {.'], matchPairs('[{]'))
        self.assertEquals(['No opening for }.'], matchPairs('[}]'))
        self.assertEquals(['No closing for \'.'], matchPairs('[\']'))
    def test_getActiveBlocksOnly(self):
        txt = """
function f() {
  ... do something ...
}
/* a short comment */
function g() {
/* a
longer
comment
that
lasts
several
lines
*/

#if 0
some
stuff in
an ifdef'ed block
#endif
}
"""
        expected = """
function f() {
  ... do something ...
}

function g() {


}
"""
        atxt = getActiveBlocksOnly(txt, getNextInactiveCppBlock, preserveLineNums=False)
        self.assertEquals(expected, atxt)
        expected = """
function f() {
  ... do something ...
}

function g() {














}
"""
        atxt = getActiveBlocksOnly(txt, getNextInactiveCppBlock)
        self.assertEquals(expected, atxt)

if __name__ == '__main__':
    unittest.main()
