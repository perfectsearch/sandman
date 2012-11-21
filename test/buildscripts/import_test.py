#!/usr/bin/env python
#
# $Id: ImportTest.py 4183 2011-01-03 20:17:03Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import unittest, os, tempfile, subprocess, sys
from testsupport import checkin, CODEROOT

CODE_FOLDER = CODEROOT + '/buildscripts'

@checkin
class ImportTest(unittest.TestCase):
    def testImports(self):
        temp_dir = tempfile.mkdtemp()
        tempScript = os.path.join(temp_dir, 'import_test.py')
        #print('Writing test import script %s' % tempScript)
        f = open(tempScript, 'wt')
        f.write('import sys, traceback\n')
        f.write('oldRestOfPath = sys.path[1:]\n')
        f.write('newPath = [sys.path[0], "%s"]\n' % CODE_FOLDER)
        f.write('for item in oldRestOfPath:\n\tnewPath.append(item)\n')
        f.write('sys.path = newPath\n')
        f.write('exitCode = 0\n')
        items = [i for i in os.listdir(CODE_FOLDER) if i.endswith('.py')]
        for item in items:
            if ' ' in item or '-' in item:
                f.write('print("%s cannot be imported because its name would cause a syntax error.")\n' % item)
                f.write('exitCode = 1\n')
            else:
                moduleName = item[0:-3]
                f.write('try:\n\timport %s\nexcept:\n' % moduleName)
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
