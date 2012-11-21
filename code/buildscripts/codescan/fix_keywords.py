#!/usr/bin/env python
# 
# $Id: fix_keywords.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 

import sys, os, check_keywords, svnwrap, optparse, sandbox

parser = optparse.OptionParser('Usage: %prog [path]\n\nEnable keyword substitution for source code without an svn:keywords property.')

_STD_PROPVAL = 'Id Date Url Revision Author'

def main(folder):
    files = check_keywords.main(False, folder, options)
    if not (files is None):
        for f in files:
            print(svnwrap.propset(f, check_keywords.KEYWORDS_PROP, _STD_PROPVAL).strip())
        print('Fixed %d files.' % len(files))

if __name__ == '__main__':
    ( options, args ) = parser.parse_args()
    folder = None
    if args:
        folder = args[0]
    main(folder)
