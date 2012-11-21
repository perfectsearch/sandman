#!/usr/bin/env python
# 
# $Id: flatten_file.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 
import sys, os, optparse
from ioutil import *

parser = optparse.OptionParser('Usage: %prog path \n\n flatten files to a single line')

if __name__ == '__main__':
    ( options, args ) = parser.parse_args()
    folder = None
    
    if len(args) < 1:
        print parser.format_help()
        sys.exit(0)
    
    if args:
        file = args[0]
    
    if not os.path.exists(file):
        sys.exit(0)
    
    openfile = open(file, 'rt')
    
    for line in openfile:
        sys.stdout.write(' ')
        sys.stdout.write(line.strip())
    
    openfile.close()
    
    sys.exit(0)
