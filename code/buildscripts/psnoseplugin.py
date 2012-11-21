import os
from nose.plugins import Plugin

IS_TEST = 'this_is_a_test'


class PSNosePlugin(Plugin):
    name = 'PSNosePlugin'

    #def options(self, parser, env=os.environ):
        #Plugin.options(self, parser, env)

    def configure(self, options, conf):
        Plugin.configure(self, options, conf)
        self.enabled = True

    def wantDirectory(self, dirname):
        if os.path.basename(dirname) == 'data':
            return False
        return True

##    def wantMethod(self, method):
##        if not hasattr(method, IS_TEST):
##            return False
##        return None

##    def wantFunction(self, function):
##        if not hasattr(function, IS_TEST):
##            return False
##        return None

    def wantFile(self, file):
        if file.endswith('_test.py'):
            return True
        return False

    #def wantModule(self, module):
        #return True

##    def wantClass(self, cls):
##        if not hasattr(cls, IS_TEST):
##            return False
##        return None

