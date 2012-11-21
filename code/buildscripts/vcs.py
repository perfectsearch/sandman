#
# Proprietary and confidential.
# Copyright 2011 Perfect Search Corporation.
# All rights reserved.
#
'''
    VCS Interface

    Manages a local VCS repository and also provides support for all other VCS
    operations used to create and maintain sandboxes for development work. It is
    expected to be the only module that interacts with the version control system.
'''

import os
import sys
import string
import subprocess
import StringIO
import tempfile
import ConfigParser
import traceback
import pprint
import re
from branchinfo import BranchInfo, BranchInfoCache
import ioutil

try:
    import bzrlib
except:
    # Work around some problems that mainly manifest in python debuggers
    # that may be running a different version of python from the one where
    # bzr is installed.
    if os.name == 'nt':
        sys.path.append('c:/Program Files (x86)/Bazaar/lib/library.zip')
    else:
        import platform
        if platform.uname()[0] == 'Darwin':
            for x in os.listdir('/Library/Python'):
                path = '/Library/Python/' + x + '/site-packages'
                if os.path.isdir(path + '/bzrlib'):
                    sys.path.insert(0, path)
                    break
    import bzrlib
from bzrlib.errors import DivergedBranches,BzrCommandError
from bzrlib.bzrdir import BzrDir
from bzrlib.trace import be_quiet
from bzrlib.builtins import *
from bzrlib.trace import enable_default_logging, be_quiet
try:
    enable_default_logging()
except:
    pass

bzrlib.initialize()

if os.name == 'nt':
    PRIVATE_VCS_FOLDER = os.path.join(os.getenv("HOMEDRIVE"), os.getenv("HOMEPATH"), 'APPDATA', 'Roaming', 'bazaar', '2.0')
else:
    PRIVATE_VCS_FOLDER = os.path.join(os.path.abspath(os.getenv("HOME")), '.bazaar')
VCS_CONF_FILE = 'ps-vcs-conf.txt'
VCS_CONF_PATH = os.path.join(PRIVATE_VCS_FOLDER, VCS_CONF_FILE)
SETTINGS_SECTION = 'settings'
MASTER_REPO_ROOT_KEY = 'master repo root'
SITE_REPO_ROOT_KEY = 'site repo root'
LOCAL_REPO_ROOT_KEY = 'local repo root'

def _run(command):
    """returns the output of running the command in a subprocess.
    Throws an exception if the command fails.
    """
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        output = process.communicate()[0]
        return output
    except:
        print(command)
        raise

