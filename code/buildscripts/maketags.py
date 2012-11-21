#!/usr/bin/env python
# 
# $Id: maketags.py 3587 2010-11-30 22:16:24Z dhh1969 $
# 
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
# 
import optparse, os, subprocess, sys

parser = optparse.OptionParser( usage="maketags.py [-v] <source directories>" )
parser.add_option( '-v', '--verbose', dest="verbose", default=False, action="store_true", help="Make this scripts output more verbose." )

def getTags( source_dir, verbose=True ):
    processes = []
    for curr, dirs, files in os.walk( source_dir ):
        if curr.count('.svn') > 0:
            if verbose:
                print( "Skipping dir %s" % curr )
            continue
        if verbose:
            print( "Getting tags for %s" % curr )
        processes.append( subprocess.Popen( 'ctags *', shell=True, cwd=curr ) )
        dir_list = dirs
        for dir in dir_list:
            if dir.count('.svn') > 0:
                if verbose:
                    print( "Skipping dir %s" % os.path.join( curr, dir ) )
                dirs.remove( dir )
                
    for proc in processes:
        proc.wait()
        

if __name__ == "__main__":
    ( options, arguments ) = parser.parse_args()
    
    if len( arguments ) > 0:
        for item in arguments:
            if os.path.isdir( item ):
                getTags( item, options.verbose )
    else:
        getTags( os.getcwd(), options.verbose )


