'''
psctest2noseplugin.py
Provides CTest-aware test discovery and execution functionality in a way
compatible with nose test framework.
'''
import os
from nose.plugins import Plugin
from nose.case import Test
import logging
import subprocess
import re
import unittest
from cmake.CTestLoader import CTestTestLoader

log = logging.getLogger('nose')

TEST_DEFINITION_PATTERN = re.compile('\(\s*(\S*)\s*"(\S*?)"\s*\)')

class PSCTest2NosePlugin(Plugin):
    """
class PSCTest2NosePlugin
Implements testrunners and tests collection based on CTest configuration data.
    """
    name = 'PSCTest2NosePlugin'
    ctestConfFileName = 'CTestTestfile.cmake'
    dirName = None
    ctestDefinitionStrings = []
    collect_only = None
    compiledTestsRoot = None
    enableOpt = 'compiled_root'
    buildConfig = 'Release'
    def options(self, parser, env):
        """Register commandline options
        """
        parser.add_option('--compiled-root',
                          action = 'store',
                          dest = self.compiledTestsRoot,
                          default = '',
                          help="Compiled tests root directory")
        parser.add_option('--build-config',
                          action = 'store',
                          default = 'Release',
                          help = "Config to look for (if build configurations supported by environment)")
    def configure(self, options, conf):
        log.debug("Configuring PSCTest2NosePlugin")
        Plugin.configure(self, options, conf)
        self.conf = conf
        if hasattr(self.conf.options, 'collect_only'):
            self.collect_only = getattr(self.conf.options, 'collect_only')
        log.debug("self.collect_only is %s" % self.collect_only)
        self.buildConfig = getattr(self.conf.options, 'build_config') if hasattr(self.conf.options, 'build_config') else None
    def wantDirectory(self, dirname):
        """
        Checks if CTest test definition file present in the dirname directory and tries
        to load these test definitions.
        Returns True if and only if test definitions were successfully loaded
        """
        log.debug("PSCTest2NosePlugin.wantDirectory(self, %s)" % dirname)
        localCTestFileName = os.path.join(dirname, self.ctestConfFileName)
        if  os.path.exists(localCTestFileName) and os.path.isfile(localCTestFileName) and os.path.getsize(localCTestFileName) > 0:
                self.dirName = dirname
                self.ctestDefinitionStrings = []
                try:
                    ctestFile = open(localCTestFileName, 'r')
                    definitionStrings = ctestFile.readlines()
                    self.ctestDefinitionStrings.append(string for string in definitionStrings if not string.startswith('#'))
                except IOerror:
                    self.dirName = None
                    self.ctestDefinitionStrings = []
                    return False
                log.debug((string for string in self.ctestDefinitionStrings))
                if len(self.ctestDefinitionStrings) != 0:
                    return True
        self.dirName = None
        self.ctestDefinitionStrings = []
        return False

def testGenerator(tests):
    def run():
        pass
    for test in tests:
        setattr(__dict__, test, run)
        yield getattr(__dict__, test)

class CollectTestSuiteFactory:
    def __init__ (self, conf):
        self.conf = conf
    def __call__(self, tests=(), **kw):
        return CollectTestSuite(tests, conf=self.conf)

class CollectTestSuite(unittest.TestSuite):
    def __init__(self, tests=(), conf=None):
        self.conf = conf
        log.debug("CollectTestSuite(%r)", tests)
        self.testNames = tests
        unittest.TestSuite.__init__(self)
    def addTest(self, test):
        log.debug("CollectTestSuite.addTest(self, %s)", test)
        if isinstance(test, unittest.TestSuite):
            self._tests.append(test)
        else:
            self._tests.append(Test(test, config = self.conf))

