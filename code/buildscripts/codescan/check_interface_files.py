#!/usr/bin/env python
#
# $Id: check_interface_files.py 9317 2011-06-10 02:09:04Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys, os
buildscriptDir = os.path.dirname(__file__)
buildscriptDir = os.path.abspath(os.path.join(buildscriptDir, os.path.pardir))
sys.path.append(buildscriptDir)
import re, sandbox, optparse, metadata
from ioutil import *

parser = optparse.OptionParser('Usage: %prog [path]\n\nCheck provides.txt and requires.txt for proper format')

VALID_VERSIONED_INTERFACE_LINE_PAT = re.compile(r'^\s*VERSIONED_INTERFACE\(\s*[a-zA-Z_:][a-zA-Z0-9_:-]*\s*,\s*[\d\.]+\s*,\s*"[^\(\)"]*"\s*\)\s*$')

def checkFile(file, warn=True):
    '''Check Versioned Interface File is valid'''
    print('  Checking %s...' % file)
    rtn = True
    for line in open(file, 'rt'):
        line = line.strip()
        if  len(line) == 0:
            continue
        if not VALID_VERSIONED_INTERFACE_LINE_PAT.match(line) :
            rtn = False
            if warn:
                print '    ERROR: %s is not valid in the %s' % (line, file)
    return rtn

class FolderChecker:
    def __init__(self, warn):
        self.rtn = True
        self.warn = warn
    def select(self, folder, dirs):
        # Exclude any *egg-info folders; these are created by pylons and have
        # files named requires.txt that don't match our conventions.
        i = len(dirs) - 1
        while i > -1:
            d = dirs[i]
            if d.endswith('egg-info'):
                dirs.remove(d)
            i -= 1
        testFile = os.path.join(folder,"provides.txt")
        if os.path.exists(testFile):
            self.rtn = self.rtn and checkFile(testFile, self.warn)
        testFile = os.path.join(folder,"requires.txt")
        if os.path.exists(testFile):
            self.rtn = self.rtn and checkFile(testFile, self.warn)
        return dirs

class DoNothingVisitor:
    def visit(self, *args):
        pass

def check(folder, warn=True):
    if not os.path.isdir(folder):
        sys.stderr.write('%s is not a valid folder.\n' % folder)
        return 1
    fc = FolderChecker(warn)
    checkedFiles, checkedFolders = metadata.visit(folder, DoNothingVisitor(), fc)
    if(fc.rtn):
        return 0
    else:
        return 1

def main(warn, folder, options=None):
    exitCode = 0
    if not folder:
        folder = sandbox.current.get_code_root()
    exitCode = check(folder, warn)
    return exitCode

if __name__ == '__main__':
    ( options, args ) = parser.parse_args()
    folder = None
    if args:
        folder = args[0]
    exitCode = main(True, folder, options)
    sys.exit(exitCode)
