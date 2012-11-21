#!/usr/bin/env python
#
# $Id: FindOrphansTest.py 9319 2011-06-10 02:59:43Z nathan_george $
#
# Proprietary and confidential
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
# Author: Alexander Sherbakov
# Created: December 27, 2010
#
import unittest, os, tempfile, sys
from codescan.find_orphans import findOrphanedFiles
from testsupport import checkin, officialbuild


def createSampleFile(path, importList = [], refList = [], wrongList = []):
    '''create sample file
    path - path to sample file
    importList - list of other sample files should be imported
    refList - list of other sample files should be referenced to (for instance by creation objects)
    wrongList - list of expressions, which shouldn't be found as sample files references'''
    baseFileName = os.path.basename(path)
    className = baseFileName[0:baseFileName.index(".java")]
    f = open(path, 'wt')
    f.write('# $Id: %s.java 1111 2010-01-01 00:00:00Z aaa\n' %baseFileName)
    for importFile in importList:
        f.write('import my.sample.%s\n' %importFile)
    f.write('public class %s extends Sample {\n' %className)
    f.write('some code there\n')
    for refClass in refList:
        f.write('%s\n' %refClass)
    for wrongRef in wrongList:
        f.write('%s\n' %wrongRef)
        f.write('some code there\n')
    f.write('}\n')
    f.close()

