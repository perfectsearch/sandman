#
# $Id: ImportTest.py 9277 2011-06-09 20:28:09Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, os, tempfile, subprocess, sys
from testsupport import checkin, RUNROOT


@checkin
class ImportTest(unittest.TestCase):
    def testImports(self):
        temp_dir = tempfile.mkdtemp()
        tempScript = os.path.join(temp_dir, 'import_test.py')
        #print('Writing test import script %s' % tempScript)
        f = open(tempScript, 'wt')
        f.write('import sys, traceback\n')
        f.write('oldRestOfPath = sys.path[1:]\n')
        f.write('newPath = [sys.path[0], "%s"]\n' % RUNROOT)
        f.write('for item in oldRestOfPath:\n\tnewPath.append(item)\n')
        f.write('sys.path = newPath\n')
        f.write('exitCode = 0\n')
        items = ['sadm_constants.py', 'sadm_util.py', 'sadm_sandbox.py', 'sadm_schedule.py']
        for item in items:
            if item.find(' ') > -1 or item.find('-') > -1:
                f.write('print("%s cannot be imported because its name would cause a syntax error.")\n' % item)
                f.write('exitCode = 1\n')
            else:
                moduleName = item[0:-3]
                f.write('try:\n\timport lib.%s\nexcept:\n' % moduleName)
                f.write('\ttraceback.print_exc()\n')
                f.write('\texitCode = 1\n')
        f.write('if exitCode: print("IMPORTS FAILED")\n')
        f.write('sys.exit(exitCode)')
        f.close()
        p = subprocess.Popen('python "%s"' % tempScript, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)
        out = p.stdout.read()
        exitCode = p.wait()
        os.remove(tempScript)
        os.rmdir(temp_dir)
        if exitCode != 0:
            self.fail(out)

if __name__ == '__main__':
    unittest.main()
