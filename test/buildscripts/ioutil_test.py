#!/usr/bin/env python
# -*- coding: utf8 -*-
# $Id: CodeStatTest.py 4165 2010-12-30 12:04:29Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest
import shutil
import sys
import os
import tempfile
from testsupport import checkin
from ioutil import *

# Produce this list by running "ls -Al"
TYPICAL_LINUX_CMAKE_FOLDER = '''
drwxrwxr-x.  3 oathizhi oathizhi  4096 Oct 14 19:55 Archive
-rw-rw-r--.  1 oathizhi oathizhi 20460 Oct 26 10:43 CMakeCache.txt
drwxrwxr-x. 35 oathizhi oathizhi  4096 Oct 28 00:33 CMakeFiles
-rw-rw-r--.  1 oathizhi oathizhi  3042 Oct 14 19:53 cmake_install.cmake
-rw-rw-r--.  1 oathizhi oathizhi   104 Oct 26 10:43 CTestCustom.cmake
-rw-rw-r--.  1 oathizhi oathizhi   104 Oct 14 19:53 CTestCustom.ctest
-rw-rw-r--.  1 oathizhi oathizhi   560 Oct 26 10:43 CTestTestfile.cmake
drwxrwxr-x.  3 oathizhi oathizhi  4096 Oct 14 19:55 Dist
-rw-rw-r--.  1 oathizhi oathizhi 27219 Oct 26 10:43 Makefile
'''

def _get_linux_items(txt):
    lines = [x.strip() for x in txt.split('\n') if x.strip()]
    dirs = [d[d.rfind(' ') + 1:] for d in lines if d.startswith('d')]
    files = [f[f.rfind(' ') + 1:] for f in lines if not f.startswith('d')]
    return (dirs, files)

LINUX_ITEMS = _get_linux_items(TYPICAL_LINUX_CMAKE_FOLDER)

# Produce this list by running "dir" cmd and removing . and .. entries
TYPICAL_WINDOWS_CMAKE_FOLDER = '''
10/27/2010  03:14 PM    <DIR>          ALL_BUILD.dir
10/27/2010  10:16 AM            19,324 ALL_BUILD.vcproj
10/28/2010  02:25 PM             2,577 ALL_BUILD.vcproj.SUMAGO.toril.user
10/27/2010  09:53 AM    <DIR>          Archive
10/27/2010  03:08 PM    <DIR>          Archive.dir
10/27/2010  10:16 AM            19,714 Archive.vcproj
10/28/2010  02:25 PM             2,577 Archive.vcproj.SUMAGO.toril.user
10/28/2010  02:27 PM            25,073 CMakeCache.txt
10/28/2010  02:27 PM    <DIR>          CMakeFiles
10/25/2010  04:12 PM             2,862 cmake_install.cmake
10/27/2010  10:16 AM            19,791 Continuous.vcproj
10/28/2010  02:25 PM             2,577 Continuous.vcproj.SUMAGO.toril.user
10/28/2010  02:25 PM        37,899,264 Core.ncb
10/25/2010  04:12 PM            35,199 Core.sln
10/28/2010  02:13 PM               108 CTestCustom.cmake
10/25/2010  04:12 PM               108 CTestCustom.ctest
10/28/2010  02:27 PM               569 CTestTestfile.cmake
10/25/2010  04:19 PM    <DIR>          Dist
10/27/2010  10:16 AM            19,829 Experimental.vcproj
10/28/2010  02:25 PM             2,577 Experimental.vcproj.SUMAGO.toril.user
10/27/2010  03:08 PM    <DIR>          MakeDist.dir
10/27/2010  10:16 AM            23,361 MakeDist.vcproj
10/28/2010  02:25 PM             2,577 MakeDist.vcproj.SUMAGO.toril.user
10/27/2010  03:08 PM    <DIR>          MakeLicense.dir
10/27/2010  10:16 AM            20,146 MakeLicense.vcproj
10/28/2010  02:25 PM             2,577 MakeLicense.vcproj.SUMAGO.toril.user
10/27/2010  10:16 AM            19,734 Nightly.vcproj
10/28/2010  02:25 PM             2,577 Nightly.vcproj.SUMAGO.toril.user
10/27/2010  10:16 AM            19,943 NightlyMemoryCheck.vcproj
10/28/2010  02:27 PM    <DIR>          RPMUtil
10/27/2010  10:16 AM            20,034 RUN_TESTS.vcproj
10/28/2010  02:25 PM             2,577 RUN_TESTS.vcproj.SUMAGO.toril.user
10/28/2010  02:58 PM    <DIR>          Testing
10/27/2010  03:10 PM    <DIR>          ZERO_CHECK.dir
10/27/2010  10:16 AM            30,772 ZERO_CHECK.vcproj
10/28/2010  02:25 PM             2,577 ZERO_CHECK.vcproj.SUMAGO.toril.user
'''

def _get_windows_items(txt):
    lines = [x.strip() for x in txt.split('\n') if x.strip()]
    dirs = [d[d.rfind(' ') + 1:] for d in lines if d.find('<DIR>') > -1]
    files = [f[f.rfind(' ') + 1:] for f in lines if f.find('<DIR>') == -1]
    return (dirs, files)

