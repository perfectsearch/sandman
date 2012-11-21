"""
Registration of test runners
----------------------------

Executes all compiled-test test runners in dry run and collects lists of all
tests and their tags in each test runner. Also stores full path to any test
runner found.
"""

import copy, subprocess, re, os, os.path, logging 

log = logging.getLogger('nose')

op_dirname = os.path.dirname
op_basename = os.path.basename
op_splitext = os.path.splitext
op_join = os.path.join
op_exists = os.path.exists
op_isfile = os.path.isfile
op_abspath = os.path.abspath
op_realpath = os.path.realpath

o_walk = os.walk

# Changes to undescore all simbols possible in a test runner name and
# inappropriate from Python's point of view
RE_TO_UNDERSCORE = re.compile('[. -]')
# Matches dry-run output string with test name and tag in groups
RE_SPLIT_DRYRUN = re.compile('^\s*(\S+)\s*: Pass -- (\S+)$')
# Matches subdirectory definition (subdirectory name in group)
RE_GET_SUBDIRECTORY = re.compile(r'(?:subdirs)\s?\(\s?(\S+)\s?\)', re.I)
# Matches CTes test definition (name and file name of a test runner are in
# groups)
RE_GET_TESTRUNNER = re.compile(r'(?:add_test)\s?\(\s?(\S+)\s?"(\S+)"\s?\)', re.I)
# Matches test environment settings (test name and environment settings are in
# groups)
## FIXME The following definition designed to extract settings for a single
## test, not some number of ones. Possibly it sould be changed
RE_GET_ENVIRONMENT = \
re.compile(r'(?:set_tests_properties)\s?\(\s?(\S+)\s?(?:properties\s+environment)\s?"(\S+)"\s?\)', re.I)

_testRunnerRegistry = list()

TEST_DEFINITIONS_NAME = 'CTestTestfile.cmake'

def getTestRunnerRegistry():
    return _testRunnerRegistry

def clearTestRunnerRegistry():
    global _testRunnerRegistry
    _testRunnerRegistry = list()

