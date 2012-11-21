#!/usr/bin/env python
#
# $Id: PsLocaleTest.py 6680 2011-04-06 17:46:58Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, sys, os
from l10n import pslocale
from testsupport import checkin

@checkin
class PsLocaleTest(unittest.TestCase):
    def test_standardize(self):
        self.assertEquals("en", pslocale.standardize("en"))
        self.assertEquals("en", pslocale.standardize("  EN\t\r\r\n"))
        self.assertEquals("zh_TW", pslocale.standardize("ZH-TW"))
        self.assertEquals("zh_TW", pslocale.standardize("Zh;tW"))
        self.assertEquals("zh_TW", pslocale.standardize("ZH.tw"))
        self.assertEquals("zh_TW", pslocale.standardize("zhtw"))
        self.assertEquals("zh_TW", pslocale.standardize("zh  tW"))
        self.assertEquals("zh_TW", pslocale.standardize("zh_tW.big5"))
        self.assertEquals("wa_BE", pslocale.standardize("wa_BE.iso885915@euro"))
        self.assertEquals("zh_CN", pslocale.standardize("zh"))
    def test_nameForCode(self):
        self.assertEquals("English", pslocale.nameForCode("en"))
        self.assertEquals("English", pslocale.nameForCode("  EN\t\r\r\n"))
        self.assertEquals("Chinese Traditional", pslocale.nameForCode("ZH-TW"))
        self.assertEquals("Chinese Simplified", pslocale.nameForCode("zh"))
        self.assertEquals(None, pslocale.nameForCode("fr_CA"))
        self.assertEquals("French", pslocale.nameForCode("fr_CA", True))
        self.assertEquals("Italian", pslocale.nameForCode("it"))
        self.assertEquals("Portuguese", pslocale.nameForCode("pt"))
        self.assertEquals("Portuguese", pslocale.nameForCode("pt_BR", True))
        self.assertEquals("German", pslocale.nameForCode("de", True))
        self.assertEquals("Japanese", pslocale.nameForCode("ja", True))
        self.assertEquals("Korean", pslocale.nameForCode("ko", True))
        self.assertEquals("Martian", pslocale.nameForCode("ma"))
    def test_bestFit(self):
        self.assertEquals("pt", pslocale.bestFit("pt_BR"))
        self.assertEquals("en", pslocale.bestFit("en"))
        self.assertEquals("zh_TW", pslocale.bestFit("ZH-TW"))
        self.assertEquals("zh_CN", pslocale.bestFit("zh.cn"))
        self.assertEquals("zh_CN", pslocale.bestFit("zh"))

if __name__ == '__main__':
    unittest.main()
