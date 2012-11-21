#!/usr/bin/env python
#
# $Id: sadm.py 10580 2011-07-06 21:42:11Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import optparse
import os
import sys
import time
import random
import re
import subprocess
import ConfigParser
import StringIO
import tempfile
import base64
import pickle
from pprint import pprint
#import xml.dom.minidom
if os.name == 'nt':
    try:
        import win32api, win32con, win32process
    except:
        pass

from lib import *

# Some symbols that need a short way to refer to them.
from lib.sadm_prompt import prompt, prompter, prompt_bool, AUTOABORT_MODE
from lib.sadm_config import config
from lib.sadm_constants import *
from lib.sadm_buildqueue import *
from lib.sadm_logs import *

# From buildscripts...
from textui.ansi import *
from textui.ansi import ansi as ansi2
from textui.colors import *
import ioutil
import dateutils
import buildinfo
import build
import aggregate_vcs
import component
import sandbox
import check_output
import metadata
import vcs
import timeout_monitor
import ospriv
import buildqueue
import sandboxtype
from report.eval_summary import *
from report.dashboard import *
from check_tools import *
from branchinfo import get_revid, BranchInfo, REVID_UNKNOWN, REVID_NO_REVISIONS

_INTERVALS = [30,20,15,14,13,12,11]
if os.name == 'nt':
    _PROCKILL_CMD = 'taskkill /f /pid'
else:
    _PROCKILL_CMD = 'kill'

_FULLY_QUALIFIED_SB_PAT = re.compile('[^.\r\n\t /]+\.[^\r\n\t]+\.[^\r\n\t /]+')
def _match_sandboxes_ex(verb, selector=None, msg=None, display_only_matches=False, args=[]):
    sandboxes = []
    invalid = False
    cnt = 1
    if args:
        cnt = len(args)
    # Allow us to match sandboxes by relative path as well as by name.
    if (selector is None) and bool(args) and len(args) == 1:
        name = args[0]
        if ('*' not in name) and (not bool(_FULLY_QUALIFIED_SB_PAT.match(name))):
            #print('looking for sandbox by relative path')
            if os.path.isdir(name):
                #print('%s is folder path' % name)
                name = ioutil.norm_seps(os.path.realpath(os.path.abspath(name)))
                #print('%s is abs folder path' % name)
                container = os.path.realpath(config.sandbox_container_folder)
                i = name.find(container)
                #print('%s is sandbox container path' % config.sandbox_container_folder)
                if i > -1:
                    name = sandbox.find_root_from_within(name)
                    if name:
                        name = ioutil.norm_seps(name, trailing=False).split('/')[-1]
                    #print('resolving sandbox from %s' % name)
                    args = [name]
                else:
                    pass #print('%s is not within %s' % (name, config.sandbox_container_folder))
    for i in range(cnt):
        name = None
        if args:
            name = args[i]
        more = sadm_prompt.choose_sandbox(verb, name, selector, allow_multi_matches=True, msg=msg, display_only_matches=display_only_matches)
        if more:
            for sb in more:
                if sb not in sandboxes:
                    sandboxes.append(sb)
    return sandboxes

def _match_sandboxes(verb, selector, *args):
    return _match_sandboxes_ex(verb, selector, args=args)

def _is_perf_test_script(name):
    name = name.lower()
    return name.startswith('perf') and (name.find('.cmake') > -1 or name.find('.ctest') > -1)

def _perf_tests_available(project, branch):
    aux_folder = join_path(config.sandbox_container_folder, project, branch, INFO_FOLDER)
    return bool([x for x in os.listdir(aux_folder) if _is_perf_test_script(x)])

def request(*args):
    if args:
        project = args[0]
    else:
        project = prompt("Top level component (e.g., buildscripts)?")
    if not project:
        return
    if len(args) > 1:
        branch = args[1]
    else:
        branch = prompt('Branch?','trunk')
    wr = vcs.get_working_repository()
    exists = False
    for br, c, a, revid in wr.branches:
        if project == c and branch == br:
            exists = True
            break
    if exists:
        print('')
        notSpecific = '%2A' # the * char, url-escaped
        if len(args) > 2:
            platform = args[2]
        else:
            platform = prompt("Platform?", '*')
        if len(args) > 3:
            bitness = args[3]
        else:
            bitness = prompt('Bitness?','64')
        if platform == '*':
            platform = notSpecific
        if bitness == '*':
            bitness = notSpecific
        if len(args) > 4:
            build_style = args[4]
        else:
            build_style = prompt('Build style (e.g., official or continuous)', 'official')
        if build_style == 'official':
            clean = 'False'
        else:
            clean = 'True'
        if len(args) > 5:
            machine = args[5]
        else:
            machine = prompt("Which machine should perform this build? ('*' if machine doesn't matter.')", "*")
        if len(args) > 6:
            requester = args[6]
        else:
            requester = prompt('Send result notification to', config.mailto)
        url = config.build_queue_url + SUBMIT_REQUEST_PAGE
        data = 'Email=%s&Component=%s&Branch=%s&build-style=%s&platform=%s&bitness=%s&requested-machine=%s&clean=%s' % (requester,project,branch,build_style,platform,bitness,machine,clean)
        req = urllib2.Request(url, data)
        base64string = base64.encodestring('sadm:password')[:-1]
        authheader = "Basic %s" % base64string
        req.add_header("Authorization", authheader)
        response = urllib2.urlopen(req).read()
        for line in response.split('\n'):
            #if line.find('<') == -1 and line.find('>') == -1 and line.find(';') == -1:
            if line.find('added.') > -1:
                print line.strip()
                break
    else:
        eprintc('%s/%s is not a valid component/branch combination.' % (project, branch), ERROR_COLOR)

def _show_dashboard(sb):
    vcs.update_checkout(sb.get_report_root())
    db = Dashboard(sb.get_report_root())
    #db.debug = True
    status = db.get_status()
    if status.result == EvalResult.OK:
        color = GREEN
    elif status.result == EvalResult.FAILED:
        color = RED
    elif status.result == EvalResult.PROBLEMATIC:
        color = YELLOW
    else: #status.result == EvalResult.UNKNOWN:
        color = BLUE
    printc('    Currently:' + color + ' ' + enum_to_str(EvalResult, status.result) + NORMTXT)
    elapsed_secs = time.time() - status.when
    dt1 = time.localtime(status.when)
    dt2 = time.localtime()
    # Since sometime today?
    if dt1.tm_year == dt2.tm_year and dt1.tm_yday == dt2.tm_yday:
        since = 'today at ' + time.strftime('%I:%M %p', time.localtime(status.when))
    else:
        # In previous week?
        if elapsed_secs < 7 * 24 * 86400:
            since = time.strftime('last %A at %I:%M %p', time.localtime(status.when))
        else:
            since = time.strftime('%A, %b %d at %I:%M %p', time.localtime(status.when)).replace(' 0', ' ')
    elapsed = dateutils.elapsed_secs_to_duration_str(elapsed_secs)
    print('    Since:     %s (%s)' % (since, elapsed))
    writec(color)
    for r in status.reasons:
        print('               ' + r)
    if not status.result == EvalResult.OK:
        print('    Logs:     %s' % sb.get_report_root())
    eprintc(NORMTXT)

def status(*args):
    sandboxes = _match_sandboxes('status', None, *args)
    if not sandboxes:
        return
    for sb in sandboxes:
        print(sb.get_name())
        if not sb.has_dashboard():
            print('    (empty)')
            print('    Run "sb eval --report" to create.\n')
        else:
            _show_dashboard(sb)

def showqueue(*args):
    req = urllib2.Request(config.build_queue_url+LIST_QUEUE_PAGE)
    base64string = base64.encodestring('sadm:password')[:-1]
    authheader = "Basic %s" % base64string
    req.add_header("Authorization", authheader)
    response = urllib2.urlopen(req).read()
    response = response.replace('bdash.lib.buildqueue', 'buildqueue')
    requests = pickle.loads(response)
    for x in requests:
            printc(str(x))

def service(*args):
    _service_build_queue()

def version(*args):
    revno = vcs.revno(APP_FOLDER, tree=True)
    if revno:
        revno = revno.strip()
    else:
        revno = 'unknown'
    print '%s.%s' % (APP_VERSION, revno)

def path(*args):
    if not args:
        args = [os.path.abspath('.')]
    sandboxes = _match_sandboxes_ex('path', args=args)
    if (not sandboxes) or (len(sandboxes) != 1):
        return 1
    for sb in sandboxes:
        print(sb.get_root())