WINDOWS_ITEMS = _get_windows_items(TYPICAL_WINDOWS_CMAKE_FOLDER)

ENVIRONS = {}
ENVIRONS['linux'] = LINUX_ITEMS
ENVIRONS['windows'] = WINDOWS_ITEMS

def _make_file(path):
    open(path, 'w').close()

def _fill_dir(path):
    for i in range(3):
        _make_file(os.path.join(path, str(i)))

def _fill_sample_folder(environ, folder):
    dirs = environ[0]
    files = environ[1]
    for d in dirs:
        path = os.path.join(folder, d)
        os.mkdir(path)
        _fill_dir(path)
    for f in files:
        _make_file(os.path.join(folder, f))

@checkin
class NukeTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        for key in ENVIRONS.keys():
            path = os.path.join(self.temp_dir, key)
            os.mkdir(path)
            #print('Made dir %s' % self.temp_dir)
            environ = ENVIRONS[key]
            _fill_sample_folder(environ, path)
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        self.temp_dir = None
    def test_simple_nuke(self):
        for folder in os.listdir(self.temp_dir):
            path = os.path.join(self.temp_dir, folder)
            nuke(path)
            self.assertFalse(os.path.isdir(path))
    def test_nuke_contents_only(self):
        for folder in os.listdir(self.temp_dir):
            path = os.path.join(self.temp_dir, folder)
            nuke(path, contents_only=True)
            self.assertTrue(os.path.isdir(path))
            self.assertFalse(bool(os.listdir(path)))
    def assertNotEmpty(self, folder):
        self.assertTrue(os.path.isdir(folder))
        self.assertTrue(bool(os.listdir(folder)))
    def test_nuke_selected(self):
        for folder in os.listdir(self.temp_dir):
            path = os.path.join(self.temp_dir, folder)
            nuke(path, skip=['CMakeFiles(/.*)?$','Archive(/.*)?$', r'CMakeCache\.txt'])
            self.assertNotEmpty(path + '/CMakeFiles')
            self.assertNotEmpty(path + '/Archive')
            self.assertTrue(os.path.isfile(path + '/CMakeCache.txt'))
            items = os.listdir(path)
            if len(items) != 3:
                self.fail('Expected 3 items to remain in folder. Got: %s' % str(items))

@checkin
class IOUtilTest(unittest.TestCase):
    def test_subdirs(self):
        sdirs = subdirs(os.path.dirname(os.path.abspath(__file__)))
        self.assertTrue('data' in sdirs)
        self.assertTrue(os.path.basename(__file__) not in sdirs)
    def test_compare_paths(self):
        self.assertEqual(0, compare_paths('a/b/c/', 'a\\b\\c'))
        self.assertEqual(1, compare_paths('a/b/c/d', 'a\\b\\c'))
        self.assertEqual(-1, compare_paths('a/b/c', 'a\\b\\c\\d'))
        if os.name == 'nt':
            self.assertEqual(0, compare_paths('a/b/c', 'A\\B\\c\\'))
    def test_TempDir(self):
        with TempDir() as td:
            path = td.path
            self.assertTrue(os.path.isdir(td.path))
        self.assertFalse(os.path.isdir(path))
    def test_WorkingDir(self):
        startdir = os.getcwd()
        parentdir = os.path.abspath('..')
        with WorkingDir('..') as twd:
            self.assertEqual(twd.path, parentdir)
        self.assertEqual(startdir, os.getcwd())

SAMPLE_TREE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'visit_test')

@checkin
class TransformTreeTest(unittest.TestCase):
    def test_simple(self):
        with TempDir() as td:
            transform_tree(SAMPLE_TREE, td.path)
            self.assertTrue(os.path.isdir(os.path.join(td.path, 'subdir', 'unvisitedSubdir')))
            self.assertTrue(os.path.isfile(os.path.join(td.path, 'subdir', 'visitedSubdir', 'c.txt')))
    def test_flatten(self):
        def flatten_path(x):
            return os.path.basename(x)
        with TempDir() as td:
            transform_tree(SAMPLE_TREE, td.path, path_transformer=flatten_path)
            self.assertFalse(os.path.isdir(os.path.join(td.path, 'subdir', 'unvisitedSubdir')))
            self.assertFalse(os.path.isfile(os.path.join(td.path, 'subdir', 'visitedSubdir', 'c.txt')))
            files = os.listdir(td.path)
            files.sort()
            self.assertEquals('.metacode.conf a.txt b.txt c.txt d.txt metadata.txt x.txt y.txt z.txt', ' '.join(files))
    def test_filter(self):
        def filter_func(x):
            return x not in ['subdir/unvisitedSubdir/', 'subdir/b.txt']
        with TempDir() as td:
            transform_tree(SAMPLE_TREE, td.path, item_filter=filter_func)
            self.assertFalse(os.path.isdir(os.path.join(td.path, 'subdir', 'unvisitedSubdir')))
            self.assertTrue(os.path.isfile(os.path.join(td.path, 'subdir', 'visitedSubdir', 'c.txt')))
            self.assertFalse(os.path.isfile(os.path.join(td.path, 'subdir', 'b.txt')))
