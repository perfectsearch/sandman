#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# $Id: distwebservices.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
from bzrlib.commands import plugin_cmds

import os
import sys
import re
import subprocess
import StringIO
import ConfigParser

from bzrlib.commands import Command, register_command
from bzrlib.option import Option
from bzrlib.builtins import cmd_revno
from bzrlib.trace import be_quiet
import bzrlib
import bzrlib.api
import string

# Make sure we can find our own private copy of buildscripts.
BUILDSCRIPTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'buildscripts')
sys.path.append(BUILDSCRIPTS_FOLDER)

# Now we can import stuff from sadm and buildscripts...
import aggregate_vcs
import sandbox
import vcs
import metadata
import component

version_info = (0,0,3, 'dev')

supported_commands = {
    'add':['add'],
    'branch':['branch'],
    'commit':['commit', 'ci', 'checkin'],
    'info':['info'],
    'merge':['merge'],
    'missing':['missing'],
    'pull':['pull'],
    'push':['push'],
    'revno':['revno'],
    'revert':['revert'],
    'status':['status', 'st', 'stat'],
    'tag':['tag'],
    'tags':['tags'],
    'tag-info':['tag-info'],
    'update':['update', 'up'],
}

class cmd_sandbox(Command):
    __doc__ = """
    Run bzr commands against an entire sandbox.

    For all bzr commands that you pass to the sandbox command you can use any alias.
    i.e. commit, ci or checkin etc.
    """
    takes_options = [
        'quiet',
        Option('message', type=str, short_name='m', help='Descriptive message (bzr sb ci).'),
        Option('directory', param_name='directory', type=str, short_name='d', help='Directory to use, rather than current.'),
        Option('branch', type=str, short_name='b', help='Branch to pull from in update.'),
        Option('to', type=str, help='Branch name to create (bzr sb branch).'),
        Option('from', type=str, param_name='source', help='What to branch from (branch/component).'),
        Option('tag', type=str, short_name='t', help='Tag name to apply (bzr sb tag).'),
        Option('tree', help='Get revno of working tree instead of repository (bzr sb revno).'),
        Option('revision', short_name='r', help='See "help revisionspec" for details.'),
    ]
    takes_args = ['command']
    aliases = ['sb']

    def run(self, command, quiet, message=None, directory='.', branch=None, to=None, source=None, tag=None, tree=False, revision=None):
        if quiet:
            be_quiet()
        functions = {
            'add':add_sandbox,
            'branch':branch_sandbox,
            'commit':commit_sandbox,
            'info':info_sandbox,
            'merge':merge_sandbox,
            'missing':missing_sandbox,
            'pull':pull_sandbox,
            'push':push_sandbox,
            'revert':revert_sandbox,
            'revno':revno_sandbox,
            'status':status_sandbox,
            'tag':tag_sandbox,
            'tags':tags_sandbox,
            'tag-info':tag_info_sandbox,
            'update':update_sandbox,
        }
        args = {
            'add':dict(directory=directory),
            'branch':dict(to=to, source=source),
            'commit':dict(msg=message, directory=directory),
            'info':dict(directory=directory),
            'merge':dict(directory=directory, source=source),
            'missing':dict(directory=directory),
            'pull':dict(directory=directory, source=source),
            'push':dict(directory=directory, to=to),
            'revert':dict(directory=directory, revision=revision),
            'revno':dict(directory=directory, tree=tree),
            'status':dict(directory=directory, revision=revision),
            'tag':dict(tag=tag, directory=directory),
            'tags':dict(directory=directory),
            'tag-info':dict(directory=directory, tag=tag),
            'update':dict(directory=directory, branch=branch),
        }
        for key in supported_commands.keys():
            if command in supported_commands[key]:
                return functions[key](**args[key])
        # I am repeatedly typing nonsense commands like "bzr sb build". Help
        # users thaw their brain freeze...
        if '|' + command + '|' in '|build|test|cr|coderoot|tr|testroot|root|eval|':
            print('This looks like an "sb" command.')
        elif command != command.lower():
            print('Did you mean "bzr sb %s"?' % command.lower())
        else:
            print('%s is not supported yet. If you need it, log a ticket.' % command)

