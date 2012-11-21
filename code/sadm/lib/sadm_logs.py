#
# $Id: sadm_logs.py 9424 2011-06-13 18:42:04Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys, os, re, time

from datetime import datetime
from sadm_util import *
from sadm_prompt import *
from sadm_constants import *
# From buildscripts...
from dateutils import LOCAL_TIMEZONE, UTC
from textui.ansi import writec, printc, NORMTXT

LASTLOG_PAT = re.compile(r'Last([A-Z][a-z]+).*\.log')
_LINENUM_WIDTH = 5
_REST_OFFSET = _LINENUM_WIDTH + 1

def _getCTestOrder(name):
    if name.find('Steer') > -1:
        return 0
    if name.find('Start') > -1:
        return 1
    elif name.find('Update') > -1:
        return 2
    elif name.find('Configure') > -1:
        return 3
    elif name.find('Build') > -1:
        return 4
    elif name.find('Test') > -1:
        return 5
    elif name.find('Archive') > -1:
        return 6
    return 7

def _cmpByCTestOrder(a, b):
    ares = _getCTestOrder(a[1])
    bres = _getCTestOrder(b[1])
    n = ares - bres
    return n

_GENERIC_ANT_LABEL_PAT = re.compile(r'[-a-z]+:')
_SVN_EMPTY_OUT_PAT = re.compile(r'^[a-z]+-out>\s*$')
_INTERESTING_LINES_PAT = re.compile(r"(?:^|[^-_a-z0-9/\\\\])(error|warning|success|fail|problem|does not appear to be a URL|does( not|n't) exist|cannot access|bad class file|unable to access|Drop site:http://$|Build name: rev unknown)|Cannot locate CTest configuration|ClassNotFoundException|Exception: SegFault|SEGFAULT", re.IGNORECASE)
_NEXT_LINE_PAT = re.compile(r'The following error occurred while executing this line:|The following tests FAILED:|\[(WARNING|ERROR_MESSAGE)\]\s*$', re.IGNORECASE)
_NONDELIM_LINES_PAT = re.compile(r'[a-z0-9]', re.IGNORECASE)
_FAIL_PAT = re.compile(r"(?:^|[^-_a-z0-9/])(error|fail|does not appear to be a URL|does( not|n't) exist|cannot access|bad class file|unable to access|No tests were found|Drop site:http://$|Build name: rev unknown|Cannot locate CTest configuration|ClassNotFoundException|Exception: SegFault|SEGFAULT)", re.IGNORECASE)
_HARMLESS_LOOKS_LIKE_FAIL_PAT = re.compile(r"represents an error and '\*' a warning|assemble_run.py does not exist")
_COUNT_ZERO_PAT = re.compile(r'(?:^|[^-_a-z0-9/\\\\])(error|warning|fail(ure)?|problem)s?\s*:\s*0($|\D)', re.IGNORECASE)
_ZERO_COUNT_PAT = re.compile(r'0 (Compiler (errors|warnings)|tests failed)', re.IGNORECASE)
_CMAKE_BUILD_SUCCEEDED_PAT = re.compile(r'==== Build: \d+ succeeded, 0 failed, \d+ up-to-date, \d+ skipped ===', re.IGNORECASE)
_TAG_PAT = re.compile(r'\d{8}')

def _isFailure(line):
    if _FAIL_PAT.search(line):
        if not bool(_HARMLESS_LOOKS_LIKE_FAIL_PAT.search(line)):
            if not bool(_ZERO_COUNT_PAT.search(line)):
                if line.find('-------- Standard Error ------') == -1:
                    if not (bool(_CMAKE_BUILD_SUCCEEDED_PAT.search(line))):
                        return True
    return False

def _getInteresting(line):
    if _INTERESTING_LINES_PAT.search(line):
        if line.find("represents an error and '*' a warning") > -1:
            return None
        if _ZERO_COUNT_PAT.search(line):
            return None
        if line.find('found 0 errors') > -1:
            return None
        if line.find('0 failures, 0 errors') > -1:
            return None
        if line.find('0 error(s), 0 warning(s)') > -1:
            return None
        if line.find('[junit] Failed:0') > -1:
            return None
        short = re.sub(_COUNT_ZERO_PAT, '', line)
        if _INTERESTING_LINES_PAT.search(short):
            return short
    return None

def _filterLog(path, listener = None):
    with open(path, 'rt') as f:
        lines = f.readlines()
    for i in range(len(lines)):
        lines[i] = str(i + 1).rjust(_LINENUM_WIDTH) + ' ' + lines[i].strip()
    itemNum = 1
    fname = os.path.basename(path)
    item = '%s (%d lines)' % (fname, len(lines))
    rest = DELIM_COLOR + '.'*(76-len(item)) + NORMTXT
    item = CMD_COLOR + str(itemNum) + ' ' + NORMTXT + item
    m = LASTLOG_PAT.match(fname)
    if m:
        item = item.replace(m.group(1), CMD_COLOR + m.group(1) + NORMTXT)
    printc(item + rest)
    # Cut empty lines
    lines = [l for l in lines if l[_REST_OFFSET:]]
    # Cut lines that just have delimiters
    lines = [l for l in lines if _NONDELIM_LINES_PAT.search(l[_REST_OFFSET:])]
    # Cut lines that are known to be noise at particular phases.
    lines = [l for l in lines if not _GENERIC_ANT_LABEL_PAT.match(l[_REST_OFFSET:])]
    tail = path.endswith('.tmp')
    # Now take the final 5 lines plus any lines with errors or warnings
    printCount = 0
    failed = False
    showNextLine = False
    lineCount = len(lines)
    i = 0
    for line in lines:
        if (showNextLine or (tail and i >= lineCount - 5)):
            interesting = line
        else:
            interesting = _getInteresting(line)
        if interesting:
            num = LINENUM_COLOR + line[0:_LINENUM_WIDTH]
            rest = line[_LINENUM_WIDTH:]
            if _isFailure(interesting):
                failed = True
                num += ERROR_COLOR
                rest += NORMTXT
            else:
                num += NORMTXT
            printc(num + rest)
            printCount += 1
        showNextLine = bool(_NEXT_LINE_PAT.search(line))
        i += 1
    if not printCount:
        print INDENT + '(nothing interesting)'
    return failed

if os.name == 'nt':
    _EDIT_LOG_CMD = 'start notepad %s'
else:
    _EDIT_LOG_CMD = 'vi -R %s'

def show_logs(sb):
    overall_log = sb.get_log_file_path()
    print(overall_log)
    if os.path.isfile(overall_log):
        print('')
        _filterLog(overall_log)
        today = time.localtime(time.time())
        when = time.localtime(os.stat(overall_log).st_mtime)
        if (when.tm_mday == today.tm_mday) and (when.tm_mon == today.tm_mon) and (when.tm_year == today.tm_year):
            whentxt = 'today at ' + time.strftime('%I:%M %p', when)
        else:
            whentxt = time.strftime('%a, %d %b at %I:%M %p', when)
        lbl = '%s log last modified %s' % (sb.get_name(), whentxt)
        lbl = lbl.rjust(78)
        lbl = lbl.replace(sb.get_name(), PARAM_COLOR + sb.get_name() + NORMTXT)
        print('')
        printc(lbl)
    else:
        print('No logs available for %s.' % sb.get_name())

