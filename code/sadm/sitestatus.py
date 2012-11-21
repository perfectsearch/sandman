#!/usr/bin/env python
# -*- coding: utf-8 -*
from __future__ import print_function

import os
import sys
try:
    from standardoptions import set_up_logging, add_standard_arguments
except:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'buildscripts'))
    from standardoptions import set_up_logging, add_standard_arguments
import argparse
import logging
import traceback
import subprocess

MASTER_SERVER = 'bazaar.example.com' ## TODO make use conf

def main(args):
    handle_arguments(args)
    set_up_logging(OPTIONS)

    branchname = OPTIONS.branch

    print('Retrieving master branch information from', MASTER_SERVER)
    master_branches = get_branch_info(MASTER_SERVER, OPTIONS.branch)


    print('Retrieving site branch information from', OPTIONS.site)
    site_branches = get_branch_info(OPTIONS.site, OPTIONS.branch)

    print('Processing')
    for branch in site_branches:
        b = find_branch(master_branches, branch)
        if not b:
            print('ERROR: branch missing from master:', branch.branch, branch.component, branch.aspect, branch.revid)
        else:
            if b.revid == branch.revid:
                master_branches.remove(b)
            else:
                b.site_revid = branch.revid

    print('\nSite Information for', OPTIONS.branch if OPTIONS.branch else 'all branches')
    print('    %d items out of date' % len(master_branches))
    for b in master_branches:
        print( '        ', b.branch, b.component, b.aspect)
        print( '            master revid:', b.revid)
        print( '            site revid  :', b.site_revid)
    return len(master_branches)


def get_branch_info(server, branchname):
    branchinfos = []
    branches = [l for l in get_revisions(server).split('\n') if l.strip() and l.startswith(branchname)]
    for b in branches:
        branch = decompose(b)
        if branch:
            branchinfos.append(branch)
    return branchinfos


def handle_arguments(args):
    parser = argparse.ArgumentParser(args[0])
    add_standard_arguments(parser)
    parser.add_argument('-b', '--branch', help='only check this branch', default='')
    parser.add_argument('-s', '--site', help='check this site server', default='10.10.10.100')
    global OPTIONS
    OPTIONS = parser.parse_args(args[1:])


def get_revisions(server):
    p = subprocess.Popen('bzr fast-branches bzr+ssh://%s/reporoot' % server,
                                                        stdout=subprocess.PIPE,
                                                        stderr=subprocess.PIPE,
                                                        shell=True)
    stdout, stderr = p.communicate()
    err = p.returncode
    if err != 0:
        print('ERROR: failed to get branches')
        return None
    return stdout


class Branch:
    def __init__(self, branch, component, aspect, revid):
        self.branch = branch
        self.component = component
        self.aspect = aspect
        self.revid = revid
        self.site_revid = None


def decompose(entry):
    parts = entry.split()
    if len(parts) != 4:
        print('entry ERROR:', entry)
    else:
        return Branch(parts[0], parts[1], parts[2], parts[3])



def find_branch(master_branches, branch):
    for b in master_branches:
        if b.branch == branch.branch and b.component == branch.component and b.aspect == branch.aspect:
            return b


if __name__ == "__main__":
    sys.exit(main(sys.argv))
