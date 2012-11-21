"""
CTestTestLoader
---------------

Test loader for nose to be able to register not only native nose's tests, but
compiled unit tests with CTest-compatible definitions.
"""
import logging, os, os.path, subprocess, re, unittest, types, sys
from nose.loader import TestLoader
from cmake.CTestTestSuite import TestSuiteFactory
from cmake.selector import Selector
from cmake.CTestRegistrar import getItemByFileName
from cmake.util import pathStartsWith, exeFileToModule
from booleansimplifier import process_expression, ValidateBooleanException

log = logging.getLogger('nose')

def install_all_modules(fullPath, moduleName):
    module = None
    if moduleName in sys.modules.keys():
        module = sys.modules[moduleName]
    else:
        module = types.ModuleType(moduleName)
        module.__path__ = module.__file__ = os.path.normpath(fullPath)
        sys.modules.setdefault(moduleName, module)
        log.debug("registerModule(): module is %s", repr(module))
        __import__(moduleName)
        module = sys.modules[moduleName]
    log.debug("install_all_modules(): module is: %s (full name is %s)",
              repr(module), sys.modules[moduleName].__dict__)
    return module

class CTestTestLoader(TestLoader):
    """Test loader that extends native nose.TestLoader to:

    * Load compiled unit tests designed for CTest;
    * Find compiled test programs according to CTest definitions.
    """
    compiledTestsRoot = None
    exclude = None
    ignoreFiles = None
    include = None
    def __init__(self, config = None, importer = None,
                 workingDir = None, selector = Selector):
        """Initialize a test loader
        """
        TestLoader.__init__(self, config, importer, workingDir, selector)
        log.debug("CTestTestLoader.__init__(): config = %s", config)
        if hasattr(config.options, 'compiled_root'):
            self.compiledTestsRoot = config.options.compiled_root
        log.debug("Compiled root is %s", self.compiledTestsRoot)
        # Each element of config.options.attr is a comma-separated list of
        # enabled of disabled test tags
        target_expression = ''
        for expression in config.options.eval_attr:
            if target_expression:
                target_expression = target_expression + '&'
            target_expression = target_expression + '(' + expression + ')'
        self.tags = process_expression(target_expression)
        Selector.tags = self.tags
        log.debug("CTestTestLoader.__init__(): set tags for Selector")
        if not self.tags:
            self.tags = 'shareable&!interactive'
            log.debug("CTestTestLoader.__init__(): Set default test tasgs")
        log.debug("CTestTestLoader.__init__(): self.tags: %s", self.tags)
    def makeTestCases(self, testFileName, tests=(), testEnvInfo={}):
        """Creates test cases according to passed test names
        """
        modifiedTestCaseName = exeFileToModule(testFileName)
        testRunnerDescription = getItemByFileName(testFileName)
        classDefinition = """import copy, unittest, subprocess, logging, re, tempfile
import os, re
from nose import SkipTest

if 'log' not in globals().keys():
    log = logging.getLogger('nose')

class TestResult:
    result = ""
    output = ""
    def __init__(self, result, output):
        log.debug("TestResult.__init__(self, %%s, %%s)", result, output)
        self.result = result
        self.output = output
        log.debug("TestResult.__init__(): self.result = %%s, self.output = %%s",
                   self.result, self.output)

RE_IS_TEST_PERFORMANCE = re.compile('(?:^|,)performance(?:$|,)')

class %s(unittest.TestCase):
    testResults = dict()
    testTags = '%s'
    test2tags = %s
    envAdditions = %s
    testNameDetectors = dict()
    @classmethod
    def setupClass(cls):
        log.debug("%%s.setupClass()", cls.__name__)
        ## Prepare command line
        testFileName = '%s'
        commandLine = [testFileName, "--chained", "--tags=%%s" %% cls.testTags]
        testList = %s
        for testName in testList:
            commandLine.append(testName)
            cls.testNameDetectors[testName] = re.compile('^(%%s)\\\\s*:' %% testName)
        log.debug("%%s.setupClass(): command line is:%%s", cls.__name__,
                  commandLine)
        if cls.envAdditions:
            env = os.environ.copy();
            for (k, v) in cls.envAdditions.items():
                env[k] = v
            testProcess = subprocess.Popen(commandLine,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       env=env)
        else:
            testProcess = subprocess.Popen(commandLine,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
        output, errors = testProcess.communicate()
        log.debug("setupClass(): len(output) = %%i", len(output))
        cls.split_output(output.splitlines(), testList)
        return True
    @classmethod
    def split_output(cls, testOutput, tests=()):
        cls.outputs = dict()
        if len(tests) == 0:
            return
        if len(testOutput) == 0:
            return
        log.debug("split_output(): test tags are: %%s", cls.test2tags)
        lines = testOutput
        for i in range(len(lines)):
            lines[i] = lines[i].strip()
        lines_filtered = filter(None, lines)
        lines = lines_filtered
        log.debug("split_output(): lines are %%s", lines)
        start = 0
        maxIdx = len(lines)
        currentTest = tests[0]
        end = None
        for nextTest in tests[1:]:
            while start < maxIdx:
                searchResult = re.search(cls.testNameDetectors[currentTest],
                                         lines[start])
                if searchResult and currentTest == searchResult.group(1):
                    break
                log.debug("split_output(): current test '%%s', next test '%%s', skipped line '%%s'", currentTest, nextTest, lines[start])
                start += 1
            end = start
            if start < maxIdx:
                while end < maxIdx:
                    searchResult = re.search(cls.testNameDetectors[nextTest],
                                             lines[end])
                    if searchResult and nextTest == searchResult.group(1):
                        break
                    end += 1
                    log.debug("split_output(): end = %%i", end)
            testOutput = filter(None, lines[start:end])
            testResult = 'Missed'
            if len(testOutput) > 0:
                log.debug("split_output(): preliminary testOutput for %%s  is: %%s",
                          currentTest, " ".join(testOutput))
                testOutput[0] = re.sub("^" + currentTest + ":", "", testOutput[0])
                matchResult = re.search("(Pass|Fail|Skip)(?: -- .*)?$", testOutput[-1])
                if matchResult:
                    if 'Pass' == matchResult.group(1):
                        testResult = 'Pass'
                    elif 'Fail' == matchResult.group(1):
                        testResult = 'Fail'
                    elif 'Skip' == matchResult.group(1):
                        testResult = 'Skip'
                    testOutput[-1] = re.sub("Pass|Fail|Skip", "", testOutput[-1])
                elif re.search(RE_IS_TEST_PERFORMANCE, cls.test2tags[currentTest]):
                    testOutput[0] = re.sub(cls.testNameDetectors[currentTest],
                                           "",
                                           testOutput[0])
                    ## Dirty hack - exploits knowledge of output format
                    testResult = 'Fail' if testOutput[0].startswith(' Error') else 'Pass'
                else:
                    testResult = 'Fail'
                log.debug("split_output(): testOutput for %%s is: %%s",
                          currentTest, " ".join(testOutput))
                strippedTestOutput = []
                for out in testOutput:
                    strippedTestOutput.append(out.strip())
                cls.outputs[currentTest] = TestResult(testResult,
                                                      "\\n".join(filter(None,
                                                                 strippedTestOutput)))
            else:
                cls.outputs[currentTest] = TestResult(testResult, "")
            currentTest = nextTest
        testResult = 'Missed'
        if end is None:
            end = 0
            while end < maxIdx:
                searchResult = re.search(cls.testNameDetectors[currentTest],
                                         lines[end])
                if searchResult and currentTest == searchResult.group(1):
                    break
                end = end + 1
        if end < maxIdx:
            searchResult = re.search(cls.testNameDetectors[currentTest],
                                     lines[end])
            if searchResult and currentTest == searchResult.group(1):
                testOutput = filter(None, lines[end:])
            if len(testOutput) > 0:
                testOutput[0] = re.sub("^" + currentTest + ":", "", testOutput[0])
                matchResult = re.search("(Pass|Fail|Skip)(?: -- .*)?$", testOutput[-1])
                if matchResult:
                    if 'Pass' == matchResult.group(1):
                        testResult = 'Pass'
                    elif 'Fail' == matchResult.group(1):
                        testResult = 'Fail'
                    elif 'Skip' == matchResult.group(1):
                        testResult = 'Skip'
                    testOutput[-1] = re.sub("Pass|Fail|Skip", "", testOutput[-1])
                elif re.search(RE_IS_TEST_PERFORMANCE, cls.test2tags[currentTest]):
                    testOutput[0] = re.sub(cls.testNameDetectors[currentTest],
                                           "",
                                           testOutput[0])
                    ## Dirty hack - exploits knowledge of output format
                    testResult = 'Fail' if testOutput[0].startswith(' Error') else 'Pass'
                else:
                    testResult = 'Fail'
                log.debug("split_output(): testOutput for %%s is: %%s",
                          currentTest, " ".join(testOutput))
                strippedTestOutput = []
                for out in testOutput:
                    strippedTestOutput.append(out.strip())
                cls.outputs[currentTest] = TestResult(testResult,
                                                      "\\n".join(filter(None,
                                                                 strippedTestOutput)))
            else:
                cls.outputs[currentTest] = TestResult(testResult, "")
        else:
            cls.outputs[currentTest] = TestResult(testResult, "")
        log.debug("split_output(): outputs: ")
        for (k,v) in cls.outputs.items():
            log.debug("split_output(): %%s => (%%s, %%s)", k, v.result, v.output)
""" % (modifiedTestCaseName, self.tags, repr(testRunnerDescription.testTags), testEnvInfo, testFileName.replace('\\', '\\\\'), repr(tests))
        log.debug("CTestTestLoader.makeTestCases(): before install_all_modules()")
        module = install_all_modules(testFileName, exeFileToModule(testFileName))
        log.debug("CTestTestLoader.makeTestCases(): module is %s", module)
        log.debug("CTestTestLoader.makeTestCases(): module.__dict__ is %s",
                  module.__dict__)
        testCases = []
        for test in tests:
            classDefinition += """    def %s(self):
        testResult = self.__class__.outputs['%s']
        log.debug("%s(): testResult is %%s", repr(testResult))
        if testResult.output and not 'Skip' in testResult.result:
            print testResult.output
        log.debug("%%s.%s(): test result is %%s", self.__class__.__name__,
                  testResult.result)
        if 'Missed' in testResult.result:
            raise ValueError('Missed')
        elif 'Fail' in testResult.result:
            raise self.failureException('Failed')
        elif 'Skip' in testResult.result:
            raise SkipTest(testResult.output.strip())
        else:
            pass
""" % (test, test, test, test)
        log.debug("CTestTestLoader.makeTestCases(): classDefinition is %s",
                  classDefinition)
        context = module.__dict__
        exec classDefinition in context
        __import__(module.__name__)
        for test in tests:
            testCases.append(context[modifiedTestCaseName](methodName=test))
        log.debug("CTestTestLoader.makeTestCases(): %s ", repr(testCases))
        return testCases
    def loadTestsFromFile(self, filename):
        log.debug("CTestTestLoader.loadTestsFromFile(%s)", filename)
        doesStartWith = False
        try:
            doesStartWith = pathStartsWith(filename, self.compiledTestsRoot)
        except:
            doesStartWith = False
        if not doesStartWith:
            log.debug("CTestTestLoader.loadTestsFromFile(): fall back to predefined behavior")
            return TestLoader.loadTestsFromFile(self, filename)
        tests = list()
        tagset = set(self.tags.split(','))
        testRunnerInfo = getItemByFileName(filename)
        log.debug("testRunnerInfo now is: %s", repr(testRunnerInfo))
        if testRunnerInfo:
            tests = testRunnerInfo.tests
        log.debug("CTestTestLoader.loadTestsFromFile(): have tests: '%s'" % tests)
        loadedTests = self.makeTestCases(filename, tests, testRunnerInfo.env)
        log.debug("CTestTestLoader.loadTestsFromFile(%s): loaded tests %s",
                  filename, loadedTests)
        log.debug("CTestTestLoader.loadTestsFromFile(): suite class is %s",
                   repr(self.suiteClass))
        return self.suiteClass(loadedTests)
