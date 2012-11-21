from __future__ import print_function
import os
import re
import subprocess
import traceback
from filelock import FileLock
import tempfile
import logging

## TODO fix_julie this belongs in the vcs lib component

REVID_NO_REVISIONS = 'no_revisions'
REVID_UNKNOWN = 'unknown'
REVID_RE = re.compile(r'.*-(\d{14})-.*')


def precondition(condition):
    assert(condition)  ## TODO fix_julie write precondition module


def revid_is_valid(revid):
    return revid is not None and ( revid == REVID_NO_REVISIONS or revid == REVID_UNKNOWN or revid.startswith('svn-') or REVID_RE.match(revid) )


def run(cmd):
    err = 1
    error_text = None
    stdout = None
    try:
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True)
        stdout, stderr = proc.communicate()
        err = proc.returncode
        if err:
            error_text = stderr
            if not error_text:
                error_text = 'Command returned %s.' % str(err)
    except KeyboardInterrupt:
        raise
    except:
        error_text = traceback.format_exc()
    if err:
        logging.error(error_text)
    return stdout, err


def make_valid_revid(revid):
    #TODO
    return revid


def get_revid(reporoot, branchpath):
    cmd = 'bzr log -l 1 --show-ids %s/%s' % (reporoot, branchpath)
    stdout, err = run(cmd)
    if err != 0:
        logging.error('unable to get revid for %s' % branchpath)
        return REVID_UNKNOWN
    if not stdout:
        return REVID_NO_REVISIONS

    revid = None
    for l in stdout.split('\n'):
        if l.startswith('revision-id:'):
            revid = l.split(':', 1)[1].strip()
            revid = make_valid_revid(revid)
    return revid


class BranchInfo:
    def __init__(self, branchname=None, componentname=None, aspectname=None, revid=None, branchpath=None):
        assert(branchpath or (branchname and componentname and aspectname))
        assert(not (branchpath and branchname))
        if branchpath:
            self.branchname, self.componentname, self.aspectname = self._split_branchpath(branchpath)
        else:
            self.branchname = branchname
            self.componentname = componentname
            self.aspectname = aspectname
        self.revid = revid if revid else REVID_UNKNOWN

    def get_branchdir(self, reporoot):
        return '/'.join((reporoot.replace('\\', '/'), self.branchpath))

    def __repr__(self):
        return '\t'.join((self.branchname, self.componentname, self.aspectname, self.revid))

    def key(self):
        return '\t'.join((self.branchname, self.componentname, self.aspectname))

    @property
    def branchpath(self):
        return '/'.join((self.branchname, self.componentname, self.aspectname))

    def _split_branchpath(self, branchpath):
        '''this is the one place that should know how to map branchpath to branch, component, aspect'''
        branch,component, aspect = branchpath.split('/')
        return branch, component, aspect


