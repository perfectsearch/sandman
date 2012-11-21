import os
import shlex
import sys
import subprocess

class Command(subprocess.Popen):
    def __init__(self, command):
        self.command = command
        if os.name == 'nt':
            self.use_shell = True
            self.args = shlex.split(command)
        else:
            self.use_shell = True
            self.args = command

        #print( "Running: subprocess.Popen( %s, shell=%s )" % (repr(self.args),self.use_shell) )
        subprocess.Popen.__init__( self, self.args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=self.use_shell )
        self.remaining_output = []
        self.finished = False
        
    def get_output(self):
        if self.finished:
            if len(self.remaining_output) > 0:
                return self.remaining_output.pop(0).strip()
            else:
                return None
        elif self.poll() is not None:
            #print( "getting remaining stdout" )
            self.remaining_output = self.stdout.readlines()
            self.finished = True
            if len( self.remaining_output ) > 0:
                return self.remaining_output.pop(0).strip()
            else:
                return None
        else:
            #print( "getting a line" )
            stdout = self.stdout.readline()
            return stdout.strip()

