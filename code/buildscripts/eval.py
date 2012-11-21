#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
#
# Evaluate a sandbox.

import os
import subprocess
import traceback
import optparse
import time
import StringIO
import re
import shutil

import sandbox
import build
import test
import publish
import buildinfo
import dateutils
import ioutil
import vcs
import aggregate_vcs

from vcs import BzrCommandError
from vcs import BranchInfo

from report.eval_summary import *
from report.dashboard import *

def _define_options():
    parser = optparse.OptionParser('Usage: %prog [options]\n\nEvaluate sandbox and record results.')
    parser.add_option('--sandbox', dest="sandbox",
                      help="path to sandbox to build",
                      metavar="FLDR", default=sandbox.current.get_root())
    parser.add_option('--no-update', dest="no_update", action='store_true', help="skip the update phase", default=False)
    parser.add_option('--log', dest="should_log", action='store_true', help="record output in log file instead of using stdout", default=False)
    parser.add_option('--report', metavar="true|false", dest="should_report", help="override dashboard reporting", default=None)
    parser.add_option('--dry-run', dest="dry_run", action='store_true', help="simulate and return success", default=False)
    parser.add_option('--build-timeout', dest="build_timeout", help="override timeout after which build should abort if no new text arrives on stdout",
                      metavar='SECS', default=None)
    parser.add_option('--test-timeout', dest="test_timeout", help="override timeout after which tests should abort if no new text arrives on stdout",
                      metavar='SECS', default=None)
    parser.add_option('--full', dest="full", action='store_true', help="Run tests for all components, not just those with code aspects.",
                      default=False)
    return parser

def update(sb, lock):
    lock.update('updating...')
    # TODO: add logging and timeout
    proc = subprocess.Popen('bzr sb update', shell=True)
    proc.communicate()
    proc.wait()
    return proc.returncode

def get_build_phase_args(argv, options):
    argv = argv[:]
    if options.dry_run:
        argv.append('--dry-run')
    if options.build_timeout:
        argv.extend(['--build-timeout', options.build_timeout])
    return argv

def get_test_phase_args(argv, options):
    argv = argv[:]
    #Need to talk to Julie
    #argv.append('--no-auto-build')
    if options.dry_run:
        argv.append('--dry-run')
    if options.test_timeout:
        argv.extend(['--test-timeout', options.test_timeout])
    if options.full:
        argv.append('--full')
    return argv

def report(sb, state):
    rr = sb.get_report_root()
    root = sb.get_root()
    need_checkin = vcs.folder_is_tied_to_vcs(rr)
    try:
        # Get latest version of reports so we are less likely to cause merge
        # conflicts.
        wr = vcs.get_working_repository()
        use_master = False
        if not need_checkin:
            url = os.path.join(wr.master_reporoot, sb.get_branch(), sb.get_top_component(), 'report', ). replace('\\', '/')
            publish.create_branch(url, False)
            use_master = True
        wr.create_or_update_checkout(rr, sb.get_top_component(), 'report', sb.get_branch(), None, use_master=use_master)
        need_checkin = vcs.folder_is_tied_to_vcs(rr)
        # Report our results.
        bi = buildinfo.BuildInfo()
        machineFolder = os.path.join(rr, bi.host).replace('\\', '/')
        summary = EvalSummary(sb.get_build_id(), sb.get_sandboxtype().get_style(), bi.host,
                              state.phase, state.reason, state.start_time,
                              state.timestamps, sb.get_targeted_platform_variant(),
                              bi.os, bi.bitness, bi.version)
        db = Dashboard(rr)
        db.add_summary(summary)
        if os.path.exists(os.path.join(root, 'eval-log.txt')):
            shutil.copy2(os.path.join(root, 'eval-log.txt'), machineFolder)
        # Check in our changes.
        if need_checkin:
            status = vcs.get_status(rr)
            if 'unknown' in status:
                vcs.add(rr)
            vcs.checkin(rr, msg="update dashboard", quiet_stderr=True)
            try:
                vcs.push(rr)
            except BzrCommandError, e:
                if 'diverged' in ("%s" % e):
                    print "\nAttemping to resolve diverged report aspect"
                    print "\nNuking report dir %s" % rr
                    if not ioutil.nuke(rr):
                        print "\nAuto resolving diverged report aspect failed!"

                    bi = BranchInfo(branchname=sb.get_branch(), componentname=sb.get_top_component(), aspectname='report')
                    aspectdir = bi.get_branchdir(wr.local_reporoot)
                    print "\nNuking report repo %s" % aspectdir
                    if not ioutil.nuke(aspectdir):
                        print "\nAuto resolving diverged report aspect failed!"

                    # Use the master because we have a problem here.
                    wr.create_local_branch(sb.get_top_component(), 'report', sb.get_branch(), use_master=True)
                    wr.create_or_update_checkout(rr, sb.get_top_component(), 'report', sb.get_branch(), None, use_master=True)

                    db = Dashboard(rr)
                    db.add_summary(summary)
                    if os.path.exists(os.path.join(root, 'eval-log.txt')):
                        shutil.copy2(os.path.join(root, 'eval-log.txt'), machineFolder)

                    status = vcs.get_status(rr)
                    if 'unknown' in status:
                        vcs.add(rr)
                    vcs.checkin(rr, msg="update dashboard", quiet_stderr=True)
                    vcs.push(rr)
                    print "\nAuto resolve diverged report aspect success!"
                else:
                    raise e
    except:
        traceback.print_exc()

