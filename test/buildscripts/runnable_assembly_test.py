#!/usr/bin/env python
#
# $Id: RunnableAssemblyTest.py 4183 2011-01-03 20:17:03Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import unittest2, os, tempfile
from testsupport import checkin, CODEROOT

import runnable_assembly
from runnable_assembly import _port_is_bound

LOCK_NAME = 'bs_test_lock'
HOST = '127.0.0.1'

@checkin
class RunnableAssemblyTest(unittest2.TestCase):

    def __init__(self, methodName='runTest'):
        unittest2.TestCase.__init__(self, methodName)
        # Pretend a runnable assembly exists in current folder; this is harmless.
        self.ra = runnable_assembly.RunnableAssembly( 'buildscripts', './' )
        self.cleanup = []

    def tearDown(self):
        lock_dir = os.path.join( tempfile.gettempdir(), 'sadm_lock' )
        for f in os.listdir( lock_dir ):
            if f.startswith( 'bs_' ) or f in self.cleanup:
                os.remove( os.path.join( lock_dir, f ) )
        self.ra.locks.clear()
        self.cleanup = []

    def test_lock_and_unlock(self):
        self.ra.lock( LOCK_NAME )
        lock_file = os.path.join( tempfile.gettempdir(), 'sadm_lock', LOCK_NAME )
        assert( os.path.isfile( lock_file ) )
        self.ra.unlock( LOCK_NAME )
        assert( not os.path.isfile( lock_file ) )

    def test_double_lock(self):
        self.ra.lock( LOCK_NAME )
        try:
            self.assertRaises(Exception, self.ra.lock, LOCK_NAME)
        finally:
            self.ra.unlock(LOCK_NAME)

    def test_unlock_unknown(self):
        self.assertRaises(Exception, self.ra.unlock, 'bs_other_lock')

    def test_lock_None(self):
        self.assertRaises(Exception, self.ra.lock, None)

    def test_unlock_busy_pid(self):
        self.ra.lock( os.getpid() )
        self.cleanup.append(str(os.getpid()))
        self.assertRaises(Exception, self.ra.unlock, os.getpid() )

    def test_unlock_free_pid(self):
        fake_pid = 12345678
        self.ra.lock( fake_pid )
        self.ra.unlock( fake_pid )

    def test_unlock_busy_port(self):
        for port in [22, 25, 3389, 111, 631]:
            if _port_is_bound(HOST, port):
                id = '%s@%d' % (HOST, port)
                self.ra.lock( id )
                self.cleanup.append(id)
                self.assertRaises(Exception, self.ra.unlock, id )
                return
        print("SKIP test_unlock_busy_port -- couldn't find busy port")

    def test_unlock_free_port(self):
        for port in [63419, 59284, 47231]:
            if not _port_is_bound(HOST, port):
                id = '%s@%d' % (HOST, port)
                self.ra.lock( id )
                self.ra.unlock( id )
                return
        print("SKIP test_unlock_free_port -- couldn't find free port")

if __name__ == '__main__':
    unittest.main()
