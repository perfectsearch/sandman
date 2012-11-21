#!/usr/bin/env python
#
# $Id: mask_ip.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import os
import subprocess
import time
import inspect
import component
import ioutil
import timeout_monitor

class CleanExclusions(object):
    def __call__(self, file_path):
        return False

class BaseBuilder:
    '''
    Not directly used. However, the class is defined so its interface/
    methods can be documented.
    '''
    def get_build_file(self):
        '''
        Usually returns the _UBER_BUILD_SCRIPT define which is in ant is specified
        to 'build.xml' and cmake is specified to 'CMakeLists.txt'.  The path is
        not included using this method.
        '''
        return None
    def config(self, sb, options):
        '''
        Set options and possibly configure required build files before an
        actual build runs.

        @param prompt If False, configure needed state using default settings.
        All builders are required to support this mode, even if they just do so
        with a no-op. If True, then set build options with an interactive tool
        like cmake-gui. Makers that don't wish to support this mode should
        return False from has_prompted_config().
        '''
        pass
    def has_prompted_config(self):
        '''
        Does this builder offer a way to ask the user questions that will set
        build options?

        All builders must implement this method, but most will return False. If
        the builder returns True, then sadm will try to call configure(prompt=
        True) when a sandbox is inited for the first time, or when the user
        calls the "sadm config" command. In all other cases, sadm calls
        configure(prompt=False).

        (We say that sadm will *try* to call configure(prompt=True) because,
        even if a builder supports prompted config, sadm can be run in batch
        mode (e.g., with the --auto-confirm switch). For this reason, all
        builders must support unprompted mode with reasonable defaults.)
        '''
        return False
    def clean(self, built_root, clean_exclusions):
        '''
        This is the only clean method we will implement for any of the builders.
        But if the individual builders require a different set of files to be
        deleted inside of the built root then they can define a different 'skip'
        method.
        @param built_root The directory which holds all of the build generated
        files.
        @param clean_exclusions A function object which will be called for each
        file to decide whether to delete it or not.
        return 0 on success and 1 on failure
        '''
        return 0 if ioutil.nuke(built_root, contents_only=True, skip=clean_exclusions) else 1
    def get_clean_exclusions(self, sb):
        '''
        This is the default exclusion object which will be passed to the clean
        method for all builders except for the CMake builder.
        '''
        return CleanExclusions()
    def build(self, sb, options, targets):
        '''
        Make all of the specified targets.

        @param options Contains .verbose and .dry_run members that can be used
        to customize the build.

        Specific targets may vary from tool to tool and component to component,
        but the following targets must be supported by every maker:

        build  - Put all binaries and other build output into the build root.
                 This is the target that sadm calls in a verify sequence or
                 during continuous integration. The 'build' target does *all*
                 population of the build root, including the Dist and Install
                 folders.

        clean  - Remove generated build output from the build root. Should not
                 simply remove all files/folders, since some data in the build
                 root might come from sadm, bzr, or other tools, instead of
                 from the build process itself.

        The following targets are not required, but have a predefined meaning
        and should be used if appropriate:

        compile - Put binaries into component-specific folders under the build
                  root, but do not populate the install folder.

        pkg     - Build installers and put them in <built root>/<component>/install.
                  Usually depends on compile.

        doc     - Run javadoc, doxygen, or a similar tool.

        test    - Run compiled unit tests. (Some compiled tests might not be
                  unit tests [e.g., timing], and some unit tests might not be
                  compiled [e.g., in a python codebase], so this target is
                  not all-inclusive.)
        '''
        for t in targets:
            print('Making "%s" target...' % t)
        print('BUILD SUCCEEDED')
        return 0
    def supports(self, sb):
        '''
        Examine code root; if it appears to build with this tool, return True.

        @param sb A sandbox object.
        '''
        return False
    def priority(self):
        '''
        Determines the order in which this maker is asked whether it supports
        a particular coderoot. (Lower numbers come first.) Any maker that can
        determine its support with 100% confidence should have priority 1.
        Makers that only claim code if other builders have rejected it should have
        a larger number.
        '''
        return 1
    def has_compiled_tests(self):
        '''
        Return true if test process should call this builder to run compiled
        tests.
        '''
        return False
    def get_name(self):
        mod = inspect.getmodule(self)
        name = mod.__name__
        return name[name.rfind('.')+1:]

class _BuildKiller():
    def __init__(self, proc):
        self.proc = proc
    def __call__(self):
        proc.terminate()
        sys.exit(1)

def run_make_command(cmd, timeout, input=None, cwd=None):
    '''
    Run an arbitrary command to help with make responsibilities.
    @param timeout secs before cmd is considered hung
    @param input If provided, these bytes are stuffed into stdin on the
    child process.
    @param cwd If provided, use the specified working directory, and
    undo it after cmd runs.
    @return tuple (returncode, stdout)
    '''
    restore_dir = None
    if cwd:
        restore_dir = os.getcwd()
        os.chdir(cwd)
    monitor = None
    stdout = ''
    err = 0
    try:
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, shell=True, bufsize=1)
            monitor = timeout_monitor.start(timeout, killfunc=_BuildKiller(proc))
            monitor.last_status = time.time()
            while True:
                line = proc.stdout.readline()
                monitor.last_status = time.time()
                if not line:
                    proc.wait()
                    break
                print(line.rstrip())
                stdout += line
            err = proc.returncode
            if err:
                print('Error: build command "%s" returned %s.' % (cmd, str(err)))
        except:
            print(cmd)
            raise
    finally:
        if monitor:
            monitor.stop()
        if restore_dir:
            os.chdir(restore_dir)
    return err, stdout
