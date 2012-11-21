#!/usr/bin/env python
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import os
import shutil
import sys
import optparse

# Define some constants that will be useful.
COMPONENT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
THIS_COMPONENT = COMPONENT_FOLDER[COMPONENT_FOLDER.rfind(os.sep) + 1:]
BUILDSCRIPTS_FOLDER = os.path.abspath(os.path.join(COMPONENT_FOLDER, '../../code/buildscripts/'))

# Now add buildscripts to our python path.
sys.path.append(BUILDSCRIPTS_FOLDER)

import sandbox
import component
import ioutil

MY_BUILT_FOLDER = sandbox.current.get_component_path(THIS_COMPONENT, component.BUILT_ASPECT_NAME)

def _define_options():
    parser = optparse.OptionParser('Usage: %prog [options]\n\nAssemble runnable package.')
    parser.add_option('--dest', dest="dest",
                      help="folder where artifacts should be assembled",
                      metavar="FLDR", default=sandbox.current.get_run_root())
    return parser

def main(argv):
    parser = _define_options()
    options, args = parser.parse_args(argv)
    dest_folder = os.path.abspath(options.dest)
    if not os.path.isdir(dest_folder):
        os.makedirs(dest_folder)
    else:
        print('    Removing old copy of %s...' % dest_folder)
        ioutil.nuke(dest_folder, contents_only=True)
    print('    Copying files to %s...' % dest_folder)
    ioutil.transform_tree(MY_BUILT_FOLDER, dest_folder)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
