#!/usr/bin/env python
# -*- coding: utf-8 -*
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
from __future__ import print_function
import sys
import os
import re
import ioutil
import component
import vcs
import metadata
import bzrlib
import tempfile
from branchinfo import BranchInfo
import sandbox


def get_vcs_component_aspects(comp, sb):
    '''
    Some aspects of a component may not exist at all; others may have been
    created dynamically. Return the subset of aspects that have some
    relationship to our vcs system.
    '''
    return [a for a in sb.get_component_aspects(comp)
            if vcs.folder_is_tied_to_vcs(sb.get_component_path(comp, a))]


def get_component_status(comp, sb, status_filter=None, aspect_filter=None, revision=None):
    '''
    Return a dictionary describing all files/folders with notable status within
    the specified component.

    Dictionary format: key = an aspect of the component ("code", "test",
    or "built"); value = sub-dictionary of notable status items. Sub-dictionary
    format: key = status label like "modified" or "unknown"; value = a list of
    paths, relative to the component's folder in the <aspect> root, of files
    with the specified status.

    @param status_filter A function that decides whether a particular status
    label is interesting. Takes a string and returns a boolean.

    @param aspect_filter A function that decides whether a particular aspect is
    interesting. Takes a string and returns a boolean.
    '''
    status = {}
    # Iterate over all aspects of the component that exist and are tied to vcs.
    for a in get_vcs_component_aspects(comp, sb):
        path = sb.get_component_path(comp, a)
        if (not aspect_filter) or aspect_filter(a):
            x = vcs.get_status(path, status_filter=status_filter, revision=revision)
            if x:
                status[a] = x
    return status


def get_sandbox_status(sb, status_filter=None, aspect_filter=None, comp_filter=None, revision=None):
    '''
    Return a dictionary of all files/folders with notable status within the
    specified sandbox.

    Dictionary format: key = a component name; value = sub-dictionary in the
    format returned by status_component().

    @param status_filter A function that decides whether a particular status
    label is interesting. Takes a string and returns a boolean.

    @param aspect_filter A function that decides whether a particular aspect is
    interesting. Takes a string and returns a boolean.

    @param comp_filter A function that decides whether a particular component is
    interesting. Takes a string and returns a boolean.
    '''
    status = {}
    for c in sb.get_on_disk_components():
        if (not comp_filter) or comp_filter(c):
            x = get_component_status(c, sb, status_filter=status_filter, aspect_filter=aspect_filter, revision=revision)
            if x:
                status[c] = x
    return status


def format_sandbox_status(sb, sandbox_status_dict, indent=''):
    txt = ''
    if sandbox_status_dict:
        components = sandbox_status_dict.keys()[:]
        components.sort()
        for comp in components:
            txt += format_component_status(sb, comp, sandbox_status_dict[comp], indent)
    if txt:
        txt = indent + sb.get_name() + '\n' + txt
    return txt


def format_component_status(sb, comp, component_status_dict, indent=''):
    txt = ''
    if component_status_dict:
        aspects = component_status_dict.keys()[:]
        aspects.sort()
        for aspect in aspects:
            txt += format_aspect_status(sb, comp, aspect, component_status_dict[aspect], '  ' + indent)
    return txt

def format_aspect_status(sb, comp, aspect, aspect_status_dict, indent='  '):
    txt = ''
    if aspect_status_dict:
        if sb and comp:
            txt += indent + _get_relative_path(sb, comp, aspect) + '\n'
        labels = aspect_status_dict.keys()[:]
        labels.sort()
        for status_label in labels:
            txt += format_status_label_items(status_label, aspect_status_dict[status_label], '  ' + indent)
    return txt

def format_aspect_info(sb, comp, aspect, info, indent='  '):
    txt = ''
    if sb and comp:
        txt += indent + _get_relative_path(sb, comp, aspect) + '\n'
    indent = indent + '    '
    info = [indent + l.rstrip() for l in info.split('\n') if l.strip()]
    txt += '\n'.join(info)
    return txt

def format_status_label_items(status_label, status_label_items, indent='    '):
    txt = ''
    if status_label_items:
        txt += indent + status_label + ':\n'
        status_label_items = status_label_items[:]
        status_label_items.sort()
        for file in status_label_items:
            txt += '  ' + indent + file + '\n'
    return txt

