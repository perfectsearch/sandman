import os, sys, time, shutil, os.path
import subprocess
from time import strftime

from textui import ansi
from textui import colors

debug=False

EXTERNAL_VM_PATH = r'\\fortknox\data\vms\dev\linux-auto.ova'
LOCAL_VM_PATH = os.path.expanduser(os.path.join('~', 'linux-auto.ova'))

DEFAULT_RELEASE_BRANCH = 'example' ## TODO Kim fix me
DEFAULT_BRANDING = 'example' ## TODO Kim fix me
DEFAULT_MIRROR = 'http://10.10.10.50/dev'

def autoCreatePSA():
    '''creates a PSA, and returns the ipaddress and name of the PSA'''
    from time import strftime
    name = strftime('Auto-PSA_%d-%M-%Y--%I%S')
    return createPSA(name), name

def createPSA(name, branding=DEFAULT_BRANDING, release=DEFAULT_RELEASE_BRANCH, repo=None):
    '''creates a PSA with the specified name, branding, and release branch
    if repo is specified, the branding and release branch of the specified
    repo will be used instead'''
    
    copyVM()

    #create a new VM
    vm = VM(name, 'root', 'psa')    
    if vm.exists():
        if vm.getState() == 'running':
            print 'shutting down VM...'
            vm.forceStop()
        vm.revert()
    else:
        print '\nCreating new VM...'
        vm.importVM(LOCAL_VM_PATH)
        vm.modify(memory = '1024', cpus = '2', memoryBalloon = '512')
        vm.save()

    #convert newly created VM into a PSA by copying and installing RPMs
    vm.start()
    print '\nConverting VM to a PSA...'
    time.sleep(5)
    vm.copyPSAtoVM(psaBranding=branding, release=release, fullMirrorPath=repo)
    time.sleep(5)
    vm.installPSA(psaBranding=branding)
    vm.update()
    print '\n\n PSA sucessfully installed!'
    
    print 'Restarting VM after PSA install'
    vm.stop()
    vm.start()
    vm.save('psa-install')

    IPAddress = vm.getIPAddress()
    sys.stdout.write('\nIP Address of newly installed PSA is ')
    ansi.printc(str(IPAddress), colors.TITLE_COLOR)
    return IPAddress

def copyVM():
    '''copy a .ova file of a vanilla Linux VM from fort knox'''
    if not os.path.exists(LOCAL_VM_PATH):
        print 'copying files over the network...'
        if os.name == 'nt':
            shutil.copy(EXTERNAL_VM_PATH, LOCAL_VM_PATH)
        else:
            if not os.path.exists('/mnt/auto-linux/'):
                os.system('sudo mkdir /mnt/auto-linux/')
            os.system('sudo mount -t cifs //fortknox/data/vms/dev/ /mnt/auto-linux/')
            shutil.copy('/mnt/auto-linux/linux-auto.ova', LOCAL_VM_PATH)
    assert os.path.exists(LOCAL_VM_PATH)
      
