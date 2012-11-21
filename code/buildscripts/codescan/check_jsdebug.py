#
# $Id: check_jsdebug.py 9317 2011-06-10 02:09:04Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import sys, os
buildscriptDir = os.path.dirname(__file__)
buildscriptDir = os.path.abspath(os.path.join(buildscriptDir, os.path.pardir))
sys.path.append(buildscriptDir)

import re, sandbox, optparse, codecs, optparse
import metadata, codescan, xmail
from ioutil import *

parser = optparse.OptionParser('Usage: %prog [options] [path]\n\nCheck whether code has active console code in javascript files.')
xmail.addMailOptions(parser)

JAVASCRIPT_PAT = re.compile(r'.*\.js$')
CONSOLE_PAT = re.compile(r'console\.[debug|log]')
COMMENT_PAT = re.compile(r'[ \t]*//[= \w\.@{}\(\)<>#/\'";:-]*')

def _read(path):
    f = codecs.open(path, 'r', 'utf-8')
    txt = f.read()
    f.close()
    return txt

def consoleMatches(matches, txt):
    m2 = []
    for m in matches:
        offset = m.start()
        linenum = codescan.getLinNumForOffset(txt, offset)


class JsDebugCheckVisitor:
    def __init__(self, warn):
        self.warn = warn
        self.categorizedFiles = {}
        self.badCount = 0
    def visit(self, folder, item, relativePath):
        if JAVASCRIPT_PAT.match(item):
            path = os.path.join(folder, item)
            txt = _read(path)
            nextInactiveBlock = codescan.pickInactiveBlockFinder(path)
            #Remove all the inactive blocks from our analysis
            txt = codescan.getActiveBlocksOnly(txt, nextInactiveBlock)
            matches = [m for m in CONSOLE_PAT.finditer(txt)]
            comments = [c for c in COMMENT_PAT.finditer(txt)]
            lines = []
            for m in matches:
                offset = m.start()
                linenum = codescan.getLineNumForOffset(txt, offset)
                comment = False
                for c in comments:
                    if (linenum == codescan.getLineNumForOffset(txt, c.start())) and (offset > c.start()):
                        comment = True
                if not comment:
                    lines.append(linenum)
            if lines:
                self.badCount += 1
                self.categorizedFiles[os.path.join(relativePath, item)] = lines

def check(path, warn=True):
    if not os.path.isdir(path):
        sys.stderr.write('%s is not a valid folder.\n' % path)
        return 1
    path = norm_seps(os.path.abspath(path), trailing=True)
    print('Checking for active console code in %s...\n' % path)
    visitor = JsDebugCheckVisitor(warn)
    checkedFiles, checkedFolders = metadata.visit(path, visitor)
    if visitor.badCount > 0:
        for key in visitor.categorizedFiles.keys():
            badFile = os.path.join(path, key)
            f = file(badFile).readlines()
            print badFile
            for line in visitor.categorizedFiles[key]:
                print ('%s - %s' % (line, f[line-1]))
    print('Checked %d files in %d folders; found %d errors.' % (checkedFiles, checkedFolders, visitor.badCount))
    return visitor.badCount, visitor.categorizedFiles

def main(warn, folder, options=None):
    badFiles = None
    exitCode = 0
    if not folder:
        folder = sandbox.current.get_code_root()
    oldStdout = None
    sendEmail = xmail.hasDest(options)
    if sendEmail:
        oldStdout = sys.stdout
        sys.stdout = FakeFile()
    try:
        exitCode, badFiles = check(folder, warn)
        if sendEmail:
            msg = sys.stdout.txt
            print(msg)
            sys.stdout = oldStdout
            oldStdout = None
            xmail.sendmail(msg, sender='Javascript Console Scanner <code.scan@example.com>',
                subject='Javascript scan on %s' % metadata.get_friendly_name_for_path(folder), options=options)
    finally:
        if oldStdout:
            sys.stdout = oldStdout
    return exitCode, badFiles

if __name__ == '__main__':
    ( options, args ) = parser.parse_args()
    folder = None
    if args:
        folder = args[0]
    exitCode, ignored = main(True, folder, options)
    sys.exit(exitCode)
