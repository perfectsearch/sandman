#!/usr/bin/env python
#
# $Id: check_copyright.py 9317 2011-06-10 02:09:04Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys, os
buildscriptDir = os.path.dirname(__file__)
buildscriptDir = os.path.abspath(os.path.join(buildscriptDir, os.path.pardir))
sys.path.append(buildscriptDir)
import re
import sandbox
import metadata
import optparse
import xmail
from ioutil import *

parser = optparse.OptionParser('Usage: %prog [options] [path]\n\nCheck whether code has correct copyright notices. Optionally, email report.')
xmail.addMailOptions(parser)

def mightHaveHeader(txt):
    if PROPRIETARY_PAT.search(txt):
        return True
    if ALL_RIGHTS_RESERVED_PAT.search(txt):
        return True
    if txt.lower().find('copyright') > -1:
        return True
    return False

def matchPatterns(patterns, txt, debug=False):
    for patList in patterns:
        if type(patList) != LIST_TYPE:
            patList = [patList]
        foundCount = 0
        for pat in patList:
            if debug:
                print('Searching for %s' % pat.pattern)
            if pat.search(txt):
                if debug:
                    print('found it')
                foundCount += 1
                if foundCount == len(patList):
                    return True
    return False

VALID_HEADER = 0
MISSING_HEADER = 1
DISALLOWED_LICENSE = 2
INCOMPLETE_COPYRIGHT = 3
ALLOWED_OPEN_SOURCE = 4

# Do NOT add #if, #ifdef, or #ifndef to FIRST_CPP_CODE_PAT -- it's legal to put a copyright notice
# after a sentry in a header.'
FIRST_CPP_CODE_PAT = re.compile(r'^\s*(#include|class|struct|const|static)\s+', re.MULTILINE)
FIRST_JAVA_CODE_PAT = re.compile(r'^\s*(import|class|interface)\s+', re.MULTILINE)
FIRST_PYTHON_CODE_PAT = re.compile(r'^\s*(import|def|class|try:|from)\s+', re.MULTILINE)
FIRST_JAVASCRIPT_CODE_PAT = re.compile(r'^\s*(function|var)\s+', re.MULTILINE)

# Get the portion of the top of a file where copyright notice might validly appear. Normally
# this means the first 1k of text, possibly shortened to the end of a C-style block comment.
# However, if we see something that we know to be valid code, truncate just before that;
# the copyright notice must precede code.
def truncate(top, name):
    i = top.find('*/')
    if i > -1:
        top = top[0:i + 2]
    else:
        i = name.rfind('.')
        if i > -1:
            ext = name[i + 1:].lower()
        pat = None
        if ext == 'py':
            pat = FIRST_PYTHON_CODE_PAT
        elif ext == 'java':
            pat = FIRST_JAVA_CODE_PAT
        elif ext in ['cpp','cxx','c','h','hpp','hxx']:
            pat = FIRST_CPP_CODE_PAT
        elif ext == 'js':
            pat = FIRST_JAVASCRIPT_CODE_PAT
        if pat:
            m = pat.search(top)
            if m:
                #print('truncating header for %s at %s (%d)' % (name, m.group(0), m.start(0)))
                top = top[0:m.start(0)]
                #print('retained header = ')
                #print top
    return top

def checkFile(root, name, relativePath, warn=True):
    path = os.path.join(root, name)
    #print(path)
    f = open(path, 'rt')
    top = f.read(1024).strip()
    if not top:
        return 0
    top = top.split('\n')
    top = '\n'.join([l.strip() for l in top if l.strip()])
    top = truncate(top, name)
    severity = 'Error'
    exitCode = MISSING_HEADER
    msg = ''
    if matchPatterns(EXPLICITLY_ALLOWED_PATS, top):
        m = THIRD_PARTY_LICENSE_PAT.search(top)
        license = m.group(1)
        warn = True # Force display
        severity = 'Info'
        msg = 'Open source (%s) explicitly allowed' % license
        exitCode = ALLOWED_OPEN_SOURCE
    elif matchPatterns(INVALID_PATS, top):
        msg = 'disallowed copyright/header'
        exitCode = DISALLOWED_LICENSE
    else:
        if not matchPatterns(VALID_PATS, top):
            msg = 'no valid copyright/header'
            if mightHaveHeader(top):
                warn = True # Force display
                severity = 'Warning'
                msg = 'incomplete copyright notice'
                exitCode = INCOMPLETE_COPYRIGHT
                #matchPatterns(EXPLICITLY_ALLOWED_PATS, top, debug=True)
        else:
            exitCode = VALID_HEADER
    if msg and (warn or (severity == 'Error')):
        print('  %s: %s: %s.' % (os.path.join(relativePath, name), severity, msg))
        #print(top)
        #print('\n')
    return exitCode

