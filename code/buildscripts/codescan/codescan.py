#!/usr/bin/env python
# 
# $Id: codescan.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 
import re

def getLineNumForOffset(txt, offset):
    n = 1
    i = 0
    for c in txt:
        if i >= offset:
            break
        if c == '\n':
            n += 1
        i += 1
    return n

def getNextCStyleBlockComment(txt, i):
    j = txt.find('/*', i)
    if j > -1:
        k = txt.find('*/', j + 2)
        if k > -1:
            return (j, k)
    return None

IF_ZERO_PAT = re.compile(r'^\s*#if\s+(FALSE|false|0)', re.MULTILINE)
def getNextIfZero(txt, i):
    k = IF_ZERO_PAT.search(txt, i)
    if k:
        return k.start()
    return -1

# For this pattern we are looking for any #if -- #ifdef, #if defined(), #if _WIN32, etc.
IF_PAT = re.compile(r'^\s*#if', re.MULTILINE)
ENDIF_PAT = re.compile(r'^\s*#endif', re.MULTILINE)
def findEndif(txt, i):
    #print('Looking for matching #endif at offset %d in "%s"' % (i, txt[i:]))
    openCount = 1
    while openCount > 0:
        openMatch = IF_PAT.search(txt, i)
        #if openMatch: print('openMatch = %d to %d' % (openMatch.start(), openMatch.end()))
        closeMatch = ENDIF_PAT.search(txt, i)
        #if closeMatch: print('closeMatch = %d to %d' % (closeMatch.start(), closeMatch.end()))
        j, which = pickClosest(openMatch, closeMatch)
        #print('closest, which = %s, %s' % (str(j), str(which)))
        if j == -1:
            return -1
        if which == 1:
            openCount -= 1
            i = closeMatch.end()
            if openCount == 0:
                return i
        else:
            #print('found new nested #if')
            openCount += 1
            i = openMatch.end()

_MATCH_OBJ_TYPE = type(re.match('x', 'x'))
_END_OF_STRING = 1024 * 1024 * 1024

def pickClosest(a, b, c = None):
    items = [a, b, c]
    somethingToMatch = False
    for i in range(len(items)):
        if items[i] is None:
            items[i] = _END_OF_STRING
        else:
            if type(items[i]) == _MATCH_OBJ_TYPE: 
                items[i] = items[i].start()
                somethingToMatch = True
            if items[i] == -1: 
                items[i] = _END_OF_STRING
            else:
                somethingToMatch = True
    if somethingToMatch:
        idx = -1
        n = _END_OF_STRING
        for i in range(len(items)):
            if items[i] < n:
                idx = i
                n = items[i]
        if n == _END_OF_STRING:
            n = -1
        return n, idx
    return -1, -1

def _findNoInactiveBlocks(x, y):
    return -1, -1

def pickInactiveBlockFinder(path):
    path = path.lower()
    if path.endswith('.cpp') or path.endswith('.h'):
        return getNextInactiveCppBlock
    if path.endswith('.java') or path.endswith('.css') or path.endswith('.js'):
        return getNextInactiveJavaBlock
    return _findNoInactiveBlocks

def getActiveBlocksOnly(txt, nextInactiveBlock, preserveLineNums=True):
    if nextInactiveBlock == _findNoInactiveBlocks:
        return txt
    activeText = ''
    i = 0
    while True:
        range = nextInactiveBlock(txt, i)
        if not range:
            break
        activeText = activeText + txt[i:range[0]]
        if preserveLineNums:
            cut = txt[range[0]:range[1]]
            lineCount = getLineNumForOffset(cut, len(cut)) - 1
            if lineCount:
                activeText = activeText + ''.rjust(lineCount,'\n')
        i = range[1]
    activeText = activeText + txt[i:]
    return activeText

def findEndOfQuotedString(txt, i):
    end = len(txt)
    while i < end:
        c = txt[i]
        if c == '\\':
            i += 1
        elif c == '"' or c == '\n':
            return i
        i += 1
    return -1

def getNextInactiveCppBlock(txt, i):
    #print('txt = "%s"' % txt)
    while True:
        #print('looking for inactive block at offset %d' % i)
        comment = txt.find('/*', i)
        #print('comment = %d' % comment)
        ifdef = getNextIfZero(txt, i)
        #print('ifdef = %d' % ifdef)
        quoted = txt.find('"', i)
        #print('quoted=%d' % quoted)
        idx, which = pickClosest(comment, ifdef, quoted)
        if idx > -1:
            #print("found inactive block starting at offset %d; which=%s" % (idx, str(which)))
            if which == 0: # comment
                end = txt.find('*/', comment + 2)
                if end == -1:
                    return idx, len(txt)
                return idx, end + 2
            elif which == 1: # #ifdef
                eol = txt.find('\n', ifdef + 1)
                if eol > -1:
                    #print('looking for endif at offset %s' % str(eol + 1))
                    end = findEndif(txt, eol + 1)
                    #print('got %d' % end)
                else:
                    end = -1
                if end == -1:
                    end = len(txt)
                return idx, end
            else: # quoted string
                #print('Found " at offset %d; now looking for end' % idx)
                end = findEndOfQuotedString(txt, idx + 1)
                #print('End = %d' % end)
                if end == -1:
                    return None
                i = end + 1
        else:
            return None

def getNextInactiveJavaBlock(txt, i):
    while True:
        comment = txt.find('/*', i)
        quoted = txt.find('"', i)
        idx, which = pickClosest(comment, quoted)
        if idx > -1:
            if which == 0: # comment
                end = txt.find('*/', comment + 2)
                if end == -1:
                    return idx, len(txt)
                return idx, end + 2
            else: # quoted string
                #print('Found " at offset %d; now looking for end' % idx)
                end = findEndOfQuotedString(txt, idx + 1)
                #print('End = %d' % end)
                if end == -1:
                    return None
                i = end + 1
        else:
            return None

def matchPairs(txt):
    stack = []
    begin = ['[', '{', '(', '"', "'"]
    end = [']', '}', ')', '"', "'"]
    warnings = []
    for i in range(len(txt)):
        if txt[i] in begin:
            if (txt[i] == '"' or txt[i] == "'"):
                if len(stack) > 0:
                    if stack.count(txt[i]) == 0:
                        stack.append(txt[i])
                        continue
                else:
                    stack.append(txt[i])
                    continue
            else:
                stack.append(txt[i])
                continue
        if txt[i] in end:
            while True:
                if len(stack) < 1:
                    warnings.append('No opening for %s.' % txt[i])
                    break
                else:
                    top = stack.pop()
                    if begin.index(top) != end.index(txt[i]):
                        if stack.count(begin[end.index(txt[i])]) == 0:
                            stack.append(top)
                            warnings.append('No opening for %s.' % txt[i])
                            break
                        else:
                            warnings.append('No closing for %s.'% top)
                    else:
                        break
    while len(stack) > 0:
        warnings.append('No closing for %s.' % stack.pop())
    return warnings

if __name__ == '__main__':
    print('This module facilitates the scanning of source code files. It is imported by')
    print('other python scripts rather than run directly.')

