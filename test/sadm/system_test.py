#
# $Id: SystemTest.py 9424 2011-06-13 18:42:04Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
from unittest2 import skip
import time, os, sys, subprocess, traceback, shutil
from testsupport import checkin, RUNROOT, TESTROOT
sys.path.append(RUNROOT)
from lib.sadm_constants import TEST_SANDBOXES, APP_FOLDER
import sandbox
import check_output
import ioutil
import StringIO
sys.path.append(TESTROOT + '/buildscripts')
import _testcase


@skip("9/15/11 this test can't be run until we finish work on the run aspect -- Julie Jones")
@checkin
class SystemTest(_testcase.TestCaseEx):
    def test_sadm_self_update(self):
        stdout = StringIO.StringIO()
        try:
            with ioutil.TempDir() as td:
                rundir = os.path.join(td.path, "run")
                # We are copying from <built root>/sadm instead of from <run root>, in case
                # sadm is ever not the top of the dependency hierarchy in a sandbox.
                shutil.copytree(sandbox.current.get_component_path('sadm', 'built'), rundir)
                def run(cmd, stdout):
                    stdout.write(cmd + '\n')
                    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    p.stdout.read()
                    p.wait()
                with ioutil.WorkingDir(rundir) as twd:
                    run('bzr init "%s"' % rundir, stdout)
                    run('bzr add', stdout)
                    run('bzr ci -m "initial commit"', stdout)
                    with ioutil.TempDir() as td2:
                        new_file = 'test-the-update-procedure'
                        run('bzr co --lightweight "%s" "%s"' % (rundir, td2.path), stdout)
                        # make a change in master
                        open(os.path.join(rundir, new_file), "w").close()
                        run('bzr add', stdout)
                        run('bzr ci -m "second commit"', stdout)
                        run('python "%s/sadm.py" update --auto-confirm --test' % td2.path, stdout)
                        self.assertTrue(os.path.isfile(os.path.join(td2.path, new_file)))
        except:
            print(stdout.getvalue())
            import traceback
            traceback.print_exc()

    def test_sadm(self):
        pinit = subprocess.Popen(['python',  APP_FOLDER+'/sadm.py', '--test', 'init', 'mathapp.trunk.test'], stdout=subprocess.PIPE)
        pinit.wait()
        output = pinit.stdout.read()
        self.assertTrue(output.find('Sandbox is ready.') > -1)
        plist = subprocess.Popen(['python',  APP_FOLDER+'/sadm.py', '--test', 'list', '--no-color'], stdout=subprocess.PIPE)
        compStr = 'mathapp.trunk.test'.ljust(35)+' - unscheduled'
        output = plist.stdout.read().strip()
        self.assertTrue(output.find(compStr) > -1)
        pstart = subprocess.Popen(['python',  APP_FOLDER+'/sadm.py', '--test', 'start', 'mathapp.trunk.test'], stdout=subprocess.PIPE)
        output = pstart.stdout.read()
        pstart.wait()
        evalLog = os.path.join(TEST_SANDBOXES, 'mathapp.trunk.test', 'eval-log.txt')
        self.assertTrue(os.path.exists(evalLog))
        evalFile = open(evalLog, 'r')
        evalData = evalFile.read()
        self.assertFalse(evalData.find('FAILED') > -1)
        evalFile.close()
        premove = subprocess.Popen(['python',  APP_FOLDER+'/sadm.py', '--test', 'remove', 'mathapp.trunk.test'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        premove.communicate('y')
        premove.wait()
        self.assertFalse(os.path.exists(TEST_SANDBOXES+'mathapp.trunk.test'))

