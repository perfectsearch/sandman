#!/usr/bin/env python
#
# $Id: check_disabled_tests.py 9317 2011-06-10 02:09:04Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import os
import sys
buildscriptDir = os.path.dirname(__file__)
buildscriptDir = os.path.abspath(os.path.join(buildscriptDir, os.path.pardir))
sys.path.append(buildscriptDir)
import re
import sandbox
import optparse
import smtplib
import svnwrap
import codescan
import xmail
import metadata
from ioutil import *
from disabled_unit_test import DisabledUnitTest

EXT_PAT = re.compile(r'.*\.(cpp|java|h|py)$', re.IGNORECASE)
_LBL_PAT = re.compile(r'^\s*([a-z]+):\s*(.*?)\s*$', re.IGNORECASE)
_DISABLED_DESCRIPTOR_MARKER = 'UNIT TEST TEMPORARILY DISABLED'
DISABLED_PAT = re.compile('/\\*[-_\\.\\* \t\r\n]*%s.*?\\*/' % _DISABLED_DESCRIPTOR_MARKER, re.DOTALL)
NON_RECURSING_FOLDERS_PAT = re.compile(r'(.svn|ext(js)?|boost|.metadata|buildtools|Debug|Release|psa-htdocs|sample-data|data|build|Archive|Dist|Install|bin|lib)$')
FROM = 'Disabled Unit Test Scanner <code.scan@example.com>' ## TODO make configurable
DISABLED_JAVA_PAT = re.compile('^\s*//\s*@Test', re.MULTILINE | re.DOTALL)

parser = optparse.OptionParser('Usage: %prog [options] [path]\n\nCheck for disabled unit tests; optionally nag developers to fix them.')
parser.add_option('--nag', dest="nag", action="store_true", help="Emit emails nagging people to fix disabled tests.")
xmail.addMailOptions(parser, to=False)

def getUnique(items):
    uniques = {}
    for x in items:
        uniques[x] = 1
    return uniques.keys()[:]

def getAddressList(txt):
    items = []
    if txt:
        txt = txt.replace(';', ',')
        items = [x.strip() for x in txt.split(',') if x.strip()]
        items = getUnique(items)
        items.sort()
    return items

def getRawAddress(address):
    i = address.find('<')
    if i > -1:
        j = address.find('>', i)
        if j == -1:
            return address[i + 1:].strip()
        return address[i + 1:j].strip()
    return address.strip()

def nag(dt, msg, options):
    if dt.owner or options.cc:
        fname = os.path.basename(dt.path)
        subject = 'disabled unit test near %s, line %d' % (fname, dt.lineNum)
        msg = ('''You are one of the people responsible for re-enabling this test. Please
get the test working, re-enable it, remove the comment that flags it as
disabled, and mark ticket #%s fixed. The sooner you can do this, the better.
Until the test is re-enabled, an important signal about the integrity of our
code is being suppressed with each build+test cycle.

''' % dt.ticket) + msg
        xmail.sendmail(msg, to=dt.owner, sender=FROM, subject=subject, options=options)
    else:
        sys.stderr.write('%s(%d): Error: disabled unit test but nobody can be nagged!\n', dt.path, dt.lineNum)

_CPP_TESTNAME_PAT = re.compile(r'^\s*(SIMPLE_TEST\s*\(\s*(.*?)\s*\)|class\s+([a-zA-Z_0-9]+)\s*:\s*(public|protected|private)\s+[a-zA-Z_0-9]+Test)', re.MULTILINE | re.DOTALL)
_JAVA_TESTNAME_PAT = re.compile(r'^\s*public\s+void\s+([a-zA-Z_0-9]+)\s*\(', re.MULTILINE | re.DOTALL)

def _extractTestNameFromMatch(m, java):
    if java:
        return m.group(1)
    elif m.group(1).find('SIMPLE_TEST') > -1:
        return m.group(2)
    else:
        return m.group(3)

def getNameOfNextTestMethod(path, txt, offset):
    i = min(len(txt), offset + 500)
    nextFewLines = txt[offset:i]
    java = path.endswith('.java')
    if java:
        testnamePat = _JAVA_TESTNAME_PAT
    else:
        testnamePat = _CPP_TESTNAME_PAT
    m = testnamePat.search(nextFewLines)
    if m:
        return _extractTestNameFromMatch(m, java)

_ALL_OR_ENTIRE_PAT = re.compile('(^|\s+)(all($|\s+)|entire\s+)', re.IGNORECASE)

def disabledTestIsProperlyDocumented(testName, disabledTests):
    if not testName:
        return False
    testName = testName.lower()
    for dut in disabledTests:
        if _ALL_OR_ENTIRE_PAT.search(dut.which):
            return True
        regex = re.compile(r'\b%s\b' % testName, re.IGNORECASE)
        if regex.search(dut.which):
            return True
    return False

