#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# $Id: distwebservices.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 

# This post build script should be able to run in python 2.4-3.0
#     so that it can run on a variety of platforms. 
import optparse, os, platform, signal, subprocess, sys, time
from pkg_resources import load_entry_point

DEBUG = False

def runCommand( command ):
    if DEBUG:
        print( "Running: %s" % command )
    return os.system( command )

def popenCommand( *args, **kwargs ):
    if DEBUG:
        if 'cwd' in kwargs:
            print( "Running %s from %s" % ( args[0], kwargs['cwd'] ) )
        else:
            print( "Running: %s" % args[0] )
    return subprocess.Popen( *args, **kwargs )

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


FEEDER_JAR = "bin/feeder.jar"
WEBSERVER_PID = "logs/nginx.pid"
if platform.system().lower().startswith( 'win' ):
    SEARCHSERVER_CMD = "bin/%s/PsHost.exe" % getHostOS()
    SEARCHSERVER_EXE = SEARCHSERVER_CMD
    WEBSERVER_EXE = "nginx"
    FASTCGI_EXE = "paster"
    LDAP_EXE = "slapd"
else:
    SEARCHSERVER_EXE = "bin/%s/PsHost" % getHostOS()
    SEARCHSERVER_CMD = "LD_LIBRARY_PATH=$LD_LIBRARY_PATH:./lib %s" % SEARCHSERVER_EXE
    WEBSERVER_EXE = "/usr/sbin/nginx"
    FASTCGI_EXE = "/usr/bin/paster"
    LDAP_EXE = "/usr/sbin/slapd"

