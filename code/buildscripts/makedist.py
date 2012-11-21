#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# $Id: makedist.py 10660 2011-07-08 11:15:06Z mikhail.pridushchenko $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

# This post build script should be able to run in python 2.4-3.0
#     so that it can run on a variety of platforms.

try:
    from hashlib import sha256 as sha
except:
    print( "Falling back to legacy algorithms (must be on python <2.5)." )
    from sha import sha as sha

import optparse, os, platform, sys, shutil, subprocess, shlex
from distfunctions import *

FILES_TO_COPY = [ # Put files to copy that do not depend on their build location here
                  #   other files should be passed in through the command line using
                  #   the dist_file and renamed_dist_file macros in CMake.  Examples follow
        #( Source, ) --> copy this file to the dist folder
        #( Source, Dest ) --> rename this file to the "dest" name ("dest" can contain folders)
        #( Source, Dest, source_dir ) --> copy the file source in directory source_dir to the name "dest"
    ]

DIST_FOLDER = None

parser = optparse.OptionParser()

def defineOptions():
    global parser

    parser.add_option( '-t', '--target', dest="target", default="Dist", help="Target bundle type", choices=['Dist', 'RPM'] )
    parser.add_option( '-b', '--bin', '--build', '--build-dir', '--build-directory', dest="buildDir", default=".", help="CMake build directory." )
    parser.add_option( '-s', '--src', '--src-dir', '--source-directory', dest="srcDir", default=".", help="CMake source directory." )
    parser.add_option( '-c', '--cfg', '--configuration', dest="config", default='Release', help="Build configuration.", choices=['Debug','Release','MinSizeRel','RelWithDebInfo', ''] )
    parser.add_option( '-p', '--platform', dest="platform", default=getHostOS(), help="Build platform.", choices=['win_x64', 'win_32', 'linux_x86-64', 'linux_i686', 'osx_x86-64', 'osx_i686', 'osx_universal', 'unknown' ] )
    parser.add_option( '-f', '--files', '--file-list', dest="files", default="", action="callback", type="string", callback=getList, help="List of files to copy to the Dist folder in the format item;item;... where item is sourceItem[,destname[,souceDir]]" )
    parser.add_option( '-u', '--conf-files', '--configuration-file-list', dest="confFiles", default="", action="callback", type="string", callback=getList, help="List of configuration files to copy to the Dist folder without overwriting any user changes.  Format is the same as the files option." )
    parser.add_option( '-l', '--lib-files', '--library-file-list', dest="libFiles", default="", action="callback", type="string", callback=getList, help="List of library files to copy to the Dist's lib/platform folder." )
    parser.add_option( '--bin-files', '--binary-files', '--binary-file-list', dest="binFiles", default="", action="callback", type="string", callback=getList, help="List of binary files to copy to the Dist's bin/platform folder." )
    parser.add_option( '-e', '--extension-files', '--extension-file-list', dest="extensionFiles", default="", action="callback", type="string", callback=getList, help="List of extension files to copy to the Dist's extensions/platform folder." )
    parser.add_option( '-i', '--init-files', '--init-file-list', dest="initFiles", default="", action="callback", type="string", callback=getList, help="List of init scripts to be placed in rc.d or init.d." )
    parser.add_option( '-d', '--dist', '--dist-folder', dest="run", default=DIST_FOLDER, help="Dist directory (where everything will be copied)." )
    parser.add_option( '-v', '--verbose', dest="verbose", default=False, help="Output extra information to the screen." )
    parser.add_option( '--manifest', '-m', dest="manifest", action="store_const", const=1, help="Build manifest file." )
    parser.add_option( '--no-manifest', dest="manifest", action="store_const", const=0, help="Don't include manifest file" )

