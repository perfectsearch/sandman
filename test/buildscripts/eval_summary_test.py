#!/usr/bin/env python
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import unittest
import sys
import os
from report.eval_summary import *
import build_id
from testsupport import checkin


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
class EvalSummaryTest(unittest.TestCase):
    def test_ctor(self):
        es = get_sample_eval_summary()
        self.assertEqual('sadm.trunk.136.20', es.build_id)
        self.assertEqual('OFFICIAL', es.style)
        self.assertEqual('zufa', es.host)
        self.assertEqual(EvalPhase.TEST, es.final_phase)
        self.assertEqual(None, es.failure_reason)
    def test_elapsed(self):
        es = get_sample_eval_summary()
        self.assertAlmostEqual(20.7, es.get_elapsed_seconds())
        self.assertAlmostEqual(11.08, es.get_elapsed_seconds(EvalPhase.UPDATE))
        self.assertAlmostEqual(0.44, es.get_elapsed_seconds(EvalPhase.BUILD))
        self.assertAlmostEqual(9.18, es.get_elapsed_seconds(EvalPhase.TEST))
    def test_start_time(self):
        es = get_sample_eval_summary()
        self.assertAlmostEqual(1314492700.49, es.get_start_time())
    def test_end_time(self):
        es = get_sample_eval_summary()
        self.assertAlmostEqual(1314492721.19, es.get_end_time())
    def test_start_and_end_equal_elapsed(self):
        es = get_sample_eval_summary()
        self.assertAlmostEqual(es.get_elapsed_seconds(), es.get_end_time() - es.get_start_time())
    def test_reported_result(self):
        es = get_sample_eval_summary()
        self.assertEqual(EvalResult.OK, es.get_reported_result())
    def test_reported_result(self):
        es = get_sample_eval_summary()
        es.failure_reason = '5 tests failed'
        self.assertEqual(EvalResult.FAILED, es.get_reported_result())
    def test_imputed_result_official(self):
        es = get_sample_eval_summary()
        es.failure_reason = '5 tests failed'
        self.assertEqual(EvalResult.FAILED, es.get_imputed_result())
    def test_imputed_result_continuous(self):
        es = get_sample_eval_summary()
        es.style = 'CONTINUOUS'
        es.failure_reason = '5 tests failed'
        self.assertEqual(EvalResult.FAILED, es.get_imputed_result())
    def test_imputed_result_experimental(self):
        es = get_sample_eval_summary()
        es.style = 'EXPERIMENTAL'
        es.failure_reason = '5 tests failed'
        self.assertEqual(EvalResult.PROBLEMATIC, es.get_imputed_result())
    def test_str(self):
        es = get_sample_eval_summary()
        ld = dateutils.format_standard_date_with_tz_offset(dateutils.parse_standard_date_with_tz_offset('2011-08-27 18:51:40.490000-0600'))
        self.assertEqual('sadm.trunk.136.20,OFFICIAL,zufa,TEST,,' + ld + ',11.08 0.44 9.18,linux_x86-64,Linux,64,2.6.35.13-92.fc14', str(es))
    def test_parse_eval_summary_line(self):
        es = parse_eval_summary_line('sadm.trunk.136.20,OFFICIAL,zufa,TEST,,2009-05-27 18:29:06-0600,11.08 0.44 9.18,linux_x86-64,Linux,64,2.6.35.13-92.fc14')
        self.assertTrue(isinstance(es.build_id, build_id.BuildID))
    def test_enum_to_str(self):
        self.assertEqual('FAILED', enum_to_str(EvalResult, EvalResult.FAILED))
    def test_str_to_enum(self):
        self.assertEqual(EvalResult.FAILED, str_to_enum(EvalResult, "FAILED"))

if __name__ == '__main__':
    unittest.main()
