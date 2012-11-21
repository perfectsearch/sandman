"""
JUnitTestLoader
---------------

Test loader for nose to be able to register not only native nose's tests, but
compiled unit tests with JUnit-compatible definitions.
"""
import logging, os, os.path, subprocess, re, unittest, types, sys, time, timeout_monitor
from nose.loader import TestLoader
from JUnitSelector import JUnitSelector
from testsupport import TESTROOT, SBROOT
from sandbox import Sandbox
from nose.failure import Failure
from booleansimplifier import process_expression, ValidateBooleanException

_timeout_monitor = None

class _ProcAbort:
    def __init__(self):
        self.proc = None
    def __call__(self):
        if self.proc:
            self.proc.terminate()

log = logging.getLogger('nose')

def install_all_modules(fullPath, className):
    log.debug("install_all_modules(%s, %s)", fullPath, className)
    module = None
    prevModule = None
    moduleNameParts = className.split('.')
    log.debug("install_all_modules() moduleNameParts = %s", moduleNameParts)
    for n in range(len(moduleNameParts))[1:]:
        moduleName = '.'.join(moduleNameParts[:n])
        log.debug("install_all_modules() moduleName = %s", moduleName)
        if moduleName in sys.modules.keys():
            module = sys.modules[moduleName]
        else:
            module = types.ModuleType(moduleName)
            module.__path__ = module.__file__ = os.path.normpath(fullPath)
            sys.modules.setdefault(moduleName, module)
            log.debug("registerModule(): module is %s", repr(module))
            __import__(moduleName)
            module = sys.modules[moduleName]
        log.debug("install_all_modules() prevModule is %s", prevModule)
        log.debug("install_all_modules() module to add is %s",
                  moduleNameParts[n - 1])
        if prevModule:
            prevModule.__dict__[moduleNameParts[n - 1]] = module
        prevModule = module
    log.debug("install_all_modules(): module is: %s (full name is %s)",
              repr(module), sys.modules[moduleName].__dict__)
    return module

