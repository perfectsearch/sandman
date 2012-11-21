"""
Utility funcitons for CMake-related modules.
--------------------------------------------
"""

import os, os.path

def adjustFileNameWin(filename):
    return filename                         \
            .replace('/', '\\')             \
            .replace('\\\\', '\\')

def adjustFileNamePOSIX(filename):
    return filename

adjustFileName = adjustFileNameWin if os.name == 'nt' else adjustFileNamePOSIX

def pathStartsWithWin(path, startsWith):
    return adjustFileName(path)             \
            .startswith(                    \
                adjustFileName(startsWith))

def pathStartsWithPOSIX(path, startsWith):
    return path.startswith(startsWith)

if 'nt' == os.name:
    pathStartsWith = pathStartsWithWin
else:
    pathStartsWith = pathStartsWithPOSIX

def exeFileToModule(fullPathName):
    base, ext = os.path.splitext(os.path.basename(fullPathName))
    return base.replace('-', '_').replace('.', '_')

