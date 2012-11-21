#
# $Id: sadm_util.py 10580 2011-07-06 21:42:11Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import os, subprocess, shlex, sys, traceback, re, time, stat
import sadm_dispatch
from sadm_constants import *
# From buildscripts...
from textui.ansi import *
from textui.colors import *
import ioutil

_VERSION_PAT = re.compile(r'.*?\d+.*')
_FLOATING_POINT_VERSION_PAT = re.compile(r'(\d+\.\d+)')
_END_OF_VERSION_PAT = re.compile('.*?\d+ ')

# Run a command and return a tuple of (stdout/stderr, exitcode).
def run(cmd, acceptFailure = False, useShell=bool(os.name == 'nt'), split=(os.name!='nt')):
    try:
        if split:
            args = shlex.split(cmd)
        else:
            args = cmd
        p = subprocess.Popen(args, stdout=subprocess.PIPE, shell=useShell, stderr=subprocess.STDOUT)
        # Sometimes a process waits for its stdout to be read before it will exit.
        # Therefore, attempt to read before we wait for exit.
        out = p.stdout.read()
        # Now wait for process to exit.
        exitcode = p.wait()
        # Append any other text that accumulated.
        out += p.stdout.read()
    except Exception:
        out = str(sys.exc_value)
        exitcode = -1
        if not acceptFailure:
            raise
    return (out, exitcode)

def indent(txt, level, width_per_indent=4):
    if level:
        return ''.rjust(level * width_per_indent, ' ') + txt
    return txt

def quote_if_needed(arg):
    if arg.find(' ') != -1:
        arg = '"%s"' % arg
    return arg

def join_path(*args):
    return ioutil.norm_seps(os.path.join(*args))

def read_file(path):
    txt = None
    if os.path.isfile(path):
        f = open(path, 'rt')
        txt = f.read()
        f.close()
    return txt

def capitalize(s):
    return s[0].upper() + s[1:]

# Create a directory and report what we've done.
def make_dir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
            print("Created folder %s." % path)
        except:
            print("Can't create directory %s" %path)
            return 0
    return 1

# Save a file and report what we've done.
def save(path, txt, report=True):
    if os.path.isfile(path):
        os.remove(path)
    f = open(path, 'w')
    f.write(txt)
    f.close()
    if report:
        print("Saved %s." % ioutil.norm_seps(path))

# Count how many items in a sequence satisfy a functor.
def count(items, func):
    n = 0
    if items:
        for x in items:
            if func(x):
                n += 1
    return n

def norm_script(script):
    if os.name == 'nt':
        script = script.replace('\\', '/')
    if script.lower().startswith(config.sandbox_container_folder.lower()):
        script = script[len(config.sandbox_container_folder):]
        if script[0] == '/':
            script = script[1:]
    return script

_DICT_TYPE = type({})
# Replace a variable in the form ^[variable] with a value.
def subst(txt, var, value = None):
    if(txt == None):
        return txt
    if type(var) == _DICT_TYPE:
        for k in var.keys():
            txt = txt.replace('^[' + k + ']', var[k])
        return txt
    else:
        return txt.replace("^[" + var + "]", value)

# Load a sample file from a reference location on disk.
def load_template(fname):
    path = os.path.join(TEMPLATES_FOLDER, fname + '.txt')
    #print('trying to load %s' % path)
    return read_file(path)

_ADMINPRIV = None
def user_has_admin_privileges(complainColor=None):
    global _ADMINPRIV
    if os.name == 'nt':
        if _ADMINPRIV is None:
            stdout, error = run("whoami /priv", acceptFailure=True)
            if error:
                _ADMINPRIV = False
            else:
                _ADMINPRIV = stdout.find("SeCreateGlobalPrivilege") > -1
        if (not _ADMINPRIV) and bool(complainColor):
            eprintc('This operation requires a command prompt started from the "Run as Administrator" menu.', complainColor)
        return _ADMINPRIV
    else:
        if _ADMINPRIV is None:
            _ADMINPRIV = (os.getegid() == 0)
        if (not _ADMINPRIV) and bool(complainColor):
            eprintc('This operation requires root privileges.', complainColor)
    return _ADMINPRIV

def get_checkOsPassword(): ######################################################
    if Schedule.password is None:
        print('\nSadm needs your OS password to interact with Windows scheduler. This info is\nnot saved.\n')
        Schedule.password = prompt('Password for ' + os.getenv('USERNAME'), mask=True)

def log(txt):
    f = open(CMD_LOG, 'at')
    f.write(time.asctime() + ' ' + txt + '\n')
    f.close()

def get_float_from_version(txt):
    m = _FLOATING_POINT_VERSION_PAT.search(txt)
    if m:
        return float(m.group())
    return 