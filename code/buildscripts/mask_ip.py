#!/usr/bin/env python
#
# $Id: mask_ip.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import sys, os, shutil, sandbox, optparse

parser = optparse.OptionParser('Usage: %prog [options] [path]\n\nMask out ip that contains trade secrets.')
parser.add_option('--dry-run', dest='dryRun', action='store_true', help='Show what would be done, but do not touch file system.')

def mask(folder, f, dryRun):
    path = os.path.join(folder, f)
    print(path)
    if not dryRun:
        f = open(path, 'wt')
        f.write('// content masked')
        f.close()

def shouldMask(folder, name):
    return name.endswith('.cpp') or name.endswith('.h') or name.endswith('.c') or name.endswith('.obj') or name.endswith('.o')

def emptyFolder(root, subdir, dryRun):
    path = os.path.join(root, subdir)
    if os.path.isdir(path):
        print(path)
        if not dryRun:
            shutil.rmtree(path)
            os.mkdir(path)

def main(root, componentsToMask, dryRun):
    buildRoot = os.path.abspath(os.path.join(root, '../build'))
    emptyFolder(root, 'buildtools', dryRun)
    emptyFolder(root, 'boost', dryRun)
    emptyFolder(root, 'sample-data', dryRun)
    componentsToMask = [x[0:x.find(' ')] for x in componentsToMask]
    for c in componentsToMask:
        path = os.path.join(root, c)
        print('Masking %s...' % path)
        for folder, dirs, files in os.walk(path):
            print('folder = %s' % folder)
            if '.svn' in dirs:
                dirs.remove('.svn')
                svnPath = os.path.join(folder, '.svn')
                print(svnPath)
                if not dryRun:
                    shutil.rmtree(svnPath)
            for f in files:
                if shouldMask(folder, f):
                    mask(folder, f, dryRun)
    if os.path.isdir(buildRoot):
        emptyFolder(buildRoot, 'Testing', dryRun)
        for c in componentsToMask:
            path = os.path.join(root, c)
            for folder, dirs, files in os.walk(path):
                for f in files:
                    if shouldMask(folder, f):
                        mask(folder, f, dryRun)

if __name__ == '__main__':
    ( options, args ) = parser.parse_args()
    sb = None
    if args:
        sb = args[0]
    else:
        sb = sandbox.current.get_code_root()
    components = [x for x in sandbox.getComponents(sb) if x.find('/psa/') > -1]
    main(sb, components, options.dryRun)
