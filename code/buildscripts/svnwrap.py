#!/usr/bin/env python
#
# $Id: svnwrap.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import sys, subprocess, re, os, tempfile

def _os_norm_sep(path):
    if os.name == 'nt':
        return path.replace('/', '\\')
    return path

def _callSvn(args):
    svn = subprocess.Popen("svn " + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    txt = svn.stdout.read().decode('utf-8')
    svn.wait()
    return txt

# Call 'svn info' on specified path and return stdout.
def info(path):
    return _callSvn("info \"%s\"" % _os_norm_sep(path))

# Call 'svn status' on specified path and return stdout.
def status(path):
    return _callSvn("status \"%s\"" % _os_norm_sep(path))

# Call 'svn propget' on specified path and return stdout.
def propget(path, propname):
    return _callSvn('propget %s "%s"' % (propname, _os_norm_sep(path)))

def _propValNeedsFile(propVal):
    if propVal.find('\n') > -1:
        return True
    if propVal.find('"') > -1:
        return True
    return False

def propset(path, propname, propval):
    tpath = None
    cmd = "propset " + propname
    if _propValNeedsFile(propval):
        ftmp, tpath = tempfile.mkstemp(text=True)
        ftmp.write(propval)
        ftmp.close()
        cmd += ' -F "%s"' % tpath
    else:
        cmd += ' "%s"' % propval
    cmd += ' "%s"' % path
    answer = _callSvn(cmd)
    if tpath:
        os.remove(tpath)
    return answer

_REV_PAT = re.compile(r"$\s*Revision\s*:\s*(\d+)\s*$", re.MULTILINE | re.IGNORECASE)
_LASTCHANGED_REV_PAT = re.compile(r"$\s*Last Changed Rev\s*:\s*(\d+)\s*$", re.MULTILINE | re.IGNORECASE)
_LASTAUTHOR_PAT = re.compile(r"$\s*Last Changed Author\s*:\s*(.*?)\s*$", re.MULTILINE | re.IGNORECASE)
_LASTCHANGED_DATE_PAT = re.compile(r"$\s*Last Changed Date\s*:\s*(\d+.*?)\s*$", re.MULTILINE | re.IGNORECASE)
_URL_PAT = re.compile(r"$\s*URL\s*:\s*(.*)\s*$", re.MULTILINE | re.IGNORECASE)

# Call 'svn info' on specified path; find revision in stdout and return -- or '0' on failure.
def rev(path):
    txt = info(path)
    #print(info)
    m = _REV_PAT.search(txt)
    if m:
        return m.group(1).strip()
    return '0'

# Call 'svn info' on specified path; find URL mapped to local working copy in stdout and return, or 'unknown' on failure.
def url(path):
    txt = info(path)
    m = _URL_PAT.search(txt)
    if m:
        return m.group(1).strip()
    return "unknown"

_STANDARD_REPO_PAT = re.compile(r'(https://[^/]+/svn/[-A-Za-z0-9]+)/(.*)')

class Info:
    def __init__(self, path):
        path = _os_norm_sep(os.path.abspath(path))
        if path.endswith('\\'):
            path = path[0:-1]
        self.localPath = path
        self.rev = self.lastChangedRev = self.lastChangedAuthor = self.lastChangedDate = self.repo = self.url = self.component = self.category = self.branch = self.pathInSvn = self.rest = None
        txt = info(path)
        m = _REV_PAT.search(txt)
        if m:
            self.rev = m.group(1).strip()
        m = _LASTCHANGED_REV_PAT.search(txt)
        if m:
            self.lastChangedRev = m.group(1).strip()
        m = _LASTAUTHOR_PAT.search(txt)
        if m:
            self.lastChangedAuthor = m.group(1).strip()
        m = _LASTCHANGED_DATE_PAT.search(txt)
        if m:
            self.lastChangedDate = m.group(1).strip()
        m = _URL_PAT.search(txt)
        if m:
            self.url = m.group(1).strip()
            m = _STANDARD_REPO_PAT.match(self.url)
            if m:
                self.repo = m.group(1).strip()
                self.pathInSvn = m.group(2).strip()
                parts = m.group(2).split('/')
                # expect: (trunk|branches/???)/(src|projects|tools/(internal|utilities))/component)
                componentIdx = 2
                partCount = len(parts)
                if partCount > 1 and parts[0] == 'branches':
                    self.branch = parts[1]
                    componentIdx += 1
                else:
                    self.branch = parts[0]
                if partCount > componentIdx - 1:
                    self.category = parts[componentIdx - 1]
                    if self.category == 'tools':
                        self.category += '/' + parts[componentIdx]
                        componentIdx += 1
                    if partCount > componentIdx:
                        self.component = parts[componentIdx]
                        self.rest = '/'.join(parts[componentIdx+1:])
    def get_branchPath(self):
        if self.branch != 'trunk':
            return 'branches/' + self.branch
        return self.branch
    def __str__(self):
        return 'Path: %s\nURL: %s\nRepository Root: %s\nRevision: %s\nLast Changed Author: %s\nLast Changed Rev: %s\nLast Changed Date: %s' % (
            self.localPath, self.url, self.repo, self.rev, self.lastChangedAuthor, self.lastChangedRev, self.lastChangedDate)

def struct( path ):
    return Info(path)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        symbols = globals()
        verb = sys.argv[1]
        if verb in symbols:
            print(symbols[verb](sys.argv[2]))
            sys.exit(0)
    else:
        print('This script wraps the command-line svn program for the convenience of')
        print('other python scripts.')
        print('')
        sys.stderr.write('    svnwrap <rev|url|component> <path>\n\n')
    sys.exit(1)