def _validate_sandbox_name(name):
    """
    Make sure this name has the required format and all parts are valid.
    It does not require the sandbox to exist, or even that the parts exist.
    Currently at the very least it must have three distinct parts i.e.
    [component.branch.user_defined_name]
    """
    i = name.find('.')
    j = name.rfind('.')
    if i == -1 or i == j:
        return 'Name must consist of three parts, separated by dots.', None, None, None
    comp = name[0:i]
    branch = name[i + 1:j]
    task = name[j + 1:]
    err = component.get_component_name_validation_error(name[0:i])
    if not err:
        err = sandbox.get_task_name_validation_error(name[j + 1:])
        if not err:
            err = component.get_branch_name_validation_error(name[i+1:j])
    return err, comp, branch, task

def _sb_name_to_fuzzy_regex(name):
    name = name.replace('.', '\\.')
    name = name.replace('*', '.*')
    name = name.replace('?', '.?')
    name = name.replace('-', '[-_]?')
    name = name.replace('_', '[-_]?')
    name = name.replace(' ', ' ?')
    if not name.endswith('$'):
        name += '$'
    return re.compile(name, re.IGNORECASE)

def _report_multi_matches_error(name, item_type, matches):
    cnt = len(matches)
    matches = '\n    '.join(matches)
    eprintc('"%s" has %d matches:\n    %s' % (name, cnt, matches),
        ERROR_COLOR)

def _get_cfg_args(missing_dict, *args):
    name = None
    tpv = None
    aspect = None
    cfg = None
    err_tuple = None, None, None, None, None, None, None
    # Parse args; for ones that we can recognize as pointing us toward a
    # particular aspect, platform, or config, remember requested semantics.
    if args:
        name = args[0]
        if args:
            args = [a.lower() for a in args if a][1:]
            for vra in component.VALID_REUSED_ASPECTS:
                if vra in args:
                    aspect = vra
                    args.remove(vra)
                    break
            if args:
                for a in args:
                    tpv = buildinfo.fuzzy_match_platform_variant(a)
                    if tpv:
                        args.remove(a)
                        break
                if args:
                    for a in args:
                        if a in ['debug','release']:
                            cfg = a
                            args.remove(cfg)
                            break
    # Make sure we have a name.
    if not name:
        name = prompt('Name? (component.branch.task)')
        if not name:
            return err_tuple
    name_uses_wildcards = name.find('*') > -1
    # Validate and/or normalize the format of our name.
    hits = _match_sandboxes('configure', None, name)
    # Special logic applies when calling 'sadm init' -- it is valid to give
    # a sandbox name for a component and/or branch that does not yet exist
    # on the current machine, or even on the master repository. In such
    # cases, we need to get a list of all possible sandboxes so we can tell
    # if we're creating something entirely new, or just referring to something
    # that's not yet present locally.
    if (not hits) and (missing_dict is not None):
        # Make sure our task name is valid.
        comp = None
        br = None
        i = name.rfind('.')
        if i > -1:
            task = name[i + 1:]
            if task.find('*') > -1:
                eprintc('Wildcards in task name are not supported.', ERROR_COLOR)
                return err_tuple
            rest = name[0:i]
            i = rest.find('.')
            if i > -1:
                comp = rest[0:i]
                br = rest[i + 1:]
        else:
            # Pick an arbitrary task name for sandbox matching; what we
            # choose won't matter, as long as it leads to well-formed
            # sandbox names.
            task = 'x'
        # Okay, it's worth our time to check vcs.
        print('"%s" does not match any local sandboxes. Checking master repo.' % name)
        code_branches = vcs.get_branches(config.master_repo_root, aspect='code')
        code_branches += vcs.get_branches(config.master_repo_root, aspect='built')
        if not code_branches:
            eprintc('Unable to fetch branches from bzr; cannot compare new sandbox name to existing component+branch combinations.', ERROR_COLOR)
            return err_tuple
        # In the lines that follow, we are going to make three lists:
        #   - unique component names
        #   - unique branch names
        #   - all sandbox names that are currently valid
        # We will use these lists to decide whether the user's request
        # refers to a brand new component or branch, or to an existing
        # component/branch that just isn't on the local machine yet.
        # We are inserting into dictionaries here, instead of lists, as a
        # convenient way to guarantee that we don't have any duplicates.
        components = {}
        branches = {}
        current_sb_names = {}
        for branchname, componentname, aspectname, revid in code_branches:
            # Disallow components and branches that are misnamed. This might
            # just be odd folders created by hand. In the past, we had a
            # "psjbase.bak" folder, for example...
            if not component.get_component_name_validation_error(componentname): #TODO login to plugin
                if not component.get_branch_name_validation_error(branchname):
                    components[componentname] = 1
                    branches[branchname] = 1
                    current_sb_names[componentname + '.' + branchname + '.' + task] = 1
        components = components.keys()
        branches = branches.keys()
        current_sb_names = current_sb_names.keys()
        # Now that we have our three lists, we can use them to analyze
        # the user's request.
        regex = _sb_name_to_fuzzy_regex(name)
        # See if the user's asking for something that the central vcs
        # already knows about.
        hits = [sandbox.Sandbox(x) for x in current_sb_names if regex.match(x)]
        if not hits:
            print('"%s" does not match any component+branch combinations in master repo.' % name)
            if not name_uses_wildcards:
                # Record the fact that the combination does not exist in vcs.
                missing_dict['combo'] = False
                # For some reason, at least one of the following doesn't exist:
                # the requested component, the requested branch, or the combination
                # of component and branch. Figure out which.
                x = None
                if comp:
                    regex = _sb_name_to_fuzzy_regex(comp)
                    x = [x for x in components if regex.match(x)]
                    if len(x) > 1:
                        _report_multi_matches_error(regex.pattern, 'Component', x)
                        return err_tuple
                missing_dict['comp'] = x
                x = None
                if br:
                    regex = _sb_name_to_fuzzy_regex(br)
                    x = [x for x in branches if regex.match(x)]
                    if len(x) > 1:
                        _report_multi_matches_error(br, 'Branch', x)
                        return err_tuple
                missing_dict['br'] = x
                #print(missing_dict)
    if hits:
        # Both the init and the config commands require a single sandbox as
        # an arg, so if we got > 1 match, we have a problem.
        if len(hits) == 1:
            name = hits[0].get_name()
        else:
            print('trying exact matches')
            exact_matches = [h for h in hits if name == h.get_name()]
            if len(exact_matches) == 1:
                name = exact_matches[0].get_name()
            else:
                _report_multi_matches_error(name, 'Sandbox', [x.get_name() for x in hits])
                return err_tuple
    else:
        # If we get here, the component and/or branch the user specified must
        # be new -- or we have a typo or bad wildcards.
        if (missing_dict is None) or name_uses_wildcards:
            return err_tuple
    # If we get here, then we either have a perfect match for the specified
    # name among our existing sandboxes or among the component+branch combos
    # known to the central VCS -- or we have a request for something new,
    # that contained no wildcards. In either case, the name we've been given
    # should conform to our naming conventions.
    err, comp, branch, task = _validate_sandbox_name(name)
    if err:
        eprintc('Invalid sandbox name. ' + err, ERROR_COLOR)
    else:
        # Get correct aspect.
        if not aspect:
            if config.machine_role == 'test':
                aspect = 'built'
            else:
                aspect = 'code'
            if sadm_prompt.prompter.get_mode() == sadm_prompt.INTERACTIVE_MODE:
                comp = name[0:name.find('.')]
                aspect = prompt('Start with which aspect of %s component?' % comp, aspect)
                if aspect.lower().startswith('b'):
                    aspect = 'built'
                else:
                    aspect = 'code'
        # Get desired targeted platform variant
        if not tpv:
            tpv = buildinfo.get_natural_platform_variant()
        if cfg and cfg.lower() not in ['release', 'debug']:
            eprintc('Build config value (%s) can only be set to release or debug', WARNING_COLOR)
            cfg = None
        if not cfg:
            cfg = 'debug' if config.machine_role == 'dev' else 'release'
        return name, comp, branch, task, aspect, tpv, cfg
    return err_tuple

