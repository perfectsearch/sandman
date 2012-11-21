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

# Define some constants that will be useful. Remember that this file only
# exists and is called when the component lives in the code root...
THIS_SCRIPT = os.path.basename(__file__)
SRC_FOLDER = os.path.dirname(os.path.abspath(__file__))
THIS_COMPONENT = SRC_FOLDER[SRC_FOLDER.rfind(os.sep) + 1:]

# Buildscripts must always be reused as code...
BUILDSCRIPTS_CODE = os.path.abspath(os.path.join(SRC_FOLDER, '..', 'buildscripts'))

# Now add buildscripts to our python path.
sys.path.append(BUILDSCRIPTS_CODE)

import sandbox
import component
import ioutil

DEST_FOLDER = sandbox.current.get_component_path(THIS_COMPONENT, component.BUILT_ASPECT_NAME)

def filter_some(item):
    if item.endswith('.bzr/'):
        return False
    return not (item.endswith('.pyc') or
            item == '_build.py')

def filter_embed(item):
    if '.bzr' in item:
        return False
    return filter_some(item)

def embed(comp):
    ioutil.transform_tree(os.path.join(DEST_FOLDER, '..', comp),
                    os.path.join(DEST_FOLDER, comp), item_filter=filter_embed)

def main():
    if os.path.isdir(DEST_FOLDER):
        print('    Removing old copy of %s...' % DEST_FOLDER)
        # We use ioutil.nuke() instead of shutil.rmtree() so we can leave the folder
        # itself around. That is helpful on dev machines where a developer might
        # have a shell open with current working dir = the folder we're trying to
        # empty.
        ioutil.nuke(DEST_FOLDER, contents_only=True)
    print('    Copying files to %s...' % DEST_FOLDER)
    ioutil.transform_tree(SRC_FOLDER, DEST_FOLDER, item_filter=filter_some)
    # Embed buildscripts under sadm so app is runnable in isolation in built form.
    embed('buildscripts')
    embed('bzr-plugins')
    return 0

if __name__ == '__main__':
    main()
