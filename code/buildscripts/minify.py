#!/usr/bin/env python
#
# $Id: sandbox.py 5794 2011-03-11 22:35:32Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import sys, os, subprocess, optparse, re
import check_output
import sandbox
import build
import webservices


def _define_options():
    description = "Make specified targets using tools appropriate for codebase."
    usage = "Usage: %prog [options] [targets]"
    parser = optparse.OptionParser(usage=usage, description=description)

    parser.add_option('--sandbox', dest="sandbox", help="path to sandbox to build",
                      metavar="FLDR", default=sandbox.current.get_root())
    return parser

def parse_args(argv):
    parser = _define_options()
    args_options, args = parser.parse_args(argv)
    return args, args_options

class Minifier:
    def __init__(self, type, br):
        self.type = type
        self.br = br
        
    def get_js_dir(self):
        if self.type == 'adminportal':
            return self.br + 'webapp/adminportal/adminportal/public/scripts'
        elif self.type == 'uibase':
            return self.br + 'webapp/uibase/public/ext4'
        elif self.type == 'search':
            return self.br + 'webapp/uibase/public/search'

    def get_mako_files(self):
        mako_files = []
        if self.type != 'search':
            mako_files.append(self.br + 'webapp/adminportal/adminportal/templates/general.mako')
        if self.type != 'adminportal':
            mako_files.append(self.br + 'webapp/searchui/searchui/templates/search.mako')
        return mako_files

    def get_pattern(self):
        if self.type == 'adminportal':
            return '^.*/appliance-ui/scripts(/.*)".*$'
        elif self.type == 'uibase':
            return '^.*script.*/ui-base/ext4(/.*)".*$'
        elif self.type == 'search':
            return '^.*script.*/ui-base/search(/.*)".*$'
    
    def get_jsmin_call(self):
        call = self.br + "/buildscripts/jsmin"
        host = webservices.getHostOS()

        if (re.search('win', host)):
            call += ".exe"

        return call + " < "

    def do_minify(self):
        mako_files = self.get_mako_files()

        js_file_test = re.compile(self.get_pattern())
        js_min_file_test = re.compile(self.type + '.js')

        files = []
        for mako in mako_files:
            fh = open(mako, 'r')
            for line in fh:
                result = js_file_test.search(line)
                if result != None and js_min_file_test.search(line) == None and files.count(result.group(1)) == 0:
                    files.append(result.group(1))
            fh.close()

        fh = open(self.get_js_dir() + '/' + self.type + '.js', 'w')        
        for file in files:
            jsmin_call = self.get_jsmin_call() + self.get_js_dir() + file
            jsmin_output = subprocess.check_output(jsmin_call, shell=True)
            jsmin_output_content = re.sub('\n', '', jsmin_output)
            fh.write(jsmin_output_content + '\n')



def main(argv):
    print("Minifying files")
    args, args_options = parse_args(argv)

    sb = sandbox.create_from_within(args_options.sandbox)
    br = sb.get_built_root()

    types = [ 'adminportal', 'uibase', 'search' ]
    for type in types:
        try: 
            mini = Minifier(type, br)
            mini.do_minify()
        except:
            print "Minify error calling jsmin:\n%s" % sys.exc_info()[0]
            raise

    print("Minify succeeded")


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
