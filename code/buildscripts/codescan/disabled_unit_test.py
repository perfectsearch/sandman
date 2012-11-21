#!/usr/bin/env python
# 
# $Id: disabled_unit_test.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 
import os
import sys
buildscriptDir = os.path.dirname(__file__)
buildscriptDir = os.path.abspath(os.path.join(buildscriptDir, os.path.pardir))
sys.path.append(buildscriptDir)
import vcs
import codescan
import re

DISABLED_DESCRIPTOR_MARKER = 'UNIT TEST TEMPORARILY DISABLED'
_LBL_PAT = re.compile(r'^\s*([a-z]+):\s*(.*?)\s*$', re.IGNORECASE)
TICKET_PAT = re.compile('(\d{2,5})')

class DisabledUnitTest:
    @staticmethod
    def _assign(dut, lbl, val):
        lbl = lbl.lower()
        if hasattr(dut, lbl):
            setattr(dut, lbl, val)
    def __init__(self, path, txt, start, end):
        self.when = ''
        self.which = ''
        self.where = ''
        self.by = ''
        self.ticket = ''
        self.owner = ''
        self.why = ''
        self.path = path
        self.revision = vcs.revno(path, True)
        self.scope = ''
        i = start
        j = end - 2
        while txt[j] == '*':
            j-= 1
        self.lineNum = codescan.getLineNumForOffset(txt, i)
        lines = [re.sub(r'^\s*\*', '', l).strip() for l in txt[i:j].split('\n') if l.strip()]
        lbl = None
        for l in lines:
            m = _LBL_PAT.match(l)
            if m:
                if lbl:
                    DisabledUnitTest._assign(self, lbl, val)
                lbl = m.group(1)
                val = m.group(2)
            elif lbl:
                val += ' ' + l
        if lbl:
            DisabledUnitTest._assign(self, lbl, val)
        if self.ticket:
            m = TICKET_PAT.search(self.ticket)
            if m:
                self.ticket = m.group(1)
        if self.owner:
            self.owner = ', '.join([x.strip() for x in self.owner.replace(';',',').split(',')])
    def getRelativePath(self):
        i = self.path.find('/code/')
        if i > -1:
            return self.path[i+6:]
        return self.path
    def __str__(self):
        return '''Revision: %s
By: %s
Which: %s
Where: %s
When: %s
Ticket: #%s
Owner: %s
Why: %s''' % (self.revision, self.by, self.which,  self.where, self.when, 
        self.ticket, self.owner, self.why)

if __name__ == '__main__':
    print('This module captures information about disabled unit tests, based on a standard')
    print('comment block. It is imported by other python scripts rather than run directly.')
