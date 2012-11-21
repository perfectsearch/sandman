#!/usr/bin/env python
#
# $Id: get_code_stats.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys
import os
import re
import optparse
import math
buildscriptDir = os.path.dirname(__file__)
buildscriptDir = os.path.abspath(os.path.join(buildscriptDir, os.path.pardir))
sys.path.append(buildscriptDir)
import sandbox
import codescan
import xmail
import metadata
from ioutil import *

EXT_PAT = metadata.INTERESTING_EXT_PAT
FROM = 'Code Stat Scanner <code.scan@example.com>'

parser = optparse.OptionParser('Usage: %prog [options] [folder]\n\nCompiles stats about a code base; optionally emails report.')
xmail.addMailOptions(parser)

def getRelevantPaths(p):
    relevant = []
    if not p.endswith('/'):
        relevant.append(p)
    while p:
        i = p.rfind('/')
        if i == -1:
            relevant.append('')
            break
        else:
            p = p[0:i+1]
            relevant.append(p)
            p = p[0:-1]
    return relevant

def getValuesKeyName(key):
    return '[' + key + ']'

def isValuesKeyName(key):
    return key[0] == '['

class StatsHolder:
    def __init__(self, rootPath):
        rootPath = norm_folder(rootPath)
        self.rootPath = rootPath
        self.statsByPath = {}
        self.statsByExtension = {}
    def getSandboxName(self):
        i = self.rootPath.find('/sandboxes/')
        if i != -1:
            x = self.rootPath[i + 11:]
            i = x.find('/code')
            if i > -1:
                x = x[0:i]
                i = x.rfind('/')
                if i > -1:
                    x = x[0:i]
            return x
        else:
            return self.rootPath
    def getRelativePath(self, path):
        endsWithSlash = path.endswith('/')
        path = os.path.abspath(path).replace('\\', '/')
        # abspath() removes trailing slash; undo
        if endsWithSlash and path[-1] != '/':
            path = path + '/'
        return path[len(self.rootPath):]
    def addStat(self, path, statName, number):
        shouldAggregate = not path.endswith('/')
        if shouldAggregate:
            k = getValuesKeyName(statName)
            dict = self.statsByExtension
            ignored, ext = os.path.splitext(path)
            #print('ext = %s' % ext)
            #sys.exit(0)
            if not ext in dict:
                dict[ext] = {}
            dict = dict[ext]
            if not statName in dict:
                dict[statName] = number
                dict[k] = [number]
            else:
                dict[statName] = dict[statName] + number
                dict[k].append(number)
        relativePath = self.getRelativePath(path)
        sbp = self.statsByPath
        for p in getRelevantPaths(relativePath):
            if not p in sbp:
                sbp[p] = {}
            dict = sbp[p]
            if not statName in dict:
                dict[statName] = number
                if shouldAggregate:
                    #print('aggregating %s for %s', (k, p))
                    dict[k] = [number]
            else:
                dict[statName] = dict[statName] + number
                if shouldAggregate:
                    dict[k].append(number)

_CPP_TESTNAME_PAT = re.compile(r'^\s*(SIMPLE_TEST\s*\(\s*(.*?)\s*\)|class\s+([a-zA-Z_0-9]+)\s*:\s*(public|protected|private)\s+[a-zA-Z_0-9]+Test)', re.MULTILINE | re.DOTALL)
_JAVA_TESTNAME_PAT = re.compile(r'^\s*public\s+void\s+([a-zA-Z_0-9]+)\s*\(', re.MULTILINE | re.DOTALL)
_PY_TESTNAME_PAT = re.compile(r'^\s*def test([a-zA-Z_0-9]+)\s*\(\s*self\s*\)\s*:', re.MULTILINE | re.DOTALL)
_CPP_CLASS_PAT = re.compile(r'^\s*(template\s*<.*?>\s*)?(class|struct|union)\s+([a-zA-Z_0-9]+)', re.MULTILINE | re.DOTALL)
_JAVA_CLASS_PAT = re.compile(r'^\s*((abstract|public|private|protected|static|final)\s+)*(class|interface)\s+([a-zA-Z_0-9]+)', re.MULTILINE | re.DOTALL)
_PY_CLASS_PAT = re.compile(r'^\s*class\s+([a-zA-Z_0-9]+).*?:', re.MULTILINE | re.DOTALL)
_TEST_FILE_PAT = re.compile(r'/test/', re.IGNORECASE)

