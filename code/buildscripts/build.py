#!/usr/bin/env python
#
# $Id: build.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import datetime
import optparse
import os
import shutil
import subprocess
import sys
import time
import traceback

import component
import runnable_assembly
import sandbox
import timeout_monitor

_META_DATA_TXT = 'metadata.txt'
_IF_TOP_DIR = '.if_top'

# I have to import builders two different ways to make the next 10 lines work.
# The first import is necessary because I can't reference builders.__all__
# without it. The second import is what brings the specific builders (ant,
# cmake, etc) into visibility without me having to enumerate all of them on
# separate import statements
from builders import __all__ as all_builders
#from builders import *
# Create a builder for each type of codebase.
_builders = {}
for builder in all_builders:
    command = \
'''
from builders.{0} import Builder as {0}_builder
new_builder = {0}_builder()
_builders[new_builder.get_name()] = new_builder
'''
    exec(command.format(builder))

def select_builder(sb):
    '''
    Find a Builder that supports the specified sandbox.
    '''
    x = _builders.values()[:]
    x.sort(cmp=lambda a,b: cmp(a.priority(), b.priority()))
    for b in x:
        if b.supports(sb):
            return b

class _SimulatedBuilder():
    def __init__(self, quiet=False):
        self.quiet = quiet
    def build(self, sb, options, targets):
        if not self.quiet:
            for t in targets:
                print('Building "{0}" target...'.format(t))
            print('BUILD SUCCEEDED')
        return 0
    def get_name(self):
        return 'simulated'

class BuilderOptions:
    def __init__(self, prompt=False, verbose=False, build_type=None, compiler=None, timeout=None, quick=False):
        self.prompt = prompt
        self.verbose = verbose
        self.build_type = build_type
        self.compiler = compiler
        self.timeout = timeout
        self.quick = quick

    def __str__(self):
        s = 'Prompt: {0}, Verbose: {1}, BuildType: {2}, Compiler: {3}, Timeout: {4}'.format \
            (self.prompt, self.verbose, self.build_type, self.compiler, self.timeout)
        return s

def _define_options():
    description = "Make specified targets using tools appropriate for codebase."
    usage = "Usage: %prog [options] [targets]"
    parser = optparse.OptionParser(usage=usage, description=description)

    parser.add_option('--sandbox', dest="sandbox", help="path to sandbox to build",
                      metavar="FLDR", default=sandbox.current.get_root())
    parser.add_option('--timeout', dest="timeout",
                      help="override timeout after which build should abort if no new text arrives on stdout",
                      type='int', metavar='SECS', default=None)
    parser.add_option('-d', '--dry-run', dest='dry_run', action='store_true', \
                      help="simulate build and return success", default=False)
    parser.add_option('-v', '--verbose', dest="verbose", action='store_true', \
                      help="emit detailed messages", default=False)
    parser.add_option('-p', '--prompt', dest="prompt", action='store_true', \
                      help="allow interacting with build tool.", default=False)
    parser.add_option('-r', '--assemble-only', dest='assemble_only', action='store_true', \
                      help="bypass building and just assemble the runnable aspect", default=False)
    parser.add_option('-b', '--builder', dest="builder", action="store", \
                      help="override auto-detected make tool", \
                      type='string', metavar='|'.join(_builders.keys()), default=None)
    parser.add_option('-t', '--build-type', dest="buildtype", action="store", \
                      help="specify the build type", \
                      type='string', metavar='Release|Debug', default=None)
    parser.add_option('-c', '--compiler', dest="compiler", action="store", \
                      help="override the default compiler (windows cmake specific)", \
                      type='string', default=None)
    parser.add_option('-a', '--auto', dest="auto", action="store_true", \
                      help="automatically rebuild whenever code updates", \
                      default=False)
    parser.add_option('--quick', dest="quick", action="store_true",
                      help="only run test if code aspect present",
                      default=False)
    return parser

def parse_args(argv):
    parser = _define_options()
    args_options, args = parser.parse_args(argv)
    if args_options.dry_run and args_options.auto:
        print('The --dry-run and --auto options are mutually exclusive.')
        sys.exit(1)
    if args_options.prompt and args_options.auto:
        print('The --prompt and --auto options are mutually exclusive.')
        sys.exit(1)

    # The user may have not been case sensitive on the key name!
    builder = None
    if args_options.builder:
        builders = [key for key in _builders.iterkeys() if key.lower() == args_options.builder.lower()]
        builder = builders[0] if len(builders) == 1 else None

        if not builder:
            raise optparse.OptionError('Invalid builder specified {0}'.format(args_options.builder), option.builder)

    build_type = None
    if args_options.buildtype and args_options.buildtype.capitalize() in ['Release', 'Debug']:
        build_type = args_options.buildtype.capitalize()

    builder_options = BuilderOptions(prompt=args_options.prompt, verbose=args_options.verbose,
                                     build_type=build_type, compiler=args_options.compiler, \
                                     timeout=args_options.timeout)
    return args, args_options, builder, builder_options

