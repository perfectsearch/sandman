#!/usr/bin/env python
# 
# $Id: save_code_path.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 

import re, sys, os

_HELP_PAT = re.compile(r'[-]?(\?|help|h)', re.IGNORECASE)
_TEST_DIR_PAT = re.compile(r'tests?', re.IGNORECASE)

def findSandboxRoot(folder):
    segments = re.split(r'[\\/]', folder)
    i = len(segments) - 1
    while i > 0:
        path = '/'.join(segments[0:i])
        if not os.path.exists(os.path.join(path, 'CMakeLists.txt')):
            root = '/'.join(segments[0:i + 1])
            return root
        i -= 1
    assert(false)

def saveCodePath(path, dirname=None, additionalData=None ):
    if dirname == None:
        dirname = os.path.dirname( os.path.abspath( path ) )

    if os.path.isfile(path):
        oldFileData = open( path, 'r' )
    else:
        oldFileData = None

    abspath = os.path.abspath(path)
    if not os.path.isdir(dirname):
        print('%s does not exist.' % dirname)
        return -1
    dirname = dirname.replace('\\', '/')
    if dirname[-1:] == '/':
        dirname = dirname[:-1]
    sandbox = findSandboxRoot(dirname)
    rest = dirname[len(sandbox):]
    if len( rest ) > 0:
        if rest[0] == '/':
            rest = rest[1:]
        prefix = re.sub(r'[^A-Za-z0-9]', '_', rest) + '_CODE'
    fileData = '#ifndef _%s_PATH\n#define _%s_PATH\n#define %s_PATH "%s"' % (prefix, prefix, prefix.upper(), dirname + '/')
    #print( "  %s_PATH = \"%s\"" % ( prefix.upper(), dirname + '/' ) )
    if additionalData != None:
        items = additionalData.split(';')
        for item in items:
            try:
                key,value = item.split(',')
                fileData += '\n#define %s_PATH "%s"' % ( key.upper(), value + '/' )
                #print( "  %s_PATH = \"%s\"" % ( key.upper(), value + '/' ) )
            except:
                pass
    fileData += '\n#endif\n'
    if fileData != oldFileData:
        f = open( abspath, 'w' )
        f.write( fileData )
        f.close()
    return 0

def showSyntax():
    dirname, fname = os.path.split(sys.argv[0])
    print('%s -- create .h file with absolute path to its folder.\r\n\r\n  Usage: %s [<path to source code>] <path to desired .h> [additional_def,value[;another_def,value]]' % (fname, fname))

if __name__ == '__main__':
    #print( "Called save_code_path with args: %s" % " ".join( sys.argv[1:] ) )
    
    if len(sys.argv) == 2:
        if not _HELP_PAT.match(sys.argv[1]):
            sys.exit(saveCodePath(sys.argv[1]))
    #if len(sys.argv) == 3:
    #    if not _HELP_PAT.match(sys.argv[2]) and not _HELP_PAT.match(sys.argv[1]):
    #        sys.exit(saveCodePath(sys.argv[2], sys.argv[1]))
    elif len(sys.argv) > 2:
        requestHelp = False
        for arg in sys.argv:
            if _HELP_PAT.match( arg ):
                break
        else:
            additionalData = " ".join( sys.argv[3:] )
            sys.exit( saveCodePath(sys.argv[2], sys.argv[1], additionalData ) )
        
    showSyntax()

