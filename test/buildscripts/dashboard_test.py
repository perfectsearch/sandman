#!/usr/bin/env python
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import unittest
import sys
import os
import ioutil
import sandbox
import dateutils
from report.dashboard import *
from report.eval_summary import *
from testsupport import checkin
from unittest2 import TestCase, skip


TEST_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'dashboard_test')

def get_db(which):
    return Dashboard(sandbox.create_from_within(os.path.join(TEST_ROOT_DIR, 'x.trunk.' + which)).get_report_root())

# For many of our tests, we have to force the dashboard to pretend that the
# current time is something other than right now; otherwise unit tests will
# start to fail in the future because the checked-in data files contain results
# that age steadily.
PRETEND_TIME = 1314508844.842
PRETEND_TIME2 = 1323801523.329

def get_sample_eval_summary():
    bi = buildinfo.BuildInfo()
    return EvalSummary(
        'sadm.trunk.136.20',
        'OFFICIAL',
        'zufa',
        EvalPhase.TEST,
        None,
        1314492700.49,
        [11.08, 0.44, 9.18],
        'linux_x86-64',
        'Linux',
        '64',
        '2.6.35.13-92.fc14'
    )


@checkin
class DashboardTest(unittest.TestCase):
    def test_get_status_OK(self):
        db = get_db('OK')
        #db.debug = True
        db._pretend_time = PRETEND_TIME
        # Make sure that we're producing the test result from the checked-in
        # data, without eliminating stuff that's aged out of relevance.
        self.assertEquals('merukesh,zufa', ','.join(db.get_recent_hosts()))
        self.assertEqual(EvalResult.OK, db.get_status().result)
    def test_get_status_UNKNOWN_too_stale(self):
        db = get_db('OK')
        #db.debug = True
        # For this test, we're going to force the pretend time to be far enough
        # in the future than none of the status data is relevant.
        db._pretend_time = PRETEND_TIME + (MAX_RETAINED_SECONDS * 2)
        # Make sure that we're producing the test result from the checked-in
        # data, without eliminating stuff that's aged out of relevance.
        self.assertFalse(db.get_recent_hosts())
        self.assertEqual(EvalResult.UNKNOWN, db.get_status().result)
    def test_get_status_PROBLEMATIC(self):
        db = get_db('PROBLEMATIC')
        # db.debug = True
        db._pretend_time = PRETEND_TIME
        # Make sure that we're producing the test result from the checked-in
        # data, without eliminating stuff that's aged out of relevance.
        self.assertEquals('merukesh,zufa', ','.join(db.get_recent_hosts()))
        self.assertEqual(EvalResult.PROBLEMATIC, db.get_status().result)
        #print(db.get_status())
    def test_get_status_FAILED(self):
        db = get_db('FAILED')
        # db.debug = True
        db._pretend_time = PRETEND_TIME
        # Make sure that we're producing the test result from the checked-in
        # data, without eliminating stuff that's aged out of relevance.
        self.assertEquals('merukesh,zufa', ','.join(db.get_recent_hosts()))
        self.assertEqual(EvalResult.FAILED, db.get_status().result)
        #print(db.get_status())
    def test_add_summary(self):
        with ioutil.TempDir() as td:
            sb = sandbox.Sandbox(os.path.join(td.path, 'buildscripts.trunk.dev'))
            sb.layout()
            es = get_sample_eval_summary()
            db = Dashboard(sb.get_report_root())
            db.add_summary(es)
            fldr = os.path.join(sb.get_report_root(), 'zufa')
            self.assertTrue(os.path.isdir(fldr))
            self.assertTrue(os.path.isfile(os.path.join(fldr, 'results.txt')))
    def test_add_summary_merge_with_existing(self):
        with ioutil.TempDir() as td:
            sb = sandbox.Sandbox(os.path.join(td.path, 'buildscripts.trunk.dev'))
            sb.layout()
            es = get_sample_eval_summary()
            db = Dashboard(sb.get_report_root())
            start_time = es.get_start_time()
            start_text = str(es)
            fldr = os.path.join(sb.get_report_root(), 'zufa')
            os.makedirs(fldr)
            fname = os.path.join(fldr, 'results.txt')
            with open(fname, 'w') as f:
                for i in range(100):
                    # Make it look like the results file has 100 entries, spaced 4
                    # hrs apart, stretching back 400 hrs. At 168 hrs per week, this
                    # should look like about 2.5 weeks of history.
                    es.start_time -= (4 * 3600)
                    f.write(str(es) + '\n')
            es.start_time = start_time
            db.add_summary(es)
            with open(fname, 'r') as f:
                lines = [l.strip() for l in f.readlines()]
            self.assertEqual(start_text, lines[0])
            self.assertEqual(85, len(lines))
            ld = dateutils.format_standard_date_with_tz_offset(dateutils.parse_standard_date_with_tz_offset('2011-08-27 14:51:40.490000-0600'))
            self.assertEqual('sadm.trunk.136.20,OFFICIAL,zufa,TEST,,' + ld + ',11.08 0.44 9.18,linux_x86-64,Linux,64,2.6.35.13-92.fc14', lines[1])
            ld = dateutils.format_standard_date_with_tz_offset(dateutils.parse_standard_date_with_tz_offset('2011-08-13 18:51:40.490000-0600'))
            self.assertEqual('sadm.trunk.136.20,OFFICIAL,zufa,TEST,,' + ld + ',11.08 0.44 9.18,linux_x86-64,Linux,64,2.6.35.13-92.fc14', lines[84])
    def test_get_build_groups(self):
        db = get_db('multi')
        db._pretend_time = PRETEND_TIME
        db.set_load_all(True)
        bids = db.get_build_group_ids()
        self.assertEqual('sadm.trunk.137.20..|sadm.trunk.136.20..|sadm.trunk.135.20..|sadm.trunk.134.10..|sadm.trunk.134.2..', '|'.join([str(bid) for bid in bids]))
        self.assertEqual(6, len(db.get_build_groups()[bids[4]]))
    def test_get_status_lower_revno(self):
        db = get_db('lower')
        db._pretend_time = PRETEND_TIME2
        # Make sure that we're calculating the correct status
        # when the revision number has decreased due to merging branchs.
        self.assertEquals('bzr-megatron,skyrim', ','.join(db.get_recent_hosts()))
        self.assertEqual(EvalResult.FAILED, db.get_status().result)
        # Check that the Code Revno for Official builds is at 1351 and not 1358
        self.assertEqual(db.get_code_revnos()['OFFICIAL'], 1351)
        #print(db.get_status())

if __name__ == '__main__':
    unittest.main()
