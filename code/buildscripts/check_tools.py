#
# $Id: check_tools.py 9413 2011-06-13 18:11:41Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import re, os, subprocess, shlex, tempfile
import buildinfo
import metadata
from textui.ansi import *
from textui.colors import *

class ReqTool:
    def __init__(self, tool, version, platforms=None, verify=None, info=None, message=None):
        self.tool = tool.lower()
        self.version = self._determine_version_type(version)
        self.platforms = platforms
        self.platforms.sort()
        self.verify = verify
        self.info = info
        self.message = message
    @staticmethod
    def from_pair(tool, info):
        parts = [p.strip() for p in info.split(',')]
        parts[0] = parts[0].decode('string_escape')
        parts[1] = [p.strip() for p in parts[1].lower().split('|')]
        parts[2] = parts[2].decode('string_escape')
        if len(parts) > 3:
            parts[3] = parts[3].decode('string_escape')
        else:
            parts.append('')
        if len(parts) > 4:
            parts[4] = parts[4].decode('string_escape')
        else:
            parts.append('')
        return ReqTool(tool, parts[0], parts[1], parts[2], parts[3], parts[4])
    def attr(self, platforms, verify, info):
        self.platforms = platforms.split('|')
        self.verify = verify
        self.info = info
    def _determine_version_type(self, version):
        m = _FLOATING_POINT_VERSION_PAT.search(str(version))
        if m or version == 'any':
            return version
        else:
            return re.compile(r'%s' %version)
    def __eq__(self, other):
        return (self.tool == other.tool and self.version == other.version and
                self.platforms == other.platforms)
    def __hash__(self):
        return hash((self.tool, self.version, self.platforms))
    def __str__(self):
        return '%s: %s,%s,%s,%s' % (
            self.tool,
            self.version,
            '|'.join(self.platforms),
            self.verify,
            self.info)

_VERSION_PAT = re.compile(r'.*?\d+.*')
_FLOATING_POINT_VERSION_PAT = re.compile(r'(\d+(\.\d+)+)')
_END_OF_VERSION_PAT = re.compile('.*?\d+ ')
_REGEX_TYPE = type(_END_OF_VERSION_PAT)

def get_unique_tools_with_greatest_version(tools):
    '''
    We only want to test each tool once. Lists of tools from across a sandbox
    might repeat the identical tool more than once, or might name a tool with
    different versions or different platforms. Reduce the specified list to the
    smaller set of just what we should test.
    '''
    t = []
    for tx in tools:
        append = True
        # Look for dups
        for j in range(len(t)):
            if tx.tool == t[j].tool:
                unioned_platforms = None
                # If platforms intersect instead of being disjoint, then the
                # tools are considered a match and should be merged.
                tx_implied = buildinfo.get_implied_platform_variants(tx.platforms)
                tj_implied = buildinfo.get_implied_platform_variants(t[j].platforms)
                intersection = set(tx_implied) & set(tj_implied)
                if intersection:
                    #print('intersection for %s on %s' % (tx.tool, str(intersection)))
                    append = False
                    unioned_platforms = set(tx.platforms) | set(t[j].platforms)
                    if tx.version > t[j].version:
                        t[j] = tx
                    if unioned_platforms:
                        t[j].platforms = unioned_platforms
                    break
        if append:
            t.append(tx)
    t.sort(key=lambda x:x.tool)
    return t

def check_tools(required_tools, targeted_platform_variant=None, quiet=False):
    exitcode = 0
    # Only test the highest version of each tool -- and only do so once per tool.
    required_tools = get_unique_tools_with_greatest_version(required_tools)
    required_tools_name_width = 10
    if required_tools:
        required_tools_name_width = max([len(tool.tool) for tool in required_tools]) + 1
    if not targeted_platform_variant:
        targeted_platform_variant = buildinfo.get_natural_platform_variant()
    else:
        targeted_platform_variant = buildinfo.fuzzy_match_platform_variant(targeted_platform_variant)
    if required_tools:
        for tool in required_tools:
            if tool.platforms is None and tool.verify is None:
                if not quiet:
                    eprintc('''No information for %s.
Please provide information to be able to verify that %s
is properly set up on this machine.''' % (tool.tool, tool.tool), ERROR_COLOR)
                exitcode = 1
            else:
                platforms = buildinfo.get_implied_platform_variants(tool.platforms)
                #print('tool %s has implied platforms %s; looking for %s' % (tool.tool, '|'.join(platforms), targeted_platform_variant))
                if targeted_platform_variant in platforms:
                    if verify_command_in_path(tool, required_tools_name_width, quiet=quiet):
                        exitcode = 1
    if os.name == 'nt':
        if os.path.exists(os.path.join(os.getcwd(), 'TempWmicBatchFile.bat')):
            os.remove(os.path.join(os.getcwd(), 'TempWmicBatchFile.bat'))
    return exitcode

