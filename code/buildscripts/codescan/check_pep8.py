#!/usr/bin/env python
#
# $Id: check_pep8.py 9319 2011-06-10 02:59:43Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys
import os
import subprocess

buildscriptDir = os.path.dirname(__file__)
buildscriptDir = os.path.abspath(os.path.join(buildscriptDir, os.path.pardir))
sys.path.append(buildscriptDir)

import re

import sandbox
import metadata
import subprocess

import optparse
import xmail
from ioutil import *

parser = optparse.OptionParser(
        'Usage: %prog [options] [path]\n\nSee whether python files pass a ' +
        'pep8 check. Optionally, email report.'
    )
xmail.addMailOptions(parser)

def hasPep8():
    try:
        import pep8
        return True
    except ImportError:
        return False


def runPep8(filename, options="--select=W601,E111,E701,W191 -r"):
    return os.system("pep8 %s %s" % (options, filename))


def checkFile(root, name, relativePath, warn=True):
    path = os.path.join(root, name)
    if (not path.endswith('.py')) or os.path.getsize(path) == 0:
        return 0
    answer = runPep8(path)
    if answer != 0:
        if warn:
            print('  %s: Warning: file fails pep8 check.' % os.path.join(
                relativePath, name))
        return 1
    else:
        pass  # print('%s pep errors = %s' % (name, answer))
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
    print('Checking pep8 compliance in %s...\n' % path)
    visitor = KeywordCheckVisitor(warn)
    checkedFiles, checkedFolders = metadata.visit(path, visitor)
    print('Checked %d files in %d folders; found %d errors.' % (
        checkedFiles, checkedFolders, len(visitor.badFiles)))
    return visitor.badFiles


def main(warn, folder, options=None):
    badFiles = []
    exitCode = 0

    if not hasPep8():
        print("Warning: This machine does not have pep8 installed.")
        if sys.platform.startswith('linux'):
            print("    install it using: yum install python-pep8")
        else:
            print("    install it using: easy_install pep8")
        return 0

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
            xmail.sendmail(msg,
                sender='Pep8 Scanner <code.scan@example.com>',
                subject='pep8 scan on %s' %
                    metadata.get_friendly_name_for_path(folder),
                options=options)
    finally:
        if oldStdout:
            sys.stdout = oldStdout
    return badFiles

def _is_potential_python_component(sb, c):
    code_dir = sb.get_component_path(c, 'code')
    # Eliminate classic java projects (ant or maven).
    if os.path.isdir(os.path.join(code_dir, 'src')):
        return False
    # Eliminate top-level and non-top-level C++ components.
    if os.path.isfile(os.path.join(code_dir, '.if_top', 'CMakeLists.txt')):
        return False
    if os.path.isfile(os.path.join(code_dir, 'CMakeLists.txt')):
        return False
    return True

def _has_clean_bzr_status(folder):
    txt = subprocess.check_output('bzr status "%s"' % folder, shell=True)
    txt = txt.strip()
    return not bool(txt)

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    folder = None
    if args:
        folder = args[0]
    if not folder:
        badFiles = []
        sb = sandbox.current
        # We're going to some effort to make this scan fast, because in many
        # sandboxes this test was taking 30-90 seconds before optimization.
        # The main ways we make it fast are:
        #   - Don't scan directories unlikely to contain python code.
        #   - In experimental sandboxes, skip any folders that don't have code
        #       checked out.
        #   - Don't scan buildscripts in complex sandboxes (buildscripts scans
        #       will only happen in simple sandboxes like tika, appliance-base,
        #       and so forth).
        checked_folders = 0
        code_components = [c for c in sb.get_on_disk_components() if sb.get_component_reused_aspect(c) == 'code']
        skip_buildscripts = len(code_components) > 4
        potential_python_components = [c for c in code_components if _is_potential_python_component(sb, c)]
        skip_checked_in = sb.get_sandboxtype().supports_checkouts()
        for c in potential_python_components:
            if c != 'buildscripts' or (not skip_buildscripts):
                folder = os.path.join(sb.get_code_root(), c)
                if (not skip_checked_in) or (not _has_clean_bzr_status(folder)):
                    checked_folders += 1
                    badFiles += main(True, os.path.join(sandbox.current.get_code_root(), c), options)
        tr = sb.get_test_root()
        for item in os.listdir(tr):
            if item != 'buildscripts' or (not skip_buildscripts):
                folder = os.path.join(tr, item)
                if os.path.isdir(folder):
                    if (not skip_checked_in) or (not _has_clean_bzr_status(folder)):
                        checked_folders += 1
                        badFiles += main(True, folder, options)
        if not checked_folders:
            print('No checked out python code found; scan skipped to optimize dev time.\nScan will be done by automated build.')
    else:
        badFiles = main(True, folder, options)
    exitCode = 0
    if len(badFiles) > 0:
        exitCode = len(badFiles)
    sys.exit(exitCode)
