# -*- coding: utf-8 -*
from __future__ import print_function
'''
this is a decorator to ensure only a single instance of a python application is running.
It expects to decorate the "main" function and expect the main function to be called with
sys.argv.append

Usage:
@single_app_instance
def main(args):
    ...path

'''    

import os
import tempfile
from filelock import FileLock, FileLockException
import traceback

def single_app_instance(main):
    def wrapper(args):
        # Don't allow multiple copies of this script to run at the same time. That
        # way we can schedule it to run every minute, and it will essentially do
        # continuous replication, starting over as soon as it finishes but never
        # running multiple instances for longer than a split second.
        appname = os.path.basename(args[0])
        lockfile = '/data/locks/' +appname + '.lock'
        try:
            with FileLock(lockfile, timeout=0):
                try:
                    return main(args)
                except FileLockException:
                    traceback.print_exc()
                    return 1
        except FileLockException:
            # Another version of this script already has the file locked; we should
            # exit without complaining.
            print('Another copy of %s is running - exiting' % appname)
            print('If there is no instance running then delete %s' % lockfile)
            return 0
    return wrapper
