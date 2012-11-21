#!/usr/bin/env python
#
# $Id: BuildInfoTest.py 3590 2010-11-30 22:51:02Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
#
import unittest, os, sys, subprocess, re
import buildinfo
from testsupport import checkin

if os.name == 'nt':
    EXPECTED_NAME = 'Windows'
elif buildinfo.UNAME[0] == 'OSX':
    EXPECTED_NAME = 'OSX'
else:
    EXPECTED_NAME = 'Linux'

@checkin
class BuildInfoTest(unittest.TestCase):
    def test_os(self):
        d = buildinfo.BuildInfo()
        self.assertTrue(d.os.find(EXPECTED_NAME) > -1)
    def test_host(self):
        d = buildinfo.BuildInfo()
        self.assertTrue(bool(d.host))
        self.assertEquals(d.host.lower(), d.host)
        self.assertTrue(d.host.find('.') == -1)
    def test_version(self):
        d = buildinfo.BuildInfo()
        self.assertTrue(re.match(r'.*\d+.*', d.version))
        if buildinfo.UNAME[0] == 'OSX':
            self.assertTrue(d.version.startswith('10.'))
            self.assertNotEquals(d.version, '10.4')
        elif os.name == 'posix':
            self.assertTrue(re.match(r'2\.6\..*', d.version) or re.match(r'3\.[0-9].*', d.version))
    def test_bitness(self):
        d = buildinfo.BuildInfo()
        self.assertEquals(type(''), type(d.bitness))
        self.assertTrue(re.match(r'32|64', d.bitness))
    def test_get_default_platform_variant(self):
        self.assertTrue(buildinfo.get_natural_platform_variant() in buildinfo.get_known_platform_variants())
    def test_fuzzy_match_platform_variant_with_named_platform(self):
        self.assertEquals("win_32", buildinfo.fuzzy_match_platform_variant('W32'))
        self.assertEquals("win_32", buildinfo.fuzzy_match_platform_variant('win_32'))
        self.assertEquals("win_32", buildinfo.fuzzy_match_platform_variant('Windows-x86'))
        self.assertEquals("win_32", buildinfo.fuzzy_match_platform_variant('32-bit windows'))
        self.assertEquals("win_x64", buildinfo.fuzzy_match_platform_variant('WIN_64'))
        self.assertEquals("win_x64", buildinfo.fuzzy_match_platform_variant('win_x86-64'))
        self.assertEquals("win_x64", buildinfo.fuzzy_match_platform_variant('Windows-x64'))
        self.assertEquals("win_x64", buildinfo.fuzzy_match_platform_variant('w64'))
        self.assertEquals("linux_i686", buildinfo.fuzzy_match_platform_variant('l32'))
        self.assertEquals("linux_i686", buildinfo.fuzzy_match_platform_variant('lInUX-32'))
        self.assertEquals("linux_i686", buildinfo.fuzzy_match_platform_variant('linux_i586'))
        self.assertEquals("linux_i686", buildinfo.fuzzy_match_platform_variant('lini386'))
        self.assertEquals("osx_universal", buildinfo.fuzzy_match_platform_variant('osx'))
        self.assertEquals("osx_universal", buildinfo.fuzzy_match_platform_variant('Mac OSX 10'))
        self.assertEquals("osx_universal", buildinfo.fuzzy_match_platform_variant('mac'))
    def test_fuzzy_match_platform_variant_with_None(self):
        self.assertEquals(None, buildinfo.fuzzy_match_platform_variant('unknown'))
    def test_fuzzy_match_platform_variant_bitness_only(self):
        if EXPECTED_NAME == 'Windows':
            self.assertEquals("win_32", buildinfo.fuzzy_match_platform_variant('32'))
            self.assertEquals("win_32", buildinfo.fuzzy_match_platform_variant('x86'))
            self.assertEquals("win_32", buildinfo.fuzzy_match_platform_variant('32-bit'))
            self.assertEquals("win_x64", buildinfo.fuzzy_match_platform_variant('64'))
            self.assertEquals("win_x64", buildinfo.fuzzy_match_platform_variant('x86-64'))
            self.assertEquals("win_x64", buildinfo.fuzzy_match_platform_variant('x64'))
        elif EXPECTED_NAME == 'Linux':
            self.assertEquals("linux_i686", buildinfo.fuzzy_match_platform_variant('32'))
            self.assertEquals("linux_i686", buildinfo.fuzzy_match_platform_variant('x86'))
            self.assertEquals("linux_i686", buildinfo.fuzzy_match_platform_variant('32-bit'))
            self.assertEquals("linux_x86-64", buildinfo.fuzzy_match_platform_variant('64'))
            self.assertEquals("linux_x86-64", buildinfo.fuzzy_match_platform_variant('x86-64'))
            self.assertEquals("linux_x86-64", buildinfo.fuzzy_match_platform_variant('x64'))
        else:
            self.assertEquals("osx_universal", buildinfo.fuzzy_match_platform_variant('osx'))

if __name__ == '__main__':
    unittest.main()