class WorkingRepository:
    """
    Provides a means of interacting with a VCS to maintain a
    local copy of the VCS repository.
    """
    def _init(self, master_reporoot, local_reporoot, site_reporoot):
        """
        Usually not called publicly; see get_working_repository() instead.
        """
        if site_reporoot and site_reporoot.lower() != 'none' and self.repo_is_accessible(site_reporoot):
            self.source_reporoot = site_reporoot
        else:
            self.source_reporoot = None
            pass #print 'INFO: no accessible site repository'

        if self.repo_is_accessible( master_reporoot):
            self.master_reporoot = master_reporoot
            if not self.source_reporoot:
                self.source_reporoot = master_reporoot
        if not self.source_reporoot:
            print "INFO: Using local repository only. Remote repository is not accessible."
        self.local_reporoot = local_reporoot
        if not os.path.isdir(self.local_reporoot):
            os.makedirs(self.local_reporoot)
        self._localbranches = get_branches(self.local_reporoot, fast=True)
        self._sourcebranches = None

    def repo_is_accessible(self, reporoot):
        """Return True if the respository is accessible.
        It might not be accessible when the network is not connected.
        """
        return True #TODO

    def get_local_revid(self, branch, component, aspect):
        try:
            p = subprocess.Popen('bzr version-info %s' % BranchInfo(branch, component, aspect).get_branchdir(self.local_reporoot),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            stdout, stderr = p.communicate()
            err = p.returncode
            if err != 0:
                raise Exception()
            else:
                revid = 'none'
                for l in stdout.split('\n'):
                    if l.startswith('revision-id:'):
                        revid = l.split(':', 1)[1].strip()
                return revid
        except:
            raise Exception()

    def get_source_revid(self, branch, component, aspect):
        for b in self.sourcebranches:
            if b[0] == branch and b[1] == component and b[2] == aspect:
                return b[3]
        return None

    def normalize( self, component, aspect, branch, task=None):   # TODO handle task
        component = component.lower()
        branch = branch.lower()
        aspect = aspect.lower()
        try:
            for b, c, a, revid in self.branches:
                if c.lower() == component and a.lower().startswith(aspect) and b.lower() == branch:
                    return c, a, b, task
        except:
            traceback.print_exc()
        raise Exception('does not exist in repository: %s/%s/%s' % (branch, component, aspect))

    @property
    def localbranches(self):
        """return a list of all branches in the local repository as component, aspect, branch tuples"""
        return self._localbranches

    @property
    def sourcebranches(self):
        if self._sourcebranches is None:
            if self.source_reporoot:
                print '\nRetrieving branch information from %s ...' % self.source_reporoot
                self._sourcebranches = get_branches(self.source_reporoot)
            else:
                self._sourcebranches = []
        return self._sourcebranches

    def resetsourcebranches(self):
        self._sourcebranches = None

    @property
    def branches(self):
        """
        Return a list of all branches in the source repository and in the local repository.
        If the source repository is not available then the list will only contain local
        branches.
        """
        branches = self.sourcebranches
        branches_minus_revid = [b[:3] for b in branches]
        branches += [b for b in self.localbranches if not b[:3] in branches_minus_revid]
        branches.sort()
        return branches

    def tag(self, tag, component, aspect, branch, revisionid):
        bi = BranchInfo(branchname=branch, componentname=component, aspectname=aspect)
        cmd, out = _prep_cmd(cmd_tag())
        revision = None
        if revisionid:
            revision = bzrlib.option._parse_revision_str("revid:%s" % str(revisionid))
        return cmd.run(revision=revision, tag_name=tag, directory=bi.get_branchdir(self.master_reporoot))

    def tags(self, component, aspect, branch, reporoot=None, lastRevision=True):
        if reporoot == None:
            reporoot = self.master_reporoot
        revision = None
        if lastRevision:
            revision = bzrlib.option._parse_revision_str("last:1")
        bi = BranchInfo(branchname=branch, componentname=component, aspectname=aspect)
        cmd, out = _prep_cmd(cmd_tags())
        cmd.run(revision=revision, directory=bi.get_branchdir(reporoot))
        return out.getvalue().strip()

    def create_local_branch(self, component, aspect, branch, use_master):
        err = 0
        if not self.source_reporoot:
            return 1
        bi = BranchInfo(branchname=branch, componentname=component, aspectname=aspect)
        aspectdir = bi.get_branchdir(self.local_reporoot)
        if not os.path.isdir(os.path.dirname(aspectdir)):
            os.makedirs(os.path.dirname(aspectdir))
        if not os.path.isdir(aspectdir):
            if use_master:
                print '\nBranching %s into local repository from %s ...' % (bi.branchpath, self.master_reporoot)
            else:
                print '\nBranching %s into local repository from %s ...' % (bi.branchpath, self.source_reporoot)
            mstbr = bi.get_branchdir(self.master_reporoot)
            srcbr = bi.get_branchdir(self.source_reporoot)
            lclbr = bi.get_branchdir(self.local_reporoot)
            if use_master:
                self.branch(mstbr, lclbr, quiet=True, quiet_stderr=True)
            else:
                self.branch(srcbr, lclbr, quiet=True, quiet_stderr=True)
            with open(lclbr+'/.bzr/branch/branch.conf', 'w') as bconf:
                bconf.write('parent_location = %s\n' %mstbr)
                bconf.write('push_location = %s\n' % mstbr)
                bconf.write('submit_location = %s\n' % mstbr)
        return err

    def update_local_branch(self, component, aspect, branch):
        ''' update (pull) the local branch from the parent '''
        try:
            if self.source_reporoot:
                source_revid = self.get_source_revid(branch, component, aspect)
                local_revid = self.get_local_revid(branch, component, aspect)
                if source_revid != local_revid:
##                print 'source_revid', source_revid, 'local_revid', local_revid
##                from pprint import pprint
##                pprint(traceback.format_stack())
                    bi = BranchInfo(branchname=branch, componentname=component, aspectname=aspect)
                    branchdir = bi.get_branchdir(self.local_reporoot)
                    print '\nUpdating %s/%s/%s in local repository from %s ...' % (branch, component, aspect, self.source_reporoot)
                    return pull(branchdir, bi.get_branchdir(self.source_reporoot))
        except DivergedBranches, e:
            # Only throw this error in the case that the aspect is not report
            if aspect != 'report':
                raise e
        return 0

    def branch_is_local(self, branch, component, aspect):
        return (branch, component, aspect) in [(b,c,a) for b,c,a,revid in self.localbranches]

    def create_or_update_local_branch(self, component, aspect, branch, use_master=False):
        ''' create or verify that the local branch exists '''
        if not self.branch_is_local(branch, component, aspect):
            return self.create_local_branch(component, aspect, branch, use_master)
        else:
            return self.update_local_branch(component, aspect, branch)

    def already_checked_out(self, folder):
        '''Return True if the specified folder already has a bzr checkout in it.'''
        bzrfldr = os.path.join(folder, '.bzr')
        return os.path.isdir(bzrfldr)

    def checkout_branch(self, target_dir, component, aspect, branch, revision=None):
        """target_dir is the directory that will contain the new checkout.
        """
        return checkout(BranchInfo(branchname=branch, componentname=component, aspectname=aspect).get_branchdir(self.local_reporoot), target_dir)

    def create_or_update_checkout(self, target_dir, component, aspect, branch, revision, use_master=False):
        err = 0
        if self.branch_exists(component, aspect, branch):
            err = self.create_or_update_local_branch(component, aspect, branch, use_master)
            if self.already_checked_out(target_dir):
                if revision:
                    if revision != revno(target_dir):
                        err = err or os.rename(target_dir, target_dir + '.bak')
                        err = err or self.checkout_branch(target_dir, component, aspect, branch, revision)
                else:
                    err = err or update_checkout(target_dir)
            else:
                err = err or self.checkout_branch(target_dir, component, aspect, branch, revision)
        elif aspect != 'report':
            raise Exception('Branch does not exist %(branch)s %(component)s %(aspect)s.' % locals())
        return err

    def branch_exists(self, component, aspect, branch):
        """check to see if the branch exists in a accessible repository.
        The component, aspect and branch passed in as parameters must be normalized.
        """
        for b, c, a, revid in self.localbranches:
            if b == branch and c == component and a.startswith(aspect):
                return True
        for b, c, a, revid in self.branches:
            if b == branch and c == component and a.startswith(aspect):
                return True
        if self.master_reporoot != self.source_reporoot:
            for b, c, a, revid in get_branches(self.master_reporoot):
                if b == branch and c == component and a.startswith(aspect):
                    return True
        return False

    def get_file_contents(self, component, aspect, branch, filepath, revision=None):
        """return the contents of a specific file directly from the local repository without a working
        copy.
        """
        #TODO: fix to support revision and run in proc

        self.create_or_update_local_branch(component, aspect, branch)
        try:
            output = get_file_contents(self.local_reporoot, component, aspect, branch, filepath, revision)
            if output:
                return output
        except:
            pass
        raise Exception('Unable to cat file from local and remote repos: %s/%s/%s/%s' % (branch, component, aspect, filepath))
        #TODO: throw exception
##        from bzrlib.builtins import cmd_cat
##        import StringIO
##        out = StringIO.StringIO()
##        c = cmd_cat()
##        c.outf=out  # capture the output
##        c.run('main.cpp', directory='C:/users/julie/bzrshare/ps-share/PsHost/trunk')
##        out.seek(0) # reset the "file"

    def _create_repo(self, repo_dir):
        return init_repo(repo_dir)

    def branch(self, from_location, to_directory, revision=None, quiet=False, quiet_stderr=False, stacked=False): #fix_julie shouldn't need to_directory since it must be local repo
        cmd, out = _prep_cmd(cmd_branch())
        #print 'Creating local branch', to_directory
        with StderrSuppressor(quiet_stderr) as ss:
            cmd.run(from_location=from_location, to_location=to_directory, revision=revision, stacked=stacked, no_tree=True)
        repo, branch, comp, aspect = to_directory.rsplit('/', 3) #fix_julie repo structure
        self.branches.append((branch, comp, aspect, 'none'))
        if not quiet:
            print(out.getvalue())
        out.close() #fix_julie bad idea

def checkout(branch_location, to_location):
    cmd, out = _prep_cmd(cmd_checkout())
    err = cmd.run(branch_location=branch_location, to_location=to_location, lightweight=True)
    print(out.getvalue())
    out.close()
    return err

_wr = None
def get_working_repository():
    '''
    Return a WorkingRepository object that can be used for all vcs operations
    on the current machine.
    '''
    global _wr
    if not _wr:
        if not os.path.isfile(VCS_CONF_PATH):
            raise Exception('Conf file %s does not exist.' % VCS_CONF_PATH)
        conf = ConfigParser.ConfigParser()
        with open(VCS_CONF_PATH, 'r') as fp:
            conf.readfp(fp)
        wr = WorkingRepository()
        wr._init(conf.get(SETTINGS_SECTION, MASTER_REPO_ROOT_KEY),
            conf.get(SETTINGS_SECTION, LOCAL_REPO_ROOT_KEY),
            conf.get(SETTINGS_SECTION, SITE_REPO_ROOT_KEY))
        _wr = wr
    return _wr

def get_file_contents(reporoot, component, aspect, branch, filepath, revision=None):
    """return the contents of a specific file directly from the local repository without a working
    copy.
    """
    bi = BranchInfo(branchname=branch, componentname=component, aspectname=aspect)
    directory = bi.get_branchdir(reporoot)
    output, err= cat(filepath, revision=revision, directory=directory)
    if err:
        print output
    if not err:
        return output

def update_checkout(target_dir, revision=None, quiet_stderr=True):
    """Make sure the working copy in the sandbox is up-to-date with the repository.
    The local repository should already have been updated.
    """
    err = 0
    cmd, out = _prep_cmd(cmd_update())
    if revision:
        revision = bzrlib.option._parse_revision_str("revno:%s" % str(revision))
    with StderrSuppressor(quiet_stderr) as es:
        err = cmd.run(dir=target_dir, revision=revision)
    return err

class StderrSuppressor:
    def __init__(self, enabled=True):
        self.old_state = None
        self.stderr = None
        if enabled:
            self.stderr = StringIO.StringIO()
    def __enter__(self):
        if self.stderr:
            self.old_state = bzrlib.trace.push_log_file(self.stderr)
        return self
    def __exit__(self, type, value, traceback):
        if self.stderr:
            bzrlib.trace.pop_log_file(self.old_state)

_MAYBE_LBL_PAT = re.compile(r'^.*:\s*(\(.*\)\s*)?$')
_VALID_BZR_LBL_PAT = re.compile('^([a-z]+:\s*|pending merge tips:.*)$')
REGEX_TYPE = type(_MAYBE_LBL_PAT)
def get_status(folder, status_filter=None, revision=None):
    '''
    Return a dictionary describing notable status for files/folders beneath the
    specified folder.

    Dictionary format: key = status label (e.g., "modified", "added", etc.);
    value = list of filenames, relative to the specified folder.

    @param status_filter A function that decides whether a particular kind of
    status is interesting. You can use this to constrain the results only to
    a list of conflicting items, for example.
    '''
    cmd, out = _prep_cmd(cmd_status())
    if revision:
        revision = bzrlib.option._parse_revision_str("revno:%s" % str(revision))
    with StderrSuppressor() as es:
        cmd.run(file_list=[folder], revision=revision)
    output = out.getvalue()
    #print('output of bzr status = "%s"' % output)
    label = None
    items = {}
    for line in output.split('\n'):
        line = line.strip()
        if line:
            if _MAYBE_LBL_PAT.match(line):
                if _VALID_BZR_LBL_PAT.match(line):
                    i = line.find(':')
                    label = line[0:i]
                    if (status_filter is None) or (status_filter(label)):
                        items[label] = []
                    else:
                        label = None
                else:
                    label = None
            else:
                if label:
                    items[label].append(line.lstrip())
    return items

def _prep_cmd(cmd):
    out = StringIO.StringIO()
    out.encoding = 'utf-8'
    cmd.outf = out
    return cmd, out

def add(folder):
    cmd, out = _prep_cmd(cmd_add())
    cmd.run(file_list=[folder])
    output = out.getvalue().strip()
    out.close()
    return output

def checkin(folder, msg, quiet=False, quiet_stderr=False):
    if quiet:
        be_quiet()
    cmd, out = _prep_cmd(cmd_commit())
    with StderrSuppressor(quiet_stderr) as ss:
        cmd.run(message=msg, selected_list=[folder])
    return out.getvalue()

def get_branches(reporoot, fast=True, aspect=None, quiet=False):
    assert(fast) #fix_julie always use fast from now on because normal doesn't have revid
    cmd = 'bzr fast-branches %s' % reporoot
    output = _run(cmd)
    branches = []
    for x in output.split('\n'):
        if x.strip():
            parts = x.split()
            if len(parts) == 4:
                branches.append(parts)
            elif len(parts) == 3:
                parts.append('none')
                branches.append(parts)
            else:
                if not quiet:
                    print 'ERROR: invalid branch', x
                    pass  # this isn't a valid branch
    verifiedbranches = [(b,c,a,revid) for b,c,a,revid in branches if c and a and b and (aspect is None or a.startswith(aspect))]
    return verifiedbranches


def get_unique_branch_names(reporoot, fast=True):
    branches = get_branches(reporoot, fast)
    names = set()
    for b,c,a,revid in branches:
        names.add(b)
    return sorted(list(names))


def get_unique_component_names(reporoot, fast=True):
    branches = get_branches(reporoot, fast)
    names = set()
    for b,c,a,revid in branches:
        names.add(c)
    return sorted(list(names))


_USELESS_PUSH_OUTPUT = re.compile('Using saved \\w+ location[^\n]+', re.DOTALL | re.MULTILINE)
def push(folder, location=None, quiet=None, quiet_stderr=True, remember=False):
    cmd, out = _prep_cmd(cmd_push())
    with StderrSuppressor(quiet_stderr) as ss:
        if location is not None:
            cmd.run(directory=folder, location=location, remember=remember)
        else:
            cmd.run(directory=folder)
    if out.getvalue().find('ERROR') > -1:
        print folder
    txt = out.getvalue().strip()
    if quiet is None:
        if _USELESS_PUSH_OUTPUT.match(txt):
            return
    if quiet != False:
        print(txt)

_USELESS_PULL_OUTPUT = re.compile('Using saved \\w+ location[^\n]+\n[\r\n]*No revisions to pull.|No revisions to pull.', re.DOTALL | re.MULTILINE)
_BRANCHES_THAT_HAVE_BEEN_PULLED = []
def pull(to_directory, from_location=None, quiet=None, quiet_stderr=False):
    global _BRANCHES_THAT_HAVE_BEEN_PULLED

    if (to_directory, from_location) in _BRANCHES_THAT_HAVE_BEEN_PULLED:
        return
    _BRANCHES_THAT_HAVE_BEEN_PULLED.append((to_directory, from_location))
    cmd, out = _prep_cmd(cmd_pull())
    with StderrSuppressor(quiet_stderr) as ss:
        cmd.run(location=from_location, directory=to_directory)
    if out.getvalue().find('ERROR') > -1:
        pass
    txt = out.getvalue().strip()
    if quiet is None:
        if _USELESS_PULL_OUTPUT.match(txt):
            return
    if quiet != False:
        print(txt)

def merge(to_directory, from_location=None, quiet=False, quiet_stderr=False):
    err = 0
    cmd, out = _prep_cmd(cmd_merge())
    with StderrSuppressor(quiet_stderr) as ss:
        err = cmd.run(location=from_location, directory=to_directory)
    if not quiet:
        print(out.getvalue())
    return err

def revno(location, tree=False):
    be_quiet()
    cmd, out = _prep_cmd(cmd_revno())
    cmd.run(location=location, tree=tree)
    return out.getvalue().strip()

def tags(directory):
    cmd, out = _prep_cmd(cmd_tags())
    cmd.run(directory=directory)
    return out.getvalue().strip()

def info(location):
    cmd, out = _prep_cmd(cmd_info())
    cmd.run(location=location)
    return out.getvalue()

def missing(directory='.'):
    cmd, out = _prep_cmd(cmd_missing())
    cmd.run(directory=directory)
    return out.getvalue()

def tag(tag, directory='.'):
    cmd, out = _prep_cmd(cmd_tag())
    return cmd.run(tag_name=tag, directory=directory)

def init_repo(location, no_trees=True):
    cmd, out = _prep_cmd(cmd_init_repository())
    return cmd.run(location, no_trees=no_trees)

def revert(file_list, revision):
    cmd, out = _prep_cmd(cmd_revert())
    return cmd.run(revision=revision, file_list=file_list)

def init(location, no_tree=True):
    cmd, out = _prep_cmd(cmd_init())
    return cmd.run(location=location, no_tree=no_tree)

def cat(filename, revision=None, directory=None):
    err = 0
    cmd, out = _prep_cmd(cmd_cat())
    name_from_revision = None
    if revision:
        if not revision.isdigit():
            name_from_revision = revision
            revision = None
    err = cmd.run(filename, revision=revision, name_from_revision=name_from_revision, directory=directory)
    return out.getvalue(), err

def ls(path):
    err = 0
    cmd, out = _prep_cmd(cmd_ls())
    err = cmd.run(path=path)
    return out.getvalue(), err

def export(dest, source, revision=None):
    err = 0
    cmd, out = _prep_cmd(cmd_export())
    err = cmd.run(dest, branch_or_subdir=source, revision=revision)
    return err

HIDDEN_VCS_FOLDER = '.bzr'
def folder_is_tied_to_vcs(folder):
    fldr = os.path.join(folder, HIDDEN_VCS_FOLDER)
    return os.path.isdir(fldr)
