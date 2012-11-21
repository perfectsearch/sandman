#!/usr/bin/env python
# 
# $Id: fix_copyright.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 
import sys, os, re, sandbox, check_copyright, optparse
from ioutil import *

parser = optparse.OptionParser('Usage: %prog [path]\n\nAdd standard header to code files that lack copyright.')

def _getHeader(fname):
    ext = ''
    i = fname.rfind('.')
    if i > -1:
        ext = fname[i+1:].lower()
    if ext in ['java','c','cpp','cxx','h','hpp','js','css','rc','cs']:
        return '/*%s\n */' % _STD_HEADER.replace('\n', '\n * ')
    if ext in ['xml','htm','html','xsl','xslt']:
        return '<!-- %s -->' % _STD_HEADER
    if ext in ['bat','cmd']:
        return 'REM ' + _STD_HEADER.replace('\n', '\nREM ')
    if ext in ['vb','vbs']:
        return "' " + _STD_HEADER.replace('\n', "\n' ")
    return '# ' + _STD_HEADER.replace('\n', '\n# ')

_UTF8_BOM = '\xEF\xBB\xBF'
def _addHeader(path, txt = None):
    if not txt:
        txt = read_file(path)
    txt = txt.replace('\r', '')
    hdr = _getHeader(path)
    # In general, we want to add the header at the beginning of the file.
    # However, for shell scripts, we want to preserve the directive that invokes
    # an interpreter as the first line.
    if txt.lstrip().startswith('#!'):
        lines = txt.lstrip().split('\n')
        firstLine = lines[0]
        return firstLine + '\n' + hdr + '\n' + '\n'.join(lines[1:])
    elif txt.startswith(_UTF8_BOM):
        return _UTF8_BOM + hdr + '\n' + txt[3:]
    else:
        return hdr + '\n' + txt

def fix(path):
    txt = _addHeader(path)
    f = open(path, 'wt')
    f.write(txt)
    f.close()
    print('  Fixed %s' % path)

def main(folder, options):
    badFileCount, files = check_copyright.main(False, folder, options)
    fixedCount = 0
    if files and check_copyright.MISSING_HEADER in files:
        toFix = files[check_copyright.MISSING_HEADER]
        fixedCount = len(toFix)
        for f in toFix:
            fix(f)
    if not (files is None):
        print('Fixed %d files.' % fixedCount)

_STD_HEADER = '''
\x24Id: filename 3521 2010-11-25 00:31:22Z svn_username $

Proprietary and confidential.
Copyright \x24Date:: 2010#$ Perfect Search Corporation.
All rights reserved.
'''

if __name__ == '__main__':
    ( options, args ) = parser.parse_args()
    folder = None
    if args:
        folder = args[0]
    main(folder, options)
