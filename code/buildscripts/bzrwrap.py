#!/usr/bin/env python
from __future__ import print_function
import argparse
import component
import logging
import os
import sys
import sandbox
import subprocess
import traceback
import vcs

def execute_bzr(command, dir):
    return NotImplemented
#def execute_bzr(command, cwd=None):
#    sb = sandbox.create_from_within(os.getcwd())
#    if not cwd:
#        sandbox.
#        cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'code', 'buildscripts')) get_top_component()
#    process = subprocess.Popen(command, \
#                               stdout=subprocess.PIPE, \
#                               stderr=subprocess.STDOUT, \
#                               shell=True, \
#                               bufsize=1, \
#                               cwd=os.path.dirname(devenv))
#    process = subprocess.Popen(command, shell=True, bufsize=1, cwd=os.path.dirname(msbuild))

def revno(dir):
    sb = sandbox.create_from_within(dir)
    revno = int(vcs.revno(sb.get_component_path(sb.get_top_component(), component.CODE_ASPECT_NAME)))
    #print('revno: {0}'.format(revno))
    print(revno)
    return revno

def parse_command_line():
    parser = argparse.ArgumentParser(description='wrap bzr commands needed by the build for easy digestion')
    parser.add_argument('-c', '--command', dest='command', required=True, help='command for bzr to execute')
    parser.add_argument('dir', metavar='DIR', help='directory to use as cwd')
    args = parser.parse_args()
    return args.command, os.path.abspath(args.dir)

def main():
    command, dir = parse_command_line()
    if command == 'revno':
        return revno(dir)
    else:
        return execute_bzr(command, dir)

if __name__ == '__main__':
    sys.exit(main())
