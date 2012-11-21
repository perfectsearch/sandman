#
# $Id: _locpaths.py 8613 2011-05-27 17:53:09Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import os, sys

LOC_FOLDER = os.path.dirname(os.path.abspath(__file__))
BUILDSCRIPTS_FOLDER = os.path.abspath(os.path.join(LOC_FOLDER, '..'))

if os.name == 'nt':
    LOC_FOLDER = LOC_FOLDER.replace('\\', '/')
    BUILDSCRIPTS_FOLDER = BUILDSCRIPTS_FOLDER.replace('\\', '/')

_added = False
if not _added:
    _added = True
    sys.path.append(BUILDSCRIPTS_FOLDER)