class CopyrightCheckVisitor:
    def __init__(self, warn):
        self.warn = warn
        self.categorizedFiles = {}
        self.badCount = 0
    def visit(self, folder, item, relativePath):
        #print('visited %s' % item)
        err = checkFile(folder, item, relativePath, self.warn)
        if not err in self.categorizedFiles:
            self.categorizedFiles[err] = []
        self.categorizedFiles[err].append(os.path.join(folder, item))
        if (err == MISSING_HEADER) or (err == DISALLOWED_LICENSE):
            self.badCount += 1

def check(path, warn=True):
    if not os.path.isdir(path):
        sys.stderr.write('%s is not a valid folder.\n' % path)
        return 1
    path = norm_folder(path)
    print('Checking copyright correctness in %s...\n' % path)
    visitor = CopyrightCheckVisitor(warn)
    checkedFiles, checkedFolders = metadata.visit(path, visitor)
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
            xmail.sendmail(msg, sender='Copyright Scanner <code.scan@example.com>', ## TODO make part of config
                subject='copyright scan on %s' % metadata.get_friendly_name_for_path(folder), options=options)
    finally:
        if oldStdout:
            sys.stdout = oldStdout
    return exitCode, badFiles

EXT_PAT = metadata.INTERESTING_EXT_PAT
PROPRIETARY_PAT = re.compile('proprietary.*confidential', re.IGNORECASE | re.DOTALL)
ALL_RIGHTS_RESERVED_PAT = re.compile('all rights reserved', re.IGNORECASE | re.DOTALL)
APPROVED_BY_PAT = re.compile(r'approved by\s*:', re.IGNORECASE)
APPROVAL_DATE_PAT = re.compile(r'approval date\s*:', re.IGNORECASE)
THIRD_PARTY_SOURCE_PAT = re.compile(r'source\s*:', re.IGNORECASE)
THIRD_PARTY_LICENSE_PAT = re.compile(r'license\s*:\s*(.*?)\s*$', re.MULTILINE | re.IGNORECASE)
STD_COPYRIGHT_PATS = [ALL_RIGHTS_RESERVED_PAT, PROPRIETARY_PAT,
    re.compile('copyright[^\r\n]+Perfect Search', re.IGNORECASE | re.DOTALL)]
GPL_COPYRIGHT_PATS = [re.compile('gnu.*general.*public.*license', re.IGNORECASE | re.DOTALL),
    re.compile('free.*software.*foundation', re.IGNORECASE | re.DOTALL)]
OPEN_SOURCE_ALLOWED_PATS = [re.compile('OPEN SOURCE INCLUDED WITH MANAGEMENT APPROVAL'),
    APPROVED_BY_PAT, APPROVAL_DATE_PAT, THIRD_PARTY_SOURCE_PAT,
    THIRD_PARTY_LICENSE_PAT]
EXPLICITLY_ALLOWED_PATS = [OPEN_SOURCE_ALLOWED_PATS]
MIT_BSD_PAT = re.compile('(MIT|BSD) license', re.IGNORECASE)
CREATIVE_COMMONS_PAT = re.compile('creative commons', re.IGNORECASE)
VALID_PATS = [STD_COPYRIGHT_PATS]
INVALID_PATS = [GPL_COPYRIGHT_PATS, MIT_BSD_PAT, CREATIVE_COMMONS_PAT]
LIST_TYPE = type([])

if __name__ == '__main__':
    ( options, args ) = parser.parse_args()
    folder = None
    if args:
        folder = args[0]
    exitCode, ignored = main(True, folder, options)
    sys.exit(exitCode)