def init(*args):
    """Layout and populate a new sandbox for a particular component."""
    missing_dict = {}
    name, comp, branch, task, aspect, tpv, cfg = _get_cfg_args(missing_dict, *args)
    if name is None:
        return
    # Create a sandbox object. This will throw an exception with a useful error
    # message if name is invalid. It does not actually write anything to disk.
    sb = sandbox.Sandbox(os.path.join(config.sandbox_container_folder, name))
    # Is this sandbox new on this box?
    first_init = not sb.exists()
    if first_init:
        # Is this sandbox also new to vcs?
        if 'combo' in missing_dict:
            eprintc('''
Creating new components and branches must be done by bzr administrators.
Refer to https:// .... /working-with-code/how-to/tasks/create-a-branch ## TODO point to proper doc site
''')
            return
    # Create skeleton on disk
    sb.layout()
    # Save config options we already know.
    sb.set_targeted_platform_variant(tpv)
    # By default, publish official builds on canonical machines.
    if first_init and config.is_canonical_machine and sb.get_sandboxtype().supports_publish():
        sb.get_sandboxtype().set_should_publish(True)
    # Fetch all source code.
    if aggregate_vcs.update_sandbox(sb, branch, aspect, False):
        eprintc('Update failed.', ERROR_COLOR)
        if first_init:
            if prompt_bool('Remove incomplete sandbox?', 'y'):
                remove(sb.get_name())
        return 1
    # Checking required tools
    _check_required_tools(sb)
    if aspect == component.CODE_ASPECT_NAME:
        # Now figure out how the sandbox will be built.
        bld = build.select_builder(sb)
        if not bld:
            eprintc('No build tool supports the codebase for %s.' % name, ERROR_COLOR)
            return 1
        else:
            print('Targeting %s; use config command to override.' % tpv)
            if cfg:
                print('Forcing a %s build currently requires a manual config command.' % cfg)
        configure(name, aspect, tpv, cfg)
        misc = metadata.get_section_info_from_disk(metadata.MISC_SECTION, os.path.join(sb.get_code_root(), comp))
        if misc:
            if metadata.TARGETED_PLATFORMS_OPTION in misc:
                tp = buildinfo.get_implied_platform_variants(
                    misc[metadata.TARGETED_PLATFORMS_OPTION].split(','))
                if tpv not in tp:
                    eprintc("%s normally doesn't build on %s." % (comp, tpv), WARNING_COLOR)
    else:
        print('Note: sandbox is built; "sb build" will only assemble runnable aspect.')
    print('Sandbox is ready.')
    sadm_util.log('init %s' % name)

def configure(*args):
    #fix_ sadm_sandbox.configure_for_eclipse(sb)
    #name, comp, branch, task, aspect, tpv, cfg = _get_cfg_args(None, *args)
    sandboxes = _match_sandboxes('configure', None, *args)
    if not sandboxes:
        return
    err = 0
    for sb in sandboxes:
        sb.set_targeted_platform_variant(buildinfo.get_natural_platform_variant())
        cfg = 'debug' if config.machine_role == 'dev' else 'release'
        sb.set_build_config(cfg)
        sb.set_auto_build(True)
        # We have to launch a subprocess here, instead of calling build.config()
        # directly, because each sandbox may have its own version of buildscripts
        # that supports different features from the one embedded in/with sadm.
        bld_cfg_arg = '--build-type %s ' % cfg.capitalize() if cfg else ''
        prompt_arg = ''
        # Always autorun configure for now. Ticket #5275
        #if prompter.get_mode() == sadm_prompt.INTERACTIVE_MODE:
        #    prompt_arg = '--prompt '
        cmd = 'python "%sbuildscripts/build.py" %s%sconfig' % (sb.get_code_root(), bld_cfg_arg, prompt_arg)
        process = subprocess.Popen(cmd, shell=True)
        process.communicate()
        if process.returncode:
            err = 1
        sadm_util.log('configure %s' % sb.get_name())
    return err

def stop(*args):
    '''
    Stop eval/build/test running against a particular sandbox.
    '''
    sandboxes = _match_sandboxes('stop', lambda sb: sb.is_locked(), *args)
    if not sandboxes:
        return
    for sb in sandboxes:
        try:
            pid = str(sb.get_lock_obj().pid)
            cmd = _PROCKILL_CMD + ' ' + pid
            subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            print('Killed %s (pid %s).' % (sb.get_name(), pid))
            print('Sandbox may need to be reset before it can be reused.')
            sadm_util.log('stop %s' % sb.get_name())
        except:
            sadm_error.write_error()

def help(ignored = None):
    sadm_help.help.show()


def needs_build(sb, tag_to_look_for):
    print "Checking for tag: %s" % tag_to_look_for
    wr = vcs.get_working_repository()
    for cps in sb.get_on_disk_components():
        for aspect in sb.get_component_aspects(cps):
            if aspect == 'test' or aspect == 'code':
                pass
            elif aspect == 'built':
                aspect = 'built.%s' % sb.get_targeted_platform_variant()
            else:
                continue
            branchpath = '%s/%s/%s' % (sb.get_branch(), cps, aspect)
            if wr.branch_is_local(sb.get_branch(), cps, aspect):
                print 'Checking for tag in %s\n' % branchpath
                revid = get_revid(config.working_repo_root, branchpath)
                if revid is None or revid == REVID_NO_REVISIONS:
                    print "No tags in empty branch %s!\n" % branchpath
                    continue
                tags = wr.tags(cps, aspect, sb.get_branch(), reporoot=None)
                folder = sb.get_component_path(cps, aspect)
                if not vcs.folder_is_tied_to_vcs(folder):
                    continue
                if tags is None or tag_to_look_for not in tags:
                    print "%s requires build.\n" % branchpath
                    return True;
            else:
                print "%s not in local branches." % branchpath


def _start(sandboxes, as_needed=False):
    err = 0
    delay = len(sandboxes) - 1
    for sb in sandboxes:
        errors = sb.get_eval_start_errors()
        if errors:
            eprintc('Cannot start %s until vcs status is clean.\n%s' % (sb.get_name(), errors), ERROR_COLOR)
            return 1
        should_reset = sb.get_sandboxtype().get_reset_on_start()
        if sb.get_sandboxtype().get_clean_on_start():
            wr = vcs.get_working_repository()
            committer = wr.get_source_revid(sb.get_branch(), sb.get_top_component(), component.CODE_ASPECT_NAME).split('-')
            committer = ''.join(committer[0:len(committer)-2])
            if config.email_list is not None:
                config.email_list.append(committer)
            else:
                config.email_list = [committer]
            # First build of each day on a continuous sandbox should clean the sandbox.
            # This isn't quite as draconian as resetting the sandbox, but it allows us
            # to automatically correct certain kinds of build problems that can accumulate
            # in a continuous sandbox. A classic example is a .class file that gets built
            # at some point, and then stops being built because its .java file has been
            # deleted. The old .class file can linger and cause problems in unit tests...
            if ospriv.user_has_admin_privileges():
                eprintc("Don't run continuous builds as an admin user.", ERROR_COLOR)
                return 1
            lb = sb.get_last_build_date()
            if lb:
                day_of_last_build = time.strftime('%Y-%m-%d', time.localtime(lb))
                today = time.strftime('%Y-%m-%d', time.localtime())
                should_reset = (day_of_last_build != today)
        if should_reset:
            if ospriv.user_has_admin_privileges():
                eprintc("Don't run official builds as an admin user.", ERROR_COLOR)
                return 1
            print('Sandbox %s needs to be reset.' % sb.get_name())
            err = reset(sb.get_name())
            if err:
                print('Reset Failed.')
                continue
        if (as_needed):
            build = False

            wr = vcs.get_working_repository()

            tag_to_look_for = wr.tags(sb.get_top_component(), 'built.%s' % sb.get_targeted_platform_variant(), sb.get_branch(), reporoot=None)
            if tag_to_look_for:
                tag_to_look_for = re.search("%s\.%s\..*\..*\..*\..*" % (sb.get_top_component(), sb.get_branch()), tag_to_look_for);

            if tag_to_look_for:
                tag_to_look_for = str(tag_to_look_for.group(0))
                tag_to_look_for = tag_to_look_for[:tag_to_look_for.rfind(' ')] # Remove the revid
                build = needs_build(sb, tag_to_look_for)
            else:
                build = True;

            if not build:
                print "Skipping build of %s because no build is needed!\n" % sb.get_name()
                eval_log = open(sandbox.EVAL_LOG, 'w')
                eval_log.write("Skipping build of %s because no build is needed!\n" % sb.get_name())
                eval_log.close()
                sb.set_last_skip_build_date(time.time())
                continue

        if (sb.get_sandboxtype().get_do_notify()) and (config.email_list is not None):
            notify = open('%snotify.txt' % sb.get_root(), 'w')
            for email in config.email_list[:]:
                while config.email_list.count(email) > 1:
                    config.email_list.remove(email)
            for email in config.email_list:
                if config.email_list.index(email) == len(config.email_list)-1:
                    notify.write(email)
                else:
                    notify.write('%s,' % email)
            notify.close()
            config.load()
        cmd = 'python "%sbuildscripts/eval.py" >"%s/%s" 2>&1' % (sb.get_code_root(), sb.get_root(), sandbox.EVAL_LOG)
        if sb.get_sandboxtype().get_nice_build() and os.name != 'nt':
            cmd = 'nice ' + cmd
        try:
            pid = subprocess.Popen(cmd, cwd=sb.get_root(), shell=True).pid
        except:
            err = 1
            print(cmd)
            traceback.print_exc()
            continue
        if sb.get_sandboxtype().get_nice_build() and os.name == 'nt' and pid != None:
            try:
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
                win32process.SetPriorityClass(handle, win32process.IDLE_PRIORITY_CLASS)
            except:
                pass
        msg = 'start %s = pid %s; see %s/%s for output.' % (sb.get_name(), pid, sb.get_name(), sandbox.EVAL_LOG)
        print(msg)
        sadm_util.log(msg)
        if delay:
            print('Pausing a few seconds to stagger start of next sandbox...')
            time.sleep(20)
            delay = delay - 1
    return err

