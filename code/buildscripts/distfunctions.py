# $Id: distfunctions.py 10660 2011-07-08 11:15:06Z mikhail.pridushchenko $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import optparse, os, platform, sys, shutil, subprocess, shlex

def getHostOS():
    host_os = "win_x64"
    if platform.system().lower().startswith("win"):
        if 'PROGRAMFILES(X86)' in os.environ:
            host_os = "win_x64"
        else:
            host_os = "win_32"
    elif platform.system().lower().startswith("linux"):
        if platform.machine() == 'x86_64':
            host_os = "linux_x86-64"
        else:
            host_os = "linux_i686"
        
    return host_os

def checkSumFile( fileName ):
    """Compute hash of the specified file"""
    m = sha()
    try:
        fd = open(fileName,"rb")
    except IOError:
        print( "Unable to open the file in readmode: %s" % filename )
        return
    for eachLine in fd:
        m.update( eachLine )
    fd.close()
    return m.hexdigest()

def copy( common_prefix, filename, distFolder, srcDir=None, destname=None ):
    """
    Copy the filename (relative to the src directory) to the destname relative to the Dist folder.
    """
    #print('got request to copy\n  common_prefix = %s\n  filename=%s\n  distFolder=%s\n  srcDir=%s\n  destname=%s' % (common_prefix, filename, distFolder, srcDir, destname))
    if destname == None:
        destname = os.path.basename( filename )
    if srcDir == None:
        srcDir = ""

    allowDoesntExist = (filename[-1:] == '?')
    if allowDoesntExist:
        filename = filename[0:-1]
    srcPath = os.path.realpath( os.path.join( srcDir, filename ) )
    destPath = os.path.realpath( os.path.join( distFolder, destname ) )
        
    if not os.path.exists( srcPath ):
        if allowDoesntExist:
            print ("Optional file %s does not exist." % srcPath)
            return (False, False)
        else:
            print( "File %s does not exist." % srcPath )
            return ( destPath, None )

    if os.path.isdir( srcPath ):
        result = []
        if not os.path.isdir( destPath ):
            os.makedirs( destPath )
        for file in os.listdir( srcPath ):
            if file.startswith( 'CMake' ) or file.startswith( 'CTest' ) or file.endswith( '.cmake' ):
                continue
            elif file.startswith( '.svn' ) or file.startswith('.bzr'):
                continue
            callResult = copy( common_prefix, file, distFolder, srcPath, os.path.join( destname, file ) )
            if isinstance( callResult, list ):
                result += callResult
            else:
                result.append( callResult )
        
        return result
    else:
        try:
            sourceCheckSum = checkSumFile( srcPath )
        except:
            sourceCheckSum = "Not Computed."
        
        try:
            destCheckSum = checkSumFile( destPath )
        except:
            destCheckSum = None
            
        relDestPath = destPath.replace( common_prefix, "").replace( '\\', '/' )

        if ( os.path.exists( srcPath ) and os.path.exists( destPath ) ) and ( sourceCheckSum == destCheckSum ):
            return ( relDestPath, sourceCheckSum )
    
        try:
            if not os.path.isdir( os.path.dirname( destPath ) ):
                os.makedirs( os.path.dirname( destPath ) )
            if not os.path.islink( os.path.join( srcDir, filename ) ):
                print( "Copying %s to %s" % ( srcPath, relDestPath ) )
                returnVal = shutil.copy( srcPath, destPath )
            elif not ( os.name == 'nt' ):
                print( "Going to handle %s" % (os.path.join( srcDir, filename ) ) )
                # Name of file symlink is pointing to
                #linkProtoName = os.path.join( distFolder, os.path.basename( srcPath ) )
                linkProtoName = os.path.basename( srcPath )
                # Name of symlink
                #linkName = os.path.basename( destDir )
                linkName = os.path.join( distFolder, destname )
                #linkName = os.path.basename( filename )
                print( "Linking %s to %s" % ( linkProtoName, linkName ) )
                os.symlink( linkProtoName.strip(), linkName.strip() )
        except:
            print( "Copy of %s returned an exception" % srcPath )
            return ( relDestPath, None )
    
        return ( relDestPath, sourceCheckSum )
    
    return None

def copyConfFile( common_prefix, filename, distFolder, srcDir=None, destname=None ):
    """
    Copy the filename (relative to the src directory) to the destname relative to the Dist folder
    only if the file does not match the destination file or the destination.default file.  This will
    allow the user to make changes to the configuration files without them being overwritten.
    """
    if destname == None:
        destname = os.path.basename( filename )
    if srcDir == None:
        srcDir = ""

    pieces = destname.split('.')
    pieces.insert( -1, '1' )
    comparename = '.'.join( pieces )
    
    srcPath = os.path.realpath( os.path.join( srcDir, filename ) )
    destPath = os.path.realpath( os.path.join( distFolder, destname ) )
    comparePath = os.path.realpath( os.path.join( distFolder, comparename ) )
        
    if not os.path.exists( srcPath ):
        print( "File %s does not exist." % srcPath )
        return ( destPath, None )
        
    try:
        sourceCheckSum = checkSumFile( srcPath )
    except:
        sourceCheckSum = "Not Computed."
    
    try:
        destCheckSum = checkSumFile( destPath )
    except:
        destCheckSum = None
        
    try:
        compareDestCheckSum = checkSumFile( comparePath )
    except:
        compareDestCheckSum = "Not Computed."
        
    
    relDestPath = destPath.replace( common_prefix, "").replace( '\\', '/' )
    relComparePath = comparePath.replace( common_prefix, "").replace( '\\', '/' )

    if ( os.path.exists( srcPath ) and os.path.exists( destPath ) ) and ( sourceCheckSum == destCheckSum == compareDestCheckSum ):
        return [ ( relDestPath, sourceCheckSum ), ( relComparePath, sourceCheckSum ) ]

    try:
        if not os.path.isdir( os.path.dirname( destPath ) ):
            os.makedirs( os.path.dirname( destPath ) )
        
        if ( sourceCheckSum != destCheckSum ) and ( destCheckSum == compareDestCheckSum ) or ( not os.path.exists( destPath ) ):
            print( "Copying %s to %s" % ( srcPath, relDestPath ) )
            returnVal = shutil.copy( srcPath, destPath )
        if ( sourceCheckSum != compareDestCheckSum ) or ( not os.path.exists( comparePath ) ):
            print( "Creating a default revision at %s" % relComparePath )
            returnVal = shutil.copy( srcPath, comparePath )
    except:
        print( "Copy of %s returned an exception" % srcPath )
        raise
        return ( relDestPath, None )

    return [ ( relDestPath, sourceCheckSum ), ( relComparePath, sourceCheckSum ) ]

def getList( option, opt_str, value, parser ):
    """
    optparse callback for returning a list from a string of format
    1a:1b,2a:2b,3a:3b,...
    """
    setattr( parser.values, option.dest, [ tuple(x.split(',')) for x in value.split('&') ] )


