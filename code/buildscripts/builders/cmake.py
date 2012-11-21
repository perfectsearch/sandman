#!/usr/bin/env python
#
# $Id: cmake.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

from __future__ import print_function
import fnmatch
import os
import re
import shutil
import subprocess
import sys

import compilers
from common import *
import ioutil
import sandbox
from sandboxtype import EXPERIMENTAL_VARIANT

_CMAKE_CACHE_FILENAME = 'CMakeCache.txt'
_COMPILER_SPECIFIER = 'CMAKE_GENERATOR'
_UBER_BUILD_SCRIPT = 'CMakeLists.txt'

def _remove_with_chmod(path):
    if os.path.isfile(path):
        os.chmod(path, 0777)
        os.remove(path)

def _copy_file(src, dst):
    _remove_with_chmod(dst)
    shutil.copyfile(src, dst)
    # We want to make the script read-only to give people a hint that they
    # shouldn't be editing it directly.
    os.chmod(dst, 0444)

def _clean_built_root(sb):
    built_components = []
    for component in sb.get_cached_components():
        if component.get_aspect().startswith('built'):
            built_components.append(component.get_name())
    built_root = sb.get_built_root()
    for file_entry in os.listdir(built_root):
        path_name = os.path.join(built_root, file_entry)
        if not os.path.isdir(path_name):
            os.remove(path_name)
        elif file_entry not in built_components:
            shutil.rmtree(path_name, ignore_errors=True)

def _is_sandbox_already_configured(built_root):
    return os.path.isfile(os.path.join(built_root, 'CMakeCache.txt')) and os.path.isfile(os.path.join(built_root, 'DartConfiguration.tcl'))

def _is_sandbox_changing_platform_variant(last_used_compiler, new_compiler):
    return ('win64' in last_used_compiler.lower() and 'win64' not in new_compiler.lower()) or \
           ('win64' in new_compiler.lower() and 'win64' not in last_used_compiler.lower())
    
def _update_platform_variant(compiler_name, sb):
    if os.name != 'nt':
        return False
    variant = 'win_x64' if 'win64' in compiler_name.lower() else 'win_32'
    if variant != sb.get_targeted_platform_variant():
        sb.set_targeted_platform_variant(variant)
        return True

def _get_cmake_cache_listed_compiler(sb):
    cmake_cache_filename = os.path.join(sb.get_built_root(), _CMAKE_CACHE_FILENAME)
    if not os.path.isfile(cmake_cache_filename):
        return None

    with file(cmake_cache_filename) as cmake_cache:
        lines = [line for line in cmake_cache if line.strip().startswith(_COMPILER_SPECIFIER)]
        if len(lines) == 0 or '=' not in lines[0]:
            return None
        return lines[0].split('=')[1].strip()

def _get_cmake_generators():
    process = subprocess.Popen('cmake', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, bufsize=1)
    help_buffer = process.stdout.read()
    process.wait()
    help_buffer += process.stdout.read()

    newline = '\r\n' if os.name == 'nt' else '\n'
    pattern = r'  (?P<generator>\w+[^=]+?)= (?P<description>Generates .*?\.){0}'.format(newline)
    
    generators = {}
    for match in re.finditer(pattern, help_buffer, re.S):
        description = match.group('description').strip().replace(newline, '')
        generators[match.group('generator').strip()] = re.sub(' +', lambda matchobj: ' ', description)
        
    return generators

def _get_cmake_compiler_specific_env(sb):
    platform_name = sb.get_targeted_platform_variant()
    developer_sandbox = sb.get_sandboxtype().supports_checkouts()
    compiler_name = compilers.get_default_compiler(platform_name, not developer_sandbox)
    if compiler_name == compilers.COMPILER_GCC:
        return 'CC=gcc CXX=g++ '
    elif compiler_name == compilers.COMPILER_CLANG:
        return 'CC=clang CXX=clang++ '
    elif compiler_name == compilers.COMPILER_MSVC_2008:
        return ''
    elif compiler_name == compilers.COMPILER_MSVC_2010:
        return ''
    elif compiler_name == compilers.COMPILER_MSVC_11:
        return ''
    else:
        return ''

