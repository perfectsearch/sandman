'''
psjunit2noseplugin.py
Provides JUnit-aware test discovery and execution functionality in a way
compatible with nose test framework.
'''
import os
from nose.plugins import Plugin
from nose.case import Test
import logging
import subprocess
import re
import unittest

log = logging.getLogger('nose')

TEST_DEFINITION_PATTERN = re.compile('\(\s*(\S*)\s*"(\S*?)"\s*\)')

class PSJUnit2NosePlugin(Plugin):
    """
class PSJUnit2NosePlugin
Implements testrunners and tests collection based on JUnit output.
    """
    name = 'PSJUnit2NosePlugin'
    junitConfFileName = 'build.xml'
    dirName = None
    junitDefinitionStrings = []
    collect_only = None
    enableOpt = 'compiled_root'
    buildConfig = 'Release'
    def options(self, parser, env):
        """Register commandline options
        """
        self.compiledTestsRoot = ''
        parser.add_option('--compiled-root',
                          action = 'store',
                          default = '',
                          help="Compiled tests root directory")
        parser.add_option('--build-config',
                          action = 'store',
                          default = 'Release',
                          help = "Config to look for (if build configurations supported by environment)")
    def configure(self, options, conf):
        log.debug("Configuring PSJUnit2NosePlugin")
        Plugin.configure(self, options, conf)
        self.conf = conf
        if hasattr(self.conf.options, 'collect_only'):
            self.collect_only = getattr(self.conf.options, 'collect_only')
        log.debug("self.collect_only is %s" % self.collect_only)
        if hasattr(self.conf.options, 'compiled_root'):
            self.compiledTestsRoot = getattr(self.conf.options, 'compiled_root')
        log.debug("self.compiledTestsRoot is %s" % self.compiledTestsRoot)
        self.buildConfig = getattr(self.conf.options, 'build_config') if hasattr(self.conf.options, 'build_config') else None
    def wantFile(self, filename):
        """
        Checks if JUnit test definition file present in the file filename.
        Returns True if and only if test definitions were found
        """
        log.debug("PSJUnit2NosePlugin.wantFile(self, %s)" % filename)
        return os.path.samefile(filename, os.path.join(self.compiledTestsRoot, self.junitConfFileName))

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

