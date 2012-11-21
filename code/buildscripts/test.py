#
# $Id: filename 3521 2010-11-25 00:31:22Z svn_username $
#
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
#
'''
This class is a simple TestRunner (of sorts) that is capable of managing pyunit
stuff, but also C++ and java tests as well as scripts and programs of arbitrary
types.
'''

import os
import sys
import subprocess
import traceback
import time
import re
import tempfile
import shutil
import random

# this file is always running out of code/buildscripts
buildscriptsdir = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
sys.path.insert(0, buildscriptsdir) # now all tests can import testsupport from buildscripts
from testsupport import TESTROOT, SBROOT
from sandbox import Sandbox
import component
import build
import timeout_monitor
from ioutil import WorkingDir, read_file
import nose
from psnoseplugin import PSNosePlugin
from psctest2noseplugin import PSCTest2NosePlugin
from ant.psjunit2noseplugin import PSJUnit2NosePlugin
import logging
import unittest
from cmake.CTestLoader import CTestTestLoader
from ant.JUnitTestLoader import JUnitTestLoader
import runnable_assembly
import global_vars
import interactive_test_setup as isetup
import test_setup as setup
from textui import ansi
from textui import colors
import controlVM
import filelock

log = logging.getLogger('nose')

SelectedTestLoader=None
SelectedCollectPlugin=PSCTest2NosePlugin

class _ProcAbort:
    def __init__(self):
        self.proc = None
    def __call__(self):
        if self.proc:
            self.proc.terminate()

_timeout_monitor = None
def _run_with_timeout(sb, pabrt, cmd):
    global _last_stdout_received
    err = 1
    try:
        proc = subprocess.Popen(cmd)
        _timeout_monitor.last_status = time.time()
        pabrt.proc = proc
        proc.wait()
        err = proc.returncode
    except:
        print(cmd)
        traceback.print_exc()
        err = 1
    return err

## TODO remove second argument after CppUnit test migration completed
def run_compiled_tests(sb, argv):
    '''
    Run all compiled tests
    '''
    errcode = 0
    bld = build.select_builder(sb)
    if ('--collect-only' not in argv) and bld and bld.has_compiled_tests():
        print('Running compiled tests...')
        if not bld.get_name() in ('cmake', 'ant'):
            errcode = 1
            build_py = SBROOT + '/code/buildscripts/build.py'
            if os.name == 'nt':
                build_py = build_py.replace('/', '\\')
            cmd = ['python', build_py ,'test']
            ##TODO move next "if" statement to JUnitTestLoader
            if quick and bld.get_build_file() == 'build.xml' and sb.is_experimental():
                cmd.append('--quick')

            # Initialize our state.
            start = time.time()
            sb.set_last_test_date(start)
            global _timeout_monitor
            _timeout_monitor = None
            try:
                # Start up a thread that will force us to exit if we hang.
                pabrt = _ProcAbort()
                _timeout_monitor = timeout_monitor.start(sb.get_test_timeout_seconds(), killfunc=pabrt)
                # Always run tests in alphabetical order, for predictability
                # and ease of explanation.
                errcode = _run_with_timeout(sb, pabrt, cmd)
            finally:
                if _timeout_monitor:
                    _timeout_monitor.stop()
            elapsed = time.time() - start
            sys.stdout.flush()
            print('\n'.ljust(71, '='))
            print('Ran compiled tests in %1.2f s\n' % elapsed)
    return errcode

