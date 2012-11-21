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
import string


MASTER_SERVER = 'bazaar.example.com' ## TODO make part of conf
INDENT = '    '

BRANCH = 0
COMPONENT = 1
ASPECT = 2

def main(args):
    handle_arguments(args)
    set_up_logging(OPTIONS)

    branchinfo = _run('bzr fast-branches ' + OPTIONS.reporoot)
    branchinfo = [b.split() for b in branchinfo.split('\n') if b.strip()]

    if OPTIONS.branch:
        branchinfo = [b for b in branchinfo if b[0].lower() == OPTIONS.branch.lower()]

    if OPTIONS.component:
        branchinfo = [b for b in branchinfo if b[1].lower() == OPTIONS.component.lower()]

    if OPTIONS.branches:
        show(branchinfo, BRANCH)
    elif OPTIONS.components:
        show(branchinfo, COMPONENT)
    elif OPTIONS.aspects:
        show(branchinfo, ASPECT)
    else:
        print('Branches:')
        show(branchinfo, BRANCH, indent=True)

        print('\nComponents:')
        show(branchinfo, COMPONENT, indent=True)

        print('\nAspects:')
        show(branchinfo, ASPECT, indent=True)


def show(branchinfo, column, indent=False):
    items = set()
    [items.add(b[column]) for b in branchinfo]
    [print((INDENT if indent else '') + c) for c in sorted(list(items), key=string.lower)]


def show_branches(branchinfo, indent=False):
    branches = set()
    [branches.add(b[0]) for b in branchinfo]
    [print((INDENT if indent else '') +c) for c in sorted(list(branches), key=string.lower)]


def _run(command):
    logging.debug('running: %s' % command)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        logging.error('failed to run %s: %s' % (command, stderr))
        raise Exception()
    return stdout


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
    parser.add_argument('-r', '--reporoot', type=str,
                        default='bzr+ssh://bazaar.example.com/reporoot',## TODO make part of conf
                        help='root of repository')
    parser.add_argument('-b', '--branches', help='only show branches', action='store_true')
    parser.add_argument('--branch', help='only show information about this branch')
    parser.add_argument('-c', '--components', help='only show components', action='store_true')
    parser.add_argument('--component', help='only show information for this component')
    parser.add_argument('-a', '--aspects', help = 'only show aspects', action='store_true')
    global OPTIONS
    OPTIONS = parser.parse_args(args[1:])


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
