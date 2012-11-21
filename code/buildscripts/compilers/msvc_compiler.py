#!/usr/bin/env python
#
# $Id: msvc_compiler.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
from __future__ import print_function
import argparse
from datetime import datetime
import os
import re
import subprocess
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if os.name == 'nt':
    from _winreg import *

from base_compiler import BaseCompiler
from ioutil import TempDir
import sandbox
from tailer import Tailer

_MSVC_VERSION_9_00 = '9.0'
_MSVC_VERSION_10_00 = '10.0'
_MSVC_VERSION_11_00 = '11.0'
_MSVC_VERSIONS = [_MSVC_VERSION_9_00, _MSVC_VERSION_10_00, _MSVC_VERSION_11_00]

_OUTPUT_FILE_TIMESTAMP = '%Y-%m-%d--%H-%M-%S-utc'

def _get_hklm_registry_key_value(sub_key, var_name):
    ERROR_FILE_NOT_FOUND = 2
    value, type = None, None
    try:
        with OpenKey(HKEY_LOCAL_MACHINE, sub_key, 0, KEY_READ) as reg:
            value, type = QueryValueEx(reg, var_name)
    except WindowsError as error:
        if error.args[0] != ERROR_FILE_NOT_FOUND:   # The system cannot find the file specified -- not an error
            raise error
    return value, type