def run_codescan_tests(sb, argv):
    '''
    Run all codescan tests
    '''
    errcode = 0
    start = time.time()
    global _timeout_monitor
    _timeout_monitor = None
    codescan_root = SBROOT + '/code/buildscripts/codescan/'
    codescan_tests = [ test for test in os.listdir(codescan_root) if test.startswith('check') and test.endswith('.py') ]
    skip_tests = [ 'check_keywords.py', 'check_ant_timeout.py', 'check_copyright.py', 'check_jsdebug.py' ]
    if os.name == 'nt':
        skip_tests.append('check_pep8.py')
    for test in codescan_tests:
        if test in skip_tests:
            continue
        if '--collect-only' in argv:
            print(test)
            continue
        cmd = ["python", os.path.join( codescan_root, test )]
        try:
            # start a thread that will force an exit if the test hangs
            pabrt = _ProcAbort()
            _timeout_monitor = timeout_monitor.start(sb.get_test_timeout_seconds(), killfunc=pabrt)
            test_errcode = _run_with_timeout(sb, pabrt, cmd)
            if test_errcode != 0:
                errcode += test_errcode
        finally:
            if _timeout_monitor:
                _timeout_monitor.stop()
        elapsed = time.time() - start
        sys.stdout.flush()
        print('\n'.ljust(71,'='))
        print('Ran %s test in %1.2f s\n' % (test, elapsed))
    return errcode


SPECIFIC_TESTS_SELECTED = False
class MyTestProgram(nose.core.TestProgram):
    def runTests(self):
        ##TODO Check second part of the condition in Windows
        if self.config.testNames and not self.config.testNames[0].endswith('/'):
            global SPECIFIC_TESTS_SELECTED
            SPECIFIC_TESTS_SELECTED = True
        else:
            print('Running all tests in %s' % TESTROOT)
            self.config.testNames = TESTROOT
        nose.core.TestProgram.runTests(self)


def _run_nose(*arg, **kw):
    ''' This was copied from nose to allow reconfiguring the tests before run'''

    """Collect and run tests, returning success or failure.

    The arguments to `run()` are the same as to `main()`:

    * module: All tests are in this module (default: None)
    * defaultTest: Tests to load (default: '.')
    * argv: Command line arguments (default: None; sys.argv is read)
    * testRunner: Test runner instance (default: None)
    * testLoader: Test loader instance (default: None)
    * env: Environment; ignored if config is provided (default: None;
      os.environ is read)
    * config: :class:`nose.config.Config` instance (default: None)
    * suite: Suite or list of tests to run (default: None). Passing a
      suite or lists of tests will bypass all test discovery and
      loading. *ALSO NOTE* that if you pass a unittest.TestSuite
      instance as the suite, context fixtures at the class, module and
      package level will not be used, and many plugin hooks will not
      be called. If you want normal nose behavior, either pass a list
      of tests, or a fully-configured :class:`nose.suite.ContextSuite`.
    * plugins: List of plugins to use; ignored if config is provided
      (default: load plugins with DefaultPluginManager)
    * addplugins: List of **extra** plugins to use. Pass a list of plugin
      instances in this argument to make custom plugins available while
      still using the DefaultPluginManager.

    With the exception that the ``exit`` argument is always set
    to False.
    """
    kw['exit'] = False
    global SelectedTestLoader
    return MyTestProgram(testLoader=SelectedTestLoader, *arg, **kw).success


def run_nose(argv):
    global SelectedCollectPlugin
    try:
        return _run_nose(argv=argv, addplugins=[
                         PSNosePlugin(),
                         SelectedCollectPlugin()
                         ])
    except SystemExit as e:
        return e.code
    except:
        traceback.print_exc()
        return False

def clean_tmp_folders():
    # On Windows machines especially, but also on Linux, our cleanup code may
    # not always work exactly as we'd like. This is because sometimes the OS
    # doesn't release handles as quickly as our cleanup code wants, sometimes
    # test harnesses are written improperly, sometimes programmers debug and
    # halt normal execution in unusual ways, etc. Over time, a lot of cruft can
    # accumulate in our temp directory due to regular testing. This function
    # clears out any test-related folders more than 24 hours old, so programmers
    # and maintainers of build machines don't have to worry about it.
    folder = tempfile.gettempdir()
    threshold = time.time() - 86400
    removed_count = 0
    for item in os.listdir(folder):
        if item.startswith('tmp') or (not item.startswith('.') and 'test' in item.lower()):
            path = os.path.join(folder, item)
            if os.path.isdir(path):
                x = os.stat(path)
                if x.st_mtime < threshold:
                    try:
                        shutil.rmtree(path)
                        removed_count += 1
                    except:
                        pass
    if removed_count:
        print('Removed %d old test-related folders from %s.' % (removed_count, folder))

