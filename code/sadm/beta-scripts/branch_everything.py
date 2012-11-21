#!/usr/bin/env python

import os, sys

os.chdir( '/home/buildmeister/sandboxes' )

new_branch = raw_input( "Enter a new branch name: " )
sandbox_type = raw_input( "Enter a sandbox type [dev]: " )
if sandbox_type.strip() == "":
    sandbox_type = "dev"

for component in open( 'appliance.components.list' ):
    if component.strip() == "":
        continue
    print( "Branch %s" % component )
    os.system( './sadm_init_expect.sh %s.%s.%s' % ( component.strip(), new_branch.strip(), sandbox_type.strip() ) )

