#!/usr/bin/env python

import os, sys, time

cwd = os.getcwd()
os.chdir( '/home/buildmeister/sandboxes' )
if len(sys.argv) < 4:
    new_branch = raw_input( "Enter a branch name: " ).strip()
    sandbox_type = raw_input( "Enter a sandbox type [dev]: " ).strip()
    from_branch = raw_input( "Enter a branch to pull from: " ).strip()
else:
    new_branch = sys.argv[-3].strip()
    sandbox_type = sys.argv[-2].strip()
    from_branch = sys.argv[-1].strip()

if sandbox_type.strip() == "":
    sandbox_type = "dev"

for component in open( os.path.join( cwd, 'appliance.components.list' ) ):
    component = component.strip()
    if component == "" or component.startswith('#'):
        continue
    print( "Running %s" % component )
    cwd = os.getcwd()
    sandbox_name = "%s.%s.%s" % ( component, new_branch, sandbox_type )
    if not os.path.isdir( os.path.join( sandbox_name, "code", "buildscripts" ) ):
        print( "*" * 75 )
        retVal = os.system( "sadm init %s" % sandbox_name )
        print( "*" * 75 )
        if retVal != 0:
            print( "sadm init %s FAILED" % sandbox_name )
            continue
    os.chdir( sandbox_name )
    print( "-" * 75 )
    os.system( "bzr sb up" )
    os.system( "bzr sb pull --from %s" % from_branch )
    os.system( "bzr sb merge --from %s" % from_branch )
    os.system( "bzr sb push" )
    print( "-" * 75 )
    print( "Finished %s" %component )
    os.chdir( cwd )