def checkFile(fpath):
    #print('checking %s' % fpath)
    disabledTests = []
    txt = read_file(fpath)
    # First, look through for tests that are disabled in the way we expect.
    standardDisableCount = 0
    for match in DISABLED_PAT.finditer(txt):
        disabledTests.append(DisabledUnitTest(fpath, txt, match.start(), match.end()))
        standardDisableCount += 1
    improper = []
    java = bool(fpath.endswith('.java'))
    # Now, scan through the file looking for stuff that's maybe disabled in the wrong way.
    # We do this so that over time, everyone who's working in the codebase converges on
    # the same best practices, instead of circumventing the system.
    if java:
        # In java, look for //@Test where we can't tie the associated method to a
        # standard comment about being disabled.
        for match in DISABLED_JAVA_PAT.finditer(txt):
            name = getNameOfNextTestMethod(fpath, txt, match.start())
            if not disabledTestIsProperlyDocumented(name, disabledTests):
                tuple = (name, 1 + codescan.getLineNumForOffset(txt, match.start()))
                improper.append(tuple)
        nextInactiveBlock = codescan.getNextInactiveJavaBlock
        testnamePat = _JAVA_TESTNAME_PAT
    elif fpath.endswith('.cpp') or fpath.endswith('.h'):
        nextInactiveBlock = codescan.getNextInactiveCppBlock
        testnamePat = _CPP_TESTNAME_PAT
    else:
        nextInactiveBlock = _findNoInactiveBlocks
        testnamePat = None
    # In both java and C++, look for methods that have been completely commented
    # out. In C++, also check for methods that have been #ifdef'ed out.'
    i = 0
    while testnamePat:
        range = nextInactiveBlock(txt, i)
        if not range:
            break
        block = txt[range[0]:range[1]]
        for match in testnamePat.finditer(block):
            name = _extractTestNameFromMatch(match, java)
            if not disabledTestIsProperlyDocumented(name, disabledTests):
                lineNum = 1 + codescan.getLineNumForOffset(txt, range[0] + match.start())
                tuple = (name, lineNum)
                improper.append(tuple)
        i = range[1]
    return disabledTests, improper

def _findNoInactiveBlocks(x, y):
    return -1, -1

class TestFolderOnlyRecurser:
    def select(self, folder, dirs):
        # We're removing items from dirs rather than simply resetting it,
        # because we have to modify the object *in place* in order to
        # prevent recursion.
        test_folder = None
        if 'test' in dirs:
            test_folder = 'test'
        elif 'Test' in dirs:
            test_folder = 'Test'
        if test_folder:
            i = len(dirs) - 1
            while i > -1:
                d = dirs[i]
                if d != test_folder:
                    dirs.remove(d)
                i -= 1
        #print('setting recursable folders under %s to %s' % (folder, str(dirs)))
        return dirs

class TestCheckVisitor:
    def __init__(self):
        self.disabledTests = []
        self.improperCount = 0
        self.improperSummary = ''
    def visit(self, folder, item, relativePath):
        #print('visited %s' % item)
        # If we're in a test folder, or anywhere below it...
        if folder.lower().find('/test/') > -1:
            disabledTestsInThisFile, improper = checkFile(folder + item)
            if disabledTestsInThisFile:
                self.disabledTests.extend(disabledTestsInThisFile)
            if improper:
                self.improperCount += len(improper)
                for tuple in improper:
                    self.improperSummary += '%s(%d): Warning: disabled unit test %s seems improperly documented.\n' % (relativePath + item, tuple[1], tuple[0])
                    info = svnwrap.Info(folder + item)
                    self.improperSummary += '    Last changed revision: %s\n' % info.lastChangedRev
                    self.improperSummary += '    Last changed by: %s\n' % info.lastChangedAuthor
                    self.improperSummary += '    Last changed date: %s\n' % info.lastChangedDate
                    self.improperSummary += '\n'

def check(path, options):
    if not os.path.isdir(path):
        sys.stderr.write('%s is not a valid folder.\n' % path)
        return 1
    path = norm_folder(path)
    print('Checking for disabled unit tests in %s...\n' % path)
    visitor = TestCheckVisitor()
    checkedFiles, checkedFolders = metadata.visit(path, visitor)
    rootLen = len(path)
    if visitor.improperSummary:
        print(visitor.improperSummary)
    shouldNag = xmail.hasDest(options) or xmail.hasHostInfo(options)
    for dt in visitor.disabledTests:
        txt = '%s(%d): Warning: disabled unit test.\n' % (dt.path[rootLen:], dt.lineNum)
        txt += '    ' + str(dt).replace('\n', '\n    ')
        print(txt + '\n')
        if visitor.improperSummary:
            txt += '\n\nIn addition, %d unit tests appear to be disabled but improperly documented.\n' % visitor.improperCount
            txt += 'Please consider fixing these as well:\n\n'
            txt += visitor.improperSummary
        if shouldNag:
            nag(dt, txt, options)
    print('Checked %d files in %d folders.\n  Found %d correctly disabled tests.\n  Found %d tests that seem to be disabled but not documented.' % (checkedFiles, checkedFolders, len(visitor.disabledTests), visitor.improperCount))

if __name__ == '__main__':
    ( options, args ) = parser.parse_args()
    if args:
        folder = args[0]
    else:
        folder = sandbox.current.get_test_root()
    exitCode = check(folder, options)
    sys.exit(exitCode)