class RegisteredTestRunner:
    """Stores all info about registered test runner.
    Note that testRunnerEnv is not a total, but only additional environment
    settings.
    """
    def __init__(self, testRunnerFileName, testRunnerName, selectionPredicate, testRunnerEnv={}):
        self.filename = op_realpath(testRunnerFileName)
        self.dirname = op_dirname(self.filename)
        self.name = testRunnerName
        self.env = copy.deepcopy(testRunnerEnv)
        self.selectionPredicate = selectionPredicate
        self.tests = list()
        self.tags = list()
        self.testTags = dict()
        log.debug("RegisteredTestRunner.__init__: testRunnerFileName is %s",
                  testRunnerFileName)
        log.debug("RegisteredTestRunner.__init__: testRunnerName is %s",
                  testRunnerName)
        log.debug("RegisteredTestRunner.__init__: testRunnerEnv is %s",
                  testRunnerEnv)
        self.populateTests()
        self.populateTags()
    def __repr__(self):
        rpr = '<%s instance: filename=%s dirname=%s name=%s env=%s tests=%s ' %\
               (self.__class__.__name__, self.filename, self.dirname, self.name,
                       repr(self.env), repr(self.tests))
        return rpr + 'tags=%s>' % repr(self.tags)
    def populateTests(self):
        """Reads and stores information about tests.
        """
        ## Execute dry-run for all tags and capture the output
        commandLine = [self.filename, "--tags=%s" % self.selectionPredicate, "--dry-run", "--chained"]
        log.debug("RegisteredTestRunner.populateTests(): Collecting tests with command line: %s", commandLine)
        env = self.env if self.env else None
        if env:
            commandLine = (" ").join(commandLine)
            if 'nt' == os.name:
                commandLine = commandLine.replace("&","^&").replace("!","^!").replace("|","^|")
            else:
                commandLine = commandLine.replace("&","\&").replace("!","\!").replace("|","\\|")
            log.debug("RegisteredTestRunner.populateTests(): Environment is: %s", env)
            dryRun = subprocess.Popen(commandLine,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    shell=True,
                                    env=env)
        else:
            log.debug("RegisteredTestRunner.populateTests(): Environment is empty, using default.")
            dryRun = subprocess.Popen(commandLine,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        ##FIXME output can be long enough to overrun the buffer of the pipe. In
        ## this case we'll have incorrect data on tests runned.
        (out, err) = dryRun.communicate()
        log.debug("RegisteredTestRunner.populateTests(): Collected output is:\n%s", out)
        ## Parse output
        lines = out.split('\n')
        log.debug("RegisteredTestRunner.populateTests(): Collected output lines are:\n%s", lines)
        for line in lines:
            result = re.search(RE_SPLIT_DRYRUN, line.strip())
            if result:
                testName = result.group(1)
                testTags = result.group(2)
                self.tests.append(testName)
                self.testTags[testName] = testTags
                log.debug("RegisteredTestRunner.populateTests(): Got test %s with tags %s", testName, testTags)
            else:
                log.debug("RegisteredTestRunner.populateTests(): No tests with tags from line '%s'", line.strip())
        log.debug("RegisteredTestRunner.populateTests(): Collected tests: %s", self.tests)
        log.debug("RegisteredTestRunner.populateTests(): Collected test tags: %s", self.testTags)
        log.debug("RegisteredTestRunner.populateTests(): Collecting test case %s done", self.name)
    def populateTags(self):
        """Constructs tag list from tests dictionary.
        """
        if 0 != len(self.tags):
            return
        for tag in self.testTags.values():
            if not tag in self.tags:
                self.tags.append(tag)
    def isValid(self):
        """Shortly checks that object is fully-constructed and has valid state.

        The state is valid if self.tags and self.tests are both not empty.
        """
        try:
            if len(self.tests) > 0 and len(self.tags) > 0:
                return True
        except:
            pass
        return False

class TestRunnerRegistrar:
    """Cycles through directories following CTest definitions and registers test
    runners.
    """
    def __init__(self, compiledRoot, buildConfig, selectionPredicate):
        log.debug("TestRunnerRegistrar.__init__(self, %s, %s, %s)",
                  compiledRoot,
                  buildConfig,
                  selectionPredicate)
        self.compiledRoot = compiledRoot
        self.buildConfig = buildConfig
        self.selectionPredicate = selectionPredicate
        registry = getTestRunnerRegistry()
        if 0 == len(registry):
            self.lookupTestSettings()
        log.debug("TestRunnerRegistrar.__init__(): Test settings discovery finished")
    def lookupTestSettings(self):
        """Service method to recursively discover and register test runners with
        their settings.
        """
        rootTestDefinitions = op_join(self.compiledRoot, TEST_DEFINITIONS_NAME)
        if not (op_exists(rootTestDefinitions) and
                op_isfile(rootTestDefinitions)):
            return
        dirsToSee = [self.compiledRoot.replace("\\","/")]
        for (dirpath_dirty, dirnames, filenames) in o_walk(self.compiledRoot):
            #normalizer dirpath to unix style path
            dirpath = dirpath_dirty.replace("\\","/")
            log.debug("TestRunnerRegistrar.lookupTestSettings(): dirpath = %s" % dirpath)
            log.debug("TestRunnerRegistrar.lookupTestSettings(): dirsToSee = %s" % dirsToSee)
            if not dirpath in dirsToSee:
                continue
            if 'nt' != os.name or op_basename(dirpath) != self.buildConfig:
                testSettingsFileName = op_join(dirpath, TEST_DEFINITIONS_NAME)
                if not (op_exists(testSettingsFileName) and
                        op_isfile(testSettingsFileName)):
                    continue
                testRunners = dict()
                envvars = dict()
                # Parsing test settings
                with open(testSettingsFileName, 'r') as testSettingsFile:
                    testSettings = testSettingsFile.readlines()
                    log.debug("TestRunnerRegistrar.lookupTestSettings(): Reading settings file %s:" % testSettingsFileName)
                    log.debug(testSettings)
                    for line in testSettings:
                        if line.strip().startswith('#'):
                            continue
                        # Registering subdirectoried for lookup
                        matchResult = re.search(RE_GET_SUBDIRECTORY, line)
                        if matchResult:
                            if 'nt' == os.name:
                                dirsToSee.append(                       \
                                        op_join(dirpath,                \
                                                matchResult.group(1),   \
                                                self.buildConfig).replace("\\\\","/").replace("\\","/"))
                            dirsToSee.append(op_join(dirpath, matchResult.group(1)).replace("\\\\","/").replace("\\","/"))
                            continue
                        # Registering test runners for lookup
                        matchResult = re.search(RE_GET_TESTRUNNER, line)
                        if matchResult:
                            testRunners[matchResult.group(2)] = \
                                re.sub(RE_TO_UNDERSCORE, '_',
                                       matchResult.group(1))
                            continue
                        # Getting environment settings for test runners
                        ##FIXME catches only one test runner
                        ##FIXME catches only one (last) definition for test runner
                        matchResult = re.search(RE_GET_ENVIRONMENT, line)
                        if matchResult:
                            key = re.sub(RE_TO_UNDERSCORE, '_', matchResult.group(1))
                            val = matchResult.group(2)
                            envvars[key] = val
                            log.debug("TestRunnerRegistrar.lookupTestSettings(): Added environment variable %s='%s'",
                                      key,
                                      val)
                            continue
                        log.debug("TestRunnerRegistrar.lookupTestSettings(): Unknown string '%s'", line)
                    testSettingsFile.close()
            # Looking for test runners
            for (trFileName, trName) in testRunners.items():
                ##FIXME only .exe tests supported - no batch files
                if 'nt' == os.name:
                    trFileName = '%s.exe' % trFileName
                log.debug("TestRunnerRegistrar.lookupTestSettings(): Looking up test runner %s (filename %s)" % (trName, trFileName))
                log.debug("TestRunnerRegistrar.lookupTestSettings(): in files: %s" % filenames)
                if trFileName in filenames:
                    log.debug("TestRunnerRegistrar.lookupTestSettings(): Test runner definitions found")
                    trFullName = op_join(dirpath, trFileName)
                    trEnv = {}
                    ##FIXME supposes only one environment variable is being
                    ## adjusted
                    if trName in envvars.keys():
                        envSettings = envvars[trName].split('=',1)
                        if 2 == len(envSettings):
                            trEnv[envSettings[0].strip()] = \
                                envSettings[1].strip()
                    log.debug("TestRunnerRegistrar.lookupTestSettings(): Appending %s to registry", trName)
                    _testRunnerRegistry.append(
                            RegisteredTestRunner(trFullName, trName, self.selectionPredicate, trEnv))
                else:
                    ##TODO Test runner declared but does not exist.
                    pass

def isFileNameInItems(filename):
        registry = getTestRunnerRegistry()
        afn = op_realpath(filename)
        for item in registry:
            if op_realpath(item.filename) == afn:
                return True
        return False

def getItemByFileName(filename):
    registry = getTestRunnerRegistry()
    afn = op_realpath(filename)
    for item in registry:
        if afn == op_realpath(item.filename):
            return item
    return None

def itemsByWildcards(wcString=None):
        """Returns all items that are matching wcString in a common wildcards
        style. wcString is supposed to have a form of
        "<path-to-test-runner>:<test-name>", where
        1) each of two parts could be omitted;
        2) wildcards can pass through a colon.

        Return type: dictionary (string to list mapping)
        Return value semantics: key is a matched test runner name, value is a
        list of matched tests. If value is an empty list, test runner matched
        totally.
        """
        if not wcString:
            return list()
        # Prepare regular expression from wcString
        if not wcString[0] in ".*^":
            regexString = '^'
        regexString = wcString                  \
                        .replace('.', r'\.')    \
                        .replace('?', '.?')     \
                        .replace('*', '.*')
        if not wcString[-1] in ".*$":
            regexString.append('$')
        pattern = re.compile('^' + regexString)
        result = dict();
        for item in getTestRunnerRegistry():
            # Check item's params
            if re.search(pattern, item.name):# name matched
                ##TODO handle
                pass
            elif re.search(pattern, item.dirname):# directory matched
                ##TODO directory matches
                pass
            elif re.search(pattern, op_basename(item.filename)):# base file name matched
                #TODO handle
                pass
            else: # checking "name:test", or "name.test", or "test" matched
                tests = list()
                for test in item.tests.keys():
                    if  re.search(pattern, item.name + '.' + test) or \
                        re.search(pattern, item.name + ':' + test) or \
                        re.search(pattern, test):
                            tests.append(test)
                if tests:
                    result[item.name] = tests
        return result