_CLASS_PATS = [_CPP_CLASS_PAT, _JAVA_CLASS_PAT, _PY_CLASS_PAT]
_TESTNAME_PATS = [_CPP_TESTNAME_PAT, _JAVA_TESTNAME_PAT, _PY_TESTNAME_PAT]

def getFileTypeIndex(path):
    path = path.lower()
    if path.endswith('.cpp') or path.endswith('.h'):
        return 0
    elif path.endswith('.java'):
        return 1
    elif path.endswith('.py'):
        return 2
    return -1

def getClassPatForPath(path):
    i = getFileTypeIndex(path)
    if i != -1:
        return _CLASS_PATS[i]

def getTestnamePatForPath(path):
    i = getFileTypeIndex(path)
    if i != -1:
        return _TESTNAME_PATS[i]

def analyzeFile(fpath, stats):
    fpath = os.path.abspath(fpath)
    rel = stats.getRelativePath(fpath)
    #print('analyzing %s' % rel)
    txt = read_file(fpath)
    byteCount = len(txt)
    stats.addStat(fpath, 'byte count, impl + test', byteCount)
    lineCount = codescan.getLineNumForOffset(txt, byteCount)
    stats.addStat(fpath, 'line count, impl + test', lineCount)
    isTest = bool(_TEST_FILE_PAT.search(fpath))
    codeType = 'impl'
    if isTest:
        codeType = 'test'
    stats.addStat(fpath, 'byte count, ' + codeType, byteCount)
    stats.addStat(fpath, 'line count, ' + codeType, lineCount)
    # See if we know how to do any further analysis on this file.
    pat = getClassPatForPath(fpath)
    if pat:
        if isTest:
            pat = getTestnamePatForPath(fpath)
            if pat:
                stats.addStat(fpath, 'unit test count', len(pat.findall(txt)))
        else:
            stats.addStat(fpath, 'class count', len(pat.findall(txt)))

def statPathIsFile(p):
    i = p.rfind('.')
    if i > -1:
        return p[i+1:] in ['cpp','h','java','py']
    return False

def statPathIsComponent(p):
    return p == '' or (p.endswith('/') and p.find('/') == len(p) - 1)

_FLOAT_TYPE = type(0.1)
def getReportLine(key, number, showKB = False, formatSpecifier='%02f'):
    numtxt = number
    ntype = type(number)
    if ntype == _FLOAT_TYPE:
        numtxt = formatSpecifier % number
        if numtxt.endswith('00'):
            numtxt = numtxt[0:-3]
    else:
        numtxt = str(number)
    line = '%s = %s' % (key, numtxt)
    if showKB:
        line += ' (%0.0f KB)' % (number / 1024.0)
    return line

def getAggregateStats(dict, key):
    values = dict.get(getValuesKeyName(key))
    avg = mean(values)
    stdev = stddev(values)
    return avg, stdev

def describeTestRatio(ratio, multiplier = 1.0):
    if ratio < 0.085 * multiplier:
        lbl = 'POOR COVERAGE'
    elif ratio < 0.20 * multiplier:
        lbl = 'fair coverage'
    elif ratio < 0.5 * multiplier:
        lbl = 'good coverage'
    else:
        lbl = 'excellent coverage'
    return '%0.2f (%s)' % (ratio, lbl)

