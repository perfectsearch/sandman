#
# $Id: filename 3521 2010-11-25 00:31:22Z svn_username $
#
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
#
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'compilers')))

# Only pick up python files, not the __init__.py file, not the common.py (interface file)

__all__ = []
for file_name in os.listdir(os.path.dirname(__file__)):
    basename, extension = os.path.splitext(file_name)
    if extension == '.py' and not basename.startswith('_') and not basename.startswith('common'):
        __all__.append(basename)
