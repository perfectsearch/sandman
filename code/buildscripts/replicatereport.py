import time
import os
import sys
import shutil
import subprocess
import argparse
import datetime
from branchinfo import BranchInfo, BranchInfoCache
from filelock import FileLock

def replicatereport(reporoot, server):
    tmp = reporoot.replace('\\','/').rstrip('/')
    reportroot = tmp[:tmp.rfind('/')] + '/reportroot'
    lock_file = '%s/lock' % reportroot
    with FileLock(lock_file, 5):
        timeFile = '%s/lastupdate.txt' % reportroot
        if server and os.path.exists(timeFile):
            finished = open(timeFile, 'r')
            finished = finished.read()
            date, t = finished.split()
            year, month, day = date.split('-')
            hour, min, sec = t.split(':')
            sec, micro = sec.split('.')
            finished = datetime.datetime(int(year), int(month), int(day), int(hour), int(min), int(sec), int(micro))
            if datetime.datetime.now() - finished < datetime.timedelta(minutes = 1):
                return
        while True:
            try:
                p = subprocess.Popen('bzr fast-branches %s' % reporoot, stdout = subprocess.PIPE, shell=True)
                reports = []
                output = p.stdout.read()
                for x in output.split('\n'):
                        if x.strip():
                            parts = x.split()
                            if len(parts) == 4:
                                reports.append(parts)
                            elif len(parts) == 3:
                                parts.append('none')
                                reports.append(parts)
                reports = [r for r in reports if r[2] == 'report']
                print 'xxxxxxxxxxxx'
                for report in reports:
                    bi = BranchInfo(branchname=report[0], componentname=report[1], aspectname=report[2])
                    branchdir = bi.get_branchdir(reporoot)
                    reportdir = bi.get_branchdir(reportroot)
                    if not os.path.exists(reportdir):
                        print 'Checking out %s.' % reportdir
                        os.makedirs(reportdir)
                        os.system('bzr co --lightweight %s %s' % (branchdir, reportdir))
                    else:
                        print 'Updating %s.' % reportdir
                        os.system('bzr up -q %s' % reportdir)
                for branch in os.listdir(reportroot):
                    rdir = os.path.join(reportroot, branch).replace('\\','/')
                    bdir = os.path.join(reporoot, branch).replace('\\','/')
                    if not os.path.exists(bdir):
                        print 'Removing %s' % rdir
                        shutil.rmtree(rdir,True,handleRmtree)
                    else:
                        for comp in os.listdir(rdir):
                            crdir = os.path.join(rdir, comp).replace('\\','/')
                            cbdir = os.path.join(bdir, comp).replace('\\','/')
                            if not os.path.exists(cbdir):
                                print 'Removing %s' % crdir
                                shutil.rmtree(crdir,True,handleRmtree)
            except KeyboardInterrupt:
                sys.exit(0)
            except:
                print(sys.exc_info()[1])
                time.sleep(10)
            if server:
                finished = open(timeFile, 'w')
                finished.write(str(datetime.datetime.now()))
                finished.close()
                break
            time.sleep(60)


def handleRmtree():
    pass

parser = argparse.ArgumentParser()
parser.add_argument('--server', dest='server', default=False, action='store_true')
parser.add_argument('-r', dest='reporoot', type=str, required=True)

if __name__ == '__main__':
    args = parser.parse_args()
    replicatereport(args.reporoot, args.server)
