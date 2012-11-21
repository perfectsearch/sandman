import os.path
from lxml import etree
import testsupport

from textui import ansi
from textui import colors
from textui.prompt import prompt

DEFAULT_SETUP_FILE = os.path.expanduser(os.path.join('~', 'test_setup.xml'))
SANDBOX_SETUP_FILE = os.path.join(testsupport.TESTROOT, 'test_setup.xml')
filepath = None #This must be set to DEFAULT_SETUP_FILE or SANDBOX_SETUP_FILE before this module is used
pprintParser = etree.XMLParser(remove_blank_text=True)

def setSetupFile(useMaster=False):
    '''sets filepath to SANDBOX_SETUP_FILE if the file exists otherwise set it to DEFAULT_SETUP_FILE'''
    global filepath
    if os.path.exists(SANDBOX_SETUP_FILE) and not useMaster:
        filepath = SANDBOX_SETUP_FILE
    else:
        filepath = DEFAULT_SETUP_FILE
    checkForSetupFile()

def prompt_bool(msg, default='n'): #textui.prompt.prompt_bool should probably be replaced with this, and used instead
    '''
    Ask user for a yes/no answer.

    @param default If None, don't default and keep asking until either 'y'
           or 'n' is received. Otherwise, use the default value if neither
           'y' or 'n' is recieved
    '''
    while True:
        ansi.writec(msg)
        if default == 'y': 
            ansi.writec(' (Y/n) ', colors.PARAM_COLOR)
        if default == 'n':
            ansi.writec(' (y/N) ', colors.PARAM_COLOR)
        else:
            ansi.writec(' (y/n) ', colors.PARAM_COLOR)
        
        answer = raw_input().strip().lower()

        if answer == 'y': 
            return True
        if answer == 'n': 
            return False
        if default != None: 
            return

def checkForSetupFile():
    '''create and initialize setup file if it doesn't exist or if it's empty'''
    if not os.path.exists(filepath):
        with open(filepath, 'w') as fh:
            fh.write('<test_setup></test_setup>')
    fh = open(filepath)
    if fh.read().strip() == '':
        fh.close()
        fh = open(filepath, 'w')
        fh.write('<test_setup></test_setup>')
    fh.close()

def getSetupXml():
    '''returns the xml currently stored in the setup file'''
    with open(filepath) as fh:
        return fh.read()
    
def setSetupXml(xml):
    '''overwrites the xml stored in the setup file'''
    with open(filepath, 'w') as fh:
        fh.write(xml)
        
def getLocation():
    '''get the location stored in the setup file'''
    root = etree.fromstring(getSetupXml(), pprintParser)
    if root.find('location') == None:
        return None
    return root.find('location').values()[0]
    
def setLocation(location):
    '''change the location stored in the setup file'''
    root = etree.fromstring(getSetupXml(), pprintParser)
    if getLocation():
        locationElement = root.find('location')
    else:
        locationElement = etree.Element('location')
    locationElement.set('location', location)
    root.append(locationElement)
    setSetupXml(etree.tostring(root, pretty_print=True))
    
def getArgs():
    '''get the args stored in the setup file'''
    root = etree.fromstring(getSetupXml(), pprintParser)
    if root.find('args') == None:
        return None
    return root.find('args').values()[0]  
    
def setArgs(args):
    '''change the args stored in the setup file'''
    root = etree.fromstring(getSetupXml(), pprintParser)
    if getArgs():
        argsElement = root.find('args')
    else:
        argsElement = etree.Element('args')
    argsElement.set('args', args)
    root.append(argsElement)
    setSetupXml(etree.tostring(root, pretty_print=True))

def getAppliances():
    '''get a list of all the appliances currently in the setup file'''
    root = etree.fromstring(getSetupXml())
    return [e.values()[0] for e in root.findall('appliances')]

def setAppliance(appName, host, user, passwd):
    '''change/add/remove and appliance stored in the setup file'''
    def addElement(elementName, elementText):
        if elementText:
            newElement = etree.Element(elementName)
            newElement.text = elementText
            applianceElement.append(newElement)

    applianceElement = etree.Element('appliances')
    applianceElement.set('appliance', appName)
    
    addElement('ipaddress', host)
    addElement('username',  user)
    addElement('password',  passwd)
    
    setApplianceElement(applianceElement)
    
