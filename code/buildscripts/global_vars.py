'''
'''
'''
   Python's "global variables" are really module level variables
   if you need to share variables between modules, you can store them here
'''
'''
'''

app = None #this will be a reference to the current existing appliance or runnable assembly

ea = None #ea is the name (a string) of an appliance passed in on the commandline that maps to information stored in the setup file

debug = False #determines if the runnable assembly, the existing appliance, and a few other modules will default to debug mode.

import os.path
import interactive_test_setup as setup
from testsupport import TESTROOT
if os.path.exists(os.path.join(TESTROOT, 'test_setup.xml')):
    setup.filepath = os.path.join(TESTROOT, 'test_setup.xml')
if os.path.exists( os.path.expanduser(os.path.join('~', 'test_setup.xml')) ):
    setup.filepath = os.path.expanduser(os.path.join('~', 'test_setup.xml'))
if setup.filepath is None:
    setup.filepath = os.path.expanduser(os.path.join('~', 'test_setup.xml'))
    setup.checkForSetupFile()
   
location = setup.getLocation() #some tests will be skipped if the proper VMs are not set up at your location
