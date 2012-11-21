#
# $Id: filename 3521 2010-11-25 00:31:22Z svn_username $
#
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
#
import sys
import time
import threading

def _kill_process(timeout, monitor, killfunc):
    if timeout is None:
        print('Assuming a 5-minute timeout.')
        timeout = 300
    remaining = float(timeout)
    while True:
        #print('waiting %d secs to kill' % remaining)
        if 'time' not in locals():
            import time as t
            t.sleep(min(remaining, 5))
        else:
            time.sleep(min(remaining, 5))
        ls = monitor.last_status
        # If our last_status is now None, that means we're supposed to exit
        # without comment because what we're monitoring is done.
        if ls is None:
            return
        remaining = timeout - (time.time() - ls)
        if remaining < 0.1:
            print('Error: timed out with idle stdout after %d seconds.' % timeout)
            killfunc()
            return

def _default_kill_func():
    sys.exit(1)

class Monitor:
    def __init__(self):
        self.keep_alive()
    def __enter__(self):
        self.keep_alive()
        return self
    def __exit__(self, type, value, traceback):
        self.stop()
    def keep_alive(self):
        self.last_status = time.time()
    def stop(self):
        '''
        Signal to the thread that's servicing this monitor that its work is
        complete; this causes the thread to exit within a few seconds. If we're
        running as a standalone process, the thread will exit immediately, even
        without the signal, because we've marked it as a daemon thread.
        '''
        self.last_status = None

def start(timeout, name='Timeout Monitor', killfunc=_default_kill_func):
    '''
    Start up a thread that will force us to exit if we hang. Return a monitor
    object that can be kept alive by calling .keep_alive(), and released by
    calling .stop().
    '''
    monitor = Monitor()
    kill_thread = threading.Thread(target=_kill_process, name=name,
                                   kwargs={'timeout': timeout,
                                           'killfunc': killfunc,
                                           'monitor': monitor})
    kill_thread.daemon = True
    kill_thread.start()
    return monitor