def setApplianceElement(applianceElement):
    '''change/add an appliance stored in the setup file using an lxml element'''
    delAppliance(applianceElement.values()[0])
    root = etree.fromstring(getSetupXml(), pprintParser)
    root.append(applianceElement)
    setSetupXml(etree.tostring(root, pretty_print=True))
        
def delAppliance(applianceName):
    '''remove all instances of a specific appliance from the setup file'''
    root = etree.fromstring(getSetupXml())
    for e in [e for e in root.findall('appliances') if e.values()[0] == applianceName]:
        root.remove(e)
    setSetupXml(etree.tostring(root, pretty_print=True))
    
def getAppInfo(appName):
    '''Get information about an existing appliance from the setup file'''                                     
    root = etree.fromstring(getSetupXml())
    for e in root.findall('appliances'):
        if e.values()[0] == appName:
            break
    else:
        return None
    host     =  e.findtext('ipaddress')
    user     =  e.findtext('username')
    password =  e.findtext('password')
    return (host, user, password)
    
def displayApplianceInfo(appName):
    '''print out information about an appliance'''
    import sys
    print 'appliance "' + appName + '" has been set up with the' \
          'ip address "%s" the username "%s" and the password "%s"' % getAppInfo(appName)
    print 'info about all of the appliances are listed below' '\n'

    for appName in getAppliances():
        appInfo = getAppInfo(appName)
        appInfo = (appName,) + appInfo
        for i in appInfo:
            i += '\t'
            sys.stdout.write(i.expandtabs(8))
        print   
        
def checkCredentials(host, user, passwd):
    '''checks if a login is possible with the credentials entered for an appliance'''
    #print not Working
    try:
        import requests, socket
        session = requests.session(verify=False) #the session will store the login cookies once we're logged in
        
        #check if the PSA is up
        try: 
            socket.create_connection((host, '80')).close()
        except: 
            raise Exception('could not connect to the PSA at %s. Is the PSA is running?' % host)

        #logout if we are logged in
        try: 
            session.get('https://%s/account/logout' % host)
        except: 
            pass
        
        #try to login to the PSA
        loginResponse = session.get('https://%s/account/dologin?login=%s&password=%s' % (host, user, passwd))
        whoami = session.get('https://%s/appliance/whoami' % host) 

        assert loginResponse and whoami, 'bad or no status code(s) recieved.'
        if '<username>%s</username>' % user not in whoami.content:
            raise Exception('After attempting to login, the user %s was not found in the whoami response.' % user)
        
        ansi.printc('successfully logged into %s'%host, colors.CMD_COLOR)
        return True
        
    except Exception, exc:
        errorMsg = 'Error logging into Existing Appliance object with the credentials\n' \
                   + 'host: %s  username: %s  password: %s\n' % (host, user, passwd) \
                   + str(exc)
        ansi.eprintc(errorMsg, colors.ERROR_COLOR)
        return False