def start(*args):
    '''
    Start eval.py in particular sandbox(es).
    '''
    sandboxes = _match_sandboxes('start', lambda x: not x.is_locked(), *args)
    if not sandboxes:
        return
    _start(sandboxes)

#Verifies that a sandbox builds correctly by doing a get,clean,build,test on the sandbox.
def verify(*args):
    sandboxes = _match_sandboxes('verify', None, *args)
    if not sandboxes:
        return
    err = 0
    for sb in sandboxes:
        if sb.is_locked():
            print('%s is locked:' + sb.get_lock_obj().get_details())
        else:
            err = aggregate_vcs.update_sandbox(sb)
            if not err:
                cmd = 'python "%sbuildscripts/build.py"' % sb.get_code_root()
                child = subprocess.Popen(cmd, shell=True)
                child.communicate()
                if child.returncode:
                    err = 1
                else:
                    cmd = 'python "%sbuildscripts/test.py"' % sb.get_code_root()
                    child = subprocess.Popen(cmd, shell=True)
                    child.communicate()
                    if child.returncode:
                        err = 1
    return err

def _check_required_tools(sb):
    rtools = []
    for comp in sb.get_on_disk_components():
        available = sb.get_component_aspects(comp)
        tools = ['run tools']
        path = ''
        if component.CODE_ASPECT_NAME in available:
            tools.append('build tools')
            path = sb.get_component_path(comp, component.CODE_ASPECT_NAME)
        elif component.BUILT_ASPECT_NAME in available:
            path = sb.get_component_path(comp, component.BUILT_ASPECT_NAME)
        if component.TEST_ASPECT_NAME in available:
            tools.append('test tools')
        for t in tools:
            section = metadata.get_section_info_from_disk(t, path)
            if section:
                for tool, info in section.iteritems():
                    rtools.append(ReqTool.from_pair(tool, info))
    if rtools:
        t = [x.replace(' tools', '') for x in tools]
        t.sort()
        print('Checking required %s tools...\n' % ' and '.join(t))
        check_tools(rtools)
        print('')

_END_OF_ALPHA = 'zzzzz'
class NextSelector:
    def __init__(self):
        self.busy = False
        self._first_alphabetically = _END_OF_ALPHA
        self._next = _END_OF_ALPHA
        self._last_started = 'A'

        # clear cached source branches
        wr = vcs.get_working_repository()
        wr.resetsourcebranches()

        # Get last few starts, most recent first
        recent = sadm_sandbox.list_recent_starts()
        if recent:
            for r in recent:
                # We get tuples in the form (name, pid, when)...
                # TODO this seems hackish, since we are trying to parse a path, not some random string to find an aspect
                # Switching to sandboxtype only revealed this problem
                if sandboxtype.SandboxType(None, path=r[0]).get_should_publish():
                    print('Most recent automatically built sandbox that we started: ' + str(r))
                    self._last_started = r[0]
                    break
    def get_next(self, sandbox_folder):
        print('in get_next(%s)' % sandbox_folder)
        if not self.busy:
            if self._next == _END_OF_ALPHA:
                if self._first_alphabetically != _END_OF_ALPHA:
                    wr = vcs.get_working_repository()
                    sb = sandbox.create_from_within(os.path.join(sandbox_folder, self._first_alphabetically))
                    branch = sb.get_branch()
                    comp = sb.get_top_component()
                    source_revid = wr.get_source_revid(branch, comp, component.CODE_ASPECT_NAME)
                    sb_revid = sb.get_sb_revid()
                    print('revid for %s in repo = ' % source_revid)
                    print('revid for %s in local sandbox = ' % sb_revid)
                    last_run = sb.get_last_successful_build_date()
                    print('last_run = %s (now = %s)' % (last_run, time.time()))
                    if last_run is None:
                        last_run = 0
                    if source_revid != sb_revid or (time.time() - last_run > 86400):
                        return self._first_alphabetically
            else:
                return self._next
        return None
    def __call__(self, sb):
        '''In a single pass through all sandboxes, figure out which sandbox we should
           start next.'''
        name = sb.get_name()
        print('NextSelector.__call__(%s)' % name)
        if not self.busy:
            if sb.is_locked():
                self.busy = name
                print('Busy with %s.' % name)
            elif sb.get_sandboxtype().get_should_schedule():
                print('%s is a schedulable sandbox' % name)
                if name < self._first_alphabetically:
                    self._first_alphabetically = name
                if name > self._last_started:
                    print('%s might be more recently started than %s' % (name, self._last_started))
                    wr = vcs.get_working_repository()
                    source_revid = wr.get_source_revid(sb.get_branch(), sb.get_top_component(),
                                                       component.CODE_ASPECT_NAME)
                    sb_revid = sb.get_sb_revid()
                    last_run = sb.get_last_successful_build_date()
                    if last_run is None:
                        print('%s has not had a successful build recently.' % name)
                        last_run = 0
                    else:
                        print('last successful build date for %s is %s' % (name, dateutils.format_standard_date_with_tz_offset(last_run)))
                    #Get next sandbox if it has had a checkin or if it has been more than 24 hours since it last ran.
                    if name < self._next:
                        if (source_revid != sb_revid) or (time.time() - last_run > 86400):
                            print("%s is better choice for next; it will be chosen unless better candidate is found." % name)
                            self._next = name
                        else:
                            print('revid has not changed, and it has been less than a day since last build.')
                    else:
                        print('%s follows %s (current choice for next sb to build), so disregarding %s as candidate for next.' % (name, self._next, name))