def _get_relative_path(sb, comp, aspect):
    if aspect == component.BUILT_ASPECT_NAME:
        return aspect + '.' + sb.get_targeted_platform_variant() + '/' + comp
    elif aspect == component.REPORT_ASPECT_NAME:
        return component.REPORT_ASPECT_NAME
    else:
        return '%s/%s' % (aspect, comp)

def _items_that_wont_checkin(lbl):
    return lbl == 'unknown' or lbl.startswith('conflict')

def _complain_aggregate(scope, operation):
    print('As a best practice, %s-wide %s is only allowed when status is clean.' % (scope, operation))
    print('Use bzr %s one directory at a time if a workaround is critical.\n' % operation)

def _complain_component_not_clean(comp, sb, operation):
    bad_status = get_component_status(comp, sb)
    if bad_status:
        print(format_component_status(sb, comp, bad_status))
        _complain_aggregate('component', operation)
        return True

def _complain_sandbox_not_clean(sb, operation):
    bad_status = get_sandbox_status(sb)
    if bad_status:
        print(format_sandbox_status(sb, bad_status))
        _complain_aggregate('sandbox', operation)
        return True

def add_component(comp, sb):
    aspects = get_vcs_component_aspects(comp, sb)
    for a in aspects:
        path = sb.get_component_path(comp, a)
        txt = vcs.add(path)
        if txt:
            print(txt)

def add_sandbox(sb):
    print(sb.get_name())
    for c in sb.get_on_disk_components():
        add_component(c, sb)


def checkin_component(msg, comp, sb, validate_status=True):
    if validate_status:
        bad_status = get_component_status(comp, status_filter=_items_that_wont_checkin)
        if bad_status:
            print(format_component_status(sb, bad_status))
            print('Some items are not ready for checkin.')
            return
    aspects = get_vcs_component_aspects(comp, sb)
    for a in aspects:
        if a.startswith(component.BUILT_ASPECT_NAME):
            continue
        path = sb.get_component_path(comp, a)
        if vcs.get_status(path):
            try:
                x = vcs.checkin(path, msg)
            except:
                print(sys.exc_info()[1])

def checkin_sandbox(msg, sb):
    bad_status = get_sandbox_status(sb, status_filter=_items_that_wont_checkin)
    if bad_status:
        print(format_sandbox_status(sb, bad_status))
        print('Some items are not ready for checkin.')
        return
    for c in sb.get_on_disk_components():
        checkin_component(msg, c, sb, validate_status=False)

def show_component_info(comp, sb):
    aspects = get_vcs_component_aspects(comp, sb)
    for a in aspects:
        path = sb.get_component_path(comp, a)
        txt = vcs.info(path)
        if txt:
            print(format_aspect_info(sb, comp, a, txt))

def show_sandbox_info(sb):
    print(sb.get_name())
    for c in sb.get_on_disk_components():
        show_component_info(c, sb)

def merge_component(comp, sb, source):
    aspects = get_vcs_component_aspects(comp, sb)
    wr = vcs.get_working_repository()
    for a in aspects:
        if a.startswith(component.BUILT_ASPECT_NAME):
            continue
        path = sb.get_component_path(comp, a)
        if source:
            if a == component.REPORT_ASPECT_NAME:
                continue
            from_location=BranchInfo(branchname=source, componentname=comp, aspectname=a).get_branchdir(wr.master_reporoot)
        else:
            from_location=BranchInfo(branchname=sb.get_branch(), componentname=comp, aspectname=a).get_branchdir(wr.master_reporoot)
        print('  ' + _get_relative_path(sb, comp, a))
        try:
            vcs.merge(path, from_location=from_location)
        except:
            print(sys.exc_info()[1])

def merge_sandbox(sb, source):
    print(sb.get_name())
    for c in sb.get_on_disk_components():
        merge_component(c, sb, source)

def missing_component(comp, sb):
    aspects = get_vcs_component_aspects(comp, sb)
    for a in aspects:
        path = sb.get_component_path(comp, a)
        txt = vcs.missing(path)
        if txt:
            print(format_aspect_info(sb, comp, a, txt))

def missing_sandbox(sb):
    print(sb.get_name())
    for c in sb.get_on_disk_components():
        missing_component(c, sb)

