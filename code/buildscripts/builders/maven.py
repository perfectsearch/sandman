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

_UBER_BUILD_SCRIPT = 'pom.xml'

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
        targets = " ".join(targets)
        targets = targets.replace('build', 'install')
        targets = targets.replace('test', 'verify')
        builtRoot = '"%s"' % sb.get_built_root()[0:-1]
        codeRoot = '"%s"' % sb.get_code_root()[0:-1]
        verboseFlag = ''
        if options.verbose:
            verboseFlag = ' -X'
        buildTypeValue = 'off'
        if options.build_type.lower().strip() == 'debug':
            buildTypeValue = 'true'
        skipTests = "false"
        if targets.find('verify') == -1:
            skipTests = "true"
        cmd = "mvn%s -Dbuilt.root=%s -Dcode.root=%s -Ddebug=%s -Dmaven.test.skip=%s %s" % (verboseFlag, builtRoot, codeRoot, buildTypeValue, skipTests, targets)
        print(cmd)
        err, stdout = run_make_command(cmd, timeout=sb.get_build_timeout_seconds(), cwd=sb.get_built_root())
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
