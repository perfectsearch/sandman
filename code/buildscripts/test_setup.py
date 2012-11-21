from interactive_test_setup import *

def setup(location=None, appliance=None, defaultArgs=None):
    setSetupFile()

    if location:
        configLocation(location)
        
    if appliance:
        configAppliance(appliance['name'], appliance['host'], appliance['user'], appliance['passwd'])
    
    if defaultArgs:
        configArgs(defaultArgs) 


def configAppliance(name, host, user, passwd):
    setAppliance(name, host, user, passwd)
    
    if not checkCredentials(host, user, passwd):
        ansi.printc('unable to log into %s if the appliance isn\'t running this is fine.' % name, colors.WARNING_COLOR)
            
    print '\n%s successfully configured. You can now use the appliance %s ' \
          'to run tests by using the command' % (name, name)
    ansi.printc('sb test --psa %s\n' % name, colors.TITLE_COLOR)

def configLocation(location):
        if location == 'ps-orem' or location == 'orem':
            setLocation('ps-orem')  
            return
        if location == 'dsr':
            setLocation('dsr')      
            return
        if location == 'other':
            setLocation('other')
            return
        raise Exception('that location does not yet exist')

def configArgs(args):
    setArgs(args)