def add_sandbox(directory):
    aggregate_vcs.add_sandbox(_find_sb(directory))

def branch_sandbox(to, source):
    if to is None:
        print('Please enter a name for the new branch using the --to option.')
        return
    if source is None:
        print('Please enter a name for the old branch/component using the --from option.')
        return
    if not '/' in source:
        print('From needs to be in format branch/component.')
        return
    err = component.get_branch_name_validation_error(to)
    if err is not None:
        print 'Branch %s' % err.lower()
        return
    wr = vcs.get_working_repository()
    wr.source_reporoot = wr.master_reporoot
    branch, comp = source.split('/')
    aggregate_vcs.branch_sandbox(wr, comp, branch, to)

def _rewrite_metadata_for_branch(target_dir, branch):
    fp = open(os.path.join(target_dir, metadata.METADATA_FILE), 'r')
    Config = ConfigParser.ConfigParser()
    Config.readfp(fp)
    fp.close()
    section = 'component dependencies'
    if Config.has_section(section):
        for option in Config.options(section):
            parts = Config.get(section, option).split(',', 1)
            parts[0] = branch
            Config.set(section, option, ','.join(parts))
    fp = open(os.path.join(target_dir, metadata.METADATA_FILE), 'w+')
    Config.write(fp)
    fp.close()

def _find_sb(directory):
    sb = sandbox.create_from_within(directory)
    if not sb:
        print('%s does not appear to be inside a sandbox.' % os.path.abspath(directory))
        sys.exit(1)
    return sb

def commit_sandbox(msg, directory):
    aggregate_vcs.checkin_sandbox(msg, _find_sb(directory))

def info_sandbox(directory):
    aggregate_vcs.show_sandbox_info(_find_sb(directory))

def merge_sandbox(directory, source):
    aggregate_vcs.merge_sandbox(_find_sb(directory), source)
    
def missing_sandbox(directory):
    aggregate_vcs.missing_sandbox(_find_sb(directory))

def pull_sandbox(directory, source):
    aggregate_vcs.pull_sandbox(_find_sb(directory), source)

def push_sandbox(directory, to):
    aggregate_vcs.push_sandbox(_find_sb(directory), to)

def revno_sandbox(directory, tree=False):
    aggregate_vcs.show_sandbox_revno(_find_sb(directory), tree=tree)

def status_sandbox(directory, revision=None):
    aggregate_vcs.show_sandbox_status(_find_sb(directory), revision=revision)

def tag_sandbox(tag, directory):
    aggregate_vcs.tag_sandbox(tag, _find_sb(directory))

def tags_sandbox(directory):
    aggregate_vcs.show_sandbox_tags(_find_sb(directory))

def tag_info_sandbox(tag, directory):
    aggregate_vcs.show_sandbox_tag_info(tag, _find_sb(directory))

def update_sandbox(directory, branch):
    return aggregate_vcs.update_sandbox(_find_sb(directory), branch)

def revert_sandbox(directory, revision):
    aggregate_vcs.revert_sandbox(_find_sb(directory), revision)

