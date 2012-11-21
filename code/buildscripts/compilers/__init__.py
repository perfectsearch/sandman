import os
import sys
from base_compiler import *
from msvc_compiler import *
from make_compiler import *

COMPILER_UNKNOWN = 'unknown'
COMPILER_GCC = 'gcc'
COMPILER_CLANG = 'clang++'
COMPILER_MSVC_2008 = 'msvc2008'
COMPILER_MSVC_2010 = 'msvc2010'
COMPILER_MSVC_11 = 'msvc11'

__all__ = ["CompilerOptions", "MakeCompiler", "MsvcCompiler"]

def create_compiler(compiler_name):
    if os.name != 'nt':
        return MakeCompiler()
    else:
        if not compiler_name or 'MinGW' in compiler_name or 'Unix' in compiler_name or 'MSYS' in compiler_name:
            return MakeCompiler()
        else:
            return MsvcCompiler()

def _does_program_exist(program_name):
    result = subprocess.call('{0} --version'.format(program_name), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result == 0

def get_available_compilers():
    available_compilers = []
    if _does_program_exist('make') and _does_program_exist('clang++'):
        available_compilers.append(COMPILER_CLANG)
    if _does_program_exist('make') and _does_program_exist('g++'):
        available_compilers.append(COMPILER_GCC)
    if os.name == 'nt':
        if MsvcCompiler._is_msvc_installed('9.0'):
            available_compilers.append(COMPILER_MSVC_2008)
        if MsvcCompiler._is_msvc_installed('10.0'):
            available_compilers.append(COMPILER_MSVC_2010)
        if MsvcCompiler._is_msvc_installed('11.0'):
            available_compilers.append(COMPILER_MSVC_11)
    return available_compilers

def get_default_compiler(platform_name, official_sandbox):
    available_compilers = get_available_compilers()
    if platform_name.startswith('linux') and COMPILER_GCC in available_compilers:
        return COMPILER_GCC
    elif platform_name.startswith('osx'):
        if COMPILER_CLANG in available_compilers:
            return COMPILER_CLANG
        elif COMPILER_GCC in available_compilers:
            return COMPILER_GCC
    elif platform_name.startswith('win'):
        if official_sandbox:
            # The new default is MSVC 2010 (express with the SDK installed) for official sandboxes
            if COMPILER_MSVC_2010 in available_compilers:
                return COMPILER_MSVC_2010
            elif COMPILER_MSVC_2008 in available_compilers:
                return COMPILER_MSVC_2008
        else:
            # The new default is MSVC 11 on developer sandboxes
            if COMPILER_MSVC_11 in available_compilers:
                return COMPILER_MSVC_11
            elif COMPILER_MSVC_2010 in available_compilers:
                return COMPILER_MSVC_2010
            elif COMPILER_MSVC_2008 in available_compilers:
                return COMPILER_MSVC_2008
    return COMPILER_UNKNOWN