def run_all(sb, argv):
    class Waiter:
        def __init__(self):
            # We introduce some variation here so multiple test processes won't
            # be likely to retry at the same instant.
            self.delay = 3 + (random.random() * 5)
            self.reported = None
            self.elapsed = 0
            self.fpath = os.path.join(tempfile.gettempdir(), 'global-test-lock.txt')
        def __call__(self):
            if self.reported is None or (time.time() - self.reported) > 300:
                sys.stdout.write('\nAs of %s, global test lock is owned by another test process:\n  ' % time.strftime('%c'))
                sys.stdout.write('\n  '.join(read_file(self.fpath).strip().split('\n')) + '\n')
                sys.stdout.flush()
                self.reported = time.time()
            else:
                sys.stdout.write("~")
                sys.stdout.flush()
            time.sleep(self.delay)
    # We use a global test lock so that different test commands cannot be run
    # in parallel. In theory, this should not be necessary -- but practice shows
    # that parallel tests are a bad idea. Some tests use system resources that
    # cannot be shared (e.g., ports). Others simply slow down the CPU or use
    # a lot of disk or RAM, and thus influence timing or other behaviors unduly.
    # While such tests should be refactored, we value accuracy/reproducibility
    # of test results more than the (potential) benefits of parallel testing,
    # so we force serial testing (at least across invocations of "sb test") here.
    sys.stdout.flush()
    waiter = Waiter()
    with filelock.FileLock(waiter.fpath, timeout=3600, delay=waiter) as flock:
        if waiter.reported:
            sys.stdout.write('\n')
            sys.stdout.flush()
        os.write(flock.fd, 'pid = %d\nstart time=%s\nsb=%s\nargs=%s' % (
            os.getpid(), time.strftime('%c'), sb.get_name(), ' '.join(sys.argv[1:])))
        global SelectedTestLoader, SelectedCollectPlugin
        try:
            runcodescan = True
            runcompiled = True
            bld = build.select_builder(sb)
            dirsToAdd = [sb.get_test_root()]
            if '--skip-codescan' in argv:
                while '--skip-codescan' in argv:
                    argv.remove( '--skip-codescan' )
                runcodescan = False
                print("Skipping codescan tests")
            if '--skip-compiled' in argv:
                while '--skip-compiled' in argv:
                    argv.remove('--skip-compiled')
                runcompiled = False
                print("Skipping compiled tests")
            if bld and bld.get_name() == 'cmake':
                argv.append('--compiled-root=%s' % sb.get_built_root())
                argv.append('--build-config=%s' % sb.get_build_config())
                argv.append('--where=%s' % sb.get_built_root())
                SelectedTestLoader = CTestTestLoader
                runcompiled = False
            elif bld and bld.get_name() == 'ant':
                argv.append('--compiled-root=%s' % sb.get_built_root())
                argv.append('--build-config=%s' % sb.get_build_config())
                argv.append('--where=%s' % sb.get_built_root())
                SelectedTestLoader = JUnitTestLoader
                SelectedCollectPlugin = PSJUnit2NosePlugin
                runcompiled = False

            # Do a little system maintenance. See func for comment about why.
            clean_tmp_folders()
            if global_vars.ea:
                pass #TODO clean out the appliance before we start running tests (this is already done between tests)
            nosetests_succeeded = run_nose(argv)

            compiled_test_error_code = 0
            codescan_test_error_code = 0
            ## TODO validate logic of the following "if" statement after compiled tests migration completed
            if runcompiled and not SPECIFIC_TESTS_SELECTED:
                os.chdir(sb.get_built_root())
                compiled_test_error_code = run_compiled_tests(sb, argv)
            if runcodescan and not SPECIFIC_TESTS_SELECTED:
                os.chdir(sb.get_built_root())
                codescan_test_error_code = run_codescan_tests(sb, argv)

            if not nosetests_succeeded:
                print ('\nERROR: tests had errors')
            if compiled_test_error_code != 0:
                print('\nERROR: compiled tests had errors')
            if codescan_test_error_code != 0:
                print('\nERROR: codescan tests had errors')
            result = compiled_test_error_code == 0 and codescan_test_error_code == 0 and nosetests_succeeded
            print('\nOverall result for test group - %s' % ('success' if result else 'failure'))
            return result
        except Exception, KeyboardInterrupt:
            traceback.print_exc()
            return False


