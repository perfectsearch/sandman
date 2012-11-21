import os
import shutil
import sys

# Define some constants that will be useful. Remember that this file only
# exists and is called when the component lives in the code root...
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

def main():
    if os.path.isdir(DEST_FOLDER):
        print('    Removing old copy of %s...' % DEST_FOLDER)
        ioutil.nuke(DEST_FOLDER, contents_only=True)
    print('    Copying files to %s...' % DEST_FOLDER)
    err = ioutil.transform_tree(SRC_FOLDER, DEST_FOLDER, item_filter=filter_some)
    return err

if __name__ == '__main__':
    main()