def pull_component(comp, sb, source):
    aspects = get_vcs_component_aspects(comp, sb)
    wr = vcs.get_working_repository()
    for a in aspects:
        pattern = '%s/%s/%s(\.[^/]+)' % (sb.get_branch(), comp, a)  #fix_julie repo structure
        aspect_suffixes = []
        for branchinfo in wr.branches:
            m = re.match(pattern, '/'.join(branchinfo))
            if m:
                aspect_suffixes.append(m.group(1))
        if aspect_suffixes:
            aspects = [a + x for x in aspect_suffixes]
        else:
            aspects = [a]
        for aspect in aspects:
            path = sb.get_component_path(comp, aspect)
            if source:
                if a.startswith(component.BUILT_ASPECT_NAME) or a == component.REPORT_ASPECT_NAME:
                    continue
                from_location = BranchInfo(branchname=source, componentname=comp, aspectname=aspect).get_branchdir(wr.source_reporoot)
            else:
                from_location = BranchInfo(branchname=sb.get_branch(), componentname=comp, aspectname=aspect).get_branchdir(wr.source_reporoot)
                print('  ' + _get_relative_path(sb, comp, aspect))
            try:
                vcs.pull(path, from_location=from_location)
            except:
                print(sys.exc_info()[1])

def pull_sandbox(sb, source):
    msg = 'Pulling %s' % sb.get_name()
    if source:
        msg += ' from %s' % source
    msg += '...'
    print(msg)
    for c in sb.get_on_disk_components():
        pull_component(c, sb, source)

def push_component(comp, sb, to, validate_status=True):
    if validate_status and _complain_component_not_clean(comp, sb, 'push'):
        return
    aspects = get_vcs_component_aspects(comp, sb)
    wr = vcs.get_working_repository()
    for a in aspects:
        if a.startswith(component.BUILT_ASPECT_NAME) or a == component.REPORT_ASPECT_NAME:
            continue
        path = sb.get_component_path(comp, a)
        if to:
            location=BranchInfo(branchname=to, componentname=comp, aspectname=a).get_branchdir(wr.master_reporoot)
        else:
            location=BranchInfo(branchname=sb.get_branch(), componentname=comp, aspectname=a).get_branchdir(wr.master_reporoot)
        print('  ' + _get_relative_path(sb, comp, a))
        vcs.push(path, location=location)

def push_sandbox(sb, to):
    if _complain_sandbox_not_clean(sb, 'push'):
        return
    print('Pushing %s...' % sb.get_name())
    for c in sb.get_on_disk_components():
        push_component(c, sb, to, validate_status=False)

def revert_component(comp, sb, revision):
    aspects = get_vcs_component_aspects(comp, sb)
    file_list = []
    for a in aspects:
        print('  ' + _get_relative_path(sb, comp, a))
        path = sb.get_component_path(comp, a)
        file_list.append(path)
        vcs.revert([path], revision)

def revert_sandbox(sb, revision):
    print(sb.get_name())
    for c in sb.get_on_disk_components():
        revert_component(c, sb, revision)

def show_component_revno(componentname, sb, tree=False):
    aspects = get_vcs_component_aspects(componentname, sb)
    for a in aspects:
        path = sb.get_component_path(componentname, a)
        print(_get_relative_path(sb, componentname, a), '\t', vcs.revno(path, tree=tree))


def show_sandbox_revno(sb, tree=False):
    if tree:
        print('%s, working tree revnos' % sb.get_name())
    else:
        print('%s, repository revnos (add --tree to get revno for working tree)' % sb.get_name())
    for componentname in sb.get_on_disk_components():
        show_component_revno(componentname, sb, tree=tree)


def show_component_status(comp, sb, status_filter=None, aspect_filter=None, revision=None):
    stat = get_component_status(comp, sb, status_filter, aspect_filter, revision=revision)
    if stat:
        print(format_component_status(sb, comp, stat).rstrip())


def show_sandbox_status(sb, status_filter=None, aspect_filter=None, comp_filter=None, revision=None):
    stat = get_sandbox_status(sb, status_filter, aspect_filter, comp_filter, revision=revision)
    if stat:
        print(format_sandbox_status(sb, stat).rstrip())


def get_component_tag_info(comp, sb, tag):
    if tag is None:
        print("Please specify a tag with the -t option")
        return 1
    has_tag = []
    same_revision = {}
    aspects = get_vcs_component_aspects(comp, sb)
    for a in aspects:
        path = sb.get_component_path(comp, a)
        txt = vcs.tags(path)
        if txt:
            if tag in txt:
                has_tag.append(_get_relative_path(sb, comp, a))
            txt = [x.split() for x in txt.split('\n')]
            revision = None
            for t in txt:
                if tag in t:
                    revision = t[1]
                    break
            if revision:
                for t in txt:
                    if t[1] == revision:
                        if _get_relative_path(sb, comp, a) in same_revision:
                            same_revision[_get_relative_path(sb, comp, a)].append(t[0])
                        else:
                            same_revision[_get_relative_path(sb, comp, a)] = [t[0]]
    return has_tag, same_revision