def main():
    global parser
    defineOptions()
    ( options, args ) = parser.parse_args()

    buildDir = os.path.realpath( options.buildDir )
    srcDir = os.path.realpath( options.srcDir )
    cfg = options.config
    if len( options.files ) == 1 and options.files[0] == ('',):
        if len( FILES_TO_COPY ) > 0:
            files = FILES_TO_COPY
        else:
            files = []
    else:
        files = options.files + FILES_TO_COPY
    confFiles = options.confFiles
    libFiles = options.libFiles
    binFiles = options.binFiles
    initFiles = options.initFiles
    extensionFiles = options.extensionFiles
    if len( cfg ) == 0:
        # try and find the build type by looking at the files parameter
        for item in files:
            if repr(item).lower().find('debug') != -1:
                cfg = "Debug"
                break
        else:
            cfg = "Release"

    plat = options.platform
    if options.verbose:
        print( "makedist: %s" % " ".join( sys.argv ) )
        print( "Running makedist on (src: %s, build: %s, cfg: %s, plat:%s)" % ( buildDir, srcDir, cfg, plat ) )

    if options.dist == None:
        distdir = os.path.realpath( os.path.join( buildDir, 'Dist', plat, cfg ) )
    else:
        distdir = os.path.realpath( options.dist )

    global DIST_FOLDER
    DIST_FOLDER = distdir + os.sep

    # add library files to the main file copy list
    for item in libFiles:
        if len( item[0] ) > 0:
            files.append( ( item[0], 'lib/%s/%s' % ( plat, os.path.basename( item[0] ) ) ) )

    # add binary files to the main file copy list
    for item in binFiles:
        if len( item[0] ) > 0:
            files.append( ( item[0], 'bin/%s/%s' % ( plat, os.path.basename( item[0] ) ) ) )

    # add extension files to the main file copy list
    for item in extensionFiles:
        if len( item[0] ) > 0:
            files.append( ( item[0], 'extensions/%s/%s' % ( plat, os.path.basename( item[0] ) ) ) )

    failedFiles = []
    fileCheckSums = []

    for item in files:
        if not isinstance( item, tuple ):
            result = copy( DIST_FOLDER, item, distdir )
        elif len( item ) >= 3:
            result = copy( DIST_FOLDER, item[0], distdir, srcDir=item[2], destname=item[1] )
        elif len( item ) == 2:
            result = copy( DIST_FOLDER, item[0], distdir, destname=item[1] )
        elif len( item[0] ) > 0:
            result = copy( DIST_FOLDER, item[0], distdir )
        else:
            result = ( None, None )

        try:
            if result[1] == None:
                failedFiles.append( item )
            elif isinstance( result, list ):
                fileCheckSums += result
            elif result[1] == False:
                pass #do nothing
            else:
                fileCheckSums.append( result )
        except:
            print( "Malformed Result object from file: %s" % repr(item) )

    for item in confFiles:
        if len(item[0]) > 0:
            if not isinstance( item, tuple ):
                result = copyConfFile( DIST_FOLDER, item, distdir )
            elif len( item ) >= 3:
                result = copyConfFile( DIST_FOLDER, item[0], distdir, srcDir=item[2], destname=item[1] )
            elif len( item ) == 2:
                result = copyConfFile( DIST_FOLDER, item[0], distdir, destname=item[1] )
            elif len( item[0] ) > 0:
                result = copyConfFile( DIST_FOLDER, item[0], distdir )
            else:
                result = ( None, None )

            try:
                if result[1] == None:
                    failedFiles.append( item )
                elif isinstance( result, list ):
                    fileCheckSums += result
                else:
                    fileCheckSums.append( result )
            except:
                print( "Malformed Result object from conf file: %s" % repr(item) )


    if len( failedFiles ) > 0:
        print( "The following files failed to copy:" )
        for file in failedFiles:
            print( "    %s" % repr( file ) )
    if not os.path.isdir(distdir):
        os.makedirs(distdir)
    if options.manifest:
        sumsFile = open( os.path.join( distdir, 'manifest.txt' ), 'w' )
        sumsFile.write( "### %s/%s manifest ###\n" % ( plat, cfg ) )
        sumsFile.write( '[\n' )
        for item in fileCheckSums:
            sumsFile.write( '\t%s,\n' % repr( item ) )
        sumsFile.write( ']\n' )

    if len( failedFiles ) != 0:
        return len( failedFiles )
    return 0

if __name__ == "__main__":
    sys.exit( main() )