def configAppliance():
    '''interactively configure an appliance'''

    appName = prompt("\nEnter the name of an existing/new appliance: ", default=None)
    assert appName

    oldHost = oldUser = oldPasswd = None
    
    if appName in getAppliances():
        oldHost, oldUser, oldPasswd = getAppInfo(appName)

        ansi.printc('\nwhat do you want to do with the appliance %s' % appName)
        ansi.writec('type '); ansi.writec('c', colors.PARAM_COLOR);     ansi.printc(' to change the appliance configurations')
        ansi.writec('type '); ansi.writec('r', colors.PARAM_COLOR);     ansi.printc(' to remove the appliance from the setup file')
        ansi.writec('type '); ansi.writec('v', colors.PARAM_COLOR);     ansi.printc(' to view info about the appliance\'s configuration')
        ansi.writec('type '); ansi.writec('check', colors.PARAM_COLOR); ansi.printc(' to check the credentials of the appliance')
        response = prompt('\n', choices='options: c, r, v, check', default='v')
        
        if response == 'c':
            print 'Changing an appliance isn\'t working right now \n the setup file must be manually changed'
            pass
        elif response == 'v':
            displayApplianceInfo(appName)
            return
        elif response == 'r':
            delAppliance(appName)
            return
        elif response == 'check':
            checkCredentials(oldHost, oldUser, oldPasswd)
            return
        else:
            ansi.eprintc('not a valid option', colors.ERROR_COLOR)
            return

    host =   prompt('\nwhat is the ip address for "%s"'             % appName, default=oldHost)
    name =   prompt('\nwhat is the username for the appliance "%s"' % appName, default=oldUser)
    passwd = prompt('\nwhat is the password for "%s"'               % appName, default=oldPasswd)

    if prompt_bool('\nWould you like to check the entered credentials for "%s"? (%s must be running):' % (appName, appName)):
        if not checkCredentials(host, name, passwd):
            ansi.printc('failed to set up %s' % appName, colors.WARNING_COLOR)
            return
            
    print '\n%s successfully configured. You can now use the appliance %s ' \
          'to run tests by using the command' % (appName, appName)
    ansi.printc('sb test --psa %s\n' % appName, colors.TITLE_COLOR)

    setAppliance(appName, host, name, passwd)
    return
    
    
def configLocation():
    '''interactively configure a location for local tests'''
    while True:
        ansi.writec('\nwhere are you located(')
        ansi.writec('ps-orem, DSR, or other', colors.PARAM_COLOR)
        ansi.writec(') this is for tests like the NetApp connnector tests that require a local machine: ')

        response = raw_input().lower().strip()
        if response == 'ps-orem' or response == 'orem':
            setLocation('ps-orem')  
            break
        if response == 'dsr':
            setLocation('dsr')      
            break
        if response == 'other':
            setLocation('other')       
            break   
        ansi.eprintc('that location does not yet exist', colors.WARNING_COLOR)
        
def configArgs():
    setArgs(raw_input('\ntype in the args you would like to automatically be used each time you run sb test' '\n'))

def setup():
    '''interactively edit the setup file. filepath must first be set'''
    checkForSetupFile()

    location = getLocation()
    if location:
        if prompt_bool('\nlocation has been configured as "%s", would you like to change this' % location):
            configLocation()
    else:
        configLocation()

    while True:
        if getAppliances() and not prompt_bool('\nDo you want to add/change/remove/view/check ' + \
                                'an appliance that is to be used when running local tests?'):
            break
        configAppliance()
        while True:
            if not prompt_bool('\nDo you want to add/change/remove/view/check another appliance?'):
                break
            configAppliance()
        break
        
    currentArgs = getArgs()
    if currentArgs:
        ansi.printc('\ncurrently sb test is adding the following args')
        ansi.writec(currentArgs, colors.PARAM_COLOR)
    if prompt_bool('\nsb test can be configured to always add arguments like -s ' '\n' \
                         'I have this configured to add' '\n' \
                         '-s --no-build-first --skip-compiled  --nologcapture' '\n' \
                         'to sb test' '\n' \
                         'for most people this is an unneccessary configuration' '\n'
                         'would you like to configure this'):
        configArgs()

def defaultSetup():
    '''call this to interactively edit the default setup file 
    that is used when a sandbox level setup file hasn't been set up'''   
    global filepath
    filepath = os.path.expanduser(os.path.join('~', 'test_setup.xml'))
    setup()
    
def sbSetup():
    '''call this to interactively edit the setup file for the current sandbox'''
    global filepath
    
    if not os.path.exists( os.path.expanduser(os.path.join('~', 'test_setup.xml')) ):
        ansi.printc('Default setup file must be set up before a sandbox level setup file can be set up', colors.ERROR_COLOR)
        ansi.printc('Entering setup for default setup file', colors.WARNING_COLOR)
        filepath = os.path.expanduser(os.path.join('~', 'test_setup.xml'))
        setup()
        return
        
    filepath = os.path.join(testsupport.TESTROOT, 'test_setup.xml')
    setup()

if __name__ == '__main__':
    setup()
    