class MsvcCompiler(BaseCompiler):
    @staticmethod
    def _is_msvc_installed(version):
        install_dir, type = _get_hklm_registry_key_value(r'SOFTWARE\Wow6432Node\Microsoft\VisualStudio\{0}'.format(version), 'InstallDir')
        return type == REG_SZ and os.path.isdir(install_dir)

    @staticmethod
    def _is_platform_sdk_installed():
        # Currently hard coded to look for v7.1
        install_dir, type = _get_hklm_registry_key_value(r'SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v7.1', 'InstallationFolder')
        return type == REG_SZ and os.path.isdir(install_dir)

    @staticmethod
    def _get_platform_sdk_path():
        # Currently hard coded to look for v7.1
        install_dir, type = _get_hklm_registry_key_value(r'SOFTWARE\Wow6432Node\Microsoft\Microsoft SDKs\Windows\v7.1', 'InstallationFolder')
        assert type == REG_SZ and os.path.isdir(install_dir)
        return install_dir

    @staticmethod
    def _get_solution_path(built_dir):
        for filename in os.listdir(built_dir):
            if filename.lower().endswith('.sln'):
                return os.path.normpath(os.path.join(built_dir, filename))
        raise RuntimeError('Solution file not found in sandbox %s. Run config first!' % os.path.dirname(built_dir))

    @staticmethod
    def _get_devenv_path(version):
        if version == _MSVC_VERSION_9_00 and 'VS90COMNTOOLS' in os.environ:
            return os.path.normpath(os.path.join(os.environ['VS90COMNTOOLS'], '..', 'IDE', 'devenv.exe'))
        elif version == _MSVC_VERSION_10_00 and 'VS100COMNTOOLS' in os.environ:
            return os.path.normpath(os.path.join(os.environ['VS100COMNTOOLS'], '..', 'IDE', 'devenv.exe'))
        elif version == _MSVC_VERSION_11_00 and 'VS110COMNTOOLS' in os.environ:
            return os.path.normpath(os.path.join(os.environ['VS110COMNTOOLS'], '..', 'IDE', 'devenv.exe'))
        else:
            raise RuntimeError('Unknown version of Microsoft Visual Studio specified')

    @staticmethod
    def _get_msbuild_path(version):
        dot_net_dir = os.path.join(os.environ['windir'], 'Microsoft.NET')

        if os.path.isdir(os.path.join(dot_net_dir, 'Framework64')):
            framework_dir = os.path.join(dot_net_dir, 'Framework64')
        else:
            framework_dir = os.path.join(dot_net_dir, 'Framework')

        if not os.path.isdir(framework_dir):
            raise RuntimeError('Unable to find the .NET Framework')

        framework_35_dir, framework_40_dir, framework_45_dir = None, None, None
        for dir_name in os.listdir(framework_dir):
            if dir_name.startswith('v4.5') and os.path.isdir(os.path.join(framework_dir, dir_name)) and os.path.isfile(os.path.join(framework_dir, dir_name, 'MSBuild.exe')):
                framework_45_dir = os.path.join(framework_dir, dir_name)
            if dir_name.startswith('v4.0') and os.path.isdir(os.path.join(framework_dir, dir_name)) and os.path.isfile(os.path.join(framework_dir, dir_name, 'MSBuild.exe')):
                framework_40_dir = os.path.join(framework_dir, dir_name)
            if dir_name.startswith('v3.5') and os.path.isdir(os.path.join(framework_dir, dir_name)) and os.path.isfile(os.path.join(framework_dir, dir_name, 'MSBuild.exe')):
                framework_35_dir = os.path.join(framework_dir, dir_name)

        # TODO_vc11_release: the 4.5 .NET is not installing with the beta but should be with the release
        if version == _MSVC_VERSION_9_00 and 'VS90COMNTOOLS' in os.environ and framework_35_dir:
            return os.path.normpath(os.path.join(framework_35_dir, 'MSBuild.exe'))
        elif version == _MSVC_VERSION_10_00 and 'VS100COMNTOOLS' in os.environ and framework_40_dir:
            return os.path.normpath(os.path.join(framework_40_dir, 'MSBuild.exe'))
        elif version == _MSVC_VERSION_11_00 and 'VS110COMNTOOLS' in os.environ and framework_45_dir:
            return os.path.normpath(os.path.join(framework_45_dir, 'MSBuild.exe'))
        elif version == _MSVC_VERSION_11_00 and 'VS110COMNTOOLS' in os.environ and framework_40_dir:
            return os.path.normpath(os.path.join(framework_40_dir, 'MSBuild.exe'))
        else:
            raise RuntimeError('Unable to find the right version of the .NET Framework')

    @staticmethod
    def _get_platform_sdk_env_path(platform):
        platform_sdk_path = MsvcCompiler._get_platform_sdk_path()
        return '"{0}" {1}'.format(os.path.join(platform_sdk_path, 'bin', 'SetEnv.Cmd'), '/x64' if platform == 'x64' else '/x86')

    @staticmethod
    def _get_compiler_version(msvc_version, platform):
        if MsvcCompiler._is_msvc_installed(msvc_version):
            # The following holds true if the FULL IDE is installed!
            if msvc_version == _MSVC_VERSION_9_00 and 'VS90COMNTOOLS' in os.environ:
                if platform == 'x64':
                    env_batch_file = '"{0}"'.format(os.path.normpath(os.path.join(os.environ['VS90COMNTOOLS'], '..', '..', 'VC', 'bin', 'amd64', 'vcvarsamd64.bat')))
                else:
                    env_batch_file = '"{0}"'.format(os.path.normpath(os.path.join(os.environ['VS90COMNTOOLS'], '..', '..', 'VC', 'bin', 'vcvars32.bat')))
            elif msvc_version == _MSVC_VERSION_10_00 and 'VS100COMNTOOLS' in os.environ:
                if platform == 'x64':
                    env_batch_file = '"{0}"'.format(os.path.normpath(os.path.join(os.environ['VS100COMNTOOLS'], '..', '..', 'VC', 'bin', 'amd64', 'vcvars64.bat')))
                else:
                    env_batch_file = '"{0}"'.format(os.path.normpath(os.path.join(os.environ['VS100COMNTOOLS'], '..', '..', 'VC', 'bin', 'vcvars32.bat')))
            elif msvc_version == _MSVC_VERSION_11_00 and 'VS110COMNTOOLS' in os.environ:
                if platform == 'x64':
                    env_batch_file = '"{0}"'.format(os.path.normpath(os.path.join(os.environ['VS110COMNTOOLS'], '..', '..', 'VC', 'bin', 'amd64', 'vcvars64.bat')))
                else:
                    env_batch_file = '"{0}"'.format(os.path.normpath(os.path.join(os.environ['VS110COMNTOOLS'], '..', '..', 'VC', 'bin', 'vcvars32.bat')))
            else:
                raise RuntimeError('Unable to determine the version of Visual Studio')
        elif MsvcCompiler._is_platform_sdk_installed():
            env_batch_file = MsvcCompiler._get_platform_sdk_env_path(platform)
        else:
            raise RuntimeError('Unable to Visual Studio or the Platform SDK')

        command = r'"{0}" && cl'.format(env_batch_file)
        #print command
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, bufsize=1)
        process.wait()
        pattern = r'^Microsoft \(R\) (?:32-bit)?\s*C/C\+\+ Optimizing Compiler Version (?P<version>(?P<major>\d+)\.(?P<minor>\d+)\.(?P<build>[^ ]+)) for (x64|(80)?x86)$'
        lines = process.stdout.readlines()
        for line in lines:
            match = re.match(pattern, line.strip())
            if match:
                return match.group('version')
        raise RuntimeError('Unable to determine the version of Visual Studio')

    @staticmethod
    def _get_project_file_ext(version):
        if version == _MSVC_VERSION_9_00:
            return '.vcproj'
        elif version == _MSVC_VERSION_10_00 or version == _MSVC_VERSION_11_00:
            return 'vcxproj'
        else:
            raise RuntimeError('Unknown version of Microsoft Visual Studio specified')

    @staticmethod
    def _get_solution_version(solution):
        with open(solution) as solution_file:
            solution_data = solution_file.readlines()
            for line in solution_data:
                line = line.strip().lower()
                if not line:
                    continue
                # This is always the first non-empty line of the solution file
                if line == 'microsoft visual studio solution file, format version 12.00':
                    return _MSVC_VERSION_11_00
                elif line == 'microsoft visual studio solution file, format version 11.00':
                    return _MSVC_VERSION_10_00
                elif line == 'microsoft visual studio solution file, format version 10.00':
                    return _MSVC_VERSION_9_00
                break
        raise RuntimeError('Error parsing solution file {0} while trying to find version.'.format(solution))

    @staticmethod
    def _create_log_filename(dir, type, config):
        timestamp = datetime.utcnow().strftime(_OUTPUT_FILE_TIMESTAMP)
        filename = '%s-%s_log-%s.txt' % (type, config, timestamp)
        return os.path.normpath(os.path.join(dir, filename.lower()))

    @staticmethod
    def _devenv_compile(options, solution, version):
        proj_extension = MsvcCompiler._get_project_file_ext(version)
        devenv = MsvcCompiler._get_devenv_path(version)
        compiler_version = MsvcCompiler._get_compiler_version(version, options.build_platform)

        project = os.path.normpath(os.path.join(options.build_dir, 'ALL_BUILD' + proj_extension))
        solutionConfig = '%s|%s' % (options.build_config.capitalize(), options.build_platform)

        if options.verbose:
            print('Compiler       : %s' % compiler_version)
            print('Compile type   : %s' % options.compile_type)
            print('Devenv         : %s' % devenv)
            print('Solution       : %s' % solution)
            print('Project        : %s' % project)
            print('Solution Config: %s' % solutionConfig)
            print('Configuration  : %s' % options.build_config)
            print('Platform       : %s' % options.build_platform)

        with TempDir() as temp_dir:
            output = MsvcCompiler._create_log_filename(temp_dir.path, options.compile_type, options.build_config)
            
            command = 'devenv.exe "%s" /%s "%s" /project "%s" /projectconfig %s /out "%s"' % \
                      (solution, options.compile_type.capitalize(), \
                       solutionConfig, project, \
                       options.build_config.capitalize(), output)

            if options.verbose:
                print('Command: %s' % command)

            process = subprocess.Popen(command, \
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, \
                                       shell=True, bufsize=1, cwd=os.path.dirname(devenv))

            # Wait a max of 10secs to see if the output file will open
            total_time = 0.0
            while not os.path.isfile(output) and total_time < 10.0:
                total_time += .5
                time.sleep(total_time)

            # Tail the output from the log file to the console
            with open(output) as build_output:
                tailer = Tailer(build_output)
                for line in tailer.follow(terminate=process.poll):
                    print(line)
                    if process.poll() != None:
                        break

        return process.returncode

    @staticmethod
    def _msbuild_compile(options, solution, version):
        msbuild = MsvcCompiler._get_msbuild_path(version)
        compiler_version = MsvcCompiler._get_compiler_version(version, options.build_platform)

        if options.verbose:
            print('Compiler       : %s' % compiler_version)
            print('Compile type   : %s' % options.compile_type)
            print('MSBuild        : %s' % msbuild)
            print('Solution       : %s' % solution)
            print('Configuration  : %s' % options.build_config)
            print('Platform       : %s' % options.build_platform)

        project = os.path.normpath(os.path.join(os.path.dirname(solution), 'ALL_BUILD.vcxproj'))
        command = 'MSBuild.exe "%s" /t:%s /p:Configuration=%s /p:platform=%s' % \
                  (project, options.compile_type, options.build_config, options.build_platform)

        if options.verbose:
            print('Command: %s' % command)

        # This is a hack due to a bug in the pre-release of Visual Studio 2012 where it sometimes
        #  does not find the right vsprops files due to this environment variable being set incorrectly!
        #  Please remove once MSVC 2012 ships to validate the bug is fixed.
        custom_env = dict(os.environ)
        custom_env['VisualStudioVersion'] = version

        return subprocess.call(command, shell=True, bufsize=1, env=custom_env, cwd=os.path.dirname(msbuild))

    def compile(self, options):
        solution = MsvcCompiler._get_solution_path(options.build_dir)
        version = MsvcCompiler._get_solution_version(solution)
        options.build_platform = 'x64' if 'x64' in options.build_platform else 'win32'

        if version == _MSVC_VERSION_9_00:
            return MsvcCompiler._devenv_compile(options, solution, version)
        elif version == _MSVC_VERSION_10_00 or version == _MSVC_VERSION_11_00:
            return MsvcCompiler._msbuild_compile(options, solution, version)
        else:
            raise RuntimeError('Unknown version of Microsoft Visual Studio specified')

