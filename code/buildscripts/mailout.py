#!/usr/bin/env python
# 
# $Id: mailout.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 

import optparse, sys, os, subprocess, xmail

parser = optparse.OptionParser('Usage: %prog --to ADDRLIST --sender ADDR --subject SUB [options] ["commandline"]\n\nRun an arbitrary command and email its stdout/stderr.')
parser.add_option('--body', dest="body", help="Body of the email if you are not running a command.")
xmail.addMailOptions(parser, sender=True, subject=True)

def mailout(args, options):
    if args:
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        txt = process.stdout.read()
        process.wait()
    elif options.body:
        if os.path.exists(options.body):
            body = open(options.body, 'r')
            txt = body.read()
            body.close()
        else:
            txt = ''
    else:
        txt = ''
    xmail.sendmail(txt, options=options)

def _requireArgs(options, *names):
    errors = []
    for name in names:
        if hasattr(options, name):
            if getattr(options, name):
                continue
        errors.append('Missing required -%s argument.' % name[0])
    return errors

def main(*argv):
    options, args = parser.parse_args()
    errors = _requireArgs(options, 'to', 'sender', 'subject')
    #if not args: errors.append('Missing commandline to run.')
    if errors:
        parser.error('\n'.join(errors))
    exitCode = mailout(args, options)
    if args:
        print('Ran "%s"; mailed output to %s.' % (args, options.to))
    return exitCode

if __name__ == '__main__':
    sys.exit(main(True, *sys.argv))
