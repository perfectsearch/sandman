#!/usr/bin/env python
#
# $Id: FixCopyrightTest.py 4187 2011-01-04 18:21:34Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import unittest, os, sys, subprocess, re
from codescan import fix_copyright
from codescan.fix_copyright import _getHeader, _addHeader
from testsupport import checkin


# The actual header has a bunch of long gobbledygook in it, that I don't want to
# copy and paste over and over again into this test. This function removes the detail
# to make visual comparison easier, and gives you one place to adjust if the template
# ever changes.'
def _simplify(txt):
    txt = txt.replace('\x24Id: filename 3521 2010-11-25 00:31:22Z svn_username $', 'Id')
    txt = txt.replace('Proprietary and confidential.', 'Prop')
    txt = txt.replace('Copyright \x24Date:: 2010#$ Perfect Search Corporation.', 'Copy')
    txt = txt.replace('All rights reserved.', 'All')
    return txt

@checkin
class FixCopyrightTest(unittest.TestCase):
    def test_getHeader(self):
        self.assertEquals("# \n# Id\n# \n# Prop\n# Copy\n# All\n# ", _simplify(_getHeader("foo.py")))
        self.assertEquals("REM \nREM Id\nREM \nREM Prop\nREM Copy\nREM All\nREM ",_simplify(_getHeader("foo.bat")))
        self.assertEquals("' \n' Id\n' \n' Prop\n' Copy\n' All\n' ", _simplify(_getHeader("foo.vbs")))
        self.assertEquals('/*\n * Id\n * \n * Prop\n * Copy\n * All\n * \n */', _simplify(_getHeader("foo.js")))
        self.assertEquals("<!-- \nId\n\nProp\nCopy\nAll\n -->", _simplify(_getHeader("foo.xml")))
    def test_addHeader(self):
        self.assertEquals("#!/usr/bin/env python\n# \n# Id\n# \n# Prop\n# Copy\n# All\n# \nhere is some source", _simplify(_addHeader("foo.py", "#!/usr/bin/env python\nhere is some source")))
        self.assertEquals('/*\n * Id\n * \n * Prop\n * Copy\n * All\n * \n */\nhere is some source', _simplify(_addHeader("foo.java", "here is some source")))

if __name__ == '__main__':
    unittest.main()
