#!/usr/bin/env python
#
# $Id: loc.py 9319 2011-06-10 02:59:43Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
import sys, os, re, optparse, codecs
from locdata import *

def _read(path):
    f = codecs.open(path, 'r', 'utf-8')
    txt = f.read()
    f.close()
    return txt

def findOp(path):
    data = LocData(path)
    data.find(path)

def importOp(path):
    '''Import translations.'''
    data = LocData(path)
    if len(args) < 2:
        print ('Please specify Zip file or Zip files location.')
        return 1
    sb = sandbox.create_from_within(path)
    importPath = os.path.join(sb.get_root(), 'translations')
    data.importZip(ioutil.norm_folder(importPath), ioutil.norm_folder(args[1]))

def exportOp(path):
    '''Generate a translation batch.'''
    data = LocData(path)
    sb = sandbox.create_from_within(path)
    exportPath = os.path.join(sb.get_root(), 'translations')
    data.export(ioutil.norm_folder(exportPath))

def checkOp(path):
    '''Verify that no extraction is required.'''
    exitCode = 0
    data = LocData(path)
    for component in data.pathsByComponent:
        if data.conf.getMilestone(component) == metadata.UI_FREEZE_MILESTONE:
            tl = data.conf.getTargetedLocales(component)
            if not tl:
                print('Error: No targeted locales are set in metadata.txt.')
                exitcode = 1
            elif len(tl) == 1 and 'en' in tl:
                print('English is the only targeted language. No localization needed.')
            elif tl:
                if data.formatErrors:
                    exitCode = 1
                    for key in data.formatErrors:
                        print ('%s%s\n' % (path, key))
                        for line in data.formatErrors[key]:
                            print ('Please change to the correct format specifiers on line %d.' % line.fileLocs[0].line)
                            print ("%s\n" % line.id)
                if data.possibleMisses:
                    print ('There are possibly strings that need translation that have been missed. Rerun loc.py with the "find" command.')
                    exitCode = 1
                strsWithWarnings, needsSync = data.check(component)
                if strsWithWarnings:
                    print('')
                    exitCode = 1
                    for str in strsWithWarnings:
                        str.warn()
                if needsSync:
                    print("""
    Warning: until a sync has been done, a visual inspection of the UI with
    locale=ma will not be accurate, because the following files are out of date:
    """)
                    for x in needsSync:
                        print('    %s' % x)
                    exitCode = 1
                else:
                    print("""
    Martian is sync'ed with English. This does not mean that translations are
    complete, but it means that visual inspection of the UI with locale=ma will
    accurately detect string extraction problems.""")
            else:
                print ('Localization not supported.')
        elif data.conf.getMilestone(component) == metadata.LOCALIZATION_COMPLETE_MILESTONE:
            exitCode, strsWithWarnings, needsSync = data.checkComplete(component)
            if exitCode == 0:
                if data.formatErrors:
                    exitCode = 1
                    for key in data.formatErrors:
                        print ('%s%s\n' % (path, key))
                        for line in data.formatErrors[key]:
                            print ('Please change to the correct format specifiers on line %d.' % line.fileLocs[0].line)
                            print ("%s\n" % line.id)
                if data.possibleMisses:
                    print ('There are possibly strings that need translation that have been missed. Rerun loc.py with the "find" command.')
                    exitCode = 1
                if strsWithWarnings:
                    print('')
                    exitCode = 1
                    for str in strsWithWarnings:
                        str.warn()
                if needsSync:
                    print("""
    Warning: until a sync has been done, a visual inspection of the UI with
    locale=ma will not be accurate, because the following files are out of date:
    """)
                    for x in needsSync:
                        print('    %s' % x)
                    exitCode = 1
                else:
                    print("""
    Martian is sync'ed with English. This does not mean that translations are
    complete, but it means that visual inspection of the UI with locale=ma will
    accurately detect string extraction problems.""")
        else:
            print ('UI not ready for localiztion.')
    return exitCode

def syncOp(folder, dryRun=False):
    '''Find all English strings. Generate Martian and placeholders in localized equivalents.'''
    data = LocData(folder)
    updatedFiles = data.sync()

_FUNCTYPE = type(syncOp)
def _getValidOps(symbols):
    candidates = [f for f in symbols.keys() if (not f.startswith('_')) and f.endswith('Op')]
    funcs = {}
    for f in candidates:
        x = symbols[f]
        if type(x) == _FUNCTYPE:
            funcs[f[0:-2]] = x
    return funcs
_OPs = _getValidOps(locals())
del _getValidOps

import sandbox, xmail, codescan

usage = 'Usage: %%prog %s [options]\n\nDo localization work. Optionally, email report of errors.' % '|'.join(_OPs.keys())
parser = optparse.OptionParser(usage)
parser.add_option('--coderoot',
    dest="coderoot",
    help="Path where code for all components is stored. Default = " + sandbox.current.get_code_root(),
    metavar="FLDR",
    default=sandbox.current.get_code_root())
xmail.addMailOptions(parser)

if __name__ == '__main__':
    exitCode = 1
    ( options, args ) = parser.parse_args()
    complainAboutOp = not args
    if not complainAboutOp:
        op = args[0]
        if not op in _OPs:
            complainAboutOp = True
    if complainAboutOp:
        print('Expected operation: ' + '|'.join(_OPs.keys()))
    else:
        op = _OPs[op]
        folder = options.coderoot
        folder = ioutil.norm_folder(folder)
        oldStdout = None
        sendEmail = xmail.hasDest(options)
        if sendEmail:
            oldStdout = sys.stdout
            sys.stdout = FakeFile()
        try:
            #print('%s %s...\n' % (args[0], folder))
            exitCode = op(folder)
            if sendEmail:
                msg = sys.stdout.txt
                print(msg)
                sys.stdout = oldStdout
                oldStdout = None
                xmail.sendmail(msg, sender='Localizer <code.scan@example.com>',
                    subject='localize %s report on %s' % (op, metadata.get_friendly_name_for_path(folder)), options=options) # TODO Configurable reporting email address
        finally:
            if oldStdout:
                sys.stdout = oldStdout
    print('exiting with code=%s' % str(exitCode))
    sys.exit(exitCode)