def generateReport(stats):
    #print(stats.statsByPath)
    report = ''
    components = [p for p in stats.statsByPath.keys() if statPathIsComponent(p)]
    files = [p for p in stats.statsByPath.keys() if statPathIsFile(p)]
    components.sort()
    files.sort()
    uberDict = stats.statsByPath['']
    avg, stdev = getAggregateStats(uberDict, 'byte count, impl')
    tooBigs = {'': max(avg + 2.5 * stdev, 20000)}
    avg, stdev = getAggregateStats(uberDict, 'line count, impl')
    tooLongs = {'': max(avg + 2.5 * stdev, 1000)}
    for ext in stats.statsByExtension.keys():
        dict = stats.statsByExtension[ext]
        avg, stdev = getAggregateStats(dict, 'byte count, impl')
        tooBigs[ext] = avg + 2.5 * stdev
        avg, stdev = getAggregateStats(dict, 'line count, impl')
        tooLongs[ext] = max(avg + 2.5 * stdev, 1000)
    for path in components:
        desc = path
        if desc == '':
            desc = 'entire folder tree'
        report += '\nStats for %s' % desc
        dict = stats.statsByPath[path]
        keys = [k for k in dict.keys() if not isValuesKeyName(k)]
        keys.sort()
        for key in keys:
            showKB = key.startswith('byte')
            report += '\n    ' + getReportLine(key, dict[key], showKB)
            if showKB or key.startswith('line'):
                values = dict[getValuesKeyName(key)]
                avg = mean(values)
                report += '; ' + getReportLine('mean', avg, showKB, formatSpecifier='%0.0f')
                report += '; ' + getReportLine('std dev', stddev(values), False, formatSpecifier='%0.1f')
        classCount = dict.get('class count', 0)
        unitTestCount = dict.get('unit test count', 0)
        if unitTestCount:
            implLineCount = dict.get('line count, impl', 0)
            testLineCount = dict.get('line count, test', 0)
            if implLineCount:
                ratio = describeTestRatio(testLineCount / float(implLineCount))
                report += '\n    ' + getReportLine('test lines per impl line', ratio)
            implByteCount = dict.get('byte count, impl', 0)
            testByteCount = dict.get('byte count, test', 0)
            if implByteCount:
                ratio = describeTestRatio(testByteCount / float(implByteCount))
                report += '\n    ' + getReportLine('test bytes per impl byte', ratio)
            if classCount:
                ratio = describeTestRatio(float(unitTestCount) / classCount, 2.5)
            else:
                ratio = '(undefined; no classes)'
        else:
            ratio = 'NO UNIT TESTS!'
        report += '\n    ' + getReportLine('tests per class', ratio)
        if path:
            myFiles = [f for f in files if f.startswith(path)]
            #testFiles = [f for f in myFiles if _TEST_FILE_PAT.search(f)]
            #implFiles = [f for f in myFiles if not _TEST_FILE_PAT.search(f)]
            tooComplex = []
            for implF in myFiles:
                ignored, ext = os.path.splitext(implF)
                size = stats.statsByPath[implF].get('byte count, impl')
                length = stats.statsByPath[implF].get('line count, impl')
                if size > tooBigs[''] or size > tooBigs[ext] or length > tooLongs[''] or length > tooLongs[ext]:
                    tooComplex.append((implF, size, length))
            if tooComplex:
                # Java doesn't support partial classes, so splitting classes into multiple
                # files isn't always practical. In C++ and python, however, there are good
                # ways to split into smaller files.
                if tooComplex[0][0].endswith('.java'):
                    comment = 'refactor suggested'
                else:
                    comment = 'REFACTOR NEEDED'
                report += '\n    unusually complex files (%s):' % comment
                for tc in tooComplex:
                    report += '\n        %s (%0.0f KB, %d lines)' % (tc[0], tc[1] / 1024.0, tc[2])
        report += '\n'
    return report

def sum(numbers):
    n = 0
    for x in numbers:
        n += x
    return n

def mean(numbers):
    return sum(numbers) / float(len(numbers))

def variance(numbers):
    avg = mean(numbers)
    diffsFromMean = [n - avg for n in numbers]
    squaredDfm = [n * n for n in diffsFromMean]
    variance = sum(squaredDfm) / len(numbers)
    return variance

def stddev(numbers):
    # This is a *population* stddev, not a sample stddev.
    # The difference is that we assume we have all possible
    # values, not just a representative sample.
    return math.sqrt(variance(numbers))

class StatsRecurser:
    def __init__(self, stats):
        self.stats = stats
    def select(self, folder, dirs):
        self.stats.addStat(folder, "scanned subdir count", len(dirs))
        return dirs

class StatsVisitor:
    def __init__(self, stats):
        self.stats = stats
    def visit(self, folder, item, relativePath):
        analyzeFile(folder + item, self.stats)
        self.stats.addStat(folder, "scanned file count", 1)

def analyze(path, prebuilt, options):
    if not os.path.isdir(path):
        sys.stderr.write('%s is not a valid folder.\n' % path)
        return 1
    path = norm_folder(path)
    stats = StatsHolder(path)
    print('\nCompiling stats for %s...' % metadata.get_friendly_name_for_path(path))
    visitor = StatsVisitor(stats)
    recurser = StatsRecurser(stats)
    visitedFiles, visitedFolders = metadata.visit(path, visitor, recurser, excludePrograms=True)#, debug=True)
    report = generateReport(stats)
    print(report)
    if xmail.hasDest(options):
        xmail.sendmail(report, subject='code stats for %s' % metadata.get_friendly_name_for_path(path),
            sender='Code Stat Scanner <code.scan@example.com>', options=options)

if __name__ == '__main__':
    options, args = parser.parse_args()
    prebuilt = []
    if args:
        folder = args[0]
    else:
        folder = sandbox.current.get_code_root()
    exitCode = analyze(folder, prebuilt, options)
    sys.exit(exitCode)