class CompilerNames(object):
    def __init__(self):
        self._names = _get_cmake_generators()

    def _get_newest_only_msvc(self, win64):
        # If MSVC 11 is the only compiler installed then use that.
        if 'VS{0}0COMNTOOLS'.format(11) in os.environ and \
           'VS{0}0COMNTOOLS'.format(10) not in os.environ and \
           'VS{0}0COMNTOOLS'.format(9) not in os.environ:
            return 'Visual Studio 11 Win64' if win64 else 'Visual Studio 11'
        # If MSVC 2010 is the only compiler installed then use that.
        elif 'VS{0}0COMNTOOLS'.format(10) in os.environ and \
             'VS{0}0COMNTOOLS'.format(9) not in os.environ:
            return 'Visual Studio 10 Win64' if win64 else 'Visual Studio 10'
        # Otherwise default to use MSVC 9 2008.
        else:
            return 'Visual Studio 9 2008 Win64' if win64 else 'Visual Studio 9 2008'

    def get_default_compiler(self, sb):
        platform_name = sb.get_targeted_platform_variant()
        developer_sandbox = sb.get_sandboxtype().supports_checkouts()
        default_compiler = compilers.get_default_compiler(platform_name, not developer_sandbox)
        is64bit = '64' in platform_name
        
        if default_compiler == compilers.COMPILER_GCC or default_compiler == compilers.COMPILER_CLANG:
            return 'Unix Makefiles'
        elif default_compiler == compilers.COMPILER_MSVC_2008:
            return 'Visual Studio 9 2008 Win64' if is64bit else 'Visual Studio 9 2008'
        elif default_compiler == compilers.COMPILER_MSVC_2010:
            return 'Visual Studio 10 Win64' if is64bit else 'Visual Studio 10'
        elif default_compiler == compilers.COMPILER_MSVC_11:
            return 'Visual Studio 11 Win64' if is64bit else 'Visual Studio 11'
        else:
            raise RuntimeError('ERROR: Unknown default compiler specified.  See compilers/__init__.py for the value of \'{0}\''.format(default_compiler))

    def parse_compiler_name(self, compiler_name):
        if compiler_name and compiler_name in self._names:
            return self._get_correct_case(compiler_name)
        else:
            return None

    def _get_correct_case(self, compiler_name):
        for name in self._names.iterkeys():
            if name.lower() == compiler_name.lower():
                return name
        raise KeyError('{0} was not found in the set of valid compilers'.format(compiler_name))

    def __str__(self):
        s = ''
        width = len(max(self._names.iterkeys(), key=len)) + 1
        format = '%-' + str(width) + 's: %s\n'
        names = self._names.keys()
        names.sort()
        for name in names:
            s += format % (name, self._names[name])
        return s

    def __contains__(self, item):
        for name in self._names.iterkeys():
            if name.lower() == item.lower():
                return True
        return False