def get_is_ide_installed(version, verbose=False):
    if verbose:
        print('Microsoft Visual Studio {0} IDE: {1}'.format(version, 'Installed' if MsvcCompiler._is_msvc_installed(version) else 'Not Installed'), end='\n\t')
    print(MsvcCompiler._get_devenv_path(version) if MsvcCompiler._is_msvc_installed(version) else '')

def _is_valid_version(version):
    if version == '2008' or version.startswith('9'):
        return _MSVC_VERSION_9_00
    elif version == '2010' or version.startswith('10'):
        return _MSVC_VERSION_10_00
    elif version.startswith('11'):
        return _MSVC_VERSION_11_00
    elif version.startswith('12'):
        return '12.0'
    else:
        raise argparse.ArgumentTypeError('Invalid compiler version specified')

def get_is_platform_sdk_installed(verbose=False):
    if verbose:
        print('Microsoft Platform SDK: {0}'.format('Installed' if MsvcCompiler._is_platform_sdk_installed() else 'Not Installed'), end='\n\t')
    print(MsvcCompiler._get_platform_sdk_path())

def get_common_tools(verbose=False):
    labels = ''
    versions = ''
    for i in range(9, 12):
        if 'VS{0}0COMNTOOLS'.format(i) in os.environ:
            versions += '{0}.0, '.format(i)
            if verbose:
                labels += 'VS{0}0COMNTOOLS, '.format(i)
    if verbose:
        print('{0} = {1}'.format(labels.rstrip(' ,'), versions.rstrip(' ,')))
    else:
        print(versions.rstrip(' ,'))

