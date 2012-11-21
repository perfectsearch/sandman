"""
CTest - aware test suite
"""

from unittest import TestSuite
import logging, subprocess

log = logging.getLogger('nose')

class CTestTestSuite(TestSuite):
    def __init__(self, tests=(), testProgram=None):
        if callable(tests):
            tests = tests()
        log.debug("CTestTestSuite.__init__(self, %s)", repr(tests))
        TestSuite.__init__(self, tests)
        self.testProgram = testProgram
    def run(self, result):
        if not testProgram is None:
            # Run compiled tests, parse output and prepare tests
            log.debug("CTestTestSuite.run(): preparing to run test program %s",
                      self.testProgram)
            log.debug("Tests to run: %s",
                      repr((test.__name__ for test in tests)))
            pass
        TestSuite.run(self, result)

class TestSuiteFactory:
    def __init__(self, conf):
        self.conf = conf
    def __call__(self, tests=(), **kw):
        return CTestTestSuite(tests)
