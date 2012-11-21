#!/usr/bin/env python

import re, os, subprocess, sys, time, traceback

masterrepo = "bzr+ssh://bazaar.example/reporoot"
siterepo = None #"bzr+ssh://10.10.10.100/reporoot"
arch = "built.linux_x86-64"

cwd = os.getcwd()
os.chdir( '/home/buildmeister/sandboxes' )
if len(sys.argv) < 3:
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
    os.system( "sadm start %s" % sandbox_name )
    # ensure the lock file is created by giving it five seconds to appear.
    time.sleep( 5 );
    tail = subprocess.Popen(["tail", "-f", "eval-log.txt"], stdout=sys.stdout, stderr=sys.stderr)
    while (os.path.isfile( "lock" )):
        time.sleep( 1 );
    tail.kill()
    print( "-" * 75 )
    print( "Finished %s" %component )

    if sandbox_type == "official":
        publishfailed = True;
        for line in open("eval-log.txt"):
            if "PUBLISH SUCCEEDED" in line:
                print( "PUBLISH SUCCEEDED" )
                publishfailed = False

        if publishfailed:
            print( "Build failed to publish." )
            print( "Stopping..." )
            exit()
    else:
        buildsuccess = False;
        for line in open("eval-log.txt"):
            if "Overall result - success" in line:
                buildsuccess = True
                break
                
            
        if buildsuccess == False:
            print "Build Failed!!!"
            exit()

    if sandbox_type == "official" and siterepo != None:
        print("Waiting for site repo revision to match master repo revision.")
        while True:
            try:
                p = subprocess.Popen(["bzr", "version-info", "%s/%s/%s/%s" % (masterrepo, new_branch, component, arch)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.wait()
                masterres, err = p.communicate()
                p = subprocess.Popen(["bzr", "version-info", "%s/%s/%s/%s" % (siterepo, new_branch, component, arch)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.wait()
                siteres, err = p.communicate()
                masterres = re.search("^revision-id: (.+)", masterres)
                siteres = re.search("^revision-id: (.+)", siteres)
                if siteres == None:
                    print("There is an error in the bzr compare")
                    exit()
                if siteres.group(0) == masterres.group(0):
                    print("Site Repo matches Master Repo.\n Site-   %s \n Master- %s" % (siteres.group(0), masterres.group(0)))
                    break;
                print("Site Repo doesn't match Master Repo.\n Site-   %s \n Master- %s" % (siteres.group(0), masterres.group(0)))
                print("%s Sleeping 30 seconds." % component)
                time.sleep(30)
            except KeyboardInterrupt:
                exit()
            except:
                traceback.print_exc()
                exit()
    
    os.chdir( cwd )

