# $Id: sadm_sandbox.py 10689 2011-07-08 16:40:43Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import tarfile
from sadm_constants import *
from sadm_error import *
# From buildscripts...
from ioutil import *
import buildinfo
import sandbox
import sandboxtype
import component

if os.name == 'nt':
    _PROCLIST_CMD = 'tasklist /V'
else:
    _PROCLIST_CMD = 'ps -ef'
_PID_IN_CMD_LOG_PAT = re.compile(r'\s+start\s+(.*?)\s*=\s*pid\s*(\d+)')
if os.name == 'nt':
    _PID_PAT = re.compile(r'^ctest.exe\s+(\d+).*')
else:
    _PID_PAT = re.compile(r'^[_a-zA-Z0-9]+\s+(\d+)\s+.*ctest\s+-S\s+steer.cmake')
_CTEST_PROPERTY_PAT = re.compile(r'^\s*set\s*\(\s*(CTEST[^ \t]+)\s*(.*?)\s*\)', re.MULTILINE | re.IGNORECASE)
_REPO_FROM_FULLPATH_PAT = re.compile('(.*)/(trunk|branches)/.*')

def _get_archive_url(repo, branch, proj):
    return join_path(repo, get_branch_path_in_svn(branch), proj)

def _is_linked_to_archive(buildRoot):
    return os.path.isdir(os.path.join(buildRoot, ARCHIVE_FOLDER, '.bzr'))

def _load_best_template(aux_folder, baseNames, suffix = ''):
    if '/\\'.find(aux_folder[-1]) == -1:
        aux_folder += '/'
    txt = ''
    if type(baseNames) == type(''):
        baseNames = [baseNames]
    preferred = baseNames[0]
    i = 0
    for baseName in baseNames:
        checkedIn = join_path(aux_folder, baseName)
        #print('probing for %s' % checkedIn)
        useCheckedIn = os.path.exists(checkedIn)
        if not useCheckedIn:
            checkedIn += CHECKEDIN_TEMPLATE_SUFFIX
            #print('probing for %s' % checkedIn)
            useCheckedIn = os.path.exists(checkedIn)
        if useCheckedIn:
            #print('Using checked-in %s as template for %s.' % (checkedIn[len(aux_folder):], preferred))
            txt = read_file(checkedIn)
            break
        else:
            #print('no checked in template')
            if i == len(baseNames) - 1:
                #print('loading %s' % preferred + suffix)
                txt = load_template(preferred + suffix)
                if txt is None:
                    raise Exception('No template found for %s.' % str(baseNames))
        i += 1
    return txt, useCheckedIn

# Write initial settings for an eclipse workspace corresponding to this sandbox.
# This is relevant even to cmake-driven projects, because eclipse may be used as
# a C++ IDE.
def configure_for_eclipse(sb, force=False):
    path = join_path(sb.get_root(), ECLIPSE_METADATA_FOLDER)
    if force or (not os.path.isdir(path)):
        tar = tarfile.open(join_path(TEMPLATES_FOLDER, ECLIPSE_METADATA_ARCHIVE))
        # Can't use tar.extractall() -- method didn't exist in python 2.4
        for tarinfo in tar:
            tar.extract(tarinfo, self.getPath())
        # If this workspace will interact with ant in any way, set ant
        # properties for code root and build root, so that running ant
        # in the IDE and running from build scripts give identical results.
        fpath = join_path(path, '.plugins/org.eclipse.core.runtime/.settings/org.eclipse.ant.core.prefs')
        txt = read_file(fpath)
        lines = txt.strip().split('\n')
        lines = [l for l in lines if l.strip() and (not ANT_ROOTPROP_PAT.match(l))]
        lines.append('property.code.root=%s' % self.get_code_root())
        lines.append('property.built.root=%s' % self.get_built_root())
        txt = '\n'.join(lines)
        f = open(fpath, 'wt')
        f.write(txt)
        f.close()

def get_last_start_date(sb):
    '''
    Return the time when this sandbox was last started.
    '''
    recent = Sandbox.list_recent_starts()
    for tuple in recent:
        #print(tuple)
        if tuple[0] == self.name:
            return tuple[2]
    return None

def list_recent_starts(max=50):
    # Return the names, pids, and start times of the last few sandboxes that
    # were started, most recent first.
    recent = get_tail(CMD_LOG, 50, lambda x: x.find(' start') > -1 and x.find('= pid') > -1)
    x = []
    for line in reversed(recent):
        m = _PID_IN_CMD_LOG_PAT.search(line)
        if m:
            when = line[0:line.find(' start')].replace('  ', ' ')
            name = m.group(1)
            # Disqualify old sadm sandboxes...
            if '/' not in name:
                x.append((name, m.group(2), when))
                if len(x) >= max:
                    break
    return x

def get_by_name_pattern(sandboxes, namePat, allow_multi_matches):
    selected = []
    namePat = namePat.strip().lower()
    if allow_multi_matches:
        namePat = namePat.replace('.', '\\.').replace('*', '.*').replace('?', '.')
        regex = re.compile('^' + namePat + '$', re.IGNORECASE)
    for sb in sandboxes:
        if allow_multi_matches:
            match = bool(regex.match(sb.get_name()))
        else:
            match = bool(sb.get_name().lower() == namePat)
        if match:
            selected.append(sb)
            if not allow_multi_matches:
                break
    return selected

DEBUG_OR_RELEASE_PAT = re.compile(r'^set\s*\(\s*CMAKE_BUILD_TYPE\s+(Debug|Release)')
# These imports have to come at end of file to avoid circular import errors
from sadm_util import *
from sadm_schedule import Schedule
from sadm_config import *