@officialbuild
class FindOrphanTest(unittest.TestCase):
    def testFindInSubdirs(self):
        tempFile = []
        subDirs = []
        try:
            #preparation of temporarily folders with subdirs
            temp_dir = tempfile.mkdtemp()
            codeRootDir = os.path.abspath(os.path.join(temp_dir, "codeRoot"))
            os.mkdir(codeRootDir)
            compDir = os.path.abspath(os.path.join(codeRootDir, "component"))
            os.mkdir(compDir)
            subDirs.append(os.path.abspath(os.path.join(compDir, "src")))
            subDirs.append(os.path.abspath(os.path.join(subDirs[0], "subdir1")))
            subDirs.append(os.path.abspath(os.path.join(subDirs[0], "subdir2")))
            for dname in subDirs:
                os.mkdir(dname)

            #preparation of temporarily files
            tempFile.append(os.path.join(compDir,'Sample0.java'))
            for i in range(1, 4):
                tempFile.append(os.path.join(subDirs[i-1],'Sample%i.java' %i))
                tempFile.append(os.path.join(subDirs[i-1],'Sample%i0.java' %i))

            #creation of temporarily files with desired properties
            createSampleFile(tempFile[0], ['Sample10'], ['Sample20'], [])
            createSampleFile(tempFile[1], ['Sample2'], [], [])
            createSampleFile(tempFile[2], [], [], [])
            createSampleFile(tempFile[3], [], ['Sample3'], [])
            createSampleFile(tempFile[4], [], [], [])
            createSampleFile(tempFile[5], [], [], [])
            createSampleFile(tempFile[6], ['Sample1'], [], [])

            #finding orphaned files
            orphanedFiles = findOrphanedFiles(codeRootDir)
            orphanedFiles.sort()
            self.assertEquals(3, len(orphanedFiles))
            self.assertEquals(['Sample10.java','Sample20.java','Sample30.java'], orphanedFiles)
        finally:
            for fname in tempFile:
                if os.path.exists(fname):
                    os.remove(fname)
            for dname in subDirs[::-1]:
                if os.path.exists(dname):
                    os.rmdir(dname)
            if os.path.exists(compDir):
                os.rmdir(compDir)
            if os.path.exists(codeRootDir):
                os.rmdir(codeRootDir)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

    def testFindInComponents(self):
        tempFile = []
        try:
            #preparation of temporarily folders: two components roots
            temp_dir = tempfile.mkdtemp()
            codeRootDir = os.path.abspath(os.path.join(temp_dir, "codeRoot"))
            os.mkdir(codeRootDir)
            compDir1 = os.path.abspath(os.path.join(codeRootDir, "component1"))
            os.mkdir(compDir1)
            compDir2 = os.path.abspath(os.path.join(codeRootDir, "component2"))
            os.mkdir(compDir2)
            srcDir1 = os.path.abspath(os.path.join(compDir1, "src"))
            os.mkdir(srcDir1)
            srcDir2 = os.path.abspath(os.path.join(compDir2, "src"))
            os.mkdir(srcDir2)

            #preparation of temporarily files for the first component root
            for i in range(1, 6):
                tempFile.append(os.path.join(srcDir1,'Sample%i.java' %i))
            #preparation of temporarily files for the second component root
            for i in range(6, 11):
                tempFile.append(os.path.join(srcDir2,'Sample%i.java' %i))

            #creation of temporarily files with desired properties for the first component root
            createSampleFile(tempFile[0], ['Sample2'], [], [])
            createSampleFile(tempFile[1], [], ['Sample3'], [])
            createSampleFile(tempFile[2], ['Sample6'], [], [])
            createSampleFile(tempFile[3], [], ['Sample9'], [])
            createSampleFile(tempFile[4], [], [], [])

            #creation of temporarily files with desired properties for the first component root
            createSampleFile(tempFile[5], ['Sample7'], [], [])
            createSampleFile(tempFile[6], [], ['Sample8'], [])
            createSampleFile(tempFile[7], ['Sample1'], [], [])
            createSampleFile(tempFile[8], [], ['Sample4'], [])
            createSampleFile(tempFile[9], [], [], [])

            #finding orphaned files without component arguments, i.e. in all components
            orphanedFiles = findOrphanedFiles(codeRootDir)
            orphanedFiles.sort()
            self.assertEquals(2, len(orphanedFiles))
            self.assertEquals(['Sample10.java','Sample5.java'], orphanedFiles)

            #finding orphaned files only in the first component root
            orphanedFiles = findOrphanedFiles(codeRootDir, ["component1"])
            self.assertEquals(1, len(orphanedFiles))
            self.assertEquals(['Sample5.java'], orphanedFiles)

            #finding orphaned files only in the second component root
            orphanedFiles = findOrphanedFiles(codeRootDir, ["component2"])
            self.assertEquals(1, len(orphanedFiles))
            self.assertEquals(['Sample10.java'], orphanedFiles)

            #finding orphaned files in the both component root
            orphanedFiles = findOrphanedFiles(codeRootDir, ["component1", "component2"])
            orphanedFiles.sort()
            self.assertEquals(2, len(orphanedFiles))
            self.assertEquals(['Sample10.java','Sample5.java'], orphanedFiles)
        finally:
            for fname in tempFile:
                if os.path.exists(fname):
                    os.remove(fname)
            if os.path.exists(srcDir1):
                os.rmdir(srcDir1)
            if os.path.exists(srcDir2):
                os.rmdir(srcDir2)
            if os.path.exists(compDir1):
                os.rmdir(compDir1)
            if os.path.exists(compDir2):
                os.rmdir(compDir2)
            if os.path.exists(codeRootDir):
                os.rmdir(codeRootDir)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

    def testCorrectSearch(self):
        tempFile = []
        try:
            #preparation of temporarily folders
            temp_dir = tempfile.mkdtemp()
            codeRootDir = os.path.abspath(os.path.join(temp_dir, "codeRoot" ))
            os.mkdir(codeRootDir)
            compDir = os.path.abspath(os.path.join(codeRootDir, "component"))
            os.mkdir(compDir)
            srcDir = os.path.abspath(os.path.join(compDir, "src"))
            os.mkdir(srcDir)

            #preparation of temporarily files
            for i in range(1, 8):
                tempFile.append(os.path.join(srcDir,'Sample%i.java' %i))

            #creation of temporarily files with desired properties
            #Sample2.java, Sample4.java and Sample6.java don't have proper references
            createSampleFile(tempFile[0], ['Sample3'], ['Sample5'], ['sample2','mSample2'])
            createSampleFile(tempFile[1], ['Sample1'], [], ['Sample4Hah','notSample4'])
            createSampleFile(tempFile[2], [], [], ['_Sample6','Sample6_'])
            createSampleFile(tempFile[3], [], ['Sample5'], ['Sample','Sample22'])
            createSampleFile(tempFile[4], [], ['Sample7'], [])
            createSampleFile(tempFile[5], [], [], ['1Sample4'])
            createSampleFile(tempFile[6], [], [], ['Sampl4'])

            #finding orphaned files
            orphanedFiles = findOrphanedFiles(codeRootDir,["component"])
            orphanedFiles.sort()
            self.assertEquals(3, len(orphanedFiles))
            self.assertEquals(['Sample2.java','Sample4.java','Sample6.java'], orphanedFiles)
        finally:
            for fname in tempFile:
                if os.path.exists(fname):
                    os.remove(fname)
            if os.path.exists(srcDir):
                os.rmdir(srcDir)
            if os.path.exists(compDir):
                os.rmdir(compDir)
            if os.path.exists(codeRootDir):
                os.rmdir(codeRootDir)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

if __name__ == '__main__':
    unittest.main()