def get_float_from_version(txt):
    m = _FLOATING_POINT_VERSION_PAT.search(txt)
    if m:
        return float(m.group(1))

# Verify that a command is available and behaves as expected.
# Return 0 if no errors, or 1 if errors. Can also return
# detected version of command, assuming cmd asked for version,
# in the outVersion param.
def verify_command_in_path(tool, tool_name_width, quiet=False):
    name = tool.tool
    cmd = tool.verify
    requiredVersion = tool.version
    if not quiet:
        writec('    ' + CMD_COLOR + name.ljust(tool_name_width) + DELIM_COLOR + '-' + NORMTXT + ' ')
    stdout, error = run(cmd, acceptFailure=True)
    if requiredVersion != 'any' and (not error):
        if type(requiredVersion) == _REGEX_TYPE:
            m = requiredVersion.search(stdout)
            ok = bool(m)
        else:
            m = _FLOATING_POINT_VERSION_PAT.search(stdout)
            ok = bool(m)
            if ok:
                detectedVersion = m.group(1)
                detectedVersionSplit = detectedVersion.split('.');
                requiredVersionSplit = requiredVersion.split('.');
                i = 0;
                ok = True
                while i < len(requiredVersionSplit):
                    if i >= len(detectedVersionSplit):
                        detectedVersionSplit.append(0) # Add in zered item to compare
#                    print "Detected: %s Required: %s" % (detectedVersionSplit[i], requiredVersionSplit[i]);
                    if int(detectedVersionSplit[i]) < int(requiredVersionSplit[i]):
                        ok = False
                        break;
                    if int(detectedVersionSplit[i]) > int(requiredVersionSplit[i]):
                        break; # Detected version is newer than ours
                    i+=1;
        if not ok:
            if not quiet:
                if type(requiredVersion) == _REGEX_TYPE:
                    eprintc(name + ' is not compatible with required version.', ERROR_COLOR)
                elif tool.message:
                    eprintc(tool.message, ERROR_COLOR)
                else:
                    eprintc(name + ' needs to be at least version %s.' % str(requiredVersion), ERROR_COLOR)
            return 1
    exitCode = 0
    if error:
        if not quiet:
            writec(ERROR_COLOR + 'Correct tool is not installed or configured correctly. ' + tool.info + NORMTXT + '\n')
        exitCode = 1
    else:
        if cmd.find('wmic') > -1:
            i = stdout.find('Version')
            if i > -1:
                stdout = stdout[i:stdout.rfind('\n')]
                stdout = stdout.replace('\n', '')
                stdout = stdout.replace('\r', '')
                stdout = ' (%s)' % stdout.strip()
            else:
                stdout = ''
        else:
            stdout = stdout.strip()
            i = stdout.find('\n')
            if i > -1:
                stdout = stdout[0:i].rstrip()
            if _VERSION_PAT.match(stdout):
                m = _END_OF_VERSION_PAT.search(stdout)
                if m:
                    stdout = stdout[0:m.end()].strip()
                stdout = ' (%s)' % stdout
            else:
                stdout = ''
        if not quiet:
            print('OK' + stdout)
    return exitCode

# Run a command and return a tuple of (stdout/stderr, exitcode).
#  Windows and Python 2.6 has an odd behavior where if a single quoted path with
#  spaces in it is passed to the os.system or a like method it will fail not 
#  finding the binary. To fix this it was necessary to double quote the path. This 
#  behavior is not found in Python >= 2.7.
def run(cmd, acceptFailure = False, useShell=bool(os.name == 'nt'), split=True):
    try:
        if cmd.find('wmic') > -1:
            com = cmd[5:]
            cmd = cmd[0:5]
        if cmd.startswith('"'):
            python_2_6_or_earlier = sys.version_info[0] == 2 and sys.version_info[1] <= 6
            args = cmd.replace('"', '""') if python_2_6_or_earlier else cmd
        elif split:
            args = shlex.split(cmd)
        else:
            args = cmd
        p = subprocess.Popen(args, stdout=subprocess.PIPE, shell=useShell, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.dirname(__file__))
        if cmd.find('wmic') > -1:
            (stdout, stderr) = p.communicate(com)
        # Sometimes a process waits for its stdout to be read before it will exit.
        # Therefore, attempt to read before we wait for exit.
        out = p.stdout.read()
        # Now wait for process to exit.
        exitcode = p.wait()
        # Append any other text that accumulated.
        if cmd.find('wmic') > -1:
            out += stdout
        else:
            out += p.stdout.read()
    except Exception:
        out = str(sys.exc_value)
        exitcode = -1
        if not acceptFailure:
            raise
    return (out, exitcode)

if __name__ == "__main__":
    import sandbox
    if len(sys.argv) > 1:
        sb = sandbox.create_from_within(sys.argv[1])
    else:
        sb = sandbox.current
    sb.check_tools()
