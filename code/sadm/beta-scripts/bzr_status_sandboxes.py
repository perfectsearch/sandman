#!/usr/bin/env python

import os, sys, time

cwd = os.getcwd()
os.chdir( '/home/buildmeister/sandboxes' )
if len(sys.argv) < 4:
    new_branch = raw_input( "Enter a branch name: " ).strip()
    sandbox_type = raw_input( "Enter a sandbox type [dev]: " ).strip()
else:
    new_branch = sys.argv[-2].strip()
    sandbox_type = sys.argv[-1].strip()

if sandbox_type.strip() == "":
    sandbox_type = "dev"

for component in open( os.path.join( cwd, 'appliance.components.list' ) ):
    component = component.strip()
    if component == "" or component.startswith('#'):
        continue
    print( "Status %s" % component )
    cwd = os.getcwd()
    sandbox_name = "%s.%s.%s" % ( component, new_branch, sandbox_type )
    os.chdir( sandbox_name )
    os.system( "bzr sb status" )
    print( "Finished %s" %component )
    os.chdir( cwd )
