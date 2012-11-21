#!/usr/bin/env python
#
# $Id: check_keywords.py 9317 2011-06-10 02:09:04Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys, os, re, sandbox, svnwrap, metadata, optparse, xmail
from ioutil import *

parser = optparse.OptionParser('Usage: %prog [options] [path]\n\nSee whether svn keyword expansion is enabled on source code files. Optionally, email report.')
xmail.addMailOptions(parser)

HELP_PAT = re.compile(r'(--?|/)(\?|(h(elp)?))$', re.IGNORECASE)
EXT_PAT = metadata.INTERESTING_EXT_PAT
NON_RECURSING_FOLDERS = ['.svn','boost','.metadata','build','Archive','Dist','Install']
KEYWORDS_PROP = "svn:keywords"

def checkFile(root, name, relativePath, warn=True):
    path = os.path.join(root, name)
    if os.path.getsize(path) == 0:
        return 0
    answer = svnwrap.propget(path, KEYWORDS_PROP).strip()
    if not answer:
        if warn:
            print('  %s: Warning: svn:keywords property not set.' % os.path.join(relativePath, name))
        return 1
    else:
        pass #print('%s svn:keywords = %s' % (name, answer))
    return 0

class KeywordCheckVisitor:
    def __init__(self, warn):
        self.warn = warn
        self.badFiles = []
    def visit(self, folder, item, relativePath):
        #print('visited %s' % item)
        err = checkFile(folder, item, relativePath, self.warn)
        if err:
            self.badFiles.append(folder + item)

def check(path, warn=True):
    if not os.path.isdir(path):
        sys.stderr.write('%s is not a valid folder.\n' % path)
        return 1
    path = norm_folder(path)
    print('Checking svn:keywords in %s...\n' % path)
    visitor = KeywordCheckVisitor(warn)
    checkedFiles, checkedFolders = metadata.visit(path, visitor)
    print('Checked %d files in %d folders; found %d errors.' % (checkedFiles, checkedFolders, len(visitor.badFiles)))
    return visitor.badFiles

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
        badFiles = check(folder, warn)
        if sendEmail:
            msg = sys.stdout.txt
            #print(msg)
            sys.stdout = oldStdout
            oldStdout = None
            xmail.sendmail(msg, sender='Keyword Scanner <code.scan@example.com>',
                subject='svn:keywords scan on %s' % metadata.get_friendly_name_for_path(folder), options=options)
    finally:
        if oldStdout:
            sys.stdout = oldStdout
    return badFiles

if __name__ == '__main__':
    ( options, args ) = parser.parse_args()
    folder = None
    if args:
        folder = args[0]
    badFiles = main(True, folder, options)
    exitCode = 0
    if badFiles:
        exitCode = len(badFiles)
    sys.exit(exitCode)