def main( options ):
    my_env = os.environ
    
    lib_path = os.path.join(os.getcwd(), 'lib' )
    
    if os.path.exists( lib_path ):
        if ( my_env.get("PYTHONPATH") is None):
            my_env["PYTHONPATH"] = lib_path
            sys.path.append(lib_path)
        else:
            my_env["PYTHONPATH"] = lib_path + ":" + my_env.get("PYTHONPATH")
            sys.path.append(lib_path)
    
    if os.path.exists( options.searchServerPath ):
        lib_path = os.path.join(os.path.realpath(os.path.dirname(options.searchServerPath)), 'lib' )
        if my_env.get("PYTHONPATH") is None:
            my_env["PYTHONPATH"] = lib_path
            sys.path.append(lib_path)
        else:
            my_env["PYTHONPATH"] = lib_path + ":" + my_env.get("PYTHONPATH")
            sys.path.append(lib_path)
        
    if os.path.exists( options.feederPath ):
        lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(options.feederPath))), 'lib' )
        if ( my_env.get("PYTHONPATH") is None):
            my_env["PYTHONPATH"] = lib_path
            sys.path.append(lib_path)
        else:
            my_env["PYTHONPATH"] = lib_path + ":" + my_env.get("PYTHONPATH")
            sys.path.append(lib_path)
            
    if options.eclipse_debug_paster:
        print "Starting a single paster process for debugging in eclipse"
        paster_process = options.eclipse_debug_paster
        if os.path.exists('webapp'):
            cwd = os.getcwd()
            os.chdir( 'webapp' )
            config = None
            if 'searchui' == paster_process:
                config =  options.searchui_conf
            elif 'searchserverui' == paster_process:
                config =  options.searchserverui_conf
            elif 'feederui' == paster_process:
                config =  options.feederui_conf
            elif 'adminportal' == paster_process:
                config =  options.adminportal_conf
            elif 'osconfig' == paster_process:
                config =  options.osconfig_conf
            if config:
                load_entry_point('PasteScript==1.7.5', 'console_scripts', 'paster')(['serve', config])
            else:
                print "Invalid paster process, %s, unable to start!"
                return

    searchServer_startCmd = SEARCHSERVER_CMD
    feeder_startCmd = 'java -jar "%s" --daemon --conf conf/feeder.conf' % options.feederPath
    retriever_startCmd = 'java -jar "%s" --daemon --log-file-name=retriever.log --conf conf/retriever.conf' % options.feederPath
    webServer_startCmd = "%s -c %s -p ." % ( options.webserverPath, options.webserver_conf )
    fastcgi_startCmd = "%s serve --reload" % ( options.fastcgiPath )
    ldap_startCmd = '%s -d 1 -f %s -h "ldaps://0.0.0.0:6636"' % ( options.ldapPath, options.ldap_conf)

    webServer_stopCmd = "%s -c %s -p . -s stop" % ( options.webserverPath, options.webserver_conf )

    searchserver = None
    feeder = None
    retriever = None
    webserver = None
    searchui = None
    searchserverui = None
    feederui = None
    adminportal = None
    ldap = None

    if os.path.exists( options.searchServerPath ) and options.runSearchServer:
        print( "Starting SearchServer" )
        searchserver = popenCommand( searchServer_startCmd, shell=True, cwd=os.path.dirname(os.path.dirname(os.path.dirname( os.path.abspath(options.searchServerPath)))) )

    if os.path.exists( options.feederPath ) and options.runFeeder:
        print( "Starting Feeder" )
        feeder = popenCommand( feeder_startCmd, shell=True, cwd=os.path.dirname(os.path.dirname( os.path.abspath(options.feederPath))) )

    if os.path.exists( options.feederPath ) and options.runRetriever:
        print( "Starting Retriever" )
        retriever = popenCommand( retriever_startCmd, shell=True, cwd=os.path.dirname(os.path.dirname( os.path.abspath(options.feederPath))) )
    
    if os.path.exists( options.fastcgiPath ) and options.runFastcgi:
        print( "Starting FastCGI Layer" )
        if os.path.exists('webapp'):
            cwd = os.getcwd()
            os.chdir( 'webapp' )
            if os.path.exists( options.searchui_conf ) and os.path.exists('searchui'):
                print( "  Search UI" )
                searchui = popenCommand( "%s %s" % ( fastcgi_startCmd, options.searchui_conf ), shell=True )
            if os.path.exists( options.searchserverui_conf ) and os.path.exists('searchserverui'):
                print( "  Search Server UI" )
                searchserverui = popenCommand( "%s %s" % ( fastcgi_startCmd, options.searchserverui_conf ), shell=True )
            if os.path.exists( options.feederui_conf ) and os.path.exists('feederui'):
                print( "  Feeder UI" )
                feederui = popenCommand( "%s %s" % ( fastcgi_startCmd, options.feederui_conf ), shell=True )
            if os.path.exists( options.adminportal_conf ) and os.path.exists('adminportal'):
                print( "  Admin Portal UI" )
                adminportal = popenCommand( "%s %s" % ( fastcgi_startCmd, options.adminportal_conf ), shell=True )
            if os.path.exists( options.osconfig_conf ) and os.path.exists('osconfig'):
                print( "  Osconfig UI" )
                adminportal = popenCommand( "%s %s" % ( fastcgi_startCmd, options.osconfig_conf ), shell=True )
            os.chdir( cwd )

    if os.path.exists( options.webserverPath ) and options.runWebserver:
        print( "Starting Webserver %s in folder %s" % ( webServer_startCmd, '.' ) )
        webserver = popenCommand( webServer_startCmd, shell=True, cwd='.' )
    
    if os.path.exists(options.ldapPath) and os.path.exists(options.ldap_conf) and options.runLdap:
        print( "Starting LDAP server %s in folder %s" % ( ldap_startCmd, '.' ) )
        ldap = popenCommand( ldap_startCmd, shell=True, cwd='.' )

    try:
        while 1:
            time.sleep(1)
    except:
        if webserver is not None:
            runCommand( webServer_stopCmd )
            os.kill( webserver.pid, signal.SIGTERM )
            if os.path.isfile( options.webserverPid ):
                print( "Nginx could not properly stop itself, killing it." )
                try:
                    pid = open( options.webserverPid, 'r' ).read()
                    pid = eval( pid )
                    if not isinstance( pid, int ):
                        print( "Webserver PID file did not contain valid information." )
                        raise Exception( "Invalid PID" )
                    os.kill( pid, signal.SIGTERM )
                    if os.path.exists( options.webserverPid ):
                        os.remove( options.webserverPid )
                except:
                    print( "Failed to stop Nginx and cleanup system." )
                    print( "  Please manually kill your nginx process, then" )
                    raw_input( "  press <enter> to continue." )
        if searchui is not None:
            os.kill( searchui.pid, signal.SIGTERM )
        if searchserverui is not None:
            os.kill( searchserverui.pid, signal.SIGTERM )
        if feederui is not None:
            os.kill( feederui.pid, signal.SIGTERM )
        if adminportal is not None:
            os.kill( adminportal.pid, signal.SIGTERM )
        if feeder is not None:
            os.kill( feeder.pid, signal.SIGTERM )
        if retriever is not None:
            os.kill( retriever.pid, signal.SIGTERM )
        if searchserver is not None:
            os.kill( searchserver.pid, signal.SIGTERM )
        if ldap is not None:
            os.kill( ldap.pid, signal.SIGTERM )


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option( '-p', '--platform', dest="platform", default=getHostOS(), help="Build platform.", choices=['win_x64', 'win_32', 'linux_x86-64', 'linux_i686', 'osx_x86-64', 'osx_i686', 'osx_universal', 'unknown' ] )
    parser.add_option( '-q', '--searchuicfg', '--searchui-configuration', dest="searchui_conf", default='../conf/search-ui-development.ini', help="Search UI Process Configuration file (normally the paster ini file)." )
    parser.add_option( '-s', '--searchserveruicfg', '--searchserverui-configuration', dest="searchserverui_conf", default='../conf/searchserver-ui-development.ini', help="Search Server UI Process Configuration file (normally the paster ini file)." )
    parser.add_option( '-f', '--feederuicfg', '--feederui-configuration', dest="feederui_conf", default='../conf/feeder-ui-development.ini', help="Feeder UI Process Configuration file (normally the paster ini file)." )
    parser.add_option( '-a', '--adminportalcfg', '--adminportal-configuration', dest="adminportal_conf", default='../conf/admin-portal-development.ini', help="Admin Portal Process Configuration file (normally the paster ini file)." )
    parser.add_option( '-o', '--osconfigcfg', '--osconfig-configuration', dest="osconfig_conf", default='../conf/osconfig-development.ini', help="Osconfig Process Configuration file (normally the paster ini file)." )
    parser.add_option( '-w', '--webcfg', '--webserver-configuration', dest="webserver_conf", default='conf/nginx/nginx.conf', help="Webserver Configuration file (normally the nginx.conf for the sandbox)." )
    parser.add_option( '-l', '--ldapcfg', '--ldap-configuration', dest="ldap_conf", default='conf/slapd-development.conf', help="OpenLDAP server configuration file location." )

    parser.add_option( "--no-searchserver", dest="runSearchServer", default=True, action="store_false", help="Set this flag to disable running the search server, even if one exists." )
    parser.add_option( "--no-feeder", dest="runFeeder", default=True, action="store_false", help="Set this flag to disable running the feeder, even if one exists." )
    parser.add_option( "--no-retriever", dest="runRetriever", default=True, action="store_false", help="Set this flag to disable running the retriever, even if one exists." )
    parser.add_option( "--no-fastcgi", dest="runFastcgi", default=True, action="store_false", help="Set this flag to disable running the fastcgi layer, even if one exists." )
    parser.add_option( "--no-webserver", dest="runWebserver", default=True, action="store_false", help="Set this flag to disable running the webserver, even if one exists." )
    parser.add_option( "--no-ldap", dest="runLdap", default=True, action="store_false", help="Set this flag to disable running the LDAP server, even if one exists." )

    parser.add_option( "--searchserver-path", dest="searchServerPath", default=SEARCHSERVER_EXE, help="Path to SearchServer binary" )
    parser.add_option( "--feeder-path", dest="feederPath", default=FEEDER_JAR, help="Path to feeder.jar" )
    parser.add_option( "--fastcgi-path", dest="fastcgiPath", default=FASTCGI_EXE, help="Executable path of the FastCGI process" )
    parser.add_option( "--webserver-path", dest="webserverPath", default=WEBSERVER_EXE, help="Executable path of the Webserver" )
    parser.add_option( "--ldap-path", dest="ldapPath", default=LDAP_EXE, help="Executable path of the LDAP server" )
    parser.add_option( "--webserver-pid", dest="webserverPid", default=WEBSERVER_PID, help="The PID file created by Nginx" )

    parser.add_option( '-v', '--debug', dest="debug", default=False, action="store_true", help="Add Verbose debug messages" )
    
    parser.add_option( '--eclipse-debug-paster', dest="eclipse_debug_paster", default=None, help="Runs only the specified paster processing (no searchserver, feeder, etc) in native python way that allows eclipse to debug it. The rest of the system should be run from the console" )
    
    ### Currently we expect any automation process to start and hold our process until they are finished with it.  
    ### When they are done they should send *one* SIGTERM (or Ctrl-C) to our process and all the sub-processes will be shutdown and our process will exit.
    ### TODO: Enhance this script so that you can run it to just start the proceses (as daemons) and then call it again and just shut down the processes that were created earlier.
    #parser.add_option( "--start-only", dest="startOnly", default=False, action="store_true", help="Only start the services, then exit." )
    #parser.add_option( "--stop-only", dest="stopOnly", default=False, action="store_true", help="Only stop the services started by a previous --start-only command." )
    
    ( options, args ) = parser.parse_args()
    if options.debug:
        DEBUG = True
        
    main( options )