def auto_test(sb, *args):
    err = 0
    print('Auto-testing whenever a build succeeds. Press CTRL+C to break.')
    try:
        while True:
            x = sb.get_last_test_date()
            y = sb.get_last_successful_build_date()
            if sb.get_last_test_date() < sb.get_last_successful_build_date():
                print('\n\nRetest started at %s...' % time.strftime('%I:%M %p'))
                run_all(sb, *args)
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    except:
        traceback.print_exc()
        err = 1
    return err

def normalize_test_path(arg):
    global SPECIFIC_TESTS_SELECTED
    if ':' in arg:
        path,test = arg.split(':',1)
        exists = os.path.exists(path)
        if exists or path.lower().endswith('.py'):
            SPECIFIC_TESTS_SELECTED = True
        if exists:
            # Handle highly-constrained case like "ss/license_test.py:LicenseTest.test_abc()"
            arg = ':'.join([os.path.abspath(path),test])
    else:
        exists = os.path.exists(arg)
        if exists or arg.lower().endswith('.py'):
            SPECIFIC_TESTS_SELECTED = True
        if exists:
            arg = os.path.abspath(arg)
    return arg

def normalize_path_args(argv):
    # This function is a bit of a kludge. What we'd like to do is find out
    # whether any of the args that were given by the user tell us to limit
    # the scope of discovery to a particular file or folder. The algorithm
    # implemented below is a good approximation but is not perfect.
    for i, arg in enumerate(argv):
        if i == 0:
            continue
        if arg.startswith('--'):
            if '=' in arg:
                opt,val = arg.split('=',1)
                argv[i] = '='.join([opt, normalize_test_path(val)])
        elif not arg.startswith('-'):
            argv[i] = normalize_test_path(arg)

def find_attr_arg_index(argv):
    for i in range(len(argv)):
        arg = argv[i]
        if arg == '-a' or arg == '--attr' or arg == '-A' or arg == '--eval-attr':
            return i

def get_modes(argv):
    modes = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--mode':
            argv[i] = None
            if i < len(argv) - 1:
                i += 1
                modes.append(argv[i])
                argv[i] = None
        elif arg == '-s':
            modes.append('stdout')
        i += 1
    argv = [a for a in argv if a is not None]
    return argv, modes

def could_have_tests(folder):
    items = os.listdir(folder)
    for item in items:
        if item not in ['.bzr', '.noseids', '.bzrignore']:
            path = os.path.join(folder, item)
            if os.path.isfile(path):
                if path.endswith('.py'):
                    return True
            else:
                return True

def getAdditionalArgs():
    '''add additional args as specified in the setup file'''
    if os.path.exists(os.path.join(TESTROOT, 'test_setup.xml')):
        isetup.filepath = os.path.join(TESTROOT, 'test_setup.xml')
    elif os.path.exists( os.path.expanduser(os.path.join('~', 'test_setup.xml')) ):
        isetup.filepath = os.path.expanduser(os.path.join('~', 'test_setup.xml'))
    else:
        return None
    return isetup.getArgs()

