#!/usr/bin/env python
#
# $Id: ioutil.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import os
import subprocess
import tempfile
import shutil
import time
import traceback
import re

import sandbox
import component
import ioutil

def assemble_default(comp, sb=None, path=None, quiet=True):
    '''
    Use default logic to populate a runnable assembly: just copy the
    component's built root.
    '''
    if sb is None:
        sb = sandbox.current
    if path is None:
        path = sb.get_run_root()
    built_path = sb.get_component_path(comp, component.BUILT_ASPECT_NAME)
    if os.path.isdir(path):
        ioutil.nuke(path, contents_only=True)
    return ioutil.transform_tree(built_path, path)

def assemble_custom(comp, sb=None, path=None, raise_on_missing=True, quiet=True):
    '''
    Use custom logic to populate a runnable assembly: call the component's
    .if_top/assemble_run.py.
    '''
    if sb is None:
        sb = sandbox.current
    if path is None:
        path = sb.get_run_root()
    #print 'assembling custom %s to %s' % (comp, path)
    assemble_script = os.path.join(sb.get_component_path(comp, sb.get_component_reused_aspect(comp)), '.if_top', 'assemble_run.py')
    if os.path.exists(assemble_script):
        cmd = 'python "%s" --dest "%s"' % (assemble_script, path)
        #print(cmd)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=sb.get_root())
        out = process.stdout.read()
        exitcode = process.wait()
        out += process.stdout.read()

        # Print the output if requested or we had a failure!
        if not quiet or exitcode != 0:
            print(out)

        # If we had a failure raise the subprocess exception for the problem
        if exitcode != 0:
            raise subprocess.CalledProcessError(exitcode, cmd)
        return 0
    else:
        if raise_on_missing:
            raise Exception('%s does not exist.' % assemble_script)
        else:
            return 1

_modes = None
def test_mode_is_active(mode):
    '''
    Tell whether a particular "test mode" is active for the duration of the
    current process. Test modes allow the same tests to be run once with
    valgrind enabled, for example, and once without -- or to be run once with
    SearchServer generating hs5 files, and once with it generating hs3.

    Modes are enabled by adding --mode X --mode Y to the "sb test" command line.
    '''
    global _modes
    if _modes is None:
        _modes = []
        path = os.path.join(sandbox.current.get_root(), '.test-modes')
        if os.path.isfile(path):
            with open(path, 'r') as f:
                _modes = [x.strip() for x in f.read().lower().split(',') if x.strip()]
    return mode.lower() in _modes

class RunnableAssembly:
    '''
    A class that manages a copy of the runnable aspect of a particular
    component. See https:// ... /working-with-code/concepts/runnable-assemblies #TODO Kim refer to correct doc

    Must be created with a path (which might not exist). Automatically assembles
    if folder doesn't exist, but does nothing in ctor if folder already exists.
    This allows a RunnableAssembly to be shared across multiple system tests.
    '''
    def __init__(self, comp, path, sb=None, debug=False):
        self.debug = debug
        if sb is None:
            sb = sandbox.current
        if not comp in sb.get_on_disk_components():
            raise Exception('%s is not a component in %s.' % (comp, sb.get_name()))
        path = ioutil.norm_folder(path)
        self.comp = comp
        self.sb = sb
        self.path = path
        if not os.path.isdir(path):
            self.assemble()
        self.persist = False
        self.lockdir = os.path.join( tempfile.gettempdir(), 'sadm_lock' )
        if not os.path.isdir( self.lockdir ):
            try:
                os.makedirs( self.lockdir )
            except OSError:
                pass
        self.locks = {}

    def assemble(self, quiet=True):
        err = assemble_custom(self.comp, self.sb, self.path, raise_on_missing=False, quiet=quiet)
        if err:
            err = assemble_default(self.comp, self.sb, self.path, quiet=quiet)
        if err:
            raise Exception('Unable to assemble runnable folder for %s in %s at %s.' % (
                self.comp, self.sb.get_name(), self.path))

    def clean(self):
        ioutil.nuke(self.path, contents_only=True)

    def reset(self):
        self.clean()
        self.assemble()

    def _rmdir(self, path):
        # On Windows, deleting temporary files is often problematic, because
        # of the way file handles are held and released, and due to interference
        # from virus scanners. We've added a loop here, to make the delete logic
        # more robust. However, we still throw an exception if we are unable to
        # clean up eventually. This is necessary to guarantee that tests relying
        # on cleanup from previous tests are valid. If a particular test harness
        # calls remove() but does not need a temp copy of the assembly to be
        # perfectly cleaned, be sure to handle the possible exception.
        try_count = 2
        if os.name == 'nt':
            try_count = 5
        while True:
            try:
                shutil.rmtree(path)
                return
            except:
                try_count -= 1
                if try_count == 0:
                    raise
                else:
                    time.sleep(0.75)

    def remove(self):
        if self.persist:
            print('Leaving %s behind for analysis.' % self.path)
        else:
            if self.debug:
                print('Removing %s' % self.path)
            #print('Removing %s' % self.path)
            # Make sure we're nowhere inside the runnable assembly's path when we
            # remove it.
            cwd = ioutil.norm_folder(os.getcwd())
            #print('path = %s; cwd = %s' % (self.path, cwd))
            if cwd.startswith(self.path):
                os.chdir(os.path.abspath(os.path.join(self.path, '..')))
            self._rmdir(self.path)

    def update_lock(self, resource, state):
        lock_file = os.path.join( self.lockdir, str(resource) )
        lock_file_obj = open( lock_file, 'a' )
        lock_file_obj.write( "\n%s" % repr( (os.getpid(), _describe_calling_test(), time.strftime('%c'), state) ) )
        lock_file_obj.close()

    def lock(self, resource, timeout=None):
        """
        Create a system resource lock where resource is the lock's name
        and lock_type controls what conditions allow the lock to be
        released (port -> the port can no longer be bound, if resource has
        an '@' in it we assume host@port, pid -> the pid can no longer exist,
        if resource is an integer, we assume it's a pid).
        """
        if resource is None:
            raise Exception( "Locking invalid resource: %s" % resource )
        is_pid = isinstance(resource, int)
        resource = str(resource)
        lock_file = os.path.join( self.lockdir, resource )
        if not os.path.isfile( lock_file ):
            #TODO: race condition on lock creation
            self.update_lock(resource,'create')
            if is_pid:
                self.locks[resource] = 'pid'
            elif resource.find( '@' ) != -1:
                self.locks[resource] = 'port'
            else:
                self.locks[resource] = None
        else:
            print( "Waiting for lock at %s to be released." % lock_file)
            #TODO: Block for test to finish
            raise Exception( self.get_lock_state( resource ) )

    def get_lock_state(self, resource):
        resource = str(resource)
        lock_file = os.path.join( self.lockdir, resource )
        if not os.path.isfile( lock_file ):
            return ( None, None, None, "%s not locked" % resource )
        with open( lock_file, 'r' ) as lf:
            states = open( lock_file, 'r' ).readlines()
            if states:
                last_state = states[-1].strip()
            else:
                last_state = ""
        if last_state is not None and last_state.startswith('(') and last_state.endswith(')'):
            last_state = eval( last_state )
        return last_state

    def unlock(self, resource):
        if resource is None:
            raise Exception( "Unlocking invalid resource: %s" % resource )
        resource = str(resource)
        if not resource in self.locks:
            raise Exception( self.get_lock_state( resource ) )

        lock_file = os.path.join( self.lockdir, resource )
        if not os.path.isfile( lock_file ):
            raise Exception( ( None, None, None, "%s not locked" % resource ) )
        else:
            # TODO: fix race condition
            if self.locks[resource] == 'port':
                etxt = 'Port %s is still bound for runnable assembly at %s.' % (resource, self.path)
                busy_func = _port_is_bound
                args = resource.split('@')
            else:
                etxt = 'Pid %s still exists for runnable assembly at %s.' % (resource, self.path)
                busy_func = _pid_exists
                args = [resource]
            ok = False
            for i in range(10):
                if not busy_func(*args):
                    ok = True
                    break
                if i < 9:
                    time.sleep(0.5)
            if not ok:
                raise Exception(etxt)
            os.remove( lock_file )
            self.locks.pop( resource )