class VM(object):
    ''' Class to control VMs '''
    def __init__(self, name, username, password):
        ''' Ctor takes the name of the vm as a string '''
        self.vmName = name
        self.user = username
        self._password = password
        
    def modify(self, memory=None, vram=None, cpus=None, memoryBalloon=None, pagefusion=False):
        '''changes the settings of the VM
        the VM must be off
        the memoryBalloon is memory that can be shared between VMs
        memory, vram. memoryBalloon is specified in magabytes
        pagefusion removes memory duplication between VMs'''
        if memory: 
            runCmd('VBoxManage modifyvm "%s" --memory %s' % (self.vmName, memory))
        if vram: 
            runCmd('VBoxManage modifyvm "%s" --vram %s' % (self.vmName, vram))
        if cpus: 
            runCmd('VBoxManage modifyvm "%s" --cpus %s' % (self.vmName, cpus))
        if memoryBalloon: 
            runCmd('VBoxManage modifyvm "%s" --guestmemoryballoon  %s' % (self.vmName, memoryBalloon))
        pagefusion = 'on' if pagefusion else 'off'
        runCmd('VBoxManage modifyvm "%s" --pagefusion %s' % (self.vmName, pagefusion))

    #TODO use self.guestProperty() too tell when the VM is up #waitGuestProperty()?
    def start(self, timeout=200): #TODO something is making this slower than a normal boot up of a PSA. (VBoxManage guestcontrol?)
        ''' Function to start the vm'''
        runCmd('VBoxManage startvm ' + self.vmName, printout=True)

        def output():
            print
            while True:
                yield sys.stdout.write('\rwaiting for VM %s to boot up.  ' % self.vmName)
                yield sys.stdout.write('\rwaiting for VM %s to boot up.. ' % self.vmName)
                yield sys.stdout.write('\rwaiting for VM %s to boot up...' % self.vmName)
        outputGen = output()
        
        #wait for the VM to start up
        for i in range(timeout / 5):
            time.sleep(5)
            try:
                out = self.runCmd('/bin/uname')
            except VBoxManageError as err:
                if err.msg.startswith('\n0%...'): #ignoring VBoxManage bug
                    pass
                #I'm ignoring this error, and breaking out of the loop as the VM is up and running when this error occurs
                if 'VBoxManage.exe: error: Process execution failed: The specified file was not found on guest.' in err.msg:
                    break
                #This is the error that we get from trying to issue the uname command when we haven't finished booting
                #I'm hiding this error and instead printing out that we are waiting for the VM to boot up
                if 'VBoxManage.exe: error: The guest execution service is not ready (yet).' in err.msg:
                    outputGen.next()
            else:
                #Once the VM is up the uname command will be sucessful and the word Linux will be outputed
                if out == 'Linux':
                    break
        else:
            raise TimeOutError

        time.sleep(1)
        print '\nVM is up'

    def stop(self):
        '''stops the vm'''
        runCmd('VBoxManage controlvm ' + self.vmName + ' acpipowerbutton', printout=False)
        for i in range(50 / 5):
            time.sleep(5)
            if self.getState() == 'powered off':
                return
        else:
            print 'Failed to halt the VM. Forcing power off.'
            self.forceStop()

    def forceStop(self):
        runCmd('VBoxManage controlvm ' + self.vmName + ' poweroff', printout=True)
        for i in range(20 / 5):
            time.sleep(5)
            if self.getState() == 'powered off':
                return
        else:
            raise TimeOutError

    def save(self, snapshot='linux-install', description=None):
        '''creates a snapshot of the VM'''
        if description is None:
            description = time.strftime('%x')
        resp = self._snapshot('VBoxManage snapshot ' + self.vmName + ' take ' + snapshot + ' --description ' + description)
        if not resp:
            raise Exception('Failed to create the snapshot "%s"' % snapshot)

    def deleteSnapshot(self, snapshot):
        '''removes a snapshot of the VM'''
        resp = self._snapshot('VBoxManage snapshot ' + self.vmName + ' delete ' + snapshot)
        if not resp:
            raise Exception('Failed to remove the snapshot "%s"' % snapshot)
            
    def revert(self, snapshot='linux-install'):
        '''reverts the VM to the given snapshot.'''
        resp = self._snapshot('VBoxManage snapshot %s restore %s' % (self.vmName, snapshot))
        if not resp:
            raise Exception('Reverting to the snapshot "%s" failed. Make sure you are using a VM that was auto created with this script' % snapshot)

    def _snapshot(self, cmd):
        try:
            runCmd(cmd, printout=True)
        except VBoxManageError as err:
            if err.msg.startswith('\n0%...'): #ignoring VBoxManage bug
                pass
            else:
                ansi.printc(err.msg, colors.ERROR_COLOR)
                raise Exception('Reverting to the snapshot "%s" failed. Make sure you are using a VM that was auto created with this script' % snapshot)

    def getIPAddress(self):
        ''' Function that will return the ip address of the current vm '''
        return guestProperty('/VirtualBox/GuestInfo/Net/0/V4/IP')
        #out = self.runCmd('/sbin/ifconfig',  'eth1')
        #if not out:
            #print 'could not auto detect ip address'
            #return None
        #for line in out.splitlines():
            #if 'inet addr:' in line:
                #ipAddress = line[line.find('inet addr:') + len('inet addr:') : line.find(' Bcast:') - 1]

        #self.ipAddress = ipAddress        
        #return ipAddress

    def copyPSAtoVM(self, mirrorRoot = DEFAULT_MIRROR, release=DEFAULT_RELEASE_BRANCH, psaBranding=DEFAULT_BRANDING, fullMirrorPath=None):
        ''' Function that will copy the RPM's of a PSA to the specified vm '''
        mirror = mirrorRoot + '/' + release + '/' + psaBranding + '-appliance/centos/6/install/' + release + '-' + psaBranding + '-appliance.repo'
        if fullMirrorPath:
            mirror = fullMirrorPath
        print 'Creating PSA from', mirror
