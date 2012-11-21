#!/usr/bin/env python
#
# $Id: base_compiler.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
from __future__ import print_function
from abc import ABCMeta
from abc import abstractmethod
import os

class CompilerOptions(object):
    def __init__(self, build_dir, type='build', config='release', platform='x64', verbose=False):
        self.build_dir = build_dir
        self.compile_type = type
        self.build_config = config
        self.build_platform = platform
        self.verbose = verbose
    def __str__(self):
        str = []
        str.append('build dir     : %s' % self.build_dir)
        str.append('compile type  : %s' % self.compile_type)
        str.append('build config  : %s' % self.build_config)
        str.append('build platform: %s' % self.build_platform)
        str.append('verbose       : %s' % self.verbose)
        return '\n'.join(str)

class BaseCompiler(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def compile(self, options):
        '''
        The actual method to dispatch a call to the native compiler
        @param sb A sandbox object.
        @param type Whether to build, clean or rebuild
        @param config Type of compile to execute; release or debug
        '''
        return NotImplemented
