#!/usr/bin/env python
#
# $Id: mask_ip.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import os
import shutil
import component
from common import *

_MAKE_FILE = '_build.py'

class Builder(BaseBuilder):
    def get_build_file(self):
        return _MAKE_FILE
    def config(self, sb, options):
        print('No build configuration is necessary.')
    def build(self, sb, options, targets):
        '''
        Make all enumerated targets.
        '''
        err = 0
        if targets == ['config']:
            self.config(sb, options)
        else:
            if options.timeout is None:
                options.timeout = 120
            cc = sb.get_cached_components()
            if not cc:
                print('%s/dependencies.txt not found; do you need to do a "bzr sb update"?' % sb.get_name())
                print('Proceeding with implied component list.')
                cc = sb.get_on_disk_components()
                br = sb.get_branch()
                cc = [component.Component(c, br, None, component.CODE_ASPECT_NAME)
                      for c in sb.get_on_disk_components()
                      if sb.get_component_reused_aspect(c) == component.CODE_ASPECT_NAME]
            for c in cc:
                if c.reused_aspect == 'code':
                    makefile = sb.get_component_path(c.name, component.CODE_ASPECT_NAME) + self.get_build_file()
                    if os.path.isfile(makefile):
                        cmd = 'python %s' % self.get_build_file()
                        if targets:
                            cmd += ' ' + ' '.join(targets)
                        print('Building %s...' % c.name)
                        err2, stdout = run_make_command(cmd, timeout=options.timeout, cwd=os.path.dirname(makefile))
                        if err2:
                            err = 1
                            print('... FAILED')
                        else:
                            print('... OK')
        return err
    def supports(self, sb):
        top_component_folder = sb.get_component_path(sb.get_top_component(), component.CODE_ASPECT_NAME)
        return os.path.isfile(top_component_folder + self.get_build_file())
    def priority(self):
        return 1

if __name__ == '__main__':
    print('script builder; called by ../build.py to "build" html, python, php, and other interpreted stuff.')