def _get_xml_text(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def _service_build_queue():
    '''
    Checks build queue and fires off builds as appropriate. Returns err on
    failure, 0 on success.
    '''
    matches = []
    desc = buildinfo.BuildInfo()
    # On windows we can cross-compile, so we don't need to restrict by bitness.
    bitness = desc.bitness
    platform = desc.os.lower()
    if 'windows' in platform:
        platform = 'windows'
    req = urllib2.Request(config.build_queue_url+LIST_QUEUE_PAGE)
    base64string = base64.encodestring('sadm:password')[:-1]
    authheader = "Basic %s" % base64string
    req.add_header("Authorization", authheader)
    response = urllib2.urlopen(req).read()
    response = response.replace('bdash.lib.buildqueue', 'buildqueue')
    requests = pickle.loads(response)
    requests = [r for r in requests if not r.assigned_time if r.platform == '*' or r.platform.lower() == platform]
    if os.name != 'nt':
        requests = [r for r in requests if bitness == r.bitness]
    if not requests:
        print('Official build queue is empty for me.')
        return 1
    sandboxes = sandbox.list(config.sandbox_container_folder)
    if os.name == 'nt':
        site = os.environ['COMPUTERNAME'].lower()
    else:
        site = os.environ['HOSTNAME'].lower()

    # try and run official sandboxes first. Then run all other types of sandboxes
    sandbox_type = ['official', '*']
    for type in sandbox_type:
        for r in requests:
            if (r.requested_machine in ['*', '']) or (r.requested_machine.lower() == site):
                sbname = r.get_sandbox_name()
                for sb in sandboxes:
                    if (sb.get_name() == sbname):
                        if (sb.get_name().find('official') > -1) and not sb.get_sandboxtype().get_should_publish():
                            pass
                        else:
                            # we first do official sandboxes, then we do other types of sandboxes
                            if (not sb.get_sandboxtype().get_variant() == 'official') and type == 'official':
                                continue;
                            if config.email_list is None:
                                config.email_list = [r.requester]
                            else:
                                config.email_list.append(r.requester)
                            url = config.build_queue_url + ASSIGN_QUEUE_PAGE
                            data = 'Component=%s&Branch=%s&bitness=%s&platform=%s&style=%s&reqMachine=%s&machine=%s' % (r.component, r.branch, r.bitness, r.platform, r.style, r.requested_machine, desc.host)
                            req = urllib2.Request(url, data)
                            req.add_header("Authorization", authheader)
                            response = urllib2.urlopen(req).read()
                            start(sbname)
                            # Only service one request at a time; if any requests remain,
                            # maybe a different machine will pick them up...
                            return 0
    print('Could not service any of the following sandboxes:')
    print(INDENT + ('\n' + INDENT).join(['%s %s %s' % (r.get_sandbox_name(), r.platform, r.bitness) for r in requests]))
    return 1

class _ChildLoopKiller():
    def __init__(self, child):
        self.child = child
    def __call__(self):
        self.child.terminate()

def loop(*args):
    # This function launches another copy of sadm as a subprocess, waits for it
    # to exit, and repeats as long as as the child process returns zero. It is
    # used to run sadm in a sort of daemon mode.
    #
    # A true daemon mode (or even running sadm in a loop from a crontab) is
    # problematic because on el5 and el6, the permissions and environment that
    # a crontab uses are different enough from those of an interactive login to
    # make the finding of commands in the path problematic. We have tried to
    # resolve these problems without a lot of success.
    #
    # In daemon mode, one of the things sadm does is automatically update itself.
    # The changes from an update take effect correctly in the child copies of
    # sadm, even though they don't effect the process in daemon mode itself,
    # because python correctly regenerates and uses a new sadm.pyc after every
    # update.
    if args:
        args = [sadm_util.quote_if_needed(a) for a in args]
        args = ' ' + ' '.join(args)
    else:
        args = ''
    timeout = 300
    time.sleep(random.randint(1, 15))
    cmd = 'python "%s" _loop_as_child %d%s' % (APP_PATH, random.randint(1, 5), args)
    print('Waiting for a brief, random interval to stagger schedules...')
    while True:
        child = subprocess.Popen(cmd, shell=True)
        #monitor = timeout_monitor.start(timeout, killfunc=_ChildLoopKiller(child))
        try:
            child.communicate()
            #monitor.last_status = time.time()
            # Give child handles time to close and clean up.
            time.sleep(1)
        except KeyboardInterrupt:
            break
        '''finally:
            if monitor:
                monitor.stop()'''

def _loop_as_child(*args):
    sandboxes = None
    # Our scheduling depends on multiples of minutes. If all VMs on a given host
    # have the same schedule, there might be a glut of actions clustered around
    # a particular minute. We already waited a random number of seconds before
    # beginning, but now we want to also alter the meaning of each minute slightly,
    # for further staggering. We use a value calculated by our parent process,
    # so that we have the same value across runs of the child.
    random_offset = int(args[0])
    args = args[1:]
    # If we were given a set of sandboxes to loop over, use them. Otherwise,
    # we will just loop over all continuous sandboxes (a set that we recalculate
    # each time through the loop).
    if args:
        sandboxes = _match_sandboxes('start', None, *args)
    while True:
        try:
            prompter.set_mode(AUTOCONFIRM_MODE)
            _next(random_offset, sandboxes)
            time.sleep(60)
        except:
            print sys.exc_info()[1]
            time.sleep(60)
            sys.exit(0)

def _get_current_minute():
    now = time.localtime()
    minute = (now[3] * 60) + now[4]
    return minute

def _update_and_restart():
    if sadm_vcs.update_program_if_needed():
        print('Restarting sadm to pick up code changes...')
        sys.exit(0)

_first_call_to_next = True
def _next(random_offset, sandboxes):
    global _first_call_to_next
    minute = (_get_current_minute() + random_offset) % 1440
    print('minute = %d' % minute)
    if minute == 0:
        # We need to check for updates unless we just barely restarted and it's
        # the same minute when our last sibling exited.
        if not _first_call_to_next:
            _update_and_restart()
    _first_call_to_next = False
    if True: #minute % 5 == 0:
        # At the top of each hour, see if new sandboxes need to be added to my
        # inventory. The rest of each hour, just repeatedly build stuff.
        sandbox_count = len(sandbox.list(config.sandbox_container_folder))
        if minute % 15 == 0 and config.is_canonical_machine and config.auto_add_sandboxes and sandbox_count < 30:
            _add_new_sandboxes()
        elif minute % 125 == 0 and config.is_canonical_machine and config.auto_add_sandboxes and False:
            _remove_retired_sandboxes()
        else:

            # Kim Ebert 2012-02-08
            # Added as termporary measure to ensure only one sandbox is running at a time in sadm loop.
            # Long term solution is to allow multiple sandboxes to run together, at which time this code should be removed
            busy = [sb for sb in sandbox.list(config.sandbox_container_folder) if sb.is_locked()]
            if busy:
                for b in busy:
                    print("Sandbox %s is busy." % b.get_name())
                return

            # Give a higher priority to official build requests than to continuous
            # ones -- only start continuous if nothing official is started.
            if config.is_canonical_machine:
                err = _service_build_queue() # returns err if nothing found/started
                should_start = bool(err)
            else:
                should_start = True
            if should_start:
                _start_next(sandboxes)

def next(*args):
    _next(0, [])

def _add_known_build_tools(sb, cached_components, known_build_tools):
    if sb.get_component_reused_aspect(sb.get_top_component()) == 'code':
        for cc in cached_components:
            aspect = sb.get_component_aspects(cc.name)[0]
            path = sb.get_component_path(cc.name, aspect)
            tool_dict = metadata.get_section_info_from_disk(metadata.BUILD_TOOLS_SECTION, path)
            if tool_dict:
                for tool in tool_dict.keys():
                    copy = False
                    if tool not in known_build_tools:
                        copy = True
                    else:
                        v1 = tool_dict[tool]
                        v2 = known_build_tools[tool]
                        if v1 > v2:
                            copy = True
                    if copy:
                        known_build_tools[tool] = tool_dict[tool]

def _remove_retired_sandboxes():
    mbranches = vcs.get_branches(config.master_repo_root)
    if mbranches:
        mbranches = [mb[0] for mb in mbranches]
        for sb in sandbox.list(config.sandbox_container_folder):
            if sb.get_branch() not in mbranches:
                sb.remove()
        branches = os.listdir(config.working_repo_root)
        for branch in os.listdir(config.working_repo_root):
            if branch not in mbranches:
                ioutil.nuke(os.path.join(os.listdir(config.working_repo_root, branch)).replace('\\', '/'))

def _add_new_sandboxes():
    '''
    Get a list of branches for the 'code' aspect of components.
    Eliminate any that I already have.
    On branches other than trunk, eliminate anything that's not a top-level
    component.
    Eliminate any that do not target the current platform.
    Eliminate any that require build tools that I don't have.
    Eliminate any that are already well covered by other build machines.
    Claim 1 at random.
    Create sandboxes for them.
    '''
    if config.branches_to_auto_add is None or not config.auto_add_sandboxes:
        return
    default_trunk_only = ['buildscripts', 'feeder', 'psjbase', 'PsFramework', 'mathapp', 'mathlib', 'PsCppUnit', 'PsEngine', 'nlplib', 'example-calculator', 'example-mathlib']
    mbranches = vcs.get_branches(config.master_repo_root, aspect='code')
    lsandboxes = sandbox.list(config.sandbox_container_folder)
    if len(lsandboxes) > 29:
        return
    lsandboxes = [[sb.get_top_component(), sb.get_component_reused_aspect(sb.get_top_component()), sb.get_branch()] for sb in lsandboxes]
    mbranches = [mb for mb in mbranches if mb not in lsandboxes]
    del(lsandboxes)
    non_trunk = [mb for mb in mbranches if mb[0] != 'trunk']
    mbranches = [mb for mb in mbranches if mb[1] not in default_trunk_only or mb[0] == 'trunk']
    known_build_tools = {}
    for sb in sandbox.list(config.sandbox_container_folder):
        try:
            cc = sb.get_cached_components()
            ccomps = [c.name for c in cc]
            if len(cc) > 1:
                cc = cc[0:-1]
                non_trunk = [nt for nt in non_trunk if nt[0] not in ccomps]
            #I don't think this is needed since check_tools is being called.
            #_add_known_build_tools(sb, cc, known_build_tools)
        except:
            pass
    mbranches = [mb for mb in mbranches if mb[0] == 'trunk' or mb in non_trunk]
    if config.branches_to_auto_add.strip().lower() != 'all':
        branches_to_add = [x.strip().lower() for x in config.branches_to_auto_add.split(',')]
        mbranches = [mb for mb in mbranches if mb[0].lower() in branches_to_add]
    random.shuffle(mbranches)
    tpv = buildinfo.get_natural_platform_variant()
    official = False
    continuous = False
    err = 1
    for mb in mbranches[:100]:
        try:
            comp, br = mb[1], mb[0]
            data = vcs.get_file_contents(config.master_repo_root, comp,
                                         component.CODE_ASPECT_NAME, br,
                                         metadata.METADATA_FILE)
            if data:
                with tempfile.TemporaryFile() as fp:
                    fp.write(data)
                    fp.seek(0)
                    misc = metadata.get_section_info_from_fp(metadata.MISC_SECTION, fp)
                    if misc:
                        if metadata.TARGETED_PLATFORMS_OPTION in misc:
                            tp = buildinfo.get_implied_platform_variants(
                                misc[metadata.TARGETED_PLATFORMS_OPTION].split('|'))
                            if tpv not in tp:
                                continue
                        if metadata.DO_NOT_INTEGRATE_OPTION in misc:
                            continue
                    tools = metadata.get_section_info_from_fp(metadata.BUILD_TOOLS_SECTION, fp)
                    rtools = []
                    if tools:
                        for tool, info in tools.iteritems():
                            rtools.append(ReqTool.from_pair(tool, info))
                    if check_tools(rtools) != 0:
                        continue
                    print mb
                    build, err = vcs.ls(os.path.join(config.master_repo_root, mb[0], mb[1], mb[2], '.if_top').replace('\\', '/'))
                    if not build and not err:
                        continue
                    td = tempfile.mkdtemp()
                    wr = vcs.get_working_repository()
                    rbranches = vcs.get_branches(config.master_repo_root, aspect='report')
                    report = False
                    for rb in rbranches:
                        if rb[1] == mb[1] and rb[0] == mb[0]:
                            report = True
                            break
                    if report:
                        try:
                            vcs.checkout('%s/%s/report/%s' % (config.master_repo_root, comp, br), td)
                        except:
                            continue
                        db = Dashboard(td)
                        hosts_platform_styles = db.get_recent_hosts_platform_styles()
                        num_continuous = 0
                        num_official = 0
                        for host in hosts_platform_styles:
                            if hosts_platform_styles[host][0] == tpv:
                                if EvalStyle.CONTINUOUS in hosts_platform_styles[host][1]:
                                    num_continuous += 1
                                if EvalStyle.OFFICIAL in hosts_platform_styles[host][1]:
                                    num_official += 1
                        if num_continuous < 3:
                            continuous = True
                        official = not num_official
                        if official or continuous:
                            break
                    else:
                        official = True
                        continuous = True
                        break
        except:
            traceback.print_tb(sys.exc_info()[2])
            print sys.exc_info()[1]
        finally:
            if official or continuous:
                break
    old_mode = prompter.get_mode()
    prompter.set_mode(AUTOABORT_MODE)
    try:
        if continuous:
            err = 0
            init('%s.%s.%s' % (comp, br, 'continuous'))
        if official:
            err = 0
            init('%s.%s.%s' % (comp, br, 'official'))
            start('%s.%s.%s' % (comp, br, 'official'))
    finally:
        prompter.set_mode(old_mode)
    return err

def _start_next(sandboxes):
    print('\n\n_start_next; sandboxes =')
    if sandboxes:
        for sb in sandboxes:
            print(sb.get_name())
    selector = NextSelector()
    sbs = sandbox.list(config.sandbox_container_folder)
    for sb in sbs:
        selector(sb)
    if selector.busy:
        print("Sandbox %s is busy." % selector.busy)
        return
    nxt = selector.get_next(config.sandbox_container_folder)
    if nxt:
        start(nxt)

# List a few recently started sandboxes, most recent first.
def last(*args):
    _show_history(True, *args)

def _show_history(eliminate_duplicates, *args):
    # We never want to prompt a user if this command was run directly from a command line.
    # However, if it was run from the menu, we can allow them to enter criteria
    # to narrow the search.
    prompt_mode = prompter.get_mode()
    if prompt_mode != sadm_prompt.INTERACTIVE_MODE:
        prompter.set_mode(sadm_prompt.AUTOCONFIRM_MODE)
    try:
        # Find sandboxes according to whatever criteria we were given. For example,
        # if we were asked to find *official, return only sandboxes where the variant
        # is "official".
        if args:
            sandboxes = [sb.get_name() for sb in _match_sandboxes('last', None, *args)]
        else:
            sandboxes = True
        if sandboxes:
            recent = sadm_sandbox.list_recent_starts()
            if recent:
                should_list = []
                already_listed = []
                for sbTuple in recent:
                    name = sbTuple[0]
                    if name not in already_listed:
                        include = not args
                        if not include:
                            include = name in sandboxes
                        if include:
                            if eliminate_duplicates:
                                already_listed.append(name)
                            should_list.append(sbTuple)
                for sbTuple in should_list:
                    row = PARAM_COLOR + sbTuple[0].ljust(35)
                    row += DELIM_COLOR +' - ' + NORMTXT + sbTuple[2]
                    printc(row)
    finally:
        # Undo temporarily forced mode.
        prompter.set_mode(prompt_mode)

def history(*args):
    _show_history(False, *args)

def reset(*args):
    '''
    Put sandbox(es) back in pristine state, exactly as they were when created.
    Required, generated cmake files are untouched (preserving any special sb
    config), but no source code or build output remains.
    '''
    sandboxes = _match_sandboxes('reset', None, *args)
    if not sandboxes:
        return
    allSandboxes = None
    for sb in sandboxes:
        if sb.is_locked():
            lck = sb.get_lock_obj()
            details = lck.get_details(lck.path)
            print('\n' + details)
            if not prompt_bool('Sandbox %s is currently locked. Stop anyway?' % sb.get_name(), 'n'):
                continue
            stop(sb.get_name())
        if sb.get_sandboxtype().supports_checkouts():
            status = aggregate_vcs.get_sandbox_status(sb)
            if status and not sb.get_sandboxtype().get_prompt_on_reset():
                print(aggregate_vcs.format_sandbox_status(sb, status))
                if not prompt_bool('Are you sure you want to reset %s?' % sb.get_name(), 'n'):
                    continue
        sb.set_last_successful_build_date(0)
        sb.set_last_build_date(0)
        sb.set_last_test_date(0)
        rt = sb.get_root()
        subdirs = [rt + d + '/' for d in os.listdir(rt) if d != 'report']
        subdirs = [d for d in subdirs if os.path.isdir(d)]
        br = sb.get_built_root()
        subdirs = [d for d in subdirs if d != br]
        for sd in subdirs:
            ioutil.nuke(sd)
        skips = r'CMakeFiles(/.*)?$;Makefile;[^/]+\.(txt|vcproj|sln|tcl|cmake|ctest)'.split(';')
        ioutil.nuke(br, skip=skips)
        print('Removed all source and build artifacts from %s.' % sb.get_name())
        return init(sb.get_name(), sb.get_targeted_platform_variant())

def tools(*args):
    tool_types = []
    default_tool_types = ['build', 'test', 'run']
    for tt in default_tool_types:
        if tt in args:
            tool_types.append('build')
            args.remove(tt)
    if not tool_types:
        tool_types = default_tool_types
    sandboxes = _match_sandboxes('tools', None, *args)
    if not sandboxes:
        return
    for sb in sandboxes:
        folder = sb.get_code_root()
        print('Checking %s tools in %s' % (', '.join(tool_types), sb.get_name()))
        sb.check_tools(tool_types=tool_types, quiet=False)
        print('')

def remove(*args):
    sandboxes = _match_sandboxes('remove', None, *args)
    if not sandboxes:
        return
    allSandboxes = None
    for sb in sandboxes:
        if False: #fix_ sb.pid:
            if not prompt_bool('CTest is currently running against %s as pid %s. Kill?' % (sb.get_name(), sb.pid), 'n'):
                continue
            stop(sb.get_name())
        if sb.get_sandboxtype().get_prompt_on_remove():
            warning = 'Local changes will be lost:\n\n'
            try:
                local_mods = aggregate_vcs.get_sandbox_status(sb)
            except:
                warning = "Sandbox status can't be determined, probably because of corruption."
                local_mods = {'none':{}}
            if local_mods:
                writec(WARNING_COLOR + warning)
                print(aggregate_vcs.format_sandbox_status(sb, local_mods).rstrip())
                printc(NORMTXT)
                if not prompt_bool('Are you sure you want to remove %s?' % sb.get_name(), 'n'):
                    continue
        if False: #fix_ sb.schedule:
            if not prompt_bool('%s is currently scheduled %s. Remove schedule?' % (sb.get_name(), str(sb.schedule)), 'n'):
                continue
            sb.schedule = None
            sb.applySchedule()
        sb.remove()
        print('Removed %s.' % sb.get_name())
        sadm_util.log('remove %s' % sb.get_name())

def setup(*args):
    '''
    Make sure this script is set up correctly and all required tools are available.
    '''
    sadm_setup.do_setup(False, *args)

_SHORT_CIRCUIT_PAT = re.compile(r'Last(Pass|Fail|Fail2orMore)\.txt', re.IGNORECASE)

# Display useful info from the most recent logs for a given sandbox.
def logs(*args):
    sandboxes = _match_sandboxes('logs', None, *args)
    if not sandboxes:
        return
    if len(sandboxes) > 1:
        print('%d matches for %s; only one set of logs viewable at a time.' % (len(sandboxes), str(args)))
        return 1
    sb = sandboxes[0]
    show_logs(sb)
    sadm_util.log('logs %s' % sb.get_name())

def tail(*args):
    lines = get_tail(CMD_LOG)
    if not lines:
        print('No events in log.')
    else:
        for line in lines:
            sys.stdout.write(line)

def check(*args):
    sandboxes = _match_sandboxes('check', None, *args)
    if not sandboxes:
        return
    for sb in sandboxes:
        print("%s:" % sb.get_name())
        if check_vcs_status(sb):
            print('    ... can be evaluated.\n')
        else:
            print('    ... CANNOT be evaluated.\n')

def showdep(*args):
    sandboxes = _match_sandboxes('showdep', None, *args)
    if not sandboxes:
        return
    wr = vcs.get_working_repository()
    for sb in sandboxes:
        top = sb.get_top_component()
        location = sb.get_code_root()
        branch = sb.get_branch()
        print("%s:" % sb.get_name())
        for cp in metadata.get_components_inv_dep_order(wr, sb.get_targeted_platform_variant(), top, location, branch, use_master=False, check_vcs=True):
            print(cp);
        print("\n")

def _start_to_finish(sb, waitForReplication=True):
    startTime = time.time()

    if sb.get_sandboxtype().get_do_build_if_tags_out_of_date():
        _start([sb], as_needed=True)
    else:
        _start([sb])

    if sb.get_last_skip_build_date():
        if sb.get_last_skip_build_date() > startTime:
            print "%s Build was skipped." % sb.get_name()
            return True

    time.sleep(5) # give some time for the sandbox to start
    ticks = 0
    while sb.lock_exists():
        ticks += 1
        if ticks >= 15:
            ticks = 0
        elif ticks == 1:
            print '\r%s\r' % ( ' ' * (48 + len(sb.get_name())) ),
            print "Waiting for %s to finish" % sb.get_name(),
        else:
            print ".",
        sys.stdout.flush()
        time.sleep(1)

    if not sb.get_last_successful_build_date():
        print "%s Build Failed." % sb.get_name()
        return False
    if (sb.get_last_successful_build_date() < startTime):
        print "%s Build Failed." % sb.get_name()
        return False
    if sb.get_sandboxtype().get_should_publish() and (not sb.get_last_publish_status()):
        print "%s Publish Failed." % sb.get_name()
        return False

    if sb.get_sandboxtype().get_should_publish() and waitForReplication and config.site_repo_root != None:
        print "Waiting for replication"
        errorCount = 0;
        while True:
            if errorCount > 10:
                print("Replication failed!")
                return False
            branchpath = '%s/%s/built.%s' % (sb.get_branch(), sb.get_top_component(),
                                             sb.get_targeted_platform_variant())
            masterrevid = get_revid(config.master_repo_root, branchpath)
            siterevid = get_revid(config.site_repo_root, branchpath)
            BAD_REVS = [REVID_NO_REVISIONS, REVID_UNKNOWN]
            if siterevid in BAD_REVS or masterrevid in BAD_REVS:
                print("There is an error in the bzr revid")
                errorCount += 1;
            elif errorCount > 0:
                errorCount -= 1;

            if siterevid == masterrevid:
                print("Site Repo matches Master Repo.\n Site-   %s \n Master- %s"
                          % (siterevid, masterrevid))
                break;
            print("Site Repo doesn't match Master Repo.\n Site-   %s \n Master- %s"
                          % (siterevid, masterrevid))
            print("%s Sleeping 30 seconds." % component)
            time.sleep(30)

    return True


def _build_above_remove_from_list(buildSandbox, sandboxes, sb_meta):
    # remove anyone from the toBuild list that depends upon us, or them
    # We are assuming that the list is always processed in the same order, and so if we remove anything that depends upon us here, we will be built before anyone who is added after this point
    for sb_meta_other_name in sandboxes:
        sb_meta_other = sandboxes[sb_meta_other_name]

        for cps in sb_meta_other['meta']:
            if (sb_meta_other['sandbox'].get_name() == sb_meta['sandbox'].get_name()):
                continue;
            if ("%s.%s.%s" % (cps.get_name(), cps.get_branch(), buildSandbox.get_variant())) == sb_meta['sandbox'].get_name():
                if sb_meta_other['toBuild'] or (not sb_meta_other['dontBuild']):
                    #print "Removing %s" % (sb_meta_other['sandbox'].get_name())
                    sb_meta_other['dontBuild'] = True;
                    sb_meta_other['toBuild'] = False;
                    _build_above_remove_from_list(buildSandbox, sandboxes, sb_meta_other);
                continue;

def _build_above(buildSandbox, simulated=False):
    '''
    This builds dependancies based upon the incoming sandbox.
    '''
    wr = vcs.get_working_repository()

    print("Please note: this function does not detect missing compoments due the way it was implemented.\n")

    print("Building %s" % buildSandbox.get_name())
    if not simulated:
        if not _start_to_finish(buildSandbox):
            return False;

    print("Checking sandboxes for dependency on %s" % buildSandbox.get_name())

    sandboxes = {};

    # get meta data for sandboxes

    sandboxes[buildSandbox.get_name()] = {'sandbox': buildSandbox, 'meta': [], 'toBuild': False, 'dontBuild': False, 'built': True, 'failed': False}

    for sb in sandbox.list(config.sandbox_container_folder):
        if sb.get_branch() != buildSandbox.get_branch():
            continue
        if sb.get_variant() != buildSandbox.get_variant():
            continue
        if sb.get_top_component() == buildSandbox.get_top_component():
            continue

        top = sb.get_top_component()
        location = sb.get_code_root()
        branch = sb.get_branch()

        cps = metadata.get_components_inv_dep_order(wr, sb.get_targeted_platform_variant(), top, location, branch, use_master=False, check_vcs=False)

        sandboxes[sb.get_name()] = {'sandbox': sb, 'meta': cps, 'toBuild': False, 'dontBuild': False, 'built': False, 'failed': False}

    # If we don't build anything we are done.
    building = True

    while (building):
        building = False

        for sb_meta_name in sandboxes:
            sb_meta = sandboxes[sb_meta_name];

            # don't build anyone who depends upon a failed sandbox
            if sb_meta['failed']:
                _build_above_remove_from_list(buildSandbox, sandboxes, sb_meta);
                continue;

            # don't build already built sandboxes
            if sb_meta['built']:
                continue;

            build_sb_meta = False

            # do we need to build it?
            for cps in sb_meta['meta']:
                try:
                    if sandboxes["%s.%s.%s" % (cps.get_name(), cps.get_branch(), buildSandbox.get_variant())]['built']:
                        build_sb_meta = True
                except KeyError, e:
                    pass;

            # we don't need to build it
            if not build_sb_meta:
                continue;

            # remove anyone who depends upon us
            _build_above_remove_from_list(buildSandbox, sandboxes, sb_meta);
            if not sb_meta['dontBuild']:
                sb_meta['toBuild'] = True;
            else:
                pass

        # Now that we know what we are going to build this round, build it.
        for sb_meta_name in sandboxes:
            sb_meta = sandboxes[sb_meta_name];

            sb_meta['dontBuild'] = False;
            if sb_meta['toBuild'] and (not sb_meta['failed']):
                print "Building %s" % sb_meta['sandbox'].get_name()
                sb_meta['toBuild'] = False;

                if not simulated:
                    if not _start_to_finish(sb_meta['sandbox']):
                        sb_meta['failed'] = True;
                        continue;

                sb_meta['built'] = True;
                building = True

    # Do we return True or False?
    for sb_meta_name in sandboxes:
        sb_meta = sandboxes[sb_meta_name];

        if sb_meta['failed']:
            return False;

    return True



def print_components_in_columns(components):
    i = 0
    while i < len(components):
        if i % 4 == 0:
            print ' ',
        print '%-19s' % components[i],
        if (i + 1) % 4 == 0:
            print
        i += 1
    print '\n'



def _build_up_to(sandboxname, simulated=False, shouldinit=True, excludes={'components':[],'tree':[]}):
    '''
    This builds required components in the order they should be built.

    This function depends upon get_components_inv_dep_order returning the proper order.
    '''
    wr = vcs.get_working_repository()
    component,branch,task = sandboxname.split('.');
    print component,branch,task
    component,aspect,branch,task = wr.normalize(component,'code',branch,task)
##    top = buildSandbox.get_top_component()
##    location = buildSandbox.get_code_root()
##    branch = buildSandbox.get_branch()

    print 'Retrieving dependendies -- be patient...'
    components = metadata.get_components_in_product(wr, branch, component, excludes)

    sandboxes = sandbox.list(config.sandbox_container_folder)

    while components:
        print "\nNeed to build %d more components:" % len(components)
        print_components_in_columns(components)
        cps = components.pop(0)
        foundSandbox = False
        branchpath = "%s.%s.%s" % (cps, branch, task)  ##TODO julie buildSandbox.get_variant())
        for sb in sandboxes:
            if (sb.get_name() == branchpath):
                foundSandbox = True
                break
        if not foundSandbox:
            if (shouldinit):
                print "Creating sandbox %s\n" % branchpath
                if not simulated:
                    init(branchpath)
                    sandboxes = sandbox.list(config.sandbox_container_folder)
                    for sb in sandboxes:
                        if (sb.get_name() == branchpath):
                            foundSandbox = True
                            break
                    if not foundSandbox:
                            print( "!!!Failed to init %s!!!" % branchpath)
                            return False
            else:
                print( "!!!Skipping missing sandbox %s!!!" % branchpath)
        print "Building %s\n" %sb.get_name();
        if not simulated:
            if not _start_to_finish(sb):
                return False
        continue;


##    print("Building %s" % buildSandbox.get_name())
##    if not simulated:
##        if not _start_to_finish(buildSandbox):
##            return False;

def StartAndWait(*args):
    sandboxes = _match_sandboxes('StartAndWait', None, *args)
    if not sandboxes:
        return
    for sb in sandboxes:
        if not _start_to_finish(sb):
            exit(-1)

def buildupto(*args):
    BuildUpTo(*args)

def bu2(*args):
    BuildUpTo(*args)

def bu2s(*args):
    BuildUpToSim(*args)

def BuildUpTo(*args):
    excludes = {'components':[],'tree':[]}
    if len(args) > 1:
        parser = optparse.OptionParser(description = "Build up to a sandbox. Use options to exclude certain sandboxes", usage = '%s %s [options]' % (os.path.basename(sys.argv[0]), sys.argv[1]))
        parser.add_option('--excludes', action = 'store', dest = 'excludes', default=None, \
                          help="Comma separated components to exclude sandboxes from build up to. example: --excludes feeder,ss,webapp")
        parser.add_option('--excludetrees', action = 'store', dest = 'excludetrees', default=None, \
                          help="Same as excludes only it'll exclude the whole tree. Such as exclude feeder will also exclude tika.")
        parsed, arg = parser.parse_args()
        if len(arg) > 2:
            parser.print_help()
            parser.exit()
        if parsed.excludes:
            excludes['components'] = parsed.excludes.split(',')
        if parsed.excludetrees:
            excludes['tree'] = parsed.excludetrees.split(',')
    if not _build_up_to(args[0], simulated=False, shouldinit=True, excludes=excludes):
        exit(-1)

##    print 'args', args
##    sandboxes = _match_sandboxes('BuildUpTo', None, *args)
##    print sandboxes
##    if sandboxes:
##        for sb in sandboxes:
##            if not _build_up_to(sb):
##                exit(-1)

def BuildUpToSim(*args):
    excludes = {'components':[],'tree':[]}
    if len(args) > 1:
        parser = optparse.OptionParser(description = "Build up to a sandbox. Use options to exclude certain sandboxes", usage = '%s %s [options]' % (os.path.basename(sys.argv[0]), sys.argv[1]))
        parser.add_option('--excludes', action = 'store', dest = 'excludes', default=None, \
                          help="Comma separated components to exclude sandboxes from build up to. example: --excludes feeder,ss,webapp")
        parser.add_option('--excludetrees', action = 'store', dest = 'excludetrees', default=None, \
                          help="Same as excludes only it'll exclude the whole tree. Such as exclude feeder will also exclude tika.")
        parsed, arg = parser.parse_args()
        if len(arg) > 2:
            parser.print_help()
            parser.exit()
        if parsed.excludes:
            excludes['components'] = parsed.excludes.split(',')
        if parsed.excludetrees:
            excludes['tree'] = parsed.excludetrees.split(',')
    if not _build_up_to(args[0], simulated=True, shouldinit=True, excludes=excludes):
        exit(-1)
    ##TODO julie
##    print 'args', args
##    sandboxes = _match_sandboxes('BuildUpTo', None, *args)
##    print sandboxes
##    if sandboxes:
##        for sb in sandboxes:
##            if not _build_up_to(sb, simulated=True):
##                exit(-1)

def BuildAbove(*args):
    sandboxes = _match_sandboxes('BuildAbove', None, *args)
    if sandboxes:
        for sb in sandboxes:
            if not _build_above(sb):
                exit(-1)

def BuildAboveSim(*args):
    sandboxes = _match_sandboxes('BuildAboveSim', None, *args)
    if sandboxes:
        for sb in sandboxes:
            if not _build_above(sb, simulated=True):
                exit(-1)

def update(*args):
    if sadm_vcs.update_program_if_needed() and (not config.test_mode):
        print('\nCalling setup to guarantee correct behavior...')
        # We want to call setup on the *new* sadm, not the old one that's already
        # running. So use os.system().
        os.system("python %s setup --auto-confirm" % APP_PATH)

def list(*args):
    if args and args[0].lower() == 'names':
        args = args[1:]
        if not args:
            args = ['all']
        for sb in _match_sandboxes('list', None, *args):
            print(sb.get_name())
    else:
        sadm_prompt.list_sandboxes(*args)

def get_latest(component, branch, tpv):
    stdout = subprocess.check_output('bzr revno "%s/%s/trunk/%s"' % (
        DEFAULT_MASTER_REPOROOT, project))
    if stdout:
        stdout = stdout.strip()
    return stdout

def latest(*args):
    component = None
    if args and args[0]:
        component = args[0]
    else:
        component = prompt("Component?")
    if component:
        rev = get_latest(component, 'trunk', 'linux_x86-64')
        if not rev:
            rev = 'unknown'
        print rev

#boost -r3293 https://subversion.assembla.com/svn/ps-share/trunk/tools/external/boost_1_44_0-headers-only
COMPONENT_PAT_TXT = r'^\s*([-_a-zA-Z0-9]+)\s+(\S+\s+)?(http\S+/ps-(?:deliver|share)/\S+/%s\S*)\s*$'
def _pin(sb, component, rev):
    print('Not currently supported.')
    return 0

def pin(*args):
    component = None
    rev = None
    if args and len(args) > 2:
        rev = args[-1]
        component = args[-2]
        args = args[0:-2]
    if not component:
        component = prompt('Component')
        if not component:
            return
    if not rev:
        rev = prompt('Revision', 'latest')
        if not rev:
            return
    if rev.lower() == 'latest':
        rev = getLatest(component)
        if not rev:
            eprintc('Unable to determine latest rev of component %s' % component, ERROR_COLOR)
            return 1
    sandboxes = _match_sandboxes('pin', None, *args)
    if not sandboxes:
        return 1
    exitCode = 0
    n = 0
    for sb in sandboxes:
        n += _pin(sb, component, rev)
    if n:
        print('Do not forget to check in changes after validating your sandbox(es).')

def where(*args):
    print(APP_FOLDER)

def foreach(*args):
    sandbox_args = []
    cmd_args = []
    if args:
        for i in range(len(args)):
            if args[i].lower() == 'do':
                sandbox_args = args[0:i]
                args = args[i+1:]
                cmd_args = []
                for a in args:
                    if a.find(' ') > -1:
                        cmd_args.append('"%s"' % a)
                    else:
                        cmd_args.append(a)
                cmd_args = ' '.join(cmd_args)
                break
    sandboxes = _match_sandboxes('foreach', None, *sandbox_args)
    if not sandboxes:
        return
    if not cmd_args:
        cmd_args = prompt('Command')
        if not cmd_args:
            return
    oldcwd = os.getcwd()
    for sb in sandboxes:
        print("in %s: %s" % (sb.get_name(), cmd_args))
        try:
            stdout = subprocess.check_output(cmd_args, shell=True, cwd=sb.get_root())
            print(stdout)
            print('')
        except Exception:
            sadm_error.write_error()

_HELP_SWITCHES = ['?','help']
def _parse_switches(args):
    bad = False
    showHelp = False
    i = j = 0
    while i < len(args):
        arg = args[i]
        # Stop parsing args after 'do' keyword in foreach ... do construct.
        if arg == 'do':
            break
        val = None
        if arg.startswith('--'):
            val = arg[2:]
        elif (i == 0 and arg.startswith('-')):
            val = arg[1:]
        elif (j == 0 and (arg.lower() in _HELP_SWITCHES)):
            val = arg
        if val:
            args.remove(arg)
            val = val.lower()
            if val in _HELP_SWITCHES:
                showHelp = True
            elif val == 'no-color':
                ansi2.set_use_colors(False)
            elif val == 'auto-confirm':
                prompter.set_mode(sadm_prompt.AUTOCONFIRM_MODE)
            elif val == 'auto-abort':
                prompter.set_mode(sadm_prompt.AUTOABORT_MODE)
            elif val == 'test':
                config.test_mode = True
                config.sandbox_container_folder = TEST_SANDBOXES
                prompter.set_mode(sadm_prompt.AUTOCONFIRM_MODE)
            else:
                # Normalize switch.
                args.insert(i, '--%s' % val)
                i += 1
        else:
            i += 1
        j += 1
    if showHelp:
        sadm_help.help.show()
        sys.exit(0)
    elif bad:
        sys.exit(1)
    return args

if __name__ == '__main__':
    err = 0
    symbols = locals()
    args = _parse_switches(sys.argv[1:])
    if not args:
        sadm_prompt.interact(symbols)
    else:
        err = sadm_dispatch.dispatch(symbols, args)
    sys.exit(err)
