#!/usr/bin/env python
#
# $Id: make_compiler.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import os
import subprocess

from base_compiler import BaseCompiler


def _is_file_in_path(filename):
    for path in os.environ['PATH'].split(os.pathsep):
        if os.path.isdir(path) and os.path.isfile(os.path.join(os.path.abspath(path), filename)):
            return True
    return False

def _get_make_binary_name():
    if os.name == 'nt':
        for filename in ['make.exe', 'mingw32-make.exe', 'mingw64-make.exe']:
            if _is_file_in_path(filename):
                return filename
        # Will fail but will give the user something to track down on the command line
        return 'make' 
    else:
        return 'make'

class MakeCompiler(BaseCompiler):
    def compile(self, options):
        if options.compile_type.lower() == 'build':
            target = 'all'
        elif options.compile_type.lower() == 'clean':
            target = 'clean'

        verbose = '--debug=b ' if options.verbose else ''
        parallel_jobs = '--jobs=4 ' if not options.verbose else ''
        make_binary = _get_make_binary_name()
        command = '{0} {1}{2}{3}'.format(make_binary, parallel_jobs, verbose, target)

        process = subprocess.Popen(command, shell=True, bufsize=1, cwd=os.path.normpath(options.build_dir))
        return process.wait()
