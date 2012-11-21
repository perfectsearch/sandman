# 
# $Id: memCheckTest.py 7057 2011-04-18 17:21:07Z ahartvigsen $
# 
#
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 
from sys import argv
import os,shlex, subprocess
from time import ctime

def memCheck(test, buildDir):
    testToCopy = test + '.exe'
    t = ctime()
    t = t[t.find(":")-2:t.find(":")+6].replace(':','')
    testToRun = test + t + '.exe'
    command= []
    if os.name == 'nt':
        buildDir = buildDir.replace('/','\\')
        testPath = buildDir + '\\' + test.replace("-TestRunner","") + '\\test\\Debug\\'
        codeDir = buildDir.replace('build', 'code')
        logsDir = os.path.expanduser('~') + '\\AppverifierLogs\\'
        command.append(['copy', testPath+testToCopy, testPath+testToRun])
        command.append(['appverif', '-enable', 'Memory', '-for', testToRun])
        command.append([testPath+testToRun])
        command.append(['appverif', '-export', 'log', '-for', testToRun, '-with', 'to='+logsDir+'\\'+testToRun+'.xml'])
        command.append(['appverif', '/n', testToRun])
        command.append(['del', testPath+testToRun])
        for c in command:
            p = subprocess.call(c, shell=True, cwd=buildDir)
            if c is command[3]:
                result = p
        f = file(logsDir+testToRun+'.xml').read()
        print f
        return result
    else:
        testPath = buildDir + '/' + test.replace("-TestRunner","") + '/test/'
        testToRun = testPath + test + '-TestRunner'
        return subprocess.call(['valgrind ' + testToCopy], shell=True, cwd=buildDir)

if __name__ == '__main__':
    memCheck(argv[1], argv[2])