def show_sandbox_tag_info(tag, sb):
    if tag is None:
        print("Please specify a tag with the -t option")
        return 1
    has_tag = []
    same_revision = {}
    print(sb.get_name())
    for c in sb.get_on_disk_components():
        ht, sr = get_component_tag_info(c, sb, tag)
        has_tag += ht
        for k, v in sr.iteritems():
            same_revision[k] = v
    print_tag_info(has_tag, same_revision, tag)


def print_tag_info(has_tag, same_revision, tag):
    print('Aspects that contain tag %s' % tag)
    for aspect in has_tag:
        print(' ', aspect)
    print('Tags at the same revsion:')
    for key in same_revision:
        print(' ', key)
        for t in same_revision[key]:
            print('   ', t)


def show_component_tags(comp, sb):
    aspects = get_vcs_component_aspects(comp, sb)
    for a in aspects:
        path = sb.get_component_path(comp, a)
        print('  ' + _get_relative_path(sb, comp, a))
        txt = vcs.tags(path)
        if txt:
            print('\n'.join(['    ' + l.rstrip() for l in txt.split('\n')]))


def show_sandbox_tags(sb):
    print(sb.get_name())
    for c in sb.get_on_disk_components():
        show_component_tags(c, sb)


def tag_component(comp, tag, sb):
    aspects = get_vcs_component_aspects(comp, sb)
    for a in aspects:
        path = sb.get_component_path(comp, a)
        vcs.tag(tag, path)

def tag_sandbox(tag, sb):
    print(sb.get_name())
    for c in sb.get_on_disk_components():
        tag_component(c, tag, sb)

def update_component(comp, sb):
    err = 0
    aspects = get_vcs_component_aspects(comp, sb)
    for a in aspects:
        if update_component_aspect(comp, sb, a):
            err = 1
    return err

def update_component_aspect(comp, sb, aspect, new_branch):
    err = 0
    wr = vcs.get_working_repository()
    if aspect == 'built':
        aspects = ['built.' + sb.get_targeted_platform_variant()]
##
##        aspects = []
##        pattern = '%s/%s/%s(\.[^/]+)' % (comp.branch, comp.name, aspect) #fix_julie repo structure
##        # Find all the built variants that have the specified branch.
##        aspect_suffixes = []
##        for branchpath in wr.branches:
##            m = re.match(pattern, '/'.join(branchpath))
##            if m:
##                if m.group(1) not in aspect_suffixes:
##                    aspect_suffixes.append(m.group(1))
##        aspects = [aspect + x for x in aspect_suffixes]
    else:
        aspects = [aspect]
    for a in aspects:
        sys.stdout.write('.')
        sys.stdout.flush()
        target_dir = sb.get_component_path(comp.name, a)
        if target_dir:
            print('  ' + _get_relative_path(sb, comp.name, a))
            aspect_folder = target_dir[0:target_dir.rfind(comp.name)]
            if not os.path.exists(aspect_folder):
                os.makedirs(aspect_folder)
            try:
                err = wr.create_or_update_checkout(target_dir, comp.name, a, comp.branch, comp.revision, use_master=new_branch)
            except:
                print(sys.exc_info()[1])
                err = 1
    return err


