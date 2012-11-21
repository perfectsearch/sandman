#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# $Id: makerpm.py 10660 2011-07-08 11:15:06Z mikhail.pridushchenko $
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

RPM_FOLDER = ''

parser = optparse.OptionParser()

def defineOptions():
    global parser

    parser.add_option( '-t', '--target', dest="target", default="Dist", help="Target bundle type", choices=['Dist', 'RPM'] )
    parser.add_option( '-b', '--bin', '--build', '--build-dir', '--build-directory', dest="buildDir", default=".", help="CMake build directory." )
    parser.add_option( '-s', '--src', '--src-dir', '--source-directory', dest="srcDir", default=".", help="CMake source directory." )
    parser.add_option( '-c', '--cfg', '--configuration', dest="config", default='Release', help="Build configuration.", choices=['Debug','Release','MinSizeRel','RelWithDebInfo', ''] )
    parser.add_option( '-p', '--platform', dest="platform", default=getHostOS(), help="Build platform.", choices=['win_x64', 'win_32', 'linux_x86-64', 'linux_i686', 'osx_x86-64', 'osx_i686', 'osx_universal', 'unknown' ] )
    parser.add_option( '-f', '--files', '--file-list', '--files-at', dest="files", default="", type="string", help="Path to file containing list of files to copy to the Dist folder in the format item;item;... where item is sourceItem[,destname[,souceDir]]" )
    parser.add_option( '-u', '--conf-files', '--configuration-file-list', dest="confFiles", default="", action="callback", type="string", callback=getList, help="List of configuration files to copy to the Dist folder without overwriting any user changes.  Format is the same as the files option." )
    parser.add_option( '-l', '--lib-files', '--library-file-list', dest="libFiles", default="", action="callback", type="string", callback=getList, help="List of library files to copy to the Dist's lib/platform folder." )
    parser.add_option( '--bin-files', '--binary-files', '--binary-file-list', dest="binFiles", default="", action="callback", type="string", callback=getList, help="List of binary files to copy to the Dist's bin/platform folder." )
    parser.add_option( '-e', '--extension-files', '--extension-file-list', dest="extensionFiles", default="", action="callback", type="string", callback=getList, help="List of extension files to copy to the Dist's extensions/platform folder." )
    parser.add_option( '-i', '--init-files', '--init-file-list', dest="initFiles", default="", action="callback", type="string", callback=getList, help="List of init scripts to be placed in rc.d or init.d." )
    parser.add_option( '--spec-file', dest="specFile", default="", type="string", help="Spec file for RPM target." )
    parser.add_option( '--version', dest="version", default="", type="string", help="Project version for RPM target." )
    parser.add_option( '--rpm-name', dest="rpmName", default="", type="string", help="RPM package base name." )
    parser.add_option( '--rpm-prefix', dest="rpmPrefix", default="", type="string", help="RPM package name prefix." )
    parser.add_option( '--appliance-version', dest="applianceVersion", default="", type="string", help="Appliance version." )
    parser.add_option( '--component', dest="packagedComponent", default="", type="string", help="Packaged component." )

