#!/usr/bin/env python
#
# $Id: mask_ip.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import os
import shutil
import sandbox
from common import *

_UBER_BUILD_SCRIPT = 'build.xml'

def _remove_with_chmod(path):
    if os.path.isfile(path):
        os.chmod(path, 0777)
        os.remove(path)

def _copy_master_build_file(sb, uber_build_script):
    try:
        # Allow ant builds to run from either the code root or the build root.
        uber_src = os.path.join(sb.get_iftop_folder_path(), uber_build_script)
        for folder in [sb.get_built_root(), sb.get_code_root()]:
            dest = os.path.join(folder, uber_build_script)
            _remove_with_chmod(dest)
            shutil.copyfile(uber_src, dest)
            # We want to make the script read-only to give people a hint that they
            # shouldn't be editing it directly.
            os.chmod(dest, 0444)
    except:
        import traceback
        traceback.print_exc()

class Builder(BaseBuilder):
    def get_build_file(self):
        return _UBER_BUILD_SCRIPT

    def config(self, sb, options):
        _copy_master_build_file(sb, self.get_build_file())

    def build(self, sb, options, targets):
        _copy_master_build_file(sb, self.get_build_file())
        if len(targets) == 1 and targets[0] == 'config':
            return
        tries_remaining = 1
        if (('build' in targets) or ('integrate' in targets)):
            tries_remaining = 2
        targets = " ".join(targets)
        builtRoot = '"%s"' % sb.get_built_root()[0:-1]
        codeRoot = '"%s"' % sb.get_code_root()[0:-1]
        verboseFlag = ''
        if options.verbose:
            verboseFlag = ' -verbose'
        quickFlag = ''
        if options.quick:
            quickFlag = ' -Dquick=True'
        buildTypeValue = 'off'
        if options.build_type.lower().strip() == 'debug':
            buildTypeValue = 'true'
        cmd = "ant%s -k -Dbuilt.root=%s -Dcode.root=%s -Dset.debug=%s%s %s" % (verboseFlag, builtRoot, codeRoot, buildTypeValue, quickFlag, targets)
        print(cmd)
        while tries_remaining > 0:
            tries_remaining -= 1
            err, stdout = run_make_command(cmd, timeout=sb.get_build_timeout_seconds(), cwd=sb.get_built_root())
            # Experience has shown that occasionally an ant build will cause an error
            # like the following:
            '''
            [javac] bad class file: com/....
            [javac] unable to access file: corrupted zip file
            [javac] Please remove or make sure it appears in the correct subdirectory of the classpath.
            '''
            # This error appears to be caused by a bug in how either ant or java itself
            # manages file handles for zip files on some platforms -- I think java is
            # sometimes opening the file for read before the handle for write is fully
            # released and flushed. The fix is to do an immediate incremental rebuild.
            if (err != 0) and (tries_remaining > 0):
                txt = ''
                if stdout:
                    txt += stdout
                if txt.find('unable to access file: corrupted zip file') == -1:
                    tries_remaining = 0
                else:
                    print('')
                    print('Build failed at least in part because zip streams were corrupted.')
                    print('This is a correctable problem that has nothing to do with source code')
                    print('integrity. Retrying...')
                    print('')
            else:
                tries_remaining = 0
        return err
    
    def get_clean_exclusions(self, sb):
        class AntExclusions(CleanExclusions):
            def __init__(self, sb):
                self._sb = sb
            def __call__(self, file_path):
                parent = os.path.join(sb.get_built_root(), file_path.split(os.sep)[0])
                return os.path.isdir(os.path.join(parent, '.bzr'))
        return AntExclusions(sb)

    def supports(self, sb):
        # This code is critical that it only checks for the build file in the code
        #  root!  If its anywhere else then the compiler isn't interested in it.
        component_name = sb.get_top_component()
        component_build_file = os.path.join(sb.get_component_path(component_name, component.CODE_ASPECT_NAME),
                                            '.if_top',
                                            self.get_build_file())
        exists = os.path.isfile(component_build_file)
        return exists

    def has_compiled_tests(self):
        return True
