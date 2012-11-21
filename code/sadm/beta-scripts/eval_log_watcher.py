#!/usr/bin/env python

from subprocess import Popen, PIPE, STDOUT
import subprocess
import time
import re
import os
import optparse

    
def main( options, args ):
    try:
        while True:
            cur_sandbox = None
            cur_pid = None
            
            try:
                sadm_list = Popen(['sadm', 'list', '--no-color'], stdout=PIPE, stderr=STDOUT)
                sadm_list_out = sadm_list.stdout.read()   
                sadm_list.wait()
            except OSError:
                print "Unable to run sadm list, is sadm installed?"
                return
            
            m = re.search("(\S*\.\S*\.\S*)\s+-.*pid=(\d+).*", sadm_list_out)
            if m:
                cur_sandbox = m.group(1).strip()
                cur_pid = m.group(2).strip()
                
            if cur_pid:
                loc = os.path.join(options.sandboxes, cur_sandbox, 'eval-log.txt')
                subprocess.call(['tail', '-f', '--pid='+cur_pid, loc])
                cur_sandbox = None
                cur_pid = None
                
            time.sleep(options.loop_sec)
    except KeyboardInterrupt:
        pass
        
if __name__ == "__main__":
    parser = optparse.OptionParser(usage='usage: %prog [options]', description='')
    parser.add_option("-s", "--sandboxes", default=os.path.join(os.getenv("HOME"), 'sandboxes'), help="The sandboxes directory, defaults to %default", action="store", type="string", dest="sandboxes")
    parser.add_option("-l", "--loop-sec", default=5, help="Time between loops when waiting for sandbox evals, defaults to %default", action="store", type="int", dest="loop_sec")
    ( options, args ) = parser.parse_args()
    
    main(options, args)
