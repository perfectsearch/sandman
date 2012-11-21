#!/usr/bin/env python
#
# $Id: sandbox.py 5794 2011-03-11 22:35:32Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
from __future__ import print_function

import os
import re
import ioutil
import ConfigParser
import time
import calendar
import subprocess
import inspect

import component
import buildinfo
import vcs
import dateutils
import check_output
import check_tools
import metadata
import build_id
import uuid
import sandboxtype

_TPV = None
_SETTINGS_SECTION = 'settings'
_INFO_SECTION = 'info'
_BUILD_TIMEOUT_KEY = 'build timeout seconds'
_TEST_TIMEOUT_KEY = 'test timeout seconds'
_PLATFORM_VARIANT_KEY = 'targeted platform'
_LAST_BUILD_DATE_KEY = 'last build date'
_LAST_SKIP_BUILD_DATE_KEY = 'last skip date'
_LAST_SUCCESSFUL_BUILD_DATE_KEY = 'last successful build date'
_LAST_TEST_DATE_KEY = 'last test date'
_BUILD_CONFIG = 'build config'
_AUTO_BUILD = 'auto build'

_STANDARD_NAME_PAT = re.compile(r'^([^.]+)\.(.+)\.([^.]+)$', re.IGNORECASE)
_LOCK_FILE = 'lock'
_PID_PAT = re.compile(r'\Wpid\s*=\s*(\d+)', re.IGNORECASE)

_CODEROOT = component.CODE_ASPECT_NAME + '/'
_BUILTROOT = component.BUILT_ASPECT_NAME + '/'
_TESTROOT = component.TEST_ASPECT_NAME + '/'
_RUNROOT = component.RUNNABLE_ASPECT_NAME + '/'
_REPORTROOT = component.REPORT_ASPECT_NAME + '/'
_CONF = 'sandbox.conf'
EVAL_LOG = 'eval-log.txt'

_BOOL_TRUE_PAT = re.compile('t(rue)?|y(es)?|on|-?1|enabled?')
def _text_to_bool(txt):
    if txt:
        txt = txt.strip().lower()
        return 'yt1'.find(txt[0]) > -1
    return txt

def get_task_name_validation_error(proposed):
    '''
    Return None if the proposed task name satisfies our naming convention, or a
    string describing problem otherwise.

    Currently, our constraints require the task name to start with a letter
    and be followed by any sequence of letters, digits, underscores, or hyphens
    --but must end with alphanum. The dot, @, ~, and other punctuation chars
    are not allowed.
    '''
    err = component.get_component_name_validation_error(proposed)
    if err:
        err = err.replace('Component', 'Task')
        err = err.replace('component', 'task')
    return err

def list(within):
    '''
    Return a list of Sandbox objects that are subdirectories of the specified
    container folder.
    '''
    items = []
    if os.path.isdir(within):
        likely = [os.path.join(within, x) for x in os.listdir(within)
                  if _STANDARD_NAME_PAT.match(x)]
        items = [Sandbox(x) for x in likely if os.path.isdir(x)]
        items.sort()
    return items

def find_root_from_within(path):
    '''
    Find the absolute path to the root of a sandbox from any file or folder
    inside a sandbox, no matter how deeply nested. Return the path prefix that
    identifies the root, or None if path doesn't look like it's inside a sandbox.

    @param path A relative or absolute path, existing or proposed.
    '''
    path = ioutil.norm_seps(os.path.abspath(path), trailing=False)
    segments = path.split('/')
    i = len(segments) - 1
    while i >= 0:
        m = _STANDARD_NAME_PAT.match(segments[i])
        if m:
            return '/'.join(segments[0:i+1]) + '/'
        i -= 1

_ASPECTS_THAT_APPEAR_IN_COMPONENT_PATH = [component.CODE_ASPECT_NAME, component.TEST_ASPECT_NAME]
def find_component_from_within(path):
    '''
    Find the component that "owns" the data in a particular subtree, no matter
    how deeply nested. Return the component name, or None if path doesn't look
    like it's inside a component's stuff.

    @param path A relative or absolute path, existing or proposed.
    '''
    path = ioutil.norm_seps(os.path.abspath(path), trailing=False)
    sbroot = find_root_from_within(path)
    if sbroot:
        path = path[len(sbroot):]
        if path:
            segments = path.split('/')
            if len(segments) > 1:
                if segments[0].startswith(component.BUILT_ASPECT_NAME + '.') or (
                        segments[0] in _ASPECTS_THAT_APPEAR_IN_COMPONENT_PATH):
                    return segments[1]
            if segments and segments[0] in component.TOP_COMPONENT_ONLY_ASPECTS:
                segments = ioutil.norm_seps(sbroot, trailing=False).split('/')
                sbname = segments[-1]
                comp, br, task = split_name(sbname)
                return comp