#        self.runCmd('/usr/bin/wget', '-P /etc/yum.repos.d/ %s' % mirror, printout=True)
        os.system('VBoxManage guestcontrol ' + self.vmName + ' execute --image "/usr/bin/wget" --username ' + self.user + ' --password ' + self.password +
                  ' --wait-exit --wait-stdout -- -P /etc/yum.repos.d/ ' + mirror)
        
    def installPSA(self, psaBranding=DEFAULT_BRANDING):
        ''' Function that will install the psa to the vm '''
#        self.runCmd('/usr/bin/yum', '-y install %s-appliance.noarch' % psaBranding, printout=True)
        os.system('VBoxManage guestcontrol ' + self.vmName + ' execute --image "/usr/bin/yum" --username ' + self.user + ' --password ' + self.password +
                 ' --wait-exit --wait-stdout --timeout 90000 -- -y install ' + psaBranding + '-appliance.noarch')
        print
        raise Exception('yum installing from the host machine isn\'t working anymore :(')
    def update(self):
        self.runCmd('/usr/bin/yum', 'update', printout=True)

    def getState(self):
        '''gets the state of the vm'''
        out = runCmd('VBoxManage showvminfo ' + self.vmName)
        for line in out.splitlines():
            if line.startswith('State:'):
                return line[line.find('State:') + len('State:') : line.find('(since')].strip()

    def getIPAddress(self):
        '''gets the ip address'''
        return runCmd('VBoxManage guestproperty get %s /VirtualBox/GuestInfo/Net/0/V4/IP' % self.vmName)[7:]

    def exists(self):
        '''checks if the VM has been registered with VirtualBox'''
        return self.vmName in runCmd('VBoxManage list vms')

    def changePassword(self, passwd):
        out = self.runCmd('/bin/echo', '%s | /usr/bin/passwd %s' % (passwd, self.user))
        assert 'all authentication tokens updated' in out
        self.password = passwd

    def update(self):
        self.runCmd('/usr/bin/yum', 'update', True)

    def guestProperty(self, property):
        '''virtual box keeps track of different peices of information about its' vms
        use this function to retreive one of those properties
        see the following website for a list of available properties
        http://www.virtualbox.org/manual/ch04.html#guestadd-guestprops
        the VM must be running in for this to work'''
        runCmd('VBoxManage guestproperty get "%s" %s' % (self.vmName, property) )[7:]

    def loggedInUsers(self):
        return self.guestProperty('/VirtualBox/GuestInfo/OS/LoggedInUsersList')

    def runCmd(self, processPath, argStr='', printout=False):
        '''runs a command line command on the VM and returns the output
        processPath is the process on the VM that is to be run for example /usr/bin/yum
        argStr is a string of arguments to passed into the process
        printout and printerr controls what gets printed to the screen'''

        cmd = 'VBoxManage guestcontrol ' + self.vmName + ' execute --image "' + processPath + '" --username ' + self.user + ' --password ' + self.password + \
              ' --wait-exit --wait-stdout --timeout 4000 -- ' + argStr

        return runCmd(cmd, printout)

def runCmd(cmd, printout=False): #TODO fix this so that printout works properly
    '''runs a commandline command and returns the output
    printout controls if the output gets printed to the screen
    if printout is True, None will always be returned'''
    
    if debug:
        printout = True
        print cmd

    if printout:
        proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, stdin=sys.stdout, shell=True)
    else:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    
    if err and err != '0':
        raise VBoxManageError(err)
    
    return out

class VBoxManageError(Exception):
    def __init__(self, msg):
        self.msg = '\n' + msg
    def __str__(self):
        return self.msg
class TimeOutError(Exception):
    pass

if __name__ == '__main__':
    autoCreatePSA()