class JUnitTestLoader(TestLoader):
    """Test loader that extends native nose.TestLoader to load and process
    execution results of compiled unit tests designed for JUnit.
    """
    compiledTestsRoot = None
    exclude = None
    ignoreFiles = None
    include = None
    def __init__(self, config = None, importer = None,
                 workingDir = None, selector = JUnitSelector):
        """Initialize a test loader
        """
        TestLoader.__init__(self, config, importer, workingDir, selector)
        log.debug("JUnitTestLoader.__init__(): config = %s", config)
        if hasattr(config.options, 'compiled_root'):
            self.compiledTestsRoot = config.options.compiled_root
            if os.name == "nt":
                self.compiledTestsRoot = self.compiledTestsRoot.replace("/", "\\")
        log.debug("Compiled root is %s, os is %s", self.compiledTestsRoot, os.name)
        # Each element of config.options.attr is a comma-separated list of
        # enabled of disabled test tags
        target_expression = ''
        for expression in config.options.eval_attr:
            if target_expression:
                target_expression = target_expression + '&'
            target_expression = target_expression + '(' + expression + ')'
        self.tags = process_expression(target_expression)
        if not self.tags:
            self.tags = 'checkin&!interactive'
            log.debug("JUnitTestLoader.__init__(): Set default test tasgs")
        log.debug("JUnitTestLoader.__init__(): self.tags: %s", self.tags)
    def makeTestCase(self, singleTestOutput, testExceptions):
        """Creates test cases according to passed test output
        """
        outputLines = singleTestOutput.splitlines()
        pathSep = '\\' if os.name == 'nt' else '/'
        fileName = outputLines[0].replace('.', pathSep)
        log.debug("JUnitTestLoader.makeTestCase(): fileName = %s", fileName)
        testName = outputLines[0].split('.')[-1]
        log.debug("JUnitTestLoader.makeTestCase(): testName = %s", testName)
        classDefinition = """
import unittest, subprocess, logging, re, tempfile, os, re, unittest
from nose import SkipTest

if 'log' not in globals().keys():
    log = logging.getLogger('nose')

class %s(unittest.TestCase):
""" % testName.replace('-', '_')
        log.debug("JUnitTestLoader.makeTestCase(): before install_all_modules()")
        module = install_all_modules(os.path.join(self.compiledTestsRoot,
                                                  fileName),
                                     outputLines[0])
        log.debug("JUnitTestLoader.makeTestCase(): module is %s", module)
        log.debug("JUnitTestLoader.makeTestCase(): module.__dict__ is %s",
                  module.__dict__)
        log.debug("JUnitTestLoader.makeTestCase(): module.__dict__ finished")
        testCases = []
        outputLines = outputLines[1:]
        outputLinesLen = len(outputLines)
        found_test_defs = False
        for n, testDefinitionString in enumerate(outputLines):
            # Skipping lines not related to test cases
            if not testDefinitionString.startswith("Testcase: "):
                continue
            ## handle test results
            i = n + 1
            currentTestOutputLines = []
            while i < outputLinesLen:
                if outputLines[i].startswith("Testcase: "):
                    break
                i = i + 1
            currentTestOutputLines = filter(None, outputLines[n + 1:i])
            for i, line in enumerate(currentTestOutputLines):
                currentTestOutputLines[i] = line.strip()
            failedStatus = False
            log.debug("JUnitTestLoader.makeTestCase(): currentTestOutputLines:")
            for line in currentTestOutputLines:
                log.debug(line)
                log.debug("")
            log.debug("")
            if currentTestOutputLines and (currentTestOutputLines[0] == 'FAILED' or 'ERROR' in currentTestOutputLines[0]):
                failedStatus = True
                currentTestOutputLines[0] = ''
            testMethodName = testDefinitionString.split(' ')[1]
            currentTestOutput = '\n'.join(currentTestOutputLines).strip()
            found_test_defs = True
            classDefinition += """    def %s(self):
        testOutput = '''%s'''""" % (testMethodName, currentTestOutput)
            if failedStatus:
                classDefinition += """
        self.fail(msg=testOutput)
"""
            else:
                classDefinition += """
        if testOutput:
            print testOutput
"""
        if not found_test_defs:
            classDefinition += '    pass\n'
            print('classDefinition =\n' + classDefinition)
        log.debug("JUnitTestLoader.makeTestCase(): classDefinition is %s",
                classDefinition)
        context = module.__dict__
        exec classDefinition in context
        for testDefinitionString in outputLines[1:]:
            if not testDefinitionString.startswith("Testcase: "):
                continue
            testMethodName = testDefinitionString.split(' ')[1]
            testCase = context[testName](methodName=testMethodName)
            log.debug("JUnitTestLoader.makeTestCase() testCase is %s",
                      testCase)
            log.debug("JUnitTestLoader.makeTestCase() testCase contents is %s",
                      testCase.__dict__)
            testCases.append(testCase)
        log.debug("JUnitTestLoader.makeTestCase(): %s ", repr(testCases))
        return testCases
    def prepareCommandLine(self):
        log.debug("JUnitTestLoader.prepareCommandLine()")
        build_py = SBROOT + '/code/buildscripts/build.py'
        if os.name == 'nt':
            build_py = build_py.replace('/', '\\')
        ##TODO add parameter to select tests by tags
        commandLine = ['python', build_py,
                       # Next line is a hack: initial space changes option into
                       # target to build (from the point of view of build.py
                       # script)
                       ##FIXME
                       ' -Drun.test.categories="%s"' % self.tags,
                       'test', '-v']
        return commandLine
    def executeTests(self, commandLine):
        log.debug("JUnitTestLoader.executeTests() with commandLine=%s", commandLine)
        # Initialize our state.
        start = time.time()
        sb = Sandbox(SBROOT)
        sb.set_last_test_date(start)
        global _timeout_monitor
        _timeout_monitor = None
        testOutput = ""
        err = 0
        try:
            # Start up a thread that will force us to exit if we hang.
            pabrt = _ProcAbort()
            _timeout_monitor = timeout_monitor.start(sb.get_test_timeout_seconds(), killfunc=pabrt)
            # Always run tests in alphabetical order, for predictability
            # and ease of explanation.
            proc = subprocess.Popen(commandLine,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            _timeout_monitor.last_status = time.time()
            pabrt.proc = proc
            testOutput, stderr = proc.communicate()
            err = proc.returncode
        except Exception as e:
            log.debug("JUnitTestLoader.executeTests(): Got exception: %s", str(e))
            err = 1
        finally:
            if _timeout_monitor:
                _timeout_monitor.stop()
        if "[junit] '-classpath" in testOutput and 'BUILD FAILED' in testOutput:
            err = 0
            log.debug("JUnitTestLoader.executeTests(): Actually it's JUnit test failed, all is fine.")
        if err != 0:
            raise Exception("Building compiled test suite failed!")
        return testOutput
    def filterTestOutput(self, testOutput):
        singleTestOutput = []
        for line in filter(None, testOutput.splitlines()):
            prepared = line.strip()
            if prepared.startswith('[junit]'):
                singleTestOutput.append(prepared)
        testOutput = '\n'.join(singleTestOutput).strip()
        singleTestOutput = re.split(r'\[junit\] Testsuite: ', testOutput)[1:]
        re_junit_mark = re.compile(r'^\[junit\] ?')
        for n, output in enumerate(singleTestOutput):
            lines = output.splitlines()
            for m, line in enumerate(lines):
                lines[m] = re.sub(re_junit_mark, '', line)
            singleTestOutput[n] = '\n'.join(filter(None, lines)).strip()
        singleTestExceptions = []
        ##TODO Extract exceptions from the last element of singleTestOutput and
        ## populate singleTestExceptions
        return filter(None, singleTestOutput), singleTestExceptions
    def makeTestCases(self, testOutput, testExceptions):
        tests = []
        for singleTestOutput in testOutput:
            testCases = self.makeTestCase(singleTestOutput, testExceptions)
            if testCases:
                for test in testCases:
                    tests.append(test)
        return tests
    def loadTestsFromFile(self, filename):
        """
        We'll exploit the knowledge of the selector implementation details:
        since the selector 'wants' only root build.xml file for JUnit-based
        tests, we can safely check initials and then fall back to inherited
        behavior or collect output for all tests.
        """
        log.debug("JUnitTestLoader.loadTestsFromFile(%s)", filename)
        if not filename.startswith(self.compiledTestsRoot):
            log.debug("JUnitTestLoader.loadTestsFromFile(): fall back to predefined behavior")
            log.debug("JUnitTestLoader.loadTestsFromFile(): compiledTestsRoot is %s", self.compiledTestsRoot)
            return TestLoader.loadTestsFromFile(self, filename)
        commandLine = self.prepareCommandLine()
        try:
            testOutput = self.executeTests(commandLine)
        except Exception as e:
            log.debug("Building JUnit test suite failed with message: %s",
                      str(e))
            return self.suiteClass(Failure(Exception,"Couldn't build compiled test suite."))
        log.debug("JUnitTestLoader.loadTestsFromFile(): got ant output:\n%s",
                  testOutput)
        singleTestOutput, singleTestExceptions = self.filterTestOutput(testOutput)
        log.debug("JUnitTestLoader.loadTestsFromFile(): JUnit filtered output:")
        for line in singleTestOutput:
            log.debug("%s\n", line)
        log.debug("JUnitTestLoader.loadTestsFromFile(): %s",
                  "JUnit filtered output finished.")
        loadedTests = self.makeTestCases(singleTestOutput,
                                         singleTestExceptions)
        log.debug("JUnitTestLoader.loadTestsFromFile(): loaded tests %s",
                  loadedTests)
        log.debug("JUnitTestLoader.loadTestsFromFile(): suite class is %s",
                  repr(self.suiteClass))
        return self.suiteClass(loadedTests)