class BranchInfoCache:
    def __init__(self, reporoot, merging=False):
        precondition(os.path.isdir(reporoot))
        self.reporoot = os.path.abspath(reporoot)

        self.supportdir = os.path.join(self.reporoot, '.bzrsupport')
        if not os.path.isdir(self.supportdir):
            os.mkdir(self.supportdir)
            os.chmod(self.supportdir, 0777)

        self.cache_file = os.path.join(self.supportdir, 'branchinfocache')
        self.lock_file = os.path.join(self.supportdir, self.cache_file + '.lock')
        self.cache_new = self.cache_file + '.new'
        self.cache_bak = self.cache_file + '.bak'
        self._load()
        self._merging = merging
        if merging:
            self._changed = False  # only used for merge_ methods

    def get_branchinfo(self, branchname, componentname, aspectname):
        for bi in self.branchinfos:
            if bi.branchname == branchname and bi.componentname == componentname and bi.aspectname == aspectname:
                return bi

    def get_revid(self, branchname, componentname, aspectname):
        bi = self.get_branchinfo(branchname, componentname, aspectname)
        return bi.revid if bi else REVID_UNKNOWN

    def _save_update(self, bi):
        precondition(not self._merging)
        updatefile = None
        updatedir='/reporoot/.bzrsupport/branchcacheupdates'
        if not os.path.isdir(updatedir):
            os.mkdir(updatedir)
        with tempfile.NamedTemporaryFile(delete=False, dir=updatedir) as f:
            updatefile = f.name
            f.write(str(bi) + '\n')
        os.chmod(updatefile, 0666)
        os.rename(updatefile, updatefile + '.ready')    

    @property
    def changed(self):
        precondition(self._merging)
        return self._changed

    def update(self, branchname, componentname, aspectname, newrevid):
        precondition(not self._merging)
        # the adding get null: for revid from bzr when there are no revisions
        if newrevid == 'null:':
            newrevid = REVID_NO_REVISIONS
        if not revid_is_valid(newrevid):
            newrevid = REVID_UNKNOWN
        bi = self.get_branchinfo(branchname, componentname, aspectname)
        if bi:
            if newrevid != bi.revid: #get_revision_date(newrevid) > get_revision_date(bi.revid):
        #            print('updating', branchname, componentname, aspectname, bi.revid, 'to', newrevid)
                bi.revid = newrevid
                self._save_update(bi) 
        else:
            bi = BranchInfo(branchname, componentname, aspectname, newrevid)
            self.branchinfos.append(bi)
            self._save_update(bi)

    @property
    def branch_names(self):
        pass

    @property
    def component_names(self, branchname=None):
        pass

    @property
    def aspect_names(self, branchname=None, componentName=None):
        pass

    def _load(self):
        if os.path.isfile(self.cache_file):
            with open(self.cache_file, 'r') as f:
                self.branchinfos = [BranchInfo(*(l.split())) for l in f.readlines() if l.strip()]
        else:
            self.branchinfos = []
        for bi in self.branchinfos:
            if not revid_is_valid(bi.revid):
                revid = REVID_UNKNOWN

    def merge_remove(self, branchinfo):
        precondition(self._merging)
        print("REMOVING", branchinfo)
        ''' this should only be used from the merge update app'''
        self.branchinfos.remove(branchinfo)
        self._changed = True

    def merge_update(self, branchname, componentname, aspectname, newrevid):
        ''' this should only be used from the merge update app'''
        precondition(self._merging)
        bi = self.get_branchinfo(branchname, componentname, aspectname)
        if bi:
            if newrevid != bi.revid: # TODO  not get_revision_date(bi.revid) or get_revision_date(newrevid) > get_revision_date(bi.revid):
                #print('\t\tupdating', branchname, componentname, aspectname, bi.revid, 'to', newrevid)
                bi.revid = newrevid
                self._changed = True
        else:
            bi = BranchInfo(branchname, componentname, aspectname, newrevid)
            self.branchinfos.append(bi)
            self._changed = True

    def merge_save(self):
        precondition(self._merging)
        ''' this should only be used from the merge update app'''
        with FileLock(self.lock_file, 50):
            with open(self.cache_new, 'w') as f:
                for bi in sorted(self.branchinfos):
                    f.write(str(bi) + '\n')

            if os.path.isfile(self.cache_file):
                if os.path.isfile(self.cache_bak):
                    os.remove(self.cache_bak)
                    assert(not os.path.isfile(self.cache_bak))
                os.rename(self.cache_file, self.cache_bak)
            os.rename(self.cache_new, self.cache_file)
            os.chmod(self.cache_file, 0666)
            self._changed = False


def get_revision_date(revid):
    if revid in (REVID_UNKNOWN, REVID_NO_REVISIONS):
        return '' # earliest revision date possible
    m = REVID_RE.match(revid)
    if m:
        return m.group(1)
    raise Exception('invalid revid')



## TODO fix_julie knows about repo structure
def get_branch_paths_from_disk(reporoot):
    '''return a list of branchpaths, one for each component aspect found'''
    VALID_COMP_NAME_PAT = re.compile('[a-z][-_a-z0-9]*$', re.IGNORECASE)

    branchpaths = []
    # Look at all directories that appear to be components. Ignore ones that
    # clearly don't match our conventions.
    for branch in os.listdir(reporoot):
        if branch.startswith('.'):
            continue
        branchdir = os.path.join(reporoot, branch)
        if os.path.isdir(branchdir):
            cdirs = [c for c in os.listdir(branchdir) if VALID_COMP_NAME_PAT.match(c)]
            for component in cdirs:
                componentdir = os.path.join(branchdir, component)
                for aspect in os.listdir(componentdir):
                    if aspect.startswith('.'):
                        continue
                    aspectdir = os.path.join(componentdir, aspect)
                    if os.path.isdir(aspectdir) and os.path.isdir(os.path.join(aspectdir, '.bzr')):
                        branchpath = '/'.join((branch, component, aspect))
                        branchpaths.append(branchpath)
    return branchpaths
