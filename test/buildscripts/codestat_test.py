#!/usr/bin/env python
#
# $Id: CodeStatTest.py 4165 2010-12-30 12:04:29Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, sys, os
from codescan.get_code_stats import *
from codescan.get_code_stats import _JAVA_CLASS_PAT, _CPP_CLASS_PAT
from testsupport import checkin, officialbuild

@officialbuild
class CodeStatTest(unittest.TestCase):
    def test_getRelevantPaths(self):
        self.assertEquals(['a/b/c/d.txt', 'a/b/c/', 'a/b/', 'a/', ''], getRelevantPaths('a/b/c/d.txt'))
        self.assertEquals(['psaCache/', ''], getRelevantPaths('psaCache/'))
    def test_addStat(self):
        x = StatsHolder("/a")
        x.addStat("/a/b/c/d.txt", "x", 5)
        x.addStat("/a/b/c/e.txt", "x", 3)
        x.addStat("/a/b/z/y.txt", "x", 1)
        x.addStat("/a/w.txt", "x", 4)
        self.assertEquals(5, x.statsByPath['b/c/d.txt']['x'])
        self.assertEquals(3, x.statsByPath['b/c/e.txt']['x'])
        self.assertEquals(1, x.statsByPath['b/z/y.txt']['x'])
        self.assertEquals(4, x.statsByPath['w.txt']['x'])
        self.assertEquals(8, x.statsByPath['b/c/']['x'])
        self.assertEquals(9, x.statsByPath['b/']['x'])
        self.assertEquals(13, x.statsByPath['']['x'])
    def test_sum(self):
        self.assertEquals(8, sum([1, 2, 3, 4, -2, 0]))
    def test_mean(self):
        self.assertAlmostEqual(5.0, mean([2, 4, 4, 4, 5, 5, 7, 9]), 3)
    def test_variance(self):
        self.assertAlmostEqual(4.0, variance([2, 4, 4, 4, 5, 5, 7, 9]), 3)
    def test_stdev(self):
        self.assertAlmostEqual(2.0, stddev([2, 4, 4, 4, 5, 5, 7, 9]), 3)
    def test_javaClassPat(self):
        self.assertTrue(_JAVA_CLASS_PAT.search('\npublic static final class Foo extends Bar'))
        self.assertTrue(_JAVA_CLASS_PAT.search('\n abstract  protected \n \tinterface _f08_Bar\nimplements Pickle'))
        self.assertTrue(_JAVA_CLASS_PAT.search('abstract public class ConnectedChild<T> extends Child<T>'))
        self.assertTrue(_JAVA_CLASS_PAT.search('\npublic class ConnectedChildTest {'))
    def test_cppClassPat(self):
        self.assertTrue(_CPP_CLASS_PAT.search('\ntemplate<class T, typename U, int V, std::numtraits W>\nclass Foo'))
        self.assertTrue(_CPP_CLASS_PAT.search('struct\n Bar'))
        self.assertTrue(_CPP_CLASS_PAT.search('\ntemplate < class T,\ntypename U,\tint V,std::numtraits W>\nstruct Foo'))
        self.assertTrue(_CPP_CLASS_PAT.search('union\n Bar'))


if __name__ == '__main__':
    unittest.main()
