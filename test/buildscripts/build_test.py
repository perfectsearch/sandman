#!/usr/bin/env python
#
# $Id: ImportTest.py 4183 2011-01-03 20:17:03Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import unittest, os, sys, tempfile, shutil
import build
import sandbox
import ioutil
from testsupport import checkin

@checkin
class BuildTest(unittest.TestCase):
    def check_select_builder(self, fil, typ):
        with ioutil.TempDir() as td:
            sb = sandbox.Sandbox(td.path + '/foo.trunk.dev')
            sb.layout()
            os.makedirs(sb.get_code_root() + 'foo')
            aux_folder = sb.get_iftop_folder_path()
            os.makedirs(aux_folder)
            f = os.path.join(aux_folder, fil)
            #print('writing %s' % f)
            open(f, 'w').close()
            bld = build.select_builder(sb)
            self.assertEqual(typ, bld.get_name())
    def test_select_builder_cmake(self):
        self.check_select_builder('CMakeLists.txt', 'cmake')
    def test_select_builder_ant(self):
        self.check_select_builder('build.xml', 'ant')