_ASPECTS_THAT_APPEAR_IN_ASPECT_PATH = [component.CODE_ASPECT_NAME, component.TEST_ASPECT_NAME, component.RUNNABLE_ASPECT_NAME]
def find_aspect_from_within(path, with_suffix=False):
    '''
    Find an aspect name from any file or folder inside a sandbox, no matter how
    deeply nested. Return the aspect name or None if path doesn't look like
    it's inside an aspect.

    @param path A relative or absolute path, existing or proposed.
    @param with_suffix If True, the built aspect is returned with its tpv suffix
    (e.g., "built.linux_x86-64" instead of "built")
    '''
    path = ioutil.norm_seps(os.path.abspath(path), trailing=False)
    sbroot = find_root_from_within(path)
    if sbroot:
        path = path[len(sbroot):]
        if path:
            segments = path.split('/')
            if segments:
                if segments[0].startswith(component.BUILT_ASPECT_NAME + '.'):
                    if with_suffix:
                        return segments[0]
                    else:
                        return component.BUILT_ASPECT_NAME
                elif segments[0] in _ASPECTS_THAT_APPEAR_IN_ASPECT_PATH:
                    return segments[0]

def create_from_within(path):
    '''
    Create a sandbox object from anywhere inside its files and folders.
    '''
    root = find_root_from_within(path)
    if root:
        return Sandbox(root)

def layout(within, top, branch, variant):
    '''
    Create the skeleton of a sandbox's folder structure.

    @param within The path that contains all sandboxes. May or may not exist.
    @param top The name of the topmost component for the sandbox (e.g.,
           "searchserver")
    @param branch The name of the branch (e.g., "trunk").
    @param variant The name of the variant (e.g., "dev" or "official").
    '''
    sb = Sandbox(os.path.join(within, top + '.' + branch + '.' + variant))
    sb.layout()
    return sb

def split_name(name):
    '''
    Split a sandbox name into its 3 constituent pieces (component, branch, task).
    Return a 3-tuple. Raises SandboxNameError if name is invalid.
    '''
    m = _STANDARD_NAME_PAT.match(name)
    if not m:
        raise SandboxNameError(name)
    return m.group(1), m.group(2), m.group(3)

def _get_component_subdirs(root, excluding=None, bzr_only=True):
    '''
    Given a folder such as a code root, built root, or test root, find all
    subdirs that appear to contain components.
    @param excluding A list of component names that should not be returned.
    @param bzr_only If True, only consider component subdirs that have a
    relationship to bazaar.
    '''
    sdirs = []
    if os.path.isdir(root):
        sdirs = [sd for sd in ioutil.subdirs(root)]
        sdirs = [sd for sd in sdirs if not component.get_component_name_validation_error(sd)]
        if excluding:
            sdirs = [sd for sd in sdirs if sd not in excluding]
        if bzr_only:
            sdirs = [sd for sd in sdirs if os.path.isdir(os.path.join(root, sd, '.bzr'))]
    return sdirs

class SandboxError(Exception):
    '''
    Report problems with sandboxes.
    '''
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class SandboxNameError(SandboxError):
    '''
    Report problems with proposed names for sandboxes.
    '''
    def __init__(self, proposedName):
        SandboxError.__init__(self, 'Expected "%s" to follow standard component.branch.variant convention.' % proposedName)

