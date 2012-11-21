#!/usr/bin/env python
#
# $Id: mask_ip.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import os
import shutil
import sys

# Define some constants that will be useful.
THIS_SCRIPT = os.path.basename(__file__)
SRC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)))
THIS_COMPONENT = SRC_FOLDER[SRC_FOLDER.rfind(os.sep) + 1:]

# Now add buildscripts to our python path.
sys.path.append(os.path.abspath(os.path.join(SRC_FOLDER, '..', 'buildscripts')))

import sandbox
import component
import vcs

DEST_FOLDER = sandbox.current.get_component_path(THIS_COMPONENT, component.BUILT_ASPECT_NAME)

def ignore_some_items(folder, items):
    return [i for i in items if i.endswith('.pyc') or i == '.if_top' or i == THIS_SCRIPT or i == vcs.HIDDEN_VCS_FOLDER]

def main():
    if os.path.isdir(DEST_FOLDER):
        print('    Removing old copy of %s...' % DEST_FOLDER)
        shutil.rmtree(DEST_FOLDER)
    print('    Copying files to %s...' % DEST_FOLDER)
    shutil.copytree(SRC_FOLDER, DEST_FOLDER, ignore=ignore_some_items)
    # Embed buildscripts under sadm so app is runnable in isolation in built form.
    shutil.copytree(os.path.join(DEST_FOLDER, '..', 'buildscripts'),
                    os.path.join(DEST_FOLDER, 'buildscripts'), ignore=ignore_some_items)
    return 0

if __name__ == '__main__':
    main()