def makeRPM( specFile, version, distRoot, rpmRoot, targetDir, rpmName, rpmPrefix, applianceVersion, platform ):
    # Makedirs:
    for i in [ os.path.join( rpmRoot, 'RPMS' ), \
               os.path.join( rpmRoot, 'SPECS' ) ] :
        if not os.path.exists( i ):
            print "makedir: %s" % i
            os.makedirs( i )

    cmd = "rpmbuild -bb --buildroot '%s' --define 'psplatform %s' --define 'psversion %s' --define 'psrelease %s' --define 'psbuildroot %s' --define 'psapplianceversion %s' --define '_topdir %s' --define 'psname %s' --define 'psprefix %s' %s" \
            % ( distRoot, platform, version, 0, distRoot, applianceVersion, rpmRoot, rpmName, rpmPrefix, specFile )
    args=shlex.split( cmd )
    p = subprocess.Popen( args, shell=bool( os.name=='nt' ), stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
    # Sometimes a process waits for its stdout to be read before it will exit.
    # Therefore, attempt to read at least some output before we wait for exit.
    txt = p.stdout.read()
    exitCode = p.wait()
    txt += p.stdout.read()
    rpmFile = ''
    for s in txt.splitlines():
        if s.find( 'Wrote: ' ) == 0:
            rpmFile = s[7:].strip()
            break

    if exitCode != 0 or len( rpmFile ) == 0:
        print( "RPM build failed:" )
        print( txt )
        return 1

    rpmSourceDirectory = os.path.dirname( rpmFile )
    rpmDirectoryListing = os.listdir( rpmSourceDirectory );
    for rpmFileName in rpmDirectoryListing:
        copy( RPM_FOLDER, rpmFileName, targetDir, rpmSourceDirectory )
    return 0

def main():
    global parser
    defineOptions()
    ( options, args ) = parser.parse_args()

    buildDir = os.path.realpath( options.buildDir )
    srcDir = os.path.realpath( options.srcDir )
    cfg = options.config
    if len( options.files ) == 0 or options.files[0] == ('',):
        if len( FILES_TO_COPY ) > 0:
            files = FILES_TO_COPY
        else:
            files = []
    else:
        files = []
        with open(options.files, 'r') as optionsFile:
            for string in filter(None, optionsFile.read().split('&')):
                candidate = string.split(',')
                if candidate[0].strip() != '':
                    files.append((candidate[0].strip(), candidate[1].strip()))
            optionsFile.close()
        files = files + FILES_TO_COPY
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

    if options.target == 'RPM':
        if options.packagedComponent == "":
            print """No packaged component specified. Use \"--component\" key.
From CMakeLists.txt rpm_component_name( "<component_name>" ) macro should be used."""
            return -1;
        installDir = os.path.realpath( os.path.join( buildDir, options.packagedComponent ) )
        installDir = os.path.realpath( os.path.join( installDir, 'install' ) )
        distTmp = os.path.join( installDir, 'install.tmp' )
        distRoot = os.path.join( distTmp, 'root' )
        rpmRoot = os.path.join( distTmp, 'rpm' )
        #targetDir = os.path.join( installDir, plat, cfg )
        targetDir = installDir
        RPM_BUNDLE_ROOT = "opt/search/" + options.applianceVersion
        distdir = os.path.join( distRoot, RPM_BUNDLE_ROOT )
        initrdDir = os.path.join( distdir, 'init' )
    elif options.dist == None:
        distdir = os.path.realpath( os.path.join( buildDir, 'Dist', plat, cfg ) )
    else:
        distdir = os.path.realpath( options.dist )

    global RPM_FOLDER
    RPM_FOLDER = distdir + os.sep
    print "RPM_FOLDER=%s" % RPM_FOLDER

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
            result = copy( RPM_FOLDER, item, distdir )
        elif len( item ) >= 3:
            result = copy( RPM_FOLDER, item[0], distdir, srcDir=item[2], destname=item[1] )
        elif len( item ) == 2:
            result = copy( RPM_FOLDER, item[0], distdir, destname=item[1] )
        elif len( item[0] ) > 0:
            result = copy( RPM_FOLDER, item[0], distdir )
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
                result = copyConfFile( RPM_FOLDER, item, distdir )
            elif len( item ) >= 3:
                result = copyConfFile( RPM_FOLDER, item[0], distdir, srcDir=item[2], destname=item[1] )
            elif len( item ) == 2:
                result = copyConfFile( RPM_FOLDER, item[0], distdir, destname=item[1] )
            elif len( item[0] ) > 0:
                result = copyConfFile( RPM_FOLDER, item[0], distdir )
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

    if options.target == 'RPM':
        for item in initFiles:
            if len(item[0]) > 0:
                if not isinstance( item, tuple ):
                    result = copy( RPM_FOLDER, item, initrddir )
                elif len( item ) >= 3:
                    result = copy( RPM_FOLDER, item[0], initrddir, srcDir=item[2], destname=item[1] )
                elif len( item ) == 2:
                    result = copy( RPM_FOLDER, item[0], initrddir, destname=item[1] )
                elif len( item[0] ) > 0:
                    result = copy( RPM_FOLDER, item[0], initrdDir )
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

    if len( failedFiles ) != 0:
        return len( failedFiles )
    if options.target != 'RPM':
        return 0
    else:
        result = makeRPM( options.specFile, options.version, distRoot, rpmRoot, targetDir, options.rpmName, options.rpmPrefix, options.applianceVersion, plat )
        shutil.rmtree( distTmp )
        return result

if __name__ == "__main__":
    sys.exit( main() )