class Sandbox:
    '''
    Manage the relative structure of folders and files that constitute
    a valid sandbox.
    '''
    def __init__(self, root):
        '''
        Create a Sandbox object that's tied (in theory) to the specified folder.
        The folder may or may not exist; it is not created by this call.

        @param root An absolute or relative path to an existing folder that
        constitutes a sandbox root.
        '''
        assert(not os.path.isfile(root))
        # First get fq path without trailing slash
        self._root = ioutil.norm_seps(os.path.abspath(root), trailing=False)
        # Last segment is the sandbox name; it can be split into its pieces with
        # a simple regex.
        self._name = self._root[self._root.rfind('/') + 1:]
        self._top, self._branch, self._variant = split_name(self._name)
        # Now put root in normal form (trailing slash).
        self._root += '/'
        # Init config object.
        self._cfg = ConfigParser.RawConfigParser()
        self._cfg.add_section('settings')
        self._cfg.defaults
        self._last_config_size = None
        self._last_config_time = None
        self._load_config()
        self._lock = None
        self._sandboxtype = sandboxtype.SandboxType(self)
    def __cmp__(self, rhs):
        return cmp(self.get_name().lower(), rhs.get_name().lower())
    def layout(self):
        '''
        Create the skeleton of a sandbox's folder structure.
        '''
        within = self.get_container()
        ancestorSandbox = find_root_from_within(within)
        if ancestorSandbox:
            raise SandboxError("%s is already a sandbox; can't create another inside it." % ancestorSandbox)
        def mkdir_if_needed(d):
            if not os.path.isdir(d):
                os.makedirs(d)
        mkdir_if_needed(self.get_code_root())
        mkdir_if_needed(self.get_built_root())
        mkdir_if_needed(self.get_test_root())
        mkdir_if_needed(self.get_run_root())
        mkdir_if_needed(self.get_report_root())
        self._save_config()
    def get_sandboxtype(self):
        return self._sandboxtype;
    def get_log_file_path(self):
        return self.get_root() + EVAL_LOG
    def get_dependencies_file_path(self):
        return self.get_root() + 'dependencies.txt'
    def lock(self, purpose, try_inherit_first=False):
        '''
        Get exclusive access to sandbox so it can't be busy doing things that
        could interfere with one another. Raise an exception if unable to get a
        lock. You should call unlock() in the finally portion of a try...finally
        block to release this lock.

        Return the lock object arbitrating access to this sandbox.
        '''
        if self._lock:
            raise LockError(self._get_lock_file())
        if try_inherit_first:
            self.try_to_inherit_lock(update_msg='%s began...' % purpose)
        if not self._lock:
            self._lock = Lock.acquire(self._get_lock_file(), purpose)
        return self._lock
    def update_lock(self, status):
        '''
        Prevent lock from expiring by writing a new status message to the lock
        file. In general, we want to be suspicious if we don't receive any
        status from the lock owner for 15 to 30 minutes, but for now, lock
        expiration is still an experimental concept, so if you don't call this
        method, you may still be okay.
        '''
        self._lock.update(status)
    def _get_lock_file(self):
        '''
        Return full path of the lock file that this sandbox uses.
        '''
        return os.path.join(self.get_root(), _LOCK_FILE)
    def get_lock_obj(self, try_to_inherit=False):
        '''
        Return lock file in active use by this sandbox, if any.

        @param try_to_inherit If False, caller must call try_to_inherit_lock()
        or lock() on a sandbox before the lock object will be anything other
        than None.
        '''
        if (not self._lock) and try_to_inherit:
            self.try_to_inherit_lock()
        return self._lock
    def is_locked(self):
        '''
        Return True if the sandbox is currently locked.
        '''
        return self.get_lock_obj(try_to_inherit=True)
    def lock_exists(self):
        '''
        Return True if there is any lock for the sandbox.
        '''
        return os.path.isfile(self._get_lock_file());
    def try_to_inherit_lock(self, update_msg=None):
        '''
        See if some other entity in the system has already locked the sandbox in
        a way that lets us participate. This is useful when sadm locks during an
        overall eval, and then the build or test phase of that eval wants to
        guarantee exclusive access; the sub-phase should try to inherit the lock
        instead of acquiring a new one.

        Return a lock object if one exists and is inheritable, or None if caller
        should use lock() to get a new, independent lock instead.
        '''
        if self._lock:
            raise LockError(self._get_lock_file())
        self._lock = Lock.inherit(self._get_lock_file(), update_msg=update_msg)
        return self._lock
    def unlock(self):
        '''
        Release lock on sandbox (if one exists and if that lock is truly owned
        by this sandbox instance instead of simply inherited).
        '''
        if self._lock:
            self._lock.release() # harmless if lock was inherited
            self._lock = None
    def _set_conf(self, section, key, value, persist=True):
        section_exists = self._cfg.has_section(section)
        if value is None:
            if not section_exists:
                return
            self._cfg.remove_option(section, key)
        else:
            if not section_exists:
                self._cfg.add_section(section)
            self._cfg.set(section, key, str(value))
        if persist:
            self._save_config()
    def _get_conf(self, section, key, default=None):
        # Check to see if we're out of date with what's on disk. The only reason
        # this can happen is if some other process wrote while our conf object
        # remained in memory. We always save immediately after every write, so
        # our own writes are never clobbered by someone else.
        self._load_config()
        if self._cfg.has_option(section, key):
            return self._cfg.get(section, key)
        return default
    def _get_date_conf(self, section, key, default=None):
        value = self._get_conf(section, key, default)
        if value:
            value = dateutils.parse_standard_date_with_tz_offset(value)
        return value
    def _set_date_conf(self, section, key, value):
        if value is not None:
            value = dateutils.format_standard_date_with_tz_offset(value)
        self._set_conf(section, key, value)
    def has_dashboard(self):
        db_file = self.get_report_root() + 'status-log.txt'
        return os.path.isfile(db_file)
    def get_sb_revid(self):
        try:
            p = subprocess.Popen('bzr version-info %s' % os.path.join(self.get_code_root(), self.get_top_component()),
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
    def get_build_id(self):
        '''
        Return a BuildID (named tuple with .component, .branch, .code_revno,
        and .test_revno) that can be used to uniquely identify this sandbox's
        state (in terms of what code and tests it contains) for build
        reproducibility.

        Build IDs are used to tag built artifacts and to coordinate test results
        across platforms. It consists of the name of the top-level component in
        the sandbox, its branch, plus the revno of the code and test aspects of
        that component. The format of build ids is documented on our build site
        (https:// ... /working-with-code) at #TODO Kim refer to correct doc site
        /overview-and-concepts/version-tags.

        Build ids are less useful when the top component aspect is built instead
        of code (as with test-only sandboxes), or when the sandbox is
        experimental and contains checkouts.
        '''
        top = self.get_top_component()
        aspects = self.get_component_aspects(top)
        if component.CODE_ASPECT_NAME in aspects:
            crev = int(vcs.revno(self.get_component_path(top, component.CODE_ASPECT_NAME)))
        else:
            crev = 0
        if component.TEST_ASPECT_NAME in aspects:
            trev = int(vcs.revno(self.get_component_path(top, component.TEST_ASPECT_NAME)))
        else:
            trev = 0
        date = dateutils.format_standard_date_with_tz_offset(time.time()).split('.')[0].strip()
        guid = str(uuid.uuid1())
        return build_id.BuildID(top, self.get_branch(), crev, trev, guid, date)
    def get_last_skip_build_date(self):
        '''
        Return the time (in seconds since epoch) when a build was skipped last
        began in this sandbox. If never, None is returned.
        '''
        return self._get_date_conf(_INFO_SECTION, _LAST_SKIP_BUILD_DATE_KEY)
    def set_last_skip_build_date(self, value=None):
        '''
        Set the time (in seconds since epoch) when a build was skipped last
        began in this sandbox.
        @param value If not specified, current time is assumed. To override, use
        seconds since epoch, datetime, or local time.struct_time as returned by
        time.localtime().
        '''
        if value is None:
            value = time.time()
        self._set_date_conf(_INFO_SECTION, _LAST_SKIP_BUILD_DATE_KEY, value)
    def get_last_successful_build_date(self):
        '''
        Return the time (in seconds since epoch) when a successful build last
        began in this sandbox. If never, None is returned.
        '''
        return self._get_date_conf(_INFO_SECTION, _LAST_SUCCESSFUL_BUILD_DATE_KEY)
    def set_last_successful_build_date(self, value=None):
        '''
        Set the time (in seconds since epoch) when a build that succeeded last
        began in this sandbox.
        @param value If not specified, current time is assumed. To override, use
        seconds since epoch, datetime, or local time.struct_time as returned by
        time.localtime().
        '''
        if value is None:
            value = time.time()
        self._set_date_conf(_INFO_SECTION, _LAST_SUCCESSFUL_BUILD_DATE_KEY, value)
    def get_last_build_date(self):
        '''
        Return the time (in seconds since epoch) when a build last began in this
        sandbox. Note that the build may not have succeeded (contrast
        get_last_successful_build_date()). If never, None is returned.
        '''
        return self._get_date_conf(_INFO_SECTION, _LAST_BUILD_DATE_KEY)
    def set_last_build_date(self, value=None):
        '''
        Set the time (in seconds since epoch) when a build last began in this
        sandbox. Note that the build may not have succeeded (contrast
        set_last_successful_build_date()).
        @param value If not specified, current time is assumed. To override, use
        seconds since epoch, datetime, or local time.struct_time as returned by
        time.localtime().
        '''
        if value is None:
            value = time.time()
        self._set_date_conf(_INFO_SECTION, _LAST_BUILD_DATE_KEY, value)
    def get_last_publish_status(self):
        '''
        Check to see if the last Publish succeeded.
        '''
        publishfailed = True;
        for line in open(self.get_log_file_path()):
            if "PUBLISH SUCCEEDED" in line:
                publishfailed = False

        return not publishfailed

    def get_last_test_date(self):
        '''
        Return the time (in seconds since epoch) when a test run last began in
        this sandbox. If never, None is returned.
        '''
        return self._get_date_conf(_INFO_SECTION, _LAST_TEST_DATE_KEY)
    def set_last_test_date(self, value=None):
        '''
        Set the time (in seconds since epoch) when a test run last began in this
        sandbox.
        @param value If not specified, current time is assumed. To override, use
        seconds since epoch, datetime, local time.struct_time as returned by
        time.localtime().
        '''
        if value is None:
            value = time.time()
        self._set_date_conf(_INFO_SECTION, _LAST_TEST_DATE_KEY, value)
    def get_last_code_date(self):
        '''
        Return the time (in seconds since epoch) when code was last modified in
        this sandbox. If code is pristine (hasn't changed from what's checked
        in), None is returned.
        '''
        when_since_epoch = 0
        cr = self.get_code_root()
        # I know I could do the list comprehensions below in a single step, but
        # I want to make this debuggable and do it in stages.
        code_components = os.listdir(cr)
        code_components = [cr + cc for cc in code_components]
        code_components = [cc for cc in code_components if os.path.isdir(cc + '/.bzr')]
        def potentially_changed_file(lbl):
            return lbl == 'modified' or lbl == 'unknown'
        for cc in code_components:
            status = vcs.get_status(cc, status_filter=potentially_changed_file)
            if status:
                for k in status.keys():
                    for m in status[k]:
                        try:
                            lastmod = os.stat(cc + '/' + m).st_mtime
                            if lastmod > when_since_epoch:
                                when_since_epoch = lastmod
                        except:
                            pass
        if not when_since_epoch:
            when_since_epoch = None
        return when_since_epoch
    def get_last_build_config(self):
        '''
        Return what the last build was done in this sandbox. If we did not support
        the Visual Studio IDE it would always match what was specified in the
        sandbox.conf. Unfortunately, users are able to open the IDE and easily
        switch whether they want a Release build or a Debug build. This method
        reports which build was done most recently.
        '''
        conf_setting = self._get_conf(_SETTINGS_SECTION, _BUILD_CONFIG, 'release')
        if os.name != 'nt':
            return conf_setting

        component_built_path = self.get_component_path(self._top, component.BUILT_ASPECT_NAME)
        if not os.path.isdir(component_built_path):
            return conf_setting

        release_dir = os.path.join(component_built_path, 'release')
        debug_dir = os.path.join(component_built_path, 'debug')

        if os.path.isdir(release_dir) and os.path.isdir(debug_dir):
            if os.path.getmtime(release_dir) < os.path.getmtime(debug_dir):
                self.set_build_config('debug')
                return 'debug'
            else:
                self.set_build_config('release')
                return 'release'
        elif os.path.isdir(release_dir) and not os.path.isdir(debug_dir):
            self.set_build_config('release')
            return 'release'
        elif not os.path.isdir(release_dir) and os.path.isdir(debug_dir):
            self.set_build_config('debug')
            return 'debug'
        else:
            return conf_setting
    def get_cached_components(self):
        '''
        Return a list of Component objects that describe the building blocks
        of the sandbox, as analyzed and cached the last time the sandbox was
        updated. Each object has a name, branch, revision, and aspect. The list
        is in inverse dependency order, meaning that the components that should
        be built first are at the top of the list, and the top component in the
        in the sandbox is at the bottom.
        '''
        try:
            lines = ioutil.read_file(self.get_dependencies_file_path())
            lines = [l.strip() for l in lines.split('\n') if l.strip() and l.find(':') > -1]
            cc = [component.parse_component_line(l, self.get_branch()) for l in lines if not l.startswith(';')]
            return cc
        except:
            pass
    def needs_build(self):
        '''
        Return true if the sandbox has never been built, or if it has code
        changes that are newer than its last build date.
        '''
        lbd = self.get_last_successful_build_date()
        #print('last build date = %s' % lbd)
        #print('last code date = %s' % self.get_last_code_date())
        if not lbd:
            return True
        return lbd < self.get_last_code_date()
    def get_required_tools(self, tool_types='build|test', targeted_platform_variant=None):
        '''
        Return a dict, indexed by tool type, where values are lists of tools
        required by this sandbox.
        @param targeted_platform_variant If None, the sandbox's active tpv
        is used as the platform on which the tools are required.
        '''
        if type(tool_types) != type([]):
            tool_types = tool_types.split('|')
        if not targeted_platform_variant:
            targeted_platform_variant = self.get_targeted_platform_variant()
        else:
            targeted_platform_variant = buildinfo.fuzzy_match_platform_variant(targeted_platform_variant)
        tdict = {}
        for ttype in tool_types:
            tdict[ttype] = []
        comps = self.get_cached_components()
        if comps:
            comps = [(c.name, c.reused_aspect) for c in comps]
        else:
            comps = self.get_on_disk_components()
            comps = [(c, self.get_component_reused_aspect(c)) for c in comps]
        for cc in comps:
            path = self.get_component_path(cc[0], cc[1])
            for ttype in tool_types:
                #print('checking %s for %s tools' % (path, ttype))
                section = metadata.get_section_info_from_disk('%s tools' % ttype, path)
                if section:
                    for tool, info in section.iteritems():
                        #print('found ' + str((tool, info)))
                        tdict[ttype].append(check_tools.ReqTool.from_pair(tool, info))
        for ttype in tdict:
            tdict[ttype] = check_tools.get_unique_tools_with_greatest_version(tdict[ttype])
        return tdict
    def check_tools(self, tool_types='build|test', targeted_platform_variant=None, quiet=False):
        tdict = self.get_required_tools(tool_types, targeted_platform_variant)
        #print('checking for ' + str(tdict))
        already_checked = []
        err = 0
        for ttype in tdict:
            check_this_time = [t for t in tdict[ttype] if t not in already_checked]
            if check_tools.check_tools(check_this_time, quiet=quiet):
                err = 1
            already_checked.extend(check_this_time)
        return err
    def get_component_reused_aspect(self, comp):
        '''
        How was the specified component in this sandbox included -- as code, or
        as built? (For developers, the top component being code is standard. For
        testers, the top component being built is common.)
        '''
        # Even when a component is included as code, it can still be present in
        # its built form, once the build has run. So testing for its presence in
        # code is the way to decided...
        if os.path.isdir(self.get_code_root() + comp):
            return 'code'
        return 'built'
    def get_targeted_platform_variant(self):
        '''
        Return the platform variant that's currently being targeted by this
        sandbox. This identifier (e.g., "linux_x86-64" or "win_32") is opaque
        to the build system, and does not obey any consistent rules across
        platforms.
        '''
        global _TPV
        tpv = self._get_conf(_SETTINGS_SECTION, _PLATFORM_VARIANT_KEY)
        if tpv is None:
            if _TPV is None:
                _TPV = buildinfo.get_natural_platform_variant()
            tpv = _TPV
        return tpv
    def set_targeted_platform_variant(self, value):
        self._set_conf(_SETTINGS_SECTION, _PLATFORM_VARIANT_KEY, value)
    def get_test_timeout_seconds(self):
        '''
        How many seconds should the sandbox wait, while testing, with stdout
        being idle, before concluding that the tests are hung?
        '''
        return int(self._get_conf(_SETTINGS_SECTION, _TEST_TIMEOUT_KEY, '3600'))
    def set_test_timeout_seconds(self, value, persist=True):
        if not value:
            value = 30
        else:
            value = int(value)
        self._set_conf(_SETTINGS_SECTION, _TEST_TIMEOUT_KEY, value)
    def get_build_timeout_seconds(self):
        '''
        For any given test subprocess, how many seconds should the sandbox wait
        with stdout being idle, before concluding that the build is hung?
        '''
        return int(self._get_conf(_SETTINGS_SECTION, _BUILD_TIMEOUT_KEY, '3600'))
    def set_build_timeout_seconds(self, value, persist=True):
        if not value:
            value = 3600
        else:
            value = int(value)
        self._set_conf(_SETTINGS_SECTION, _BUILD_TIMEOUT_KEY, value)
    def get_build_config(self):
        '''
        The build config setting is our attempt to record whether this sandbox is
        established to build Debug or Release.  The ways to modify this value is
        to either pass a -release or -debug to 'sadm init' or directly modify
        sandbox.conf and edit the 'build cfg = <cfg>' line or to pass a new config
        to the build.py script (which also means 'sb build') using
        --build-type <cfg>.
        '''
        return self._get_conf(_SETTINGS_SECTION, _BUILD_CONFIG, 'release')
    def set_build_config(self, value, persist=True):
        self._set_conf(_SETTINGS_SECTION, _BUILD_CONFIG, value, persist)
    def get_auto_build(self):
        return self._get_conf(_SETTINGS_SECTION, _AUTO_BUILD, True)
    def set_auto_build(self, value, persist=True):
        self._set_conf(_SETTINGS_SECTION, _AUTO_BUILD, value, persist)
    def get_container(self):
        '''
        Returns a fully qualified path to the folder that contains this sandbox,
        and possibly others that are siblings.
        '''
        return ioutil.norm_folder(os.path.abspath(self.get_root() + '..'))
    def get_root(self):
        '''
        Returns a fully qualified path to root folder for the current sandbox.
        All separators are forward slashes; ends with a trailing slash.
        '''
        return self._root
    def get_name(self):
        '''
        Returns the unique name of sandbox, consisting of its topmost component
        name, its branch, and its variant, in dotted notation.
        '''
        return self._name
    def get_code_root(self):
        '''
        Returns a fully qualified path to the code root folder for the current
        sandbox. All separators are forward slashes; ends with a trailing slash.
        This is the folder where all source code resides. Each component in
        the sandbox has a sub-folder that is a direct child of the code root.
        '''
        return self._root + _CODEROOT
    def get_built_root(self):
        '''
        Returns a fully qualified path to the built root folder for the current
        sandbox. All separators are forward slashes; ends with a trailing slash.
        This is the folder where all build artifacts reside. Most components in
        the sandbox build into a sub-folder that is a direct child of the
        built root.
        '''
        return self._root + _BUILTROOT[0:-1] + '.' + self.get_targeted_platform_variant() + '/'
    def get_test_root(self):
        '''
        Returns a fully qualified path to the test root folder for the current
        sandbox. All separators are forward slashes; ends with a trailing slash.
        This is the folder where all non-compiled tests (whether unit, system,
        or other) reside. Most components in the sandbox have corresponding
        tests in a sub-folder that is a direct child of the test root.
        '''
        return self._root + _TESTROOT
    def get_run_root(self):
        '''
        Returns a fully qualified path to the run root folder for the current
        sandbox. All separators are forward slashes; ends with a trailing slash.
        This is the folder where the product can be run for testing or debugging
        purposes without doing an install.
        '''
        return self._root + _RUNROOT
    def get_report_root(self):
        '''
        Returns a fully qualified path to the report root folder for the current
        sandbox. All separators are forward slashes; ends with a trailing slash.
        This is the folder where the top component's dashboard and build queue
        are persisted.
        '''
        return self._root + _REPORTROOT
    def get_iftop_folder_path(self):
        '''
        Returns the folder that contains auxiliary files to help the build
        system for this sandbox. Each component has such a folder, originally
        located at <code root>/<top component>/.if_top. If the top component
        is built, then it is relocated to <built root>/<top component>/.if_top.
        '''
        return self.get_component_path(self._top, self.get_component_reused_aspect(self._top)) + '.if_top/'
    def get_log_folder_path(self):
        '''
        Return the folder that contains logs of sandbox evaluation stuff.
        '''
        return self.get_root() + 'logs/'
    def get_top_component(self):
        '''
        Return the name of the topmost component in the sandbox's dependency
        hierarchy. This name is the first segment of the overall sandbox name.
        '''
        return self._top
    def get_branch(self):
        '''
        Return the name of the branch associated with the topmost component
        in the sandbox.
        '''
        return self._branch
    def get_variant(self):
        '''
        Return a user-defined name that describes the purpose and semantics of
        the sandbox. Common variant names include "dev", "continuous", and
        "official". Names with "32" and "64" in them govern the bitness of C++
        builds on Windows (where cross-compile is supported). Names containing
        key strings are mapped to formal semantics (anything with "continuous"
        --> continuous; anything with "official" or "nightly" or "daily" -->
        official). All other names imply experimental.
        '''
        return self._variant
    def remove(self):
        '''
        Remove all evidence that a sandbox ever existed.
        '''
        ioutil.nuke(self.get_root())
    def exists(self):
        '''
        Return True if sandbox folder is actually present on disk.
        '''
        return os.path.isdir(self.get_root())
    def get_component_path(self, comp, aspect):
        '''
        Get fully qualified path for a particular aspect of a component.
        This path may not exist, if a component does not (yet) particpate in the
        sandbox in the specified aspect. It is also possible that a particular
        component doesn't *have* the requested aspect (e.g., only the top-level
        component will have a runnable or report aspect). In these cases, None
        is returned.

        @param aspect One of component.CODE_ASPECT_NAME,
               component.BUILT_ASPECT_NAME, or component.TEST_ASPECT_NAME -- or
               "built." + a targeted platform variant.
        '''
        if (aspect not in component.ASPECT_BRANCH_NAMES) and (aspect != 'built'):
            raise Exception('Unrecognized aspect: %s' % aspect)
        if aspect in component.TOP_COMPONENT_ONLY_ASPECTS:
            if comp == self.get_top_component():
                return self.get_root() + aspect + '/'
        else:
            if aspect == component.BUILT_ASPECT_NAME:
                aspect = aspect + '.' + self.get_targeted_platform_variant()
            return self.get_root() + aspect + '/' + comp + '/'
    def get_component_aspects(self, comp):
        '''
        List all aspects of a component that are present in the current sandbox.
        '''
        aspects = []
        for a in component.ASPECTS:
            path = self.get_component_path(comp, a)
            if path and os.path.isdir(path):
                aspects.append(a)
        aspects.sort()
        return aspects
    def get_on_disk_components(self):
        '''
        List all components that are present in the current sandbox, where
        "present" means that they have a subdir beneath the code root or built
        root with a .bzr subdir.
        '''
        comps = []
        if os.path.isdir(self.get_code_root()):
            comps = _get_component_subdirs(self.get_code_root())
        if os.path.isdir(self.get_built_root()):
            bcomps = _get_component_subdirs(self.get_built_root(), excluding=comps)
            comps.extend(bcomps)
        comps.sort()
        return comps
    def get_eval_start_errors(self):
        '''
        Return a string describing why the sandbox cannot be evaluated right now,
        or None if the sandbox could be evaluated.
        '''
        if self.is_locked():
            return '%s is currently locked: ' + self._lock.get_details()
        status_filter=None
        if self.get_sandboxtype().supports_checkouts():
            status_filter = lambda lbl: lbl == 'conflicts'
        bad_status = aggregate_vcs.get_sandbox_status(self, status_filter=status_filter)
        if bad_status:
            return '%s has items that are incompatible with eval:\n' + aggregate_vcs.format_sandbox_status(self, bad_status)
    def __str__(self):
        return self._name
    def _load_config(self):
        cpath = self._get_conf_path()
        if os.path.isfile(cpath):
            info = os.stat(cpath)
            lcs = self._last_config_size
            lct = self._last_config_time
            should_reload = (lcs is None or lcs != info.st_size or lct is None or str(round(lct,2)) != str(round(info.st_mtime,2)))
            if should_reload:
                self._last_config_size = info.st_size
                self._last_config_time = info.st_mtime
                self._cfg.read(cpath)
        else:
            self._last_config_size = None
            self._last_config_time = None
    def _save_config(self):
        with open(self._get_conf_path(), 'w') as fp:
            self._cfg.write(fp)
    def _get_conf_path(self):
        return self.get_root() + _CONF

_sbroot = find_root_from_within(os.path.abspath(__file__))
if _sbroot:
    current = Sandbox(_sbroot)
else:
    current = None
del(_sbroot)

_PID_PAT = re.compile('^\s*pid\s*=\s*(\d+)\s*$', re.MULTILINE | re.IGNORECASE)
class Lock:
    '''
    Manages lock state for sandboxes, to prevent them from being built, tested,
    published, etc while a conflicting action is in progress.
    '''
    @staticmethod
    def acquire(path, purpose, status='started'):
        #print('acquiring %s' % path)
        if Lock._lock_exists(path):
            raise LockError(path)
        lk = Lock()
        lk.path = path
        lk.pid = os.getpid()
        lk.purpose = purpose
        lk.start_date = time.time()
        lk.update(status)
        lk.inherited = False
        return lk
    @staticmethod
    def inherit(path, update_msg=None):
        #print('inheriting %s' % path)
        if Lock._lock_exists(path):
            lk = Lock()
            f = open(path, 'r')
            rows = [row.strip().split('=') for row in f.readlines() if row and row.find('=') > -1]
            for row in rows:
                attr = row[0].strip().replace(' ', '_')
                val = row[1].strip()
                if attr.endswith('date'):
                    val = dateutils.parse_standard_date_with_tz_offset(val)
                lk.__dict__[attr] = val
            lk.inherited = True
            lk.path = path
            if update_msg:
                lk.update(update_msg)
            return lk
    @staticmethod
    def _lock_exists(path):
        if not os.path.exists(path):
            return False
        #print('%s exists; checking pid' % path)
        valid_pid = False
        f = open(path, 'r')
        txt = f.read()
        f.close()
        m = _PID_PAT.search(txt)
        if m:
            pid = m.group(1)
            #print('pid = %s' % pid)
            if os.name == 'nt':
                cmd = 'tasklist /FI "PID eq %s"' % pid
            else:
                cmd = 'ps -p %s' % pid
            try:
                stdout = subprocess.check_output(cmd, shell=True)
                valid_pid = bool(re.search('\W%s\W' % pid, stdout, re.MULTILINE))
            except:
                valid_pid = False
        if not valid_pid:
            os.remove(path)
        return valid_pid
    @staticmethod
    def get_details(path, indent='    '):
        f = open(path, 'r')
        txt = f.read().strip()
        f.close()
        txt = indent + txt.replace('\n', '\n' + indent) + '\n'
        return txt
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self.release()
    def update(self, status):
        self.last_status = status
        f = open(self.path, 'w')
        f.write(str(self))
        f.close()
    def release(self):
        if not self.inherited:
            if os.path.isfile(self.path):
                os.remove(self.path)
    def __setattr__(self, attr, value):
        if attr == 'last_status':
            if value is None:
                value = ''
            self.__dict__['last_status_date'] = time.time()
            self.__dict__['last_status'] = str(value).replace('\r', '').replace('\n', ' ').replace('  ', ' ').strip()
        else:
            self.__dict__[attr] = value
    def __str__(self):
        # Could use config parser, but I want these keys to always appear in same
        # order and I don't need any of cp's other features, so I'm doing this raw...
        return '''purpose=%s
start date=%s
last status=%s
last status date=%s
pid=%s
''' % (self.purpose, dateutils.format_standard_date_with_tz_offset(self.start_date),
       self.last_status, dateutils.format_standard_date_with_tz_offset(self.last_status_date),
       self.pid)

class LockError(Exception):
    '''
    Report locking problem.
    '''
    def __init__(self, path):
        self.msg = 'Lock at ' + path + ' already exists:\n' + Lock.get_details(path)
    def __str__(self):
        return self.msg

_GETTER_PREFIXES = 'get_|is_|has_|exists|supports_'.split('|')

def _is_property_getter(member):
    if not inspect.ismethod(member):
        return False
    name = member.__name__
    getter = False
    # I am using a whitelist here, instead of a blacklist. The reason is that
    # some methods on a sandbox are dangerous (e.g., remove()). I don't want to
    # accidentally call these methods. It is safer to only call methods that I
    # *know* are safe.
    for p in _GETTER_PREFIXES:
        if name.startswith(p):
            getter = True
    if not getter:
        return False
    argspec = inspect.getargspec(member.im_func)
    if not argspec.args:
        return False
    if (not argspec.defaults) and len(argspec.args) == 1:
        return True
    return (argspec.defaults) and len(argspec.args) == 1 + len(argspec.defaults)

_BOOL_GETTER_PREFIXES = 'is_|has_|exists|supports_'.split('|')
def _is_boolean(prop_getter):
    for p in _BOOL_GETTER_PREFIXES:
        if prop_getter.__name__.startswith(p):
            return True
    return False

def _get_property_name(prop_getter):
    name = prop_getter.__name__
    if name.startswith('get_'):
        name = name[4:]
    return name

def _serialize_list(lst):
    items = [str(x).strip() for x in lst]
    delim = ', '
    for i in items:
        if ',' in i:
            delim = '; '
            break
    return delim.join(items)

def _show_property(prop_getter, label=False):
    value = prop_getter()
    if value is None:
        if _is_boolean(prop_getter):
            value = False
    elif hasattr(value, 'extend'):
        value = _serialize_list(value)
    elif hasattr(value, 'keys'):
        print('%s: ' % _get_property_name(prop_getter).ljust(28), end='')
        indent = ''
        for key, val in value.iteritems():
            if hasattr(val, 'extend'):
                val = _serialize_list(val)
            print(indent + '%s: %s' % (key, val))
            if not indent:
                indent = ' '.rjust(30)
        return
    if prop_getter.__name__.endswith('date'):
        try:
            value = dateutils.format_standard_date_with_tz_offset(value)
        except:
            pass
    else:
        value = str(value)
    if label:
        print('%s: %s' % (_get_property_name(prop_getter).ljust(28), value))
    else:
        print(value)

# This import is at the bottom because of a circular import error; sandbox wants
# to use aggregate_vcs, and vice-versa.
import aggregate_vcs

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        arg = sys.argv[1].lower()
        if arg.startswith('/'):
            arg = arg[1:]
        elif arg.startswith('-'):
            arg = arg[1:]
            if arg.startswith('-'):
                arg = arg[1:]
        methods = inspect.getmembers(current, _is_property_getter)
        methods.sort(key=lambda x: _get_property_name(x[1]))
        if arg == 'properties':
            for tuple in methods:
                _show_property(tuple[1], label=True)
        else:
            x = [tuple for tuple in methods if tuple[0] == arg]
            if not x:
                x = [tuple for tuple in methods if tuple[0] == 'get_' + arg]
            if x:
                name, method = x[0]
                _show_property(method)
            else:
                print('No such property: %s.' % arg)
                sys.exit(1)
        sys.exit(0)
    print('sandbox properties -- Display all known sandbox properties.')
    print('sandbox <propname> -- Display a single sandbox property.')