def _pid_exists(pid):
    if os.name == 'nt':
        cmd = 'tasklist /FI "PID eq %s"' % pid
    else:
        cmd = 'ps -p %s 2>/dev/null' % pid
    try:
        stdout = subprocess.check_output(cmd, shell=True)
        stdout = [' ' + l.strip() for l in stdout.split('\n')]
        regex = '\W%s\W' % pid
        stdout = [l for l in stdout if re.search(regex, l) and 'defunct' not in l]
        return bool(stdout)
    except:
        return False

def _get_port_from_line(line):
    i = line.find(':')
    if i > -1:
        j = i + 1
        while not line[j].isspace():
            j += 1
        return int(line[i+1:j])
    return 0

def _port_is_bound(host,port):
    if host not in [ 'localhost', '127.0.0.1', '0.0.0.0', '::1' ]:
        return False # we can't tell, so assume port is not bound
    if os.name == 'nt':
        cmd = "netstat -p TCP -noa"
        relevant = lambda line: ':' in line and ('ESTABLISHED' in line or 'LISTENING' in line)
    else:
        cmd = "netstat -tpln 2>/dev/null"
        relevant = lambda line: ':' in line
    try:
        stdout = subprocess.check_output(cmd, shell=True)
        ports = [_get_port_from_line(l) for l in stdout.split('\n') if relevant(l)]
        port = int(port)
        return port in ports
    except:
        return False

def _describe_calling_test():
    my_fname = os.path.basename(__file__)
    stack = traceback.extract_stack()
    i = 1
    while i < len(stack):
        fname, line, caller, code_at_line = stack[i]
        fname = ioutil.norm_seps(fname)
        if not fname.endswith('/' + my_fname):
            if caller.startswith('test') or caller.startswith('setUp') or caller.startswith('tearDown'):
                i = fname.find('/test/')
                j = fname.rfind('/')
                if i > -1:
                    i += 6
                if j > -1:
                    j += 1
                folder = fname[i:j]
                fname = os.path.basename(fname)
                return caller, folder, fname, line
        i += 1
    # If we get here, something's wrong. As a fall-back, just report line nums
    # and file names for any stuff that looks interesting.
    fnames = []
    for fname, line, caller, code_at_line in stack:
        if 'site-packages' not in fname and 'unittest2' not in fname:
            fname = ioutil.norm_seps(fname)
            if '/buildscripts/test.py' not in fname and '/unittest' not in fname:
                fname = os.path.basename(fname)
                if fname != my_fname:
                    fnames.append('%s(%d)' % (fname, line))
    fnames = ','.join(fnames)
    i = fnames.rfind('(')
    if i > -1:
        fnames = fnames[0:i]
    return 'unknown_func', 'unknown_component', fnames, line

class TempRunnableAssembly(RunnableAssembly):
    '''
    A class that creates a RunnableAssembly in a temp folder, and automatically
    removes it at the end of a python "with" block.
    '''
    def __init__(self, comp, sb=None):
        self.path = tempfile.mkdtemp()
        RunnableAssembly.__init__(self, comp, path, sb)
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self.remove()