class Builder(BaseBuilder):
    def get_build_file(self):
        return _UBER_BUILD_SCRIPT

    def config(self, sb, options):
        '''
        Prompt the user for choices about which build options should
        be active; use the results to prepare the build root for targets
        to be made. This might involve creating/configuring makefiles,
        etc.
        '''
        # The following use of iftop is okay since supports validates that we are
        #  in the code root already
        uber_src = os.path.join(sb.get_iftop_folder_path(), self.get_build_file())
        uber_dst = os.path.join(sb.get_code_root(), self.get_build_file())
        _copy_file(uber_src, uber_dst)

        open(sb.get_code_root() + 'CTestCustom.ctest', 'w').close()
        timeout = sb.get_build_timeout_seconds()

        compiler_names = CompilerNames()
        user_specified_compiler = compiler_names.parse_compiler_name(options.compiler)
        default_compiler = compiler_names.get_default_compiler(sb)
        last_used_compiler = _get_cmake_cache_listed_compiler(sb)
        last_used_build_root = sb.get_built_root()

        if options.compiler and not user_specified_compiler:
            print('ERROR: compiler specified is unknown. Use one of the following:\n{0}'.format(compiler_names))
            return 2

        compiler_name = user_specified_compiler if user_specified_compiler else default_compiler

        #print('Sandbox is {0}already configured'.format('' if _is_sandbox_already_configured(last_used_build_root) else 'not '))
        #print('Last used compiler is {0}'.format(last_used_compiler))
        print('Using compiler {0}'.format(compiler_name))

        if _update_platform_variant(compiler_name, sb):
            print('Removing build directory {0}'.format(os.path.basename(last_used_build_root)))
            ioutil.nuke(last_used_build_root, contents_only=False)

        if _is_sandbox_already_configured(last_used_build_root) and last_used_compiler and last_used_compiler != compiler_name:
            print('Removing contents of build directory {0}'.format(os.path.basename(sb.get_built_root())))
            _clean_built_root(sb)

        build_cfg = '-DCMAKE_BUILD_TYPE:STRING={0} '.format(options.build_type.capitalize() if options.build_type else '')

        if not options.prompt:
            verbose = ' --trace' if options.verbose else ''
            generator = compiler_name
            cmd = _get_cmake_compiler_specific_env(sb)
            cmd += 'cmake {0}-G"{1}" --build "{2}" "{3}"{4}'.format(build_cfg, generator, sb.get_built_root(), sb.get_code_root(), verbose)
        else:
            tool = 'cmake-gui' if os.name == 'nt' else 'ccmake'
            timeout = 3600*4    # Time-out is 4 hours for the UI version! Lets hope they want control of their command prompt before then.
            cmd = '{0} "{1}"'.format(tool, sb.get_code_root())

        if not os.path.isdir(sb.get_built_root()):
            os.mkdir(sb.get_built_root())

        exitCode, stdout = run_make_command(cmd, timeout=sb.get_build_timeout_seconds(), cwd=sb.get_built_root())

        return exitCode

    def get_clean_exclusions(self, sb):
        class CMakeExclusions(CleanExclusions):
            def __init__(self, sb):
                self._sb = sb
                self._cleaned = False
            def __call__(self, file_path):
                if not self._cleaned:
                    if os.name == 'nt':
                        Builder._compile_target(self._sb, 'clean', 'Release')
                        Builder._compile_target(self._sb, 'clean', 'Debug')
                    else:
                        Builder._compile_target(self._sb, 'clean', self._sb.get_build_config())
                    self._cleaned = True
                return True
        return CMakeExclusions(sb)

    def build(self, sb, options, targets):
        '''
        Make all enumerated targets.
        '''
        # The following use of iftop is okay since supports validates that we are
        #  in the code root already
        uber_src = os.path.join(sb.get_iftop_folder_path(), self.get_build_file())
        uber_dst = os.path.join(sb.get_code_root(), self.get_build_file())
        _copy_file(uber_src, uber_dst)

        targets = set([target.lower() for target in targets])

        if 'config' in targets or 'build' in targets:
            targets = targets - set(['config'])
            exitCode = self.config(sb, options)
            if exitCode != 0 or len(targets) == 0:
                return exitCode

        if 'build' in targets:
            targets = targets - set(['build'])
            exitCode = Builder._compile_target(sb, 'build', sb.get_build_config(), options.verbose)
            if exitCode != 0 or len(targets) == 0:
                return exitCode

        cmd = 'ctest -T ' + ' -T '.join(targets)
        if options.verbose:
            cmd += ' --verbose'
        exitCode, stdout = run_make_command(cmd, timeout=sb.get_build_timeout_seconds(), cwd=sb.get_built_root())
        return exitCode

    @staticmethod
    def _compile_target(sb, target, config, verbose=False):
        compiler = compilers.create_compiler(_get_cmake_cache_listed_compiler(sb))
        if not compiler:
            raise RuntimeError('ERROR: Unable to identify the compiler specified inside of {0}.'.format(_CMAKE_CACHE_FILENAME))
        compiler_options = compilers.CompilerOptions(sb.get_built_root(), \
                                                     type=target, \
                                                     config=config, \
                                                     platform=sb.get_targeted_platform_variant(), \
                                                     verbose=verbose)
        exitCode = compiler.compile(compiler_options)
        print('{0} exit code: {1}\n'.format(target.capitalize(), exitCode))
        return exitCode

    def has_prompted_config(self):
        return True

    def supports(self, sb):
        # This code is critical that it only checks for the build file in the code
        #  root!  If its anywhere else then the compiler isn't interested in it.
        component_name = sb.get_top_component()
        component_build_file = os.path.join(sb.get_component_path(component_name, component.CODE_ASPECT_NAME),
                                            '.if_top',
                                            self.get_build_file())
        return os.path.isfile(component_build_file)

    def has_compiled_tests(self):
        return True
