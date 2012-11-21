#!/usr/bin/env python
#
'''
Provides version stamp to embed in binaries and file names.
'''
import sys
import os
import subprocess
import check_output
import ioutil
import datetime
import sandbox
import optparse

SB = sandbox.current
TOP = SB.get_top_component()

def _define_options():
    parser = optparse.OptionParser('Usage: %prog [options]\n\nGet current component version stamp.')
    parser.add_option('-c', '--component', dest="component",
                      help="component name",
                      metavar="COMPONENT", default=TOP)
    return parser

def get_current_version_stamp(component = TOP):
    rev = 0
    try:
        path = SB.get_component_path(component, SB.get_component_reused_aspect(component))
        with ioutil.WorkingDir(path) as wd:
            output = subprocess.check_output('bzr revno', shell=True)
            rev = int(output.strip())
    except:
        pass
    now = datetime.datetime.now()
    return '%s.%s.%s.%d' % (now.year - 2007, now.month, now.day, rev)

if __name__ == '__main__':
    parser = _define_options()
    options, args = parser.parse_args(sys.argv)
    print get_current_version_stamp(options.component)