_MODE_FILE = '.test-modes'
quick = True
addingArgs = True

def main(argv):
    try:
        if '-h' in argv or '--help' in argv:
            return run_nose(argv)

        sb = Sandbox(SBROOT)

        #Add different options for using an appliance to run a test
        #more info about this can be found at
        #https:// ... /working-with-code/concepts/existing-appliances/run-tests-using-an-appliance # TODO refer to correct doc site
        #TODO move all the info below into the above website.
        #
        #This can
        #  speed things up when creating test
        #  Allows one to debug a test with a full appliance
        #  can be used to run tests with an appliance setup from a variety of repos
        #
        #This does not
        #  Replace the current system of running tests off of a sandbox as an appliance
        #  Does not leave behind it's files in a way that is easy to inspect
        #  Is not as reproducable of an environment
        #
        #The different options available are
        #  --setup sets up appliances to run tests off of, as well as some
        #  other setup options related to tests
        #  --sb-setup same as --setup, but is specific to the current sandbox
        #  --ip ipaddress --ea applianceName --user username --passwd password 
        #  accomplishes the same thing as --setup, but without going through the interactive prompts 
        #  --no-adding-args using --setup sb test can be set up to automatically add
        #  arguments when you run sb test, this prevents that from happening
        #  --app someApplianceName the setup file created with --setup or --sb-setup
        #  maps a user defined name with the appliance credentials. You can specify the name
        #  of one of those appliances to run test off of, or you can use a new name and 
        #  a brand new appliance will be created and used. You can then reuse that appliance as many times as desired
        #  --recreate-psa this can only be used with an appliance that was previously created
        #  with the above command. This restores the VM to a snapshot before any PSA RPMs were
        #  copied over and installed, the VM then refetches all of the necessary RPMs and
        #  installs them
        #  --branding someBranding --release release_branch these can be used to specify the branding and release
        #  branch when creating a PSA
        #  --repo this can be used instead of the above command to specify a different repo to install off of
        #  this command overrides any branding or release branches that were specified with the above command
        
        if '--setup' in argv:
            argv.remove('--setup')
            isetup.defaultSetup()
            print '\n'
            sys.exit('setup is complete')
        if '--sb-setup' in argv:
            argv.remove('--sb-setup')
            isetup.sbSetup()
            print '\n'
            sys.exit('setup is complete')
        global addingArgs
        if '--no-adding-args' in argv:
            addingArgs = False
            argv.remove('--no-adding-args')
        if addingArgs:
            argsToAdd = getAdditionalArgs()
            if argsToAdd:
                added = ''
                for arg in argsToAdd.split():
                    if arg not in argv:
                        added += ' ' + arg
                        argv.append(arg)
                if added:
                    print 'added', added
        global_vars.ea = None
        ip = None
        user = None
        passwd = None

        def retreiveAndDelArg(arg):
            for i, tryArg in enumerate(argv):
                if tryArg == arg:
                    ret = argv[i + 1]
                    del argv[i]
                    del argv[i]
            return ret

        branding = None
        release = None
        repo = None
        
        for i, arg in enumerate(argv):
            if arg == '--ea' or arg == '--psa':
                global_vars.ea = argv[i + 1]
                del argv[i]
                del argv[i]
        for i, arg in enumerate(argv):                
            if arg == '--ip' or arg == '--host':
                ip = argv[i + 1]
                del argv[i]
                del argv[i]
        for i, arg in enumerate(argv):       
            if arg == '--user':
                user = argv[i + 1]
                del argv[i]
                del argv[i]
        for i, arg in enumerate(argv):                
            if arg == '--passwd' or arg == '--password':
                passwd = argv[i + 1]
                del argv[i]
                del argv[i]

        for i, arg in enumerate(argv):
            if arg == '--release':
                release = argv[i + 1]
                del argv[i]
                del argv[i]
        for i, arg in enumerate(argv):
            if arg == '--branding':
                branding = argv[i + 1]
                del argv[i]
                del argv[i]
        for i, arg in enumerate(argv):
            if arg == '--repo':
                repo = argv[i + 1]
                del argv[i]
                del argv[i]
                
        if global_vars.ea and ip and user and passwd:
            setup.setSetupFile()
            setup.configAppliance(global_vars.ea, ip, user, passwd)
      
        #make sure we're creating a new PSA if an appliance sandbox type is being used
        if 'appliance' in sb.get_sandboxtype().get_variant():
            global_vars.ea = 'sb-test-appliance'
            if '--recreate-psa' not in argv and global_vars.ea in isetup.getAppliances():
                argv.append('--recreate-psa')
        isetup.setSetupFile()
        
        #create the appliance if the appliance doesn't exist in the setup file
        if global_vars.ea and global_vars.ea not in isetup.getAppliances():
            ansi.printc('Appliance %s does not exist, will attempt to create it in 5 seconds, push ctrl+c to cancel' % global_vars.ea, colors.WARNING_COLOR)
            time.sleep(5)
            ip = controlVM.createPSA(global_vars.ea, branding, release, repo)
            isetup.setAppliance(global_vars.ea, ip, 'root', 'psa')
        if '--recreate-psa' in argv:
            assert global_vars.ea, 'A VM must be specified with the --ea option to use the --recreate-psa option'
            controlVM.createPSA(global_vars.ea, branding, release, repo)
            argv.remove('--recreate-psa')
            

        # Support "modes" of tests. This allows us to run a set of tests in
        # more than one way -- for example, with valgrind enabled or disabled,
        # or with SearchServer using hs5 versus hs3.
        mode_path = os.path.join(sb.get_root(), _MODE_FILE)
        argv, modes = get_modes(argv)
        if os.path.isfile(mode_path):
            os.remove(mode_path)
        if modes:
            if modes[0].lower() != 'none':
                with open(mode_path, 'w') as f:
                    f.write(','.join(modes))

        attr_arg = find_attr_arg_index(argv)
        if len(modes) == 0 and attr_arg is None:
            modeattrs = sb.get_sandboxtype().get_test_mode_attrs_combo()
            result = 0
            runcompiled = True
            runcodescan = True
            for modeattr in modeattrs.split(';'):
                runnable_assembly._modes = None
                if modeattr.find(':') == -1:
                    if len(modeattr) > 3:
                        print('Skipping mode+attr combo "%s" because no separator ":" was found' % modeattr)
                    continue
                print('Running mode+attr combo: %s' % modeattr)
                mode, attrs = modeattr.split(':')
                argnew = argv[:]#copy argv  into argnew so we can append things for this round of tests
                argnew.insert(1, '-A')
                argnew.insert(2, attrs.strip())
                argnew.insert(3, '--mode')
                argnew.insert(4, mode.strip())
                if not runcompiled:
                    argnew.append('--skip-compiled')
                if not runcodescan:
                    argnew.append('--skip-codescan')
                result = result + main(argnew);
                runcompiled = False
                runcodescan = False
                print("")
            if result == 0:
                print("All test combos passed.")
            else:
                print("%s test combos failed!" % result)
            return result
        elif attr_arg is None:
            argv.insert(1, '-A')
            attrs = sb.get_sandboxtype().get_test_attrs()
            argv.insert(2, attrs)
            print('Running tests that are: %s.' % attrs)
        else:
            # If we're running interactive tests, make sure we're also
            # running with the -s switch.
            print('Running tests that are: %s.' % argv[attr_arg + 1])
            x = argv[attr_arg + 1].replace('not ', '!')
            if 'interactive' in x and '!interactive' not in x:
                if '-s' not in argv:
                    argv.insert(1, '-s')

        if len(modes) > 0:
            if modes[0].lower() == 'none':
                modes = []

        print('Running modes: %s' % ','.join(modes))
        # Make sure any path args in the arg list are fully normalized so they
        # are not sensitive to working directory changes.
        normalize_path_args(argv)

        # If we're collecting tests, it's virtually guaranteed that we want to
        # display the list...
        if '--collect-only' in argv:
            if '-v' not in argv and '--verbose' not in argv:
                verbosity_found = False
                for a in argv:
                    if a.startswith('--verbosity'):
                        verbosity_found = True
                        break
                if not verbosity_found:
                    argv.append('--verbose')

        # The "full" flag tells us to test all components in the sandbox,
        # instead of just the ones that are present in code form. If our scope
        # is full, no special effort is required. However, if our scope is
        # normal (quick), we have to tell nose which subdirs to use during
        # discovery.
        if not SPECIFIC_TESTS_SELECTED:
            global quick
            if '--full' in argv:
                argv.remove('--full')
                quick = False
            if '--quick' in argv:
                quick = True
                argv.remove('--quick')
            if quick:
                subset = []
                cr = sb.get_code_root()
                tr = sb.get_test_root()
                deps = [l.name for l in sb.get_cached_components()]
                for c in deps:
                    if component.CODE_ASPECT_NAME in sb.get_component_aspects(c) or c == sb.get_top_component():
                        component_test_root = sb.get_component_path(c, component.TEST_ASPECT_NAME)
                        if os.path.isdir(component_test_root):
                            if could_have_tests(component_test_root):
                                # Nose treats the first --where arg as a specifier
                                # of the working directory, and subsequent --where
                                # args as folders to use for discovery. So if we're
                                # going to add --where, we have to guarantee working
                                # dir is the first --where.
                                if not subset:
                                    argv.append('--where')
                                    argv.append(sb.get_root())
                                argv.append('--where')
                                argv.append(component_test_root)
                                subset.append(c)
                if subset:
                    print('Targeting: ' + ', '.join(subset) + ' (--full to override).')

        # The default behavior of the "sb test" command is supposed to be that
        # all tests get run, no matter what part of the sandbox you're in when
        # you invoke the command. This is consistent with "sb build", "sb publish",
        # and other sandbox-level commands. By default, nose will discover tests
        # beginning in the current working directory. We could override nose's
        # behavior by adding an extra arg that specifies that the scope for
        # discovery is the test root, but this would interfere with other logic
        # that we have, that disables the running of compiled tests when any
        # sort of constraining file/directory scope is given. So the simplest
        # way to achieve our goal is to temporarily set the current working dir
        # to the test root whenever no explicit scope is provided.
        try:
            restore_dir = os.getcwd()
            os.chdir(sb.get_test_root())    # always run tests with the current directory being the test root

            if '--with-id' not in argv:
                argv.insert(1, '--with-id')
            if '--auto' in argv:
                argv.remove('--auto')
                auto_test(sb, argv)
            else:
                if '--build-first' in argv:
                    sb.set_auto_build(True)
                    argv.remove('--build-first')
                    err = build.main([])
                    if err:
                        return err
                elif '--no-build-first' in argv:
                    sb.set_auto_build(False)
                    argv.remove('--no-build-first')
                # Before running tests, automatically build sandbox if it's out of date.
                # This allows testers to get a built sandbox and immediately run tests. It
                # also allows developers to repeatedly code and test without explicitly
                # rebuilding in between.
                elif sb.needs_build() and sb.get_auto_build():
                    print('''
    Built artifacts are out of date and will be refreshed before running tests.
    To run tests without automatic build as needed, use "--no-build-first".
                ''')
                    err = build.main([])
                    if err:
                        return err

                return 0 if run_all(sb, argv) else 1

        finally:
            os.chdir(restore_dir)
    except:
        print(traceback.print_exc())
        return 1 # make sure bad things show up as an error


if __name__ == '__main__':
    sys.exit(main(sys.argv))