def update_sandbox(sb, branch=None, aspect=None, new_branch=False):
    sys.stdout.write('Getting %s \n' % sb.get_name())
    sys.stdout.flush()
    err = 0
    try:
        top = sb.get_top_component()
        wr = vcs.get_working_repository()
        old_srr = None
        if not branch:
            branch = sb.get_branch()
        try:
            location = sb.get_code_root()
            if not aspect:
                aspect = sb.get_component_reused_aspect(sb.get_top_component())
            deps = metadata.get_components_inv_dep_order(wr, sb.get_targeted_platform_variant(), top, location, branch, aspect=aspect, use_master=new_branch)
            for comp in deps:
                aspects = [comp.reused_aspect, component.TEST_ASPECT_NAME]
                if comp.name == sb.get_top_component():
                    for br, c, asp, revid in wr.localbranches:
                        if br == branch and c == comp.name and asp == component.REPORT_ASPECT_NAME:
                            aspects.append(component.REPORT_ASPECT_NAME)
                            break
                    if component.REPORT_ASPECT_NAME not in aspects:
                        rbranches = vcs.get_branches(wr.master_reporoot, aspect=component.REPORT_ASPECT_NAME)
                        rbranches = [x[1] for x in rbranches if x[0] == branch]
                        if comp.name in rbranches:
                            aspects.append(component.REPORT_ASPECT_NAME)
                for a in aspects:
                    # TODO: warn if component reused aspect has changed
                    if update_component_aspect(comp, sb, a, new_branch):
                        err = 1
        except KeyboardInterrupt:
            sys.exit(1)
        except:
            print(sys.exc_info()[1])
        finally:
            if old_srr:
                wr.source_reporoot = old_srr
        if not err:
            bad_status = get_sandbox_status(sb, status_filter=lambda lbl: lbl.startswith('conflict'))
            if bad_status:
                print(format_sandbox_status(sb, bad_status))
                print('Manual intervention needed to resolve conflicts.')
                err = 1
        # Record our dependencies for later use.
        with open(sb.get_dependencies_file_path(), 'w') as f:
            for comp in deps:
                f.write(str(comp) + '\r\n')
    finally:
        print('')
        return err


##def create_component(workingRepo, name, branch='trunk', restricted=False):
##    assert('.' not in name)
##    metatext = '''[component dependencies]
##buildscripts: code
##
##[mics]
##targeted platforms: windows, linux, osx
##
##[build tools]
##python:     2.6,    windows|linux|osx,  python -V,                                                  Download from activestate.com
##nose:       1.1,    windows|linux|osx,  nosetests -V,                                               on Windows run "easy_install nose"
##unittest2:  0.5,    windows|linux|osx,  python -c "import unittest2; print unittest2.__version__",  on Windows run "easy_install unittest2"
##argparse:   1.1,    windows|linux|osx,  python -c "import argparse; print argparse.__version__",    on Windows run "easy_install argparse"
##pep8:       0.5,    windows|linux|osx,  python -c "import pep8; print pep8.__version__",            on windows run "easy_install pep8"
##
##[test tools]
##
##[run tools]
##'''
##    transport = bzrlib.transport.get_transport(workingRepo.master_reporoot)
##    if branch != 'trunk':
##        transport.mkdir('trunk/' + name)
##    else:
##        transport.mkdir(branch + '/' + name)
##    for aspect in [component.CODE_ASPECT_NAME, component.TEST_ASPECT_NAME]:
##        location = os.path.join(workingRepo.master_reporoot, 'trunk', name, aspect).replace('\\','/')
##        vcs.init(location)
##    tf = tempfile.mkdtemp()
##    vcs.checkout(os.path.join(workingRepo.master_reporoot, 'trunk',name, component.CODE_ASPECT_NAME).replace('\\','/'), tf)
##    metafile = open(os.path.join(tf, 'metadata.txt'), 'w')
##    metafile.write(metatext)
##    metafile.close()
##    vcs.add(tf.replace('\\','/'))
##    vcs.checkin(tf, 'Create metadata.txt file.', quiet=True)
##    if branch != 'trunk':
##        branch_sandbox(workingRepo, name, 'trunk', branch, use_master=True)
##    if restricted:
##        tmpfile = None
##        try:
##            reposupport = tempfile.mkdtemp()
##            vcs.checkout(os.path.join(workingRepo.master_reporoot, 'repositorysupport').replace('\\','/'), reposupport)
##            restrictedComponents = open(os.path.join(reposupport, 'RestrictedComponents.txt'), 'a')
##            restrictedComponents.write(name+'\n')
##            restrictedComponents.close()
##            vcs.checkin(reposupport, 'Add %s to the list of restricted components.' % name, quiet=True)
##            loggerhead = '/data/conf/etc/httpd/conf.d/loggerhead.conf'
##            text = transport.get(loggerhead)
##            text = text.getvalue()
##            lines = text.split('\n')
##            for line in lines:
##                if 'Location' in line and '/code' in line:
##                    i = lines.index(line)
##                    break
##            comps = open(os.path.join(reposupport, 'RestrictedComponents.txt'), 'r')
##            comps = comps.read().split('\n')
##            while '' in comps:
##                comps.remove('')
##            lines[i] = '<Location ~ "/reporoot/(buildtools|(%s)/code).*">' % '|'.join(sorted(comps))
##            if os.name == 'nt':
##                tmpfile = os.environ['USERPROFILE'] + '\\tmp.txt'
##            else:
##                tmpfile = os.environ['HOME'] + '/tmp.txt'
##            fp = open(tmpfile, 'w')
##            fp.write('\n'.join(lines))
##            fp.close()
##            fp = open(tmpfile, 'r')
##            err = transport.put_file(loggerhead, fp)
##            err = err != len('\n'.join(lines))
##            fp.close()
##        except:
##            print(sys.exc_info()[1])
##            print('''
##Something happened will adding %s to the list of restricted components.
##If you are not a member of psdev then you don't have the correct permissions
##to create a restricted component.
##
##If you are a member of psdev then please run
##bzr co bzr+ssh:bazaar.example.com/reporoot/repositorysupport <temp dir>
##And then add %s to RestrictedComponents.txt and check it back in.
##''' % (name, name))
##        finally:
##            if tmpfile:
##                os.remove(tmpfile)
##            transport.disconnect()
##