class cmd_component(Command):
    __doc__ = """
    Run bzr commands against all aspects of a component.

    For all bzr commands that you pass to the component command you can use any alias.
    i.e. commit, ci or checkin etc.
    """
    takes_options = [
        'quiet',
        Option('component', help='Component to execute command on.', type=str, short_name='c'),
        Option('message', type=str, short_name='m', help='Descriptive message (bzr component ci).'),
        Option('directory', param_name='directory', type=str, short_name='d', help='Directory to use, rather than current.'),
        Option('branch', type=str, short_name='b', help='Branch name to create (bzr component branch).'),
        Option('tag', type=str, short_name='t', help='Tag name to apply (bzr component tag).'),
        Option('tree', help='Get revno of working tree instead of repository (bzr component revno).'),
        Option('revision', short_name='r', help='See "help revisionspec" for details.'),
    ]
    takes_args = ['command']

    def run(self, command, quiet, message=None, component=None, directory='.', branch='', tag=None, tree=False, revision=None):
        if quiet:
            be_quiet()
        get_implied_comp = not component
        if component:
            parts = re.split('[\\/]', component)
            if len(parts) > 1:
                if not directory or (directory == '.'):
                    directory = component
                    get_implied_comp = True
                else:
                    raise Exception("Directory and component can't both contain path segments.")
        if get_implied_comp:
            component = sandbox.find_component_from_within(directory)
        if component is None:
            print("No valid component.")
            return
        functions = {
            'add':add_component,
            'branch':branch_component,
            'commit':commit_component,
            'info':info_component,
            'merge':merge_component,
            'missing':missing_component,
            'pull':pull_component,
            'push':push_component,
            'revert':revert_component,
            'revno':revno_component,
            'status':status_component,
            'tag':tag_component,
            'tags':tags_component,
            'tag-info':tag_info_component,
            'update':update_component,
        }
        args = {
            'add':dict(comp=component, directory=directory),
            'branch':dict(comp=component, directory=directory, branch=branch),
            'commit':dict(msg=message, comp=component, directory=directory),
            'info':dict(comp=component, directory=directory),
            'merge':dict(comp=component, directory=directory),
            'missing':dict(comp=component, directory=directory),
            'pull':dict(comp=component, directory=directory),
            'push':dict(comp=component, directory=directory),
            'revert':dict(comp=component, directory=directory, revision=revision),
            'revno':dict(comp=component, directory=directory, tree=tree),
            'status':dict(comp=component, directory=directory, revision=revision),
            'tag':dict(comp=component, directory=directory),
            'tags':dict(comp=component, directory=directory),
            'tag-info':dict(comp=component, directory=directory, tag=tag),
            'update':dict(comp=component, directory=directory),
        }
        for key in supported_commands.keys():
            if command in supported_commands[key]:
                return functions[key](**args[key])
        if command != command.lower():
            print('Did you mean "bzr component %s"?' % command.lower())
        else:
            print('%s is not supported yet. If you need it, log a ticket.' % command)

#Component functions
def add_component(comp, directory):
    aggregate_vcs.add_component(comp, _find_sb(directory))

def branch_component(comp, directory, branch):
    if not branch:
        print('Please enter a name for the new branch using the -b option.')
        return
    err = component.get_branch_name_validation_error(branch)
    if err:
        print err
        return
    wr = vcs.get_working_repository()
    aggregate_vcs.branch_component(wr.master_reporoot, comp, branch, _find_sb(directory))

def commit_component(msg, comp, directory):
    aggregate_vcs.checkin_component(msg, comp, _find_sb(directory))

def info_component(comp, directory):
    aggregate_vcs.show_component_info(comp, _find_sb(directory))

def merge_component(comp, directory):
    aggregate_vcs.merge_component(comp, _find_sb(directory))
    
def missing_component(comp, directory):
    aggregate_vcs.missing_component(comp, _find_sb(directory))

def pull_component(comp, directory):
    aggregate_vcs.pull_component(comp, _find_sb(directory))

def push_component(comp, directory):
    aggregate_vcs.push_component(comp, _find_sb(directory))

def revert_component(comp, directory, revision):
    aggregate_vcs.revert_component(comp, _find_sb(directory), revision)

def revno_component(comp, directory, tree=False):
    aggregate_vcs.show_component_revno(comp, _find_sb(directory), tree=tree)

def status_component(comp, directory, revision=None):
    aggregate_vcs.show_component_status(comp, _find_sb(directory), revision=revision)

def tags_component(comp, directory):
    aggregate_vcs.show_component_tags(comp, _find_sb(directory))

def tag_info_component(comp, directory, tag):
    has_tag, same_revision = aggregate_vcs.get_component_tag_info(comp, _find_sb(directory), tag)
    aggregate_vcs.print_tag_info(has_tag, same_revision, tag)

def update_component(comp, directory):
    aggregate_vcs.update_component(comp, _find_sb(directory))

def tag_component(comp, tag, directory):
    aggrecate_vcs.tag_component(comp, tag, directory)

register_command(cmd_sandbox)
register_command(cmd_component)
