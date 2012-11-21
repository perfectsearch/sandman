#!/usr/bin/env python
#
# $Id: archive.py 9317 2011-06-10 02:09:04Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import optparse
import os
import sys
import subprocess
import shutil
import traceback
import time

import sandbox
import vcs
import component
import buildinfo
import ioutil
import aggregate_vcs
import dateutils
import timeout_monitor

DEFAULT_ARCHIVE_REPO = 'bzr+ssh://bazaar.example.com/reporoot/' # TODO KIM move to Conf file
#fix_ ODE_REVISION_FILE = 'code-revisions.txt'
MANIFEST = 'manifest.txt'

parser = optparse.OptionParser()
parser.add_option('--sandbox',
                  dest="sandbox",
                  help="override path to sandbox with publishable artifacts",
                  metavar="FLDR",
                  default=sandbox.current.get_root())
parser.add_option('--repo',
                  dest="repo",
                  help="override repo where artifacts should be checked in",
                  metavar="FLDR",
                  default=DEFAULT_ARCHIVE_REPO)
parser.add_option('-v', '--verbose', dest="verbose", action='store_true',
                  help="emit detailed messages", default=False)
parser.add_option('--dry-run',
                  dest="dry_run",
                  action="store_true",
                  help="do everything except checkin",
                  default=False)

_verbosity = 1
_timeout_monitor = None

def vprint(line, verbosity=1):
    if _timeout_monitor:
        _timeout_monitor.keep_alive()
    if verbosity <= _verbosity:
        print(line)