class EvalState:
    '''Record info about eval.'''
    def __init__(self):
        self.start_time = time.time()
        self.timestamps = []
        self.reason = None
        self.phase = None
        self.err = 0

class Phase:
    '''Do housekeeping during eval.'''
    def __init__(self, state, phase_enum, lock):
        self.state = state
        self.phase_enum = phase_enum
        self.lock = lock
    def __enter__(self):
        self.state.phase = self.phase_enum
        phase_name = enum_to_str(EvalPhase, self.phase_enum)
        phase_name = phase_name[0].upper() + phase_name[1:].lower()
        self.lock.update(phase_name)
        #print('entering %s phase' % phase_name)
        self.state.reason = '%s failed.' % phase_name
        self.start_time = time.time()
    def __exit__(self, type, value, traceback):
        #print('exiting phase')
        ts = self.state.timestamps
        ts.append(time.time() - self.start_time)

_bool_true_pat = re.compile(r't(rue)?|y(es)?|-?1', re.IGNORECASE)
def _should_report(sb, options):
    if options.should_report != False:
        # If no reporting behavior was forced, then our default behavior is to
        # report in all continuous/official sandboxes, as well as an experimental
        # ones that are fully checked in. (The 'sb verify' command overrides this
        # to always disable reporting.)
        if options.should_report is None:
            if sb.get_sandboxtype().get_always_report():
                options.should_report = not aggregate_vcs.get_sandbox_status(sb)
            else:
                options.should_report = True
        else:
            options.should_report = bool(_bool_true_pat.match(options.should_report))
    return options.should_report

def evaluate(sb, options):
    state = EvalState()
    phase_argv = ['--sandbox', sb.get_root()]
    with ioutil.WorkingDir(sb.get_root()) as td:
        with sb.lock('eval') as lock:
            try:
                try:
                    if not options.no_update:
                        with Phase(state, EvalPhase.UPDATE, lock) as phase:
                            state.err = update(sb, lock)
                    if not state.err:
                        with Phase(state, EvalPhase.BUILD, lock) as phase:
                            argv = get_build_phase_args(phase_argv, options)
                            state.err = build.main(argv)
                    if not state.err:
                        with Phase(state, EvalPhase.TEST, lock) as phase:
                            argv = get_test_phase_args(["test"], options)
                            state.err = test.main(argv)
                    if (not state.err) and sb.get_sandboxtype().get_should_publish():
                        with Phase(state, EvalPhase.PUBLISH, lock) as phase:
                            state.err = publish.main(phase_argv)
                except:
                    txt = traceback.format_exc()
                    print(txt)
                    # It is possible for us to get an exception as we try to enter
                    # a phase (including the first one). In such a case, we need
                    # to work extra hard to help the user understand what's wrong.
                    txt = txt.replace('\r', '').replace('\n', '; ').replace(',', ' ')
                    state.reason = 'exception in build process itself: ' + txt
                    if not state.timestamps:
                        state.timestamps.append(time.time())
                        state.phase = EvalPhase.UPDATE
            finally:
                if os.path.exists(os.path.join(sb.get_root(), 'notify.txt')):
                    if (not sb.get_sandboxtype().get_notify_on_success()) and (not state.err):
                        os.remove('%snotify.txt' % sb.get_root())
                    else:
                        notify = open('%snotify.txt' % sb.get_root(), 'r')
                        emails = notify.read()
                        notify.close()
                        body = ''
                        if os.path.exists(os.path.join(sb.get_root(), 'eval-log.txt')):
                            body = os.path.join(sb.get_root(), 'eval-log.txt')
                        os.remove('%snotify.txt' % sb.get_root())
                        bi = buildinfo.BuildInfo()
                        if state.err:
                            status = 'Failed'
                        else:
                            status = 'Succeeded'
                        subject = '%s build of %s on %s %s.' % (sb.get_variant(), sb.get_top_component(), bi.host, status)
                        arguments = '--to %s --sender sadm --subject "%s" --host smtp.example.com --port 587' % (emails, subject) # TODO KIM TO CONF
                        arguments += ' --username buildmaster@example.com --password password' # TODO KIM TO CONF
                        if body:
                            arguments += ' --body "%s"' % body
                        os.system('python %s/buildscripts/mailout.py %s' % (sb.get_code_root(), arguments))
                if not state.err:
                    state.reason = ''
                if _should_report(sb, options):
                    report(sb, state)
                else:
                    print('Skipping report phase.')
    return state.err

if __name__ == '__main__':
    import sys
    parser = _define_options()
    options, args = parser.parse_args(sys.argv)
    try:
        sb = sandbox.create_from_within(options.sandbox)
        if not sb:
            print('%s does not appear to be inside a sandbox.' % os.path.abspath(options.sandbox))
            err = 1
        else:
            err = evaluate(sb, options)
    except:
        traceback.print_exc()
        err = 1
    sys.exit(err)

