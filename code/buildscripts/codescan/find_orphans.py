#!/usr/bin/env python
#
# $Id: find_orphans.py 4370 2011-01-12 20:26:36Z dhh1969 $
#
# Proprietary and confidential
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
# Author: Alexander Sherbakov
# Created: December 27, 2010
#
__all__ = ['findOrphanedFiles']
import os, sandbox, re, sys

SVN_PAT = re.compile(r'.*\.svn', re.IGNORECASE)

def findRegexpInFile(path, regExp):
    '''check if file path contains regular expression regExp'''
    f = open(path, 'rt')
    isFind = None
    for line in f.readlines():
        isFind = regExp.search(line)
        if (isFind):
            break
    f.close()
    return (isFind)

def takeAllFilesList(baseDir):
    '''take the list of all files from the current dir baseDir'''
    allFiles = []
    for roots,dirs,files in os.walk(baseDir):
        for dname in dirs:
            if SVN_PAT.search(dname):
                dirs.remove(dname)
                break
        allFiles.extend([ os.path.abspath(os.path.join(roots,fname)) for fname in files if fname.endswith(".java") ])
    return allFiles

def takeOrphanedFilesList(searchedFiles, allSandboxFiles):
    '''find all orphaned files from the list of searchedFiles
    check for references across allSandboxFiles list'''
    orphanedFiles = []
    for searchedFile in searchedFiles:
        isFind = False
        baseFileName = os.path.basename(searchedFile)
        className = baseFileName[0:baseFileName.index(".java")]
        checkPattern = re.compile(r'\b' + className + r'\b')
        for fname in allSandboxFiles:
            if fname != searchedFile:
                isFind = findRegexpInFile(fname, checkPattern)
                if (isFind):
                    break
        if (not isFind):
            orphanedFiles.append(os.path.basename(baseFileName))
    return orphanedFiles

def findOrphanedFiles(codeRoot, components = []):
    '''find all orphaned files from the codeRoot/component/src for all components from "components" list;
    if "components" is empty, search for orphand files in all components;
    in all cases, we always check for references across the entire sandbox. '''
    allSandboxFiles = []
    searchedFiles = []
    for component in os.listdir(codeRoot):
        if (not SVN_PAT.search(component)):
            path = os.path.abspath(os.path.join(codeRoot, component, "src"))
            if os.path.exists(path):
                allSandboxFiles.extend(takeAllFilesList(path))

    if len(components) > 0:
        for component in components:
            path = os.path.abspath(os.path.join(codeRoot, component, "src"))
            if os.path.exists(path):
                searchedFiles.extend(takeAllFilesList(path))
            else:
                sys.stderr.write('%s is not a valid component.\n' % component)
    else:
        searchedFiles = allSandboxFiles
    return takeOrphanedFilesList(searchedFiles, allSandboxFiles)

def main(*argv):
    print("Searching for orphaned files...")
    codeRoot = sandbox.current.get_code_root()
    orphanedFilesList = []
    exitCode = 0
    isCorrectComponents = False
    if len(argv) > 1:
        orphanedFilesList = findOrphanedFiles(os.path.abspath(os.path.join(codeRoot)), argv[1:])
        components = ""
        for component in argv[1:]:
            path = os.path.abspath(os.path.join(codeRoot, component, "src"))
            if (os.path.exists(path)):
                components += component+" "
        if components != "":
            print("\norphaned files in components")
            print("%s:\n" %components)
            isCorrectComponents = True
    else:
        orphanedFilesList = findOrphanedFiles(os.path.abspath(os.path.join(codeRoot)))
        print("\norphaned files in sandbox:\n")

    if (not isCorrectComponents):
        return 1
    if len(orphanedFilesList) == 0:
        print("No orphaned files\n")
    else:
        print(orphanedFilesList)
    return len(orphanedFilesList)

if __name__ == '__main__':
    exitCode = main(*sys.argv)
    sys.exit(exitCode)