def bzr_node_needs_creating(url, bzr_cmd, txt_to_find):
    cmd = 'bzr %s %s' % (bzr_cmd, url)
    vprint(cmd, verbosity=2)
    proc = subprocess.Popen(cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    err = proc.wait()
    if err:
        return proc.stdout.read().lower().find('not a branch') > -1
    return txt_to_find not in proc.stdout.read().lower()

def create_branch(url, dry_run):
    cmd = 'bzr init --no-tree %s' % url
    vprint(cmd, verbosity=2)
    err = os.system(cmd)
    return err

# Make sure the local copy of the built root contains the very latest stuff,
# so that when we diff against our new output, the diff is comprehensive and
# accurate.
def convert_to_working_copy(sb, folder_to_publish, options):
    vprint('Converting %s to working copy.' % folder_to_publish, verbosity=1)
    use_master = False
    branch = '%s%s/%s/built.%s' % (options.repo, sb.get_branch(), sb.get_top_component(), #fix_julie repo structure knowledge
                                   sb.get_targeted_platform_variant())
    if bzr_node_needs_creating(branch, 'version-info', 'branch-nick:'):
        err = vcs.init(branch)
        if err:
            return err
        use_master = True
    tmpfldr = sb.get_built_root() + '.' + sb.get_top_component() + '~tmp~'
    wr = vcs.get_working_repository()
    err = wr.create_or_update_checkout(tmpfldr, sb.get_top_component(),
                                 'built.%s' % sb.get_targeted_platform_variant(),
                                 sb.get_branch(), revision=None,
                                 use_master=use_master)
    if err:
        return err
    try:
        for x in [x for x in os.listdir(tmpfldr) if x.startswith('.bzr')]:
            dest = os.path.join(folder_to_publish, x)
            if os.path.exists(dest):
                if os.path.isfile(dest):
                    os.remove(dest)
                else:
                    vprint('Error: %s already exists.' % dest)
                    return 1
            src = os.path.join(tmpfldr, x)
            os.rename(src, dest)
    finally:
        shutil.rmtree(tmpfldr)
    return 0

def checkin(sb, folder_to_publish, dry_run):
    msg = str(sb.get_build_id())
    if buildinfo.get_natural_platform_variant() != sb.get_targeted_platform_variant():
        msg += ' ' + sb.get_targeted_platform_variant()
    msg = '%s from %s' % (msg, str(buildinfo.BuildInfo()))
    cmd = 'bzr ci -m "%s"' % msg
    vprint(cmd, verbosity=1)
    err = 0
    if not dry_run:
        try:
            vcs.checkin(folder_to_publish, msg)
            push_loc = '%s%s/%s/built.%s' % (DEFAULT_ARCHIVE_REPO, sb.get_branch(),  # fix_julie repo structure knowledge
                                             sb.get_top_component(),
                                             sb.get_targeted_platform_variant())
            vcs.push(folder_to_publish, push_loc)
        except:
            txt = traceback.format_exc()
            if 'PointlessCommit' in txt:
                vprint('No changes need to be committed.', verbosity=1)
            else:
                raise
    return err

def apply_tag(sb, dry_run):
    tag = str(sb.get_build_id())
    vprint('Applying tag "%s" to entire sandbox.' % tag, verbosity=1)
    if dry_run:
        return
    err = 0
    for c in sb.get_cached_components():
        for a in sb.get_component_aspects(c.name):
            folder = sb.get_component_path(c.name, a)
            if vcs.folder_is_tied_to_vcs(folder):
                revid = None
                try:
                    vprint('Applying tag %s %s' % (c.get_name(), a), verbosity=1)
                    wr = vcs.get_working_repository()
                    if a == 'built':
                        a = "built.%s" % sb.get_targeted_platform_variant()
                    try:
                        revid = wr.get_local_revid(sb.get_branch(), c.get_name(), a)
                    except:
                        revid = None
                    wr.tag(tag, c.get_name(), a, sb.get_branch(), revisionid=revid)
                except:
                    txt = traceback.format_exc()
                    relative_path = folder[len(sb.get_root()):]
                    if 'TagAlreadyExists' in txt:
                        vprint('%s already tagged.' % relative_path, verbosity=2)
                    else:
                        vprint('Unable to tag %s.' % relative_path, verbosity=1)
                        if revid:
                            vprint('Untable to tag revid %s.' % revid, verbosity=1)
                        vprint('%s' % txt, verbosity=2)
    return err

def _bzr_status_is_interesting(status):
    return status != 'modified' and status != 'deleted'

def walktree(relative_path, folder_to_publish):
    files = []
    for f in os.listdir(os.path.join(folder_to_publish, relative_path)):
        path = (os.path.join(folder_to_publish, relative_path, f))
        if os.path.isdir(path):
            files += walktree(os.path.join(relative_path, f), folder_to_publish)
        else:
            files.append('%s,%s' % (os.path.join(relative_path, f), os.stat(path).st_size))
    return files

def add_manifest(sb, folder_to_publish):
    try:
        files = walktree('', folder_to_publish)
        fp = open(os.path.join(folder_to_publish, MANIFEST), 'w')
        fp.write('Last published on %s\n' % dateutils.format_standard_date_with_tz_offset(time.time()))
        fp.write('\n'.join(files))
        fp.close()
    except:
        return 1
    return 0

def add_new_files(sb, folder_to_publish):
    status = vcs.get_status(folder_to_publish, status_filter=_bzr_status_is_interesting)
    if 'conflicted' in status:
        vprint('Conflicting items; publish requires manual intervention.')
        vprint('  ' + '\n  '.join(status['conflicted']))
        return 1
    if 'unknown' in status:
        vprint('Adding new files.', verbosity=1)
        cmd = 'bzr add'
        vprint(cmd, verbosity=2)
        err = os.system(cmd)
        if err:
            return err
    return 0

def add_default_ignores():
    if not os.path.exists('.bzrignore'):
        vprint('Creating default .bzrignore.', verbosity=2)
        ignoreFile = open('.bzrignore', 'w')
        ignoreTypes = ['*.obj\n', '*.o\n', '*.pdb\n', '*.a\n', 'CMakeFiles\n']
        ignoreFile.writelines(ignoreTypes)
        ignoreFile.close()

def do_publish(sb, options):
    folder_to_publish = sb.get_built_root() + sb.get_top_component()
    try_again = 3
    try:
        with ioutil.WorkingDir(folder_to_publish) as td:
            try:
                add_default_ignores()
                err = add_manifest(sb, folder_to_publish)
                if err:
                    return err
                err = convert_to_working_copy(sb, folder_to_publish, options)
                if err:
                    return err
                err = add_new_files(sb, folder_to_publish)
                if err:
                    return err
                err = checkin(sb, folder_to_publish, options.dry_run)
                if err:
                    return err
                err = apply_tag(sb, options.dry_run)
                return err
            finally:
                    if not options.dry_run:
                        bzrfldr = os.path.join(folder_to_publish, vcs.HIDDEN_VCS_FOLDER)
                        if os.path.isdir(bzrfldr):
                            shutil.rmtree(bzrfldr)
        try_again = 0
    except:
        txt = traceback.format_exc()
        if 'ConnectionReset' in txt:
            print('Network connectivity problems. Trying again in 30 seconds.')
            time.sleep(30)
            try_again -= 1
        else:
            print(txt)
            return 1

def main(argv):
    # Read command line; set options.
    ( options, args ) = parser.parse_args(argv)
    sb = sandbox.Sandbox(options.sandbox)
    test_run = sb.get_last_test_date()
    '''if not test_run:
        print('Tests need to be run on %s before it can be published.' % sb.get_name())
        return 1'''
    if options.verbose or options.dry_run:
        global _verbosity
        _verbosity = 2
    with timeout_monitor.Monitor() as monitor:
        global _timeout_monitor
        _timeout_monitor = monitor
        # Do the main work of the script.
        try:
            err = do_publish(sb, options)
        except:
            traceback.print_exc()
            err = 1
    # Make sure we report an error if we didn't succeed.
    if err:
        vprint('\nPUBLISH FAILED\n')
    else:
        vprint('\nPUBLISH SUCCEEDED\n')
    return err

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

