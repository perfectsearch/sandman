#!/usr/bin/env python
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import unittest2
import sandbox
from testsupport import checkin, officialbuild

'''
What I'm trying to prove here is that officialbuild tests get run as part of official
builds. This is a bit of a tricky problem. The ideal way to prove this would be
to do an official build and see which tests get run, but setting up that env
and monitoring a full build seems like overkill. The quick and dirty way to
prove this is:

- Provide both a officialbuild and a checkin test in this test case.
- Make sure the officialbuild test sorts before the checkin one alphabetically, and
  appears first in the class, so that it will be run first.
- If the tests get invoked as part of an eval cycle in an official sandbox,
  make sure the officialbuild test gets called. Otherwise, do nothing.

This has the disadvantage that the test is not run all the time. But it should
be run with every official build, on every build machine, on every OS -- and I
think that's good enough.
'''
reusable_test_called = False
class ReusableTest(unittest2.TestCase):
    @officialbuild
    def test_1(self):
        # This test should be called first, if it's called at all. If the call
        # happens, record that fact.
        global reusable_test_called
        reusable_test_called = True
    @checkin
    def test_2(self):
        # This test should always be called, and if both tests are called, this
        # one should come second. If circumstances are right, make sure the
        # other test was called first.
        sb = sandbox.current
        if sb.get_sandboxtype().get_variant() == 'official' and sb.is_locked():
            self.assertTrue(reusable_test_called)

