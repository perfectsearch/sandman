"""
Test Selection
--------------

This very selector is a partial replacement for default selector from nose. It
was specially designed to handle non-python executable files (compiled test
runners) independently of handling python-scripted test cases, which it leaves
unchanged.

Test selection is handled by a Selector. The test loader calls the
appropriate selector method for each object it encounters that it
thinks may be a test.
"""

import logging
import os
import nose.selector
from CTestRegistrar import TestRunnerRegistrar, isFileNameInItems, clearTestRunnerRegistry
from cmake.util import pathStartsWith

log = logging.getLogger('nose.selector')

# for efficiency and easier mocking
op_join = os.path.join
op_basename = os.path.basename
op_exists = os.path.exists
op_splitext = os.path.splitext
op_isabs = os.path.isabs
op_abspath = os.path.abspath

class Selector(nose.selector.Selector):
    """Replacement test selector. Able to handle compiled test runners in a
    special way, independently of python tests.

    Examines test candidates and determines whether, given the specified
    configuration, the test candidate should be selected as a test.
    """
    tags = ""
    def __init__(self, config):
        nose.selector.Selector.__init__(self, config)
        clearTestRunnerRegistry()
        ## getting root dir for compiled tests and setting it None (if it's
        ## empty) to use it in boolean expressions.
        self.compiledRoot = getattr(config.options, 'compiled_root', None)
        if '' == self.compiledRoot:
            self.compiledRoot = None
    def wantFile(self, file):
        """Is the file a wanted test file?

        The file must be an executable module registered as compiled test runner
        or a python source file. Last should be held by parent selector class.
        """
        if not (self.compiledRoot and pathStartsWith(file, self.compiledRoot)):
            log.debug("File %s will have default processing:", file)
            log.debug("self.compiledRoot is %s", self.compiledRoot)
            return nose.selector.Selector.wantFile(self, file)
        registrar = TestRunnerRegistrar(self.compiledRoot, self.config.options.build_config, Selector.tags)
        log.debug("Selector.wantFile(): Selector.tags='%s'" % Selector.tags)
        wanted = isFileNameInItems(file)
        if wanted:
            log.debug("File %s: wanted is %s", file, wanted)
            return wanted 