def get_version(version, verbose=False):
    try:
        compiler_version = MsvcCompiler._get_compiler_version(version, 'win32')
    except:
        compiler_version = ''
    if verbose:
        print('Microsoft Visual Studio {0} Compiler: {1}'.format(version, compiler_version))
    else:
        print(compiler_version)

def get_versions(verbose=False):
    versions = ''
    for version in _MSVC_VERSIONS:
        try:
            compiler_version = MsvcCompiler._get_compiler_version(version, 'win32')
        except:
            compiler_version = ''
        if verbose:
            print('Microsoft Visual Studio {0} Compiler: {1}'.format(version, compiler_version))
        else:
            versions += '{0}, '.format(compiler_version)
    if not verbose:
        print(versions.rstrip(' ,'))

def main():
    version_description = 'Arguments which take a version parameter is referring to the version of product family.  For example this can be Visual Studio 2008.  Valid values are 9, 10, 11 or 2008, 2010, 11.'
    parser = argparse.ArgumentParser(description='Abstracts the Microsoft Compiler.  ' + version_description)
    parser.add_argument('--is-ide-installed', metavar='VERSION', dest='is_ide_installed', type=_is_valid_version, help='Query whether the Visual Studio IDE is installed.')
    parser.add_argument('--is_platform_sdk_installed', dest='is_platform_sdk_installed', default=False, action='store_true', help='Query whether the Platform SDK is installed.')
    parser.add_argument('--get-comntools-variables', dest='comntools', default=False, action='store_true', help='Request the VSx0COMNTOOLS environment variables as a comma delimited list of versions.  (i.e. 9.0, 10.0, 11.0)')
    parser.add_argument('--get_compiler_version', metavar='VERSION', dest='get_version', type=_is_valid_version, help='Access the version number of the compiler.')
    parser.add_argument('--get_compiler_versions', dest='get_versions', default=False, action='store_true', help='Access the version numbers of all installed compilers.')
    parser.add_argument('--verbose', '-v', dest='verbose', default=False, action='store_true', help='Output more information than just the requested answer')
    args = parser.parse_args()

    if args.is_ide_installed:
        get_is_ide_installed(args.is_ide_installed, args.verbose)
    if args.is_platform_sdk_installed:
        get_is_platform_sdk_installed(args.verbose)
    if args.comntools:
        get_common_tools(args.verbose)
    if args.get_version:
        get_version(args.get_version, args.verbose)
    if args.get_versions:
        get_versions(args.verbose)

    return 0

if __name__ == "__main__":
    sys.exit(main())