def copy_required_built_files(sb):
    component_built_dir = os.path.join(sb.get_built_root(), sb.get_top_component())
    component_code_dir = os.path.join(sb.get_code_root(), sb.get_top_component())

    # Ensure that the component directory exists
    if not os.path.isdir(component_built_dir):
        os.makedirs(component_built_dir)

    code_meta = os.path.join(component_code_dir, _META_DATA_TXT)
    built_meta = os.path.join(component_built_dir, _META_DATA_TXT)
    if os.path.isfile(code_meta):
        # If the destination exists then delete it
        if os.path.isfile(built_meta):
            os.remove(built_meta)
        # Copy from the code aspect to the built aspect
        shutil.copy2(code_meta, built_meta)

    code_if_top = os.path.join(component_code_dir, _IF_TOP_DIR)
    built_if_top = os.path.join(component_built_dir, _IF_TOP_DIR)
    if os.path.isdir(code_if_top):
        # If the destination exists then delete it
        if os.path.isdir(built_if_top):
            shutil.rmtree(built_if_top)
        # Copy from the code aspect to the built aspect
        shutil.copytree(code_if_top, built_if_top)

def assemble_run(sb):
    print('Assembling run/...')
    err = 0
    try:
        try:
            sbr = sb.get_root()
            top = sb.get_top_component()
            assemble_script = sb.get_iftop_folder_path() + 'assemble_run.py'
            built_path = sb.get_component_path(top, component.BUILT_ASPECT_NAME)
            if os.path.exists(assemble_script):
                runnable_assembly.assemble_custom(top, sb)
            else:
                print('    {0} does not exist. Copying {1} instead.'.format(
                    assemble_script,#[len(sbr):],
                    built_path[len(sbr):]))
                runnable_assembly.assemble_default(top, sb)
        except:
            # Make sure our finally block reports outcome.
            err = 1
            raise
    finally:
        if err:
            print('... FAILED')
        else:
            print('... OK')
    return err

def do_build(sb, args_options, args, builder, builder_options):
    err = 0
    try:
        build_date = time.time()
        # Start up a thread that will force us to exit if we hang.
        if builder_options.timeout is not None:
            sb.set_build_timeout_seconds(int(builder_options.timeout), persist=False)
        global _timeout_monitor
        _timeout_monitor = timeout_monitor.start(sb.get_build_timeout_seconds())
        try:
            err = 0
            configuring = 'config' in args
            building = bool([x for x in args if x.startswith('build')])
            if not configuring:
                # Always call the script builder, even for sandboxes that are driven
                # by ant, cmake, etc. This will allow us to build the buildscripts
                # component and any other components that just contain script, like
                # python components, php components, pure html+javascript, etc.
                if builder.get_name() not in ['script', 'simulated'] and not args_options.assemble_only:
                    err = _builders['script'].build(sb, builder_options, args)
            if not err:
                if not args_options.assemble_only:
                    copy_required_built_files(sb)
                    if 'clean' in args:
                        err = builder.clean(sb.get_built_root(), builder.get_clean_exclusions(sb))
                        args.remove('clean')
                    if not err and len(args) > 0:
                        if building:
                            sb.set_last_build_date(build_date)
                        err = builder.build(sb, builder_options, args)
                if not err and building:
                    # Always generate the runnable aspect for the sandbox. We do
                    # this outside of the main build tool because logic to create
                    # runnable aspects doesn't need to vary from code type to code
                    # type; it's always a bunch of file copies.
                    err = assemble_run(sb)
        finally:
            _timeout_monitor.stop()
        if not err:
            sb.set_last_successful_build_date(build_date)
    except:
        err = 1
        traceback.print_exc()
    return err

def auto_build(sb, args_options, args, builder, builder_options):
    err = 0
    print('Auto-building whenever code changes. Press CTRL+C to break.')
    try:
        while True:
            if sb.needs_build():
                print('\n\nRebuild started at {0:%I:%M %p}...'.format(datetime.datetime.now()))
                do_build(sb, args_options, args, builder, builder_options)
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    except:
        traceback.print_exc()
        err = 1
    return err

def main(argv):
    err = 0

    args, args_options, builder, builder_options = parse_args(argv)
    sb = sandbox.create_from_within(args_options.sandbox)
    # Is this a buildable sandbox?
    if component.CODE_ASPECT_NAME not in sb.get_component_aspects(sb.get_top_component()):
        builder = _SimulatedBuilder(True)
    else:
        if not builder_options.build_type:
            builder_options.build_type = sb.get_build_config()
        else:
            sb.set_build_config(builder_options.build_type)
        builder_options.quick = args_options.quick

        args_options.assemble_only = args_options.assemble_only and os.path.isdir(sb.get_built_root())

        if args_options.dry_run:
            builder = _SimulatedBuilder()
        else:
            # If cmdline specified a builder name, look up the corresponding object.
            # Otherwise, select default one.
            if builder:
                builder = _builders[builder]
            else:
                builder = select_builder(sb)
                if not builder:
                    if not os.path.isdir(sb.get_code_root()):
                        # User has requested a built sandbox -- now requesting that it be runnable!
                        args_options.assemble_only = True
                    else:
                        print('No build tool supports {0}.'.format(sb.get_code_root()))
                        return 2
        print('Using {0} as build tool.'.format(builder.get_name()))

    if not args:
        args = ['build']

    if args_options.auto:
        if sb.get_component_reused_aspect(sb.get_top_component()) != component.CODE_ASPECT_NAME:
            print("Can't auto-build if top component is pre-built.")
            err = 1
        else:
            auto_build(sb, args_options, args, builder, builder_options)
    else:
        err = do_build(sb, args_options, args, builder, builder_options)
    return err

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
