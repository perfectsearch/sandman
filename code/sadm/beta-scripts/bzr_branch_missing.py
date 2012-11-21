#!/usr/bin/env python

from subprocess import Popen, PIPE, STDOUT
import subprocess
import re 
import optparse

DEBUG = False
REPO_LOC = '/data/repo/reporoot/'

def main( options, args ):
    base_branch = args[0]
    other_branch = args[1]
    
    aspects = options.aspects.split(',')
    
    if options.user:
        ssh_cmd = options.user + '@' + options.server
    else:
        ssh_cmd = options.server
    
    branch_error = ""
    
    ls = Popen(['ssh', ssh_cmd, '""ls %(repo_loc)s%(other_branch)s/""' % {'other_branch':other_branch,'repo_loc':REPO_LOC}], stdout=PIPE, stderr=STDOUT)
    ls_out = ls.stdout.read()   
    ls.wait()
    if ls.returncode != 0:
        branch_error = "Unable to find other_branch:'%(other_branch)s'" % {'other_branch':other_branch}
        
    ls = Popen(['ssh', ssh_cmd, '""ls %(repo_loc)s%(base_branch)s/""' % {'base_branch':base_branch,'repo_loc':REPO_LOC}], stdout=PIPE, stderr=STDOUT)
    ls_out = ls.stdout.read()   
    ls.wait()
    if ls.returncode == 0:
        c_list = [x for x in re.split('\s*', ls_out) if len(x) > 0]
    else:
        if len(branch_error) > 0:
            branch_error = branch_error + ' and '
        branch_error = branch_error + "Unable to find base_branch:'%(base_branch)s'" % {'base_branch':base_branch}

    if len(branch_error) > 0:
        print branch_error
        return
    
    if DEBUG:
        print "Component List:"
        print str(c_list)
    
    print 'Comparing %s to %s in %s:\n' % (base_branch, other_branch, str(aspects))
    for component in c_list:
        for aspect in ['code', 'test']:

            p = Popen(['ssh', ssh_cmd, '""cd %(repo_loc)s%(base_branch)s/%(component)s/%(aspect)s ; bzr missing  %(repo_loc)s%(other_branch)s/%(component)s/%(aspect)s""' % {'repo_loc':REPO_LOC, 'component':component, 'aspect':aspect, 'base_branch':base_branch, 'other_branch':other_branch}], stdout=PIPE, stderr=STDOUT)
            out = p.stdout.read()
            p.wait()
            if 'extra revision' in out and not DEBUG:
                print "%s/%s in %s %s compared to %s." % (component, aspect, base_branch, out[0:out.find(':')].replace('You have', 'has').strip(), other_branch)
            
            if DEBUG:
                print '*'*20
                print '*' + '%s/%s' % (component, aspect)
                print '*'*20
                print out
                print '*'*20

if __name__ == "__main__":
    parser = optparse.OptionParser(usage='usage: %prog [options] BASE_BRANCH OTHER_BRANCH', description='Simple script to run a series of bzr missing commands for all components in a base branch against another branch.  The missing commands are run from bzr server (site server or master server) so that not all components need to be checked out. Requires two branches to compare.  This program makes assumption about the structure (branch/component/aspect) and location of the repo root (%(repo_loc)s).  Also, it is recomended that you have an ssh key to the bzr server or you will be type a lot of passwords.' % {'repo_loc':REPO_LOC})
    parser.add_option("-u", "--bzr-username", help="The user on the bzr server", action="store", type="string", dest="user")
    parser.add_option("-s", "--bzr-server", help="Hostname or ip address of the bzr server [default: %default]", action="store", default='10.10.10.100', type="string", dest="server")
    parser.add_option("-a", "--aspects", help="Aspect that will be tested for each component. (Comma sparated list with no spaces at all) [default: %default]", action="store", default='code,test', type="string", dest="aspects")
    parser.add_option( '-v', '--debug', dest="debug", default=False, action="store_true", help="Add Verbose debug messages" )
    ( options, args ) = parser.parse_args()
    
    if not len(args) == 2:
        parser.error('Two Branches were not given')
    
    if options.debug:
        DEBUG = True
    
    main(options, args)