def main(args):
    ''' This main is for running tests and debugging only. Normally
    this module is imported.
    '''
    handle_arguments(args)
    set_up_logging(OPTIONS)

    if OPTIONS.branch:
        if OPTIONS.component:
            return branch_component(vcs.get_working_repository(), OPTIONS.component, OPTIONS.b, OPTIONS.to)
        else:
            branch, component = OPTIONS.to.split('/')
            return branch_sandbox(vcs.get_working_repository(), component, OPTIONS.b, branch)

    sb = sandbox.Sandbox(OPTIONS.sandbox_root)
    if OPTIONS.revno:
        if OPTIONS.component:
            show_component_revno(OPTIONS.component, sb, OPTIONS.tree)
        else:
            show_sandbox_revno(sb, OPTIONS.tree)
    if OPTIONS.tags:
        if OPTIONS.component:
            show_component_tags(OPTIONS.component, sb)
        else:
            show_sandbox_tags(sb)
    if OPTIONS.info:
        if OPTIONS.component:
            show_component_info(OPTIONS.component, sb)
        else:
            show_sandbox_info(sb)
    if OPTIONS.status:
        if OPTIONS.component:
            show_component_status(OPTIONS.component, sb)
        else:
            show_sandbox_status(sb)
    if OPTIONS.tag_info:
        show_sandbox_tag_info(OPTIONS.t, sb)
    if OPTIONS.update:
        if OPTIONS.component:
            update_component(OPTIONS.component, sb)
        else:
            update_sandbox(sb)
    if OPTIONS.tag:
        if OPTIONS.component:
            tag_component(OPTIONS.component, sb)
        else:
            tag_sandbox(sb)
    if OPTIONS.pull:
        if OPTIONS.component:
            pull_component(OPTIONS.component, sb)
        else:
            pull_sandbox(sb, OPTIONS.source)
    if OPTIONS.push:
        if OPTIONS.component:
            push_component(OPTIONS.component, sb)
        else:
            push_sandbox(sb, OPTIONS.source)


def handle_arguments(args):
    parser = argparse.ArgumentParser(args[0])
    add_standard_arguments(parser)
    parser.add_argument('-s', '--sandboxroot', dest='sandbox_root', type=str)
    parser.add_argument('-c', '--component', type=str)
    parser.add_argument('-t', type=str, help='tag for tag-info command')
    parser.add_argument('-b', type=str, help='branch for branch command')
    parser.add_argument('--to', type=str, help='target branch/component for branch command')
    parser.add_argument('--source', type=str, help='source branch for pull')

    parser.add_argument('--revno', action='store_true')
    parser.add_argument('--tree', action='store_true')
    parser.add_argument('--tags', action='store_true')
    parser.add_argument('--info', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--tag-info', action='store_true')
    parser.add_argument('--branch', action='store_true')
    parser.add_argument('--pull', action='store_true')

    parser.add_argument('--push', action='store_true')
    parser.add_argument('--merge', action='store_true')
    parser.add_argument('--add', action='store_true')
    parser.add_argument('--ci', action='store_true')
    parser.add_argument('--revert', action='store_true')
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--tag', action='store_true')
    global OPTIONS
    OPTIONS = parser.parse_args(args[1:])


if __name__ == "__main__":
    try:
        from standardoptions import set_up_logging, add_standard_arguments
    except:
        sys.path.append('/data/buildscripts')
        from standardoptions import set_up_logging, add_standard_arguments
    import argparse
    import logging
    sys.exit(main(sys.argv))

