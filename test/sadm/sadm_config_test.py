#!/usr/bin/env python
#
# $Id: ConfigTest.py 10173 2011-06-28 20:45:12Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, sys, os
from testsupport import RUNROOT, checkin
from ioutil import FakeFile
sys.path.append(RUNROOT )
from lib.sadm_constants import *
from lib.sadm_config import *
from lib.sadm_config import _REQUIRED_TOOLS, _read_val
from lib.sadm_schedule import *

# This sample is only used to test our parsing ability;
# the actual values in the file are largely irrelevant.
_SAMPLE_CONFIG_FILE1 = '''
a=b
#foo-version=1.2.3
vcs-credentials-cached=False
allow-perf-tests=true
ctest-version = 2.8
cmake-version=2.9
gcc-version=4.0
msvc-version=8.0
schedule-continuous-manually=False
javac-version=1.6.3
appverif-version=4.0

ant-version=1.7.19.debug
'''

# This sample is used to compare against a config object
# loaded from disk, so its values have to be reasonable.
_SAMPLE_CONFIG_FILE2 = '''
working_repo_root=%s/reporoot
allow_official_builds=True
is_canonical_machine=False
machine_role=dev
master_repo_root=bzr+ssh://bazaar.example.com/master ## TODO fix me
automated_vcs_user=psbuildmaster
build_queue_url=https://bazaar.example.com/ ## TODO fix me
schedule_continuous_manually=False
test_mode=False
auto_update=True
auto_add_sandboxes=False
sandbox_container_folder=%s/sandboxes
''' % (HOMEDIR, HOMEDIR)

_SAMPLE_CONFIG_CLEAN = _SAMPLE_CONFIG_FILE2.replace('  gcc-version   ', 'gcc-version').replace('= True', '=True')

@checkin
class ConfigTest(unittest.TestCase):
    def testReadVal(self):
        self.assertEquals(True, _read_val('true'))
        self.assertEquals(False, _read_val('false'))
        self.assertEquals(True, _read_val('   true'))
        self.assertEquals(False, _read_val('\tfalse'))
        self.assertEquals(True, _read_val('True'))
        self.assertEquals(False, _read_val('fAlSE'))
        self.assertEquals(True, _read_val('1'))
        self.assertEquals(False, _read_val('0'))
        self.assertEquals(True, _read_val('yes'))
        self.assertEquals(False, _read_val('no'))
        self.assertEquals(True, _read_val('yEs'))
        self.assertEquals(False, _read_val('NO'))
        self.assertEquals('truly', _read_val(' truly '))
        self.assertEquals('pickle', _read_val('pickle'))
        self.assertEquals('-1', _read_val('-1'))
    def testToolKeys(self):
        for key in _REQUIRED_TOOLS.keys():
            self.assertEquals(key.lower(), key)
    def testLoad1(self):
        # Load a completely blank config, without consulting .sadm.conf on disk.
        x = Config('')
        x.load(_SAMPLE_CONFIG_FILE1)
        x.set_complete_perf_db_url('')
        self.assertEquals(None, x.get_complete_perf_db_url())
        self.assertEquals(None, x.allow_official_builds)
    def testLoad2(self):
        # Load a blank config, using actual .sadm.conf on disk but overriding
        # with values from our sample.
        x = Config()
        x.load(_SAMPLE_CONFIG_FILE2)
        url = "jdbc:mysql://db1..com/perftest?user=perftest-writer&password=FIXME" ## TODO FIX ME
        x.set_complete_perf_db_url(url)
        self.assertEquals(url.replace('FIXME', '%s'), x.perf_log_db_url)
        self.assertEquals('FIXME', x.perf_log_password)
        self.assertEquals(url, x.get_complete_perf_db_url())
        self.assertEquals(True, x.allow_official_builds)
    def testSaveNoChanges(self):
        # Load a completely blank config, without consulting .sadm.conf on disk.
        # True version values for msvc and appverif, if we're on windows, will be
        # overridden by what we put in the sample.
        x = Config('')
        x.load(_SAMPLE_CONFIG_FILE2)
        f = FakeFile()
        # This save should produce output that's identical to our input, except
        # that it might be in a different order. The appverif and msvc stuff
        # embedded in the sample don't cause us problems; they are simply there
        # to guarantee that what we save has such values even on linux, so the
        # test can be uniform.
        x.save(f)
        lines1 = [l.strip() for l in _SAMPLE_CONFIG_CLEAN.strip().split('\n')]
        lines1.sort()
        lines2 = [l.strip() for l in f.txt.strip().split('\n')]
        lines2.sort()
        self.assertEquals(str(lines1), str(lines2))
    def testSaveWithChanges(self):
        # Load a completely blank config, without consulting .sadm.conf on disk.
        x = Config('')
        x.automated_vcs_user = DEFAULT_VCS_USER
        f = FakeFile()
        x.save(f)
        lines = [l.strip() for l in f.txt.strip().split('\n')]
        lines.sort()
        samples = [
            'schedule_continuous_manually=False', 
            'is_canonical_machine=False', 
            'auto_add_sandboxes=False',
            'auto_update=True',
            'automated_vcs_user=build',
            'machine_role=dev'
        ]
        samples.append('build_queue_url=%s' %DEFAULT_BUILD_QUEUE)
        samples.append('test_mode=%s' % str(x.test_mode))
        samples.append('working_repo_root=%s/reporoot' % HOMEDIR.replace('\\', '/'))
        samples.append('hioin=%s' % str(x.host_is_on_internal_network()))
        samples.append('sandbox_container_folder=%s/sandboxes' % HOMEDIR.replace('\\', '/'))
        samples.append('master_repo_root=%s' % DEFAULT_MASTER_REPOROOT)
        samples.sort()
        self.assertEquals(str(samples), str(lines))

if __name__ == '__main__':
    unittest.main()
