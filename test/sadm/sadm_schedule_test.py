#!/usr/bin/env python
#
# $Id: ScheduleTest.py 9424 2011-06-13 18:42:04Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, sys, re, os
from testsupport import RUNROOT, TESTROOT, checkin
from ioutil import FakeFile
sys.path.append(RUNROOT)
from lib.sadm_schedule import *
sys.path.append(TESTROOT + '/buildscripts')
import _testcase


@checkin
class ScheduleTest(unittest.TestCase):
    def checkParse(self, x, expectedText, expectedTasks):
        s = Schedule(x)
        msg = ''
        gotText = str(s)
        if expectedText != gotText:
            msg += 'Bad parse of schedule "%s":\n  expected "%s"\n  got      "%s"\n' % (x, expectedText, gotText)
        exTasks = str(expectedTasks)
        gotTasks = str(s.toTasks())
        if os.name == 'nt':
            # If we got one of the tasks that has a specific start time in it,
            # that depends on when our logic runs, then substitute the specific
            # start time that was in effect last time we captured expected
            # output.
            if exTasks.find('15:51') > -1:
                gotTasks = re.sub(r'/st \d+:\d+', '/st 15:51', gotTasks)
        else:
            # If we have a schedule of every N hours, then the minute on which we
            # begin will depend on when we parse it. Compensate for comparison's sake.'
            if expectedText.endswith('h'):
                exTasks = "['1" + exTasks[exTasks.find(' '):]
                gotTasks = "['1" + gotTasks[gotTasks.find(' '):]
        if exTasks != gotTasks:
            msg += 'Bad task generation for schedule "%s":\n  expected "%s"\n  got      "%s"\n' % (x, exTasks, gotTasks)
        if msg:
            sys.stderr.write(msg)
            return 1
        return 0
    def setUp(self):
        self.stdout = sys.stdout
        sys.stdout = FakeFile()
    def tearDown(self):
        sys.stdout = self.stdout
        del(self.stdout)
    def test_never(self):
        sch = Schedule('never')
        self.assertFalse(sch.isInRange('0300'))
        self.assertTrue(sch.isNever())
        self.assertFalse(sch.toTasks())
        self.assertEquals(None, sch.every)
        self.assertEquals(None, sch.at)
        self.assertFalse(sch.is_periodic())
        self.assertEquals("never", str(sch))
    def test_time_with_colon(self):
        sch = Schedule('at 18:15')
        self.assertEquals("['1815']", str(sch.at))
    def test_time_every_with_colon_in_range(self):
        sch = Schedule('every 15 m, 11:03 to 2115')
        self.assertEquals("['1103', '2115']", str(sch.range))
    def test_multiple_times(self):
        sch = Schedule('at 2304,1821, 1:25')
        self.assertEquals("['0125', '1821', '2304']", str(sch.at))
    def test_isInRange(self):
        sch = Schedule('every 10 m, 0300 to 1700')
        self.assertTrue(sch.isInRange('0300'))
        self.assertTrue(sch.isInRange(1300))
        self.assertFalse(sch.isInRange(1700))
        self.assertFalse(sch.isInRange(1900))
        sch = Schedule('every 10 m, 1700 to 0300')
        self.assertFalse(sch.isInRange('0300'))
        self.assertTrue(sch.isInRange('0259'))
        self.assertFalse(sch.isInRange(1300))
        self.assertTrue(sch.isInRange(1700))
        self.assertTrue(sch.isInRange(2359))
    def testBug_toTasks_endInclusive(self):
        s = Schedule('every 20 m from 2000 to 1900')
        # Used to cause error:
        #  File "sadm_schedule.py", line 184, in toTasks
        #  if endInclusive == 0:
        #      UnboundLocalError: local variable 'endInclusive' referenced before assignment
        tasks = s.toTasks()
        # Range logic is currently unsupported on windows; it should parse, but when you call
        # toTasks(), your settings aren't reflected. So don't assert much on windows.
        cron = not bool(os.name == 'nt')
        if cron:
            self.assertEquals("['*/20 20-23,0-18 * * *']", str(tasks))
        else:
            self.assertEquals(1, len(tasks))
        # Try another variant just for completeness -- this never failed.
        s = Schedule('every 15m from 1100 to 1900')
        tasks = s.toTasks()
        if cron:
            self.assertEquals("['*/15 11-18 * * *']", str(tasks))
        else:
            self.assertEquals(1, len(tasks))
    def testScheduleParsing(self):
        errors = 0
        cron = not bool(os.name == 'nt')
        if cron:
            tasks = ['25 13,14 * * *', '50 01 * * *']
        else:
            tasks = ['/sc daily /st "01:50:00"', '/sc daily /st "13:25:00"', '/sc daily /st "14:25:00"']
        errors += self.checkParse('at 1325,1425 ,150,0150', 'at 0150, 1325, 1425', tasks)
        #
        if cron:
            tasks = ['8 */15 * * *']
        else:
            tasks = ['/sc hourly /mo 15 /st 15:51:00']
        errors += self.checkParse('every 15hours', 'every 15 h', tasks)
        #
        if cron:
            tasks = ['*/5 * * * *']
        else:
            tasks = ['/sc minute /mo 5 /st 15:51:00']
        errors += self.checkParse('every 05m', 'every 5 m', tasks)
        #
        if cron:
            tasks = ['*/7 8-13 * * *']
        else:
            # On windows, if you set a start time and end time, the task expires, which is not
            # the semantics we want. So we currently don't support /st and /et
            #tasks = ['/sc minute /mo 7 /st 08:00:00 /et 14:00:00']
            tasks = ['/sc minute /mo 7 /st 15:51:00']
        errors += self.checkParse('every 7 min from 0800 to 1400', 'every 7 m, 0800-1400', tasks)
        #
        if cron:
            tasks = ['15 10,13 * * *', '0,45 8,11 * * *', '30 9,12 * * *']
        else:
            #tasks = ['/sc minute /mo 45 /st 08:00:00 /et 14:00:00']
            tasks = ['/sc minute /mo 45 /st 15:51:00']
        errors += self.checkParse('every 43m,0800- 1400', 'every 45 m, 0800-1400', tasks)
        if errors:
            self.fail('')
        if sys.stdout.txt.find('Rounded interval to every 45 minutes for simplicity') == -1:
            self.fail('Expected to see a message rounding 43 min to 45 min on stdout. Instead, saw:\n' + sys.stdout.txt)

if __name__ == '__main__':
    unittest.main()
