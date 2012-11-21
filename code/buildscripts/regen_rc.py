#!/usr/bin/env python
# 
# $Id: regen_rc.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys, os, re, datetime, stat, codecs

RCFILE_CODEPAGE = 'iso-8859-1'
VER_PAT = re.compile(r'(\s+|")(\d{1,2}\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+)', re.MULTILINE)
COPYRIGHT_PAT = re.compile('(copyright\\s*(\\(c\\)|\xa9|\xc2\xa9)?\\s*(\\d{4})(\\s*--?\\s*(\\d{4}))?)', re.MULTILINE | re.IGNORECASE)
TODAY = datetime.date.today()

def generateVersionString(svnRev, spaces):
    spacer = ''
    if spaces:
        spacer = ' '
    return '%d,%s%d,%s%d,%s%s' % (TODAY.year - 2007, spacer, TODAY.month, spacer, TODAY.day, spacer, svnRev)
    
def getComparableText(txt):
    return txt.replace('\r','').replace('\n','').replace('\t','').replace(' ', '')
    
def rewrite(path, txt):
    fileExists = os.path.isfile(path)
    shouldWrite = not fileExists
    if not shouldWrite:
        f = codecs.open(path, 'rb')
        oldTxt = getComparableText(str(f.read()))
        f.close()
        shouldWrite = (oldTxt != getComparableText(txt))
    if shouldWrite:
        folder, fname = os.path.split(path)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        print('Writing %s' % path)
        f = codecs.open(path + '.tmp', 'wb', RCFILE_CODEPAGE)
        f.write(txt)
        f.close()
        if fileExists:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            os.remove(path)
        os.rename(path + '.tmp', path)
    
def regen(rev, template, outpath):
    f = codecs.open(template, 'rb', RCFILE_CODEPAGE)
    txt = str(f.read())
    f.close()
    newTxt = ''
    offset = 0
    for m in re.finditer(VER_PAT, txt):
        oldVersion = m.group(2)
        spaces = (oldVersion.find(' ') != -1)
        newVersion = generateVersionString(rev, spaces)
        newTxt = newTxt + txt[offset:m.start(2)] + newVersion
        offset = m.end(2)
        if oldVersion.replace(' ', '') != newVersion.replace(' ', ''):
            print('  %s: %s --> %s' % (template, oldVersion, newVersion))
    txt = newTxt + txt[offset:]
    newTxt = ''
    offset = 0
    for m in re.finditer(COPYRIGHT_PAT, txt):
        yearGroup = 5
        if not m.group(yearGroup):
            yearGroup = 3
        year = m.group(yearGroup)
        if year:
            newCopyright = 'Copyright 2005-' + str(TODAY.year)
            if newCopyright != m.group(1):
                newTxt = newTxt + txt[offset:m.start(1)] + newCopyright
                offset = m.end(1)
                print('  %s: %s --> %s' % (template, m.group(1), newCopyright))
    txt = newTxt + txt[offset:]
    rewrite(outpath, txt)
            
if __name__ == '__main__':
    print(sys.argv)
    pairs = []
    badSyntax = (len(sys.argv) != 3)
    if len(sys.argv) == 3:
        svnrev = sys.argv[1]
        pairs = [pair.split('#') for pair in sys.argv[2].split(',')]
        if pairs:
            for pair in pairs:
                if len(pair) != 2:
                    badSyntax = True
                    break
        else:
            badSyntax = True
    elif len( sys.argv ) == 4:
        badSyntax = False
        svnrev = sys.argv[1]
        pairs = [( sys.argv[2], sys.argv[3] )]
    if badSyntax:
        print('regen_rc SVNREV IN#OUT[,IN#OUT...]')
        print('  Regenerate 1 or more RC files (OUT) from templates (IN, typically')
        print('  *.rc.in), using date+SVNREV to make version stamp, and adjusting')
        print('  copyright notice as needed.')
    else:
        for pair in pairs:
            regen(svnrev, pair[0], pair[1])
    if badSyntax:
        sys.exit(1)
    sys.exit(0)

