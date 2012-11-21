'''
Provides information similar to platform.uname(), but normalizes format for
easy comparison, and adds some extra pieces of info that are useful in
describing a build or software version.
'''
#!/usr/bin/env python
#
# $Id: buildinfo.py 9317 2011-06-10 02:09:04Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import os, platform, datetime, sys

_u = platform.uname()
UNAME = [_u[0], _u[1], _u[2], _u[3], _u[4], _u[5]]
if os.name == 'nt':
    ver = UNAME[2]
    if UNAME[3].startswith('6.1.') and ver.startswith('post2008'):
        ver = '7'
    UNAME[0] = UNAME[0] + ' ' + ver
    UNAME[2] = UNAME[3]
elif UNAME[0].startswith('Darwin'):
    UNAME[0] = 'OSX'
    import subprocess
    p = subprocess.Popen('sw_vers -productVersion', stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)
    p.wait()
    # Best way to find software version is to call sw_vers. Uname reports
    # 10.4 when sw_vers reports 10.6.4. Forums on internet report that there
    # is a mapping algorithm, but it's more useful and simpler to just get
    # the number that users are familiar with.
    UNAME[2] = p.stdout.read().decode('utf-8').strip()
elif UNAME[0] == 'Linux':
    i = UNAME[2].rfind('.')
    if i > -1 and UNAME[2][i+1:].find('86') > -1:
        UNAME[2] = UNAME[2][0:i]

if UNAME[1].find('.') > -1:
    UNAME[1] = UNAME[1][0:UNAME[1].find('.')]

BITNESS = '32'
if (UNAME[4].find('64') > -1) or (UNAME[5].find('64') > -1):
    BITNESS = '64'

now = datetime.datetime.now()
TODAYS_VERSIONSTAMP = '%d.%d.%d' % (now.year - 2007, now.month, now.day)

# On one of our canonical build machines we sometimes got host names
# with embedded ansi escape sequences. We have not yet been able to
# understand why. The problem appears to happen only on rhel6. To
# guard against it, look for control chars and break the string before
# they occur.
def _cleanHostName(txt):
    name = ''
    for c in txt:
        if ord(c) >= 32:
            name += c
        else:
            break
    return name

_defpv = None
def get_natural_platform_variant():
    '''
    Tell what platform variant is the most natural fit for the current OS. This
    variant name is the one that matches mainstream C++ development on the box.
    '''
    global _defpv
    if _defpv is None:
        _defpv = 'unknown'
        bi = BuildInfo()
        _defpv = bi.os.lower()
        if _defpv == 'osx':
            _defpv += '_universal'
        elif _defpv == 'linux':
            if bi.bitness == '32':
                _defpv += '_i686'
            else:
                _defpv += '_x86-64'
        elif _defpv.startswith('win'):
            if bi.bitness == '32':
                _defpv = 'win_32'
            else:
                _defpv = 'win_x64'
    return _defpv

_KNOWN_PVs = ['win_x64', 'win_32', 'linux_x86-64', 'linux_i686', 'osx_universal']
def get_known_platform_variants():
    '''
    List all the known platform variants. This list will have to grow as we
    add support for ARM, iPhone, etc.
    '''
    return _KNOWN_PVs

def get_implied_platform_variants(variants):
    '''
    Given an informal list of "supported platforms", expand into a formal list
    of all known variants implied by the list.
    '''
    out = []
    if variants:
        for v in variants:
            v = v.lower().strip()
            if v == 'windows':
                out.extend([kv for kv in _KNOWN_PVs if kv.startswith('win')])
            elif v == 'linux':
                out.extend([kv for kv in _KNOWN_PVs if kv.startswith('lin')])
            else:
                v = fuzzy_match_platform_variant(v)
                if v:
                    out.append(v)
    out = list(set(out))
    out.sort()
    return out

def fuzzy_match_platform_variant(pv):
    '''
    Given a platform variant that might be incorrectly formatted (e.g., wrong
    case, or hyphens instead of underscores, or wrong way of referring to
    bitness and architecture), give back canonical form. This function will have
    to be maintained as we add support for ARM, iPhone, etc.
    '''
    bitness = 64
    pv = pv.lower()
    if '32' in pv or ('86' in pv and '64' not in pv):
        bitness = 32
    if pv.startswith('w') or 'win' in pv:
        if bitness == 64:
            return 'win_x64'
        else:
            return 'win_32'
    elif pv.startswith('l') or 'lin' in pv:
        if bitness == 64:
            return 'linux_x86-64'
        else:
            return 'linux_i686'
    elif 'osx' in pv or 'mac' in pv:
        return 'osx_universal'
    else:
        # If we've been given some kind of bitness, assume that the user
        # wants the current platform. If we have received neither bitness
        # nor an identifiable platform, then let function return None.
        if bitness == 32 or '64' in pv:
            os_prefix = get_natural_platform_variant()
            i = os_prefix.find('_')
            return fuzzy_match_platform_variant(os_prefix[:i + 1] + str(bitness))


class BuildInfo:
    '''
    Based on platform.uname(), but uses named fields, and compensates for
    uname's inconsistent field semantics. Fields include os (one of 'Windows',
    'Linux', 'OSX'), version of OS (e.g., '7' or '2008' on Windows; '2.6.31' on
    Linux; '10.6.4' on OSX), host (DNS or netbios name of the machine, with any
    domain suffixes removed, and normalized to lower case), bitness (the string
    '32' or '64'), stamp (embedded in build numbers; rotates daily).
    '''
    def __init__(self):
        self.os = UNAME[0]
        self.host = _cleanHostName(UNAME[1].lower())
        self.version = UNAME[2]
        self.bitness = BITNESS
        self.stamp = TODAYS_VERSIONSTAMP
    def __str__(self):
        return '%s -- %s %s-bit %s' % (self.host, self.os, self.bitness, self.version)

if __name__ == '__main__':
    descr = BuildInfo()
    if len(sys.argv) > 1:
        if sys.argv[1] == '--version-stamp':
            print(descr.stamp)
        elif sys.argv[1] == '--default-platform-variant':
            print(get_natural_platform_variant())
    else:
        print(str(descr))
