#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# $Id: webservices.py 10168 2011-06-28 19:07:29Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

# This post build script should be able to run in python 2.4-3.0
#     so that it can run on a variety of platforms.
import optparse, os, platform, signal, subprocess, sys, time

import sandbox

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

OSCONFIG_DIR = os.path.join(sandbox.current.get_run_root(), 'osconfig')
FEEDER_JAR = os.path.join(sandbox.current.get_run_root(), "feeder/bin/feeder.jar")
WEBSERVER_PID = os.path.join(sandbox.current.get_run_root(), 'logs', 'nginx.pid')
if platform.system().lower().startswith( 'win' ):
    SEARCHSERVER_EXE = os.path.join(sandbox.current.get_run_root(), 'SearchServer', 'SearchServer.exe')
    WEBSERVER_EXE = os.path.join(sandbox.current.get_run_root(), 'nginx', 'nginx.exe')
    FASTCGI_EXE = "paster"
else:
    SEARCHSERVER_EXE = os.path.join(sandbox.current.get_run_root(), 'SearchServer', 'SearchServer')
    WEBSERVER_EXE = "/usr/sbin/nginx"
    FASTCGI_EXE = "/usr/bin/paster"

def main( options ):
    searchServer_startCmd = "%s" % options.searchServerPath
    feeder_startCmd = 'java -jar "%s" --daemon --conf feeder/conf/feeder.conf' % options.feederPath
    osconfig_ini = os.path.join(sandbox.current.get_run_root(), 'webapp-conf', 'osconfig-development.ini' )
    osconfig_startCmd = '%s serve --reload %s' % ( options.fastcgiPath, osconfig_ini )
    webServer_startCmd = "%s -c %s -p ." % ( options.webserverPath, options.webserver_conf )
    fastcgi_startCmd = "%s serve --reload %s" % ( options.fastcgiPath, options.fastcgi_conf )

    webServer_stopCmd = "%s -c %s -p . -s stop" % ( options.webserverPath, options.webserver_conf )
    
    # TEMPORARY DISABLED
    #if platform.system().lower().startswith( 'linux' ):
    #    searchServer_startCmd = "LD_LIBRARY_PATH=$LD_LIBRARY_PATH:../../lib/%s/ %s" % ( getHostOS(), searchServer_startCmd )

    searchserver = None
    feeder = None
    osconfig = None
    webserver = None
    fastcgi = None

    if os.path.exists( options.searchServerPath ) and options.runSearchServer:
        print( "Starting SearchServer" )
        searchserver = subprocess.Popen( searchServer_startCmd, shell=True, cwd=os.path.dirname( options.searchServerPath) )

    if os.path.exists( options.feederPath ) and options.runFeeder:
        print( "Starting Feeder" )
        feeder = subprocess.Popen( feeder_startCmd, shell=True, cwd=sandbox.current.get_run_root() )

    my_env = os.environ

    lib_path = os.path.join(sandbox.current.get_code_root(), 'buildscripts')

    if os.path.exists( lib_path ):
        if ( my_env.get("PYTHONPATH") is None):
            my_env["PYTHONPATH"] = lib_path
        else:
            my_env["PYTHONPATH"] = lib_path + os.path.pathsep + my_env.get("PYTHONPATH")

    if os.path.exists( options.searchServerPath ):
        lib_path = os.path.join(sandbox.current.get_run_root(),'SearchServer', 'lib' )
        if ( my_env.get("PYTHONPATH") is None):
            my_env["PYTHONPATH"] = lib_path
        else:
            my_env["PYTHONPATH"] = lib_path + os.path.pathsep + my_env.get("PYTHONPATH")

    if os.path.exists( options.feederPath ):
        lib_path = os.path.join(sandbox.current.get_run_root(),'feeder', 'lib' )
        if ( my_env.get("PYTHONPATH") is None):
            my_env["PYTHONPATH"] = lib_path
        else:
            my_env["PYTHONPATH"] = lib_path + os.path.pathsep + my_env.get("PYTHONPATH")

    if os.path.exists( options.osconfigPath ) and options.runOsconfig:
        print( "Starting osconfig process" )
        osconfig = subprocess.Popen( osconfig_startCmd, shell=True, cwd=options.osconfigPath )

    if os.path.exists( options.fastcgiPath ) and options.runFastcgi:
        print( "Starting FastCGI Layer" )
        fastcgi = subprocess.Popen( fastcgi_startCmd, shell=True, env=my_env )

    if os.path.exists( options.webserverPath ) and options.runWebserver:
        print( "Starting Webserver %s in folder %s" % ( webServer_startCmd, sandbox.current.get_run_root() ) )
        webserver = subprocess.Popen( webServer_startCmd, shell=True, cwd=sandbox.current.get_run_root() )

    try:
        while 1:
            time.sleep(1)
    except:
        if webserver is not None:
            os.system( webServer_stopCmd )
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
        if fastcgi is not None:
            os.kill( fastcgi.pid, signal.SIGTERM )
        if osconfig is not None:
            os.kill( osconfig.pid, signal.SIGTERM )
        if feeder is not None:
            os.kill( feeder.pid, signal.SIGTERM )
        if searchserver is not None:
            os.kill( searchserver.pid, signal.SIGTERM )


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option( '-p', '--platform', dest="platform", default=getHostOS(), help="Build platform.", choices=['win_x64', 'win_32', 'linux_x86-64', 'linux_i686', 'osx_x86-64', 'osx_i686', 'osx_universal', 'unknown' ] )
    parser.add_option( '-c', '--cgicfg', '--fastcgi-configuration', dest="fastcgi_conf", default='development.ini', help="Fast CGI Process Configuration file (normally the paster ini file)." )
    parser.add_option( '-w', '--webcfg', '--webserver-configuration', dest="webserver_conf", default='webapp-conf/nginx/nginx.conf', help="Webserver Configuration file (normally the nginx.conf for the sandbox)." )

    parser.add_option( "--no-searchserver", dest="runSearchServer", default=True, action="store_false", help="Set this flag to disable running the search server, even if one exists." )
    parser.add_option( "--no-feeder", dest="runFeeder", default=True, action="store_false", help="Set this flag to disable running the feeder, even if one exists." )
    parser.add_option( "--no-osconfig", dest="runOsconfig", default=True, action="store_false", help="Set this flag to disable running the osconfig process, even if one exists." )
    parser.add_option( "--no-fastcgi", dest="runFastcgi", default=True, action="store_false", help="Set this flag to disable running the fastcgi layer, even if one exists." )
    parser.add_option( "--no-webserver", dest="runWebserver", default=True, action="store_false", help="Set this flag to disable running the webserver, even if one exists." )

    parser.add_option( "--searchserver-path", dest="searchServerPath", default=SEARCHSERVER_EXE, help="Path to SearchServer binary" )
    parser.add_option( "--feeder-path", dest="feederPath", default=FEEDER_JAR, help="Path to feeder.jar" )
    parser.add_option( "--osconfig-path", dest="osconfigPath", default=OSCONFIG_DIR, help="Path to the osconfig directory." )
    parser.add_option( "--fastcgi-path", dest="fastcgiPath", default=FASTCGI_EXE, help="Executable path of the FastCGI process" )
    parser.add_option( "--webserver-path", dest="webserverPath", default=WEBSERVER_EXE, help="Executable path of the Webserver" )
    parser.add_option( "--webserver-pid", dest="webserverPid", default=WEBSERVER_PID, help="The PID file created by Nginx" )

    ### Currently we expect any automation process to start and hold our process until they are finished with it.
    ### When they are done they should send *one* SIGTERM (or Ctrl-C) to our process and all the sub-processes will be shutdown and our process will exit.
    ### TODO: Enhance this script so that you can run it to just start the proceses (as daemons) and then call it again and just shut down the processes that were created earlier.
    #parser.add_option( "--start-only", dest="startOnly", default=False, action="store_true", help="Only start the services, then exit." )
    #parser.add_option( "--stop-only", dest="stopOnly", default=False, action="store_true", help="Only stop the services started by a previous --start-only command." )

    ( options, args ) = parser.parse_args()

    main( options )
