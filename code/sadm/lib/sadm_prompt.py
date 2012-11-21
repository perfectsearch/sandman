# $Id: sadm_prompt.py 10030 2011-06-24 20:29:25Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
#import re, sys, traceback, shlex
import sadm_sandbox
import sadm_cmd
from sadm_constants import *
from sadm_util import *
from sadm_error import *
from sadm_dispatch import *
from sadm_config import *
from sadm_vcs import update_program_if_needed
from sadm_sandbox import get_by_name_pattern
# From buildscripts...
from textui.ansi import *
from textui.colors import *
from textui.getch import *
import sandbox

_PROMPT_OFFSET = 54

INTERACTIVE_MODE = 0
AUTOABORT_MODE = 1
AUTOCONFIRM_MODE = 2

MENU = ''
for cmd in [c for c in sadm_cmd.commands() if 'dev' in c.tags]:
    syntax = cmd.syntax.ljust(25)
    width = len(syntax)
    params = syntax[len(cmd.verb):]
    params = params.replace(' do ', ' ' + CMD_COLOR + 'do' + PARAM_COLOR + ' ')
    syntax = CMD_COLOR + cmd.abbrev + NORMTXT + cmd.verb[len(cmd.abbrev):] + PARAM_COLOR + params
    MENU += syntax + DELIM_COLOR + '- ' + NORMTXT + cmd.descrip + '\n'

class Prompt:
    def __init__(self):
        self._mode = None
        self.has_shown_menu = False
    def get_mode(self):
        return self._mode
    def set_mode(self, value):
        self._mode = value
    def can_interact(self):
        return (self._mode is None) or (self._mode == INTERACTIVE_MODE)

# Create a global instance to be used by the program.
prompter = Prompt()

# Write a question to stdout. Wait for the user to answer it.
# If defaultValue is set, show the value that will be used
# if the user just presses Enter.
def prompt(q, defaultValue = None, color=PARAM_COLOR, mask=None):
    mode = prompter.get_mode()
    if mode is None:
        prompter.set_mode(INTERACTIVE_MODE)
    elif mode == AUTOCONFIRM_MODE:
        return defaultValue
    elif mode == AUTOABORT_MODE:
        print('mode = %s' % str(mode))
        raise Exception('Interactive prompting disallowed; aborting.')
    while q.startswith('\n'):
        print('')
        q = q[1:]
    txt = q
    width = len(txt)
    if not (defaultValue is None):
        defaultValue = str(defaultValue)
        txt = txt + " [" + color + str(defaultValue) + NORMTXT + "]"
        width += 3 + len(defaultValue)
    if width > _PROMPT_OFFSET:
        i = txt[0:_PROMPT_OFFSET].rindex(' ')
        print(txt[0:i])
        txt = INDENT + txt[i + 1:].lstrip()
        width = width - (i + 1) + len(INDENT)
    if width < _PROMPT_OFFSET:
        txt = txt + ' '*(_PROMPT_OFFSET-width)
    writec(txt + ": " + color)
    try:
        if CYGWIN:
            sys.stdout.flush()
        if mask:
            answer = readMasked()
        else:
            answer = sys.stdin.readline().strip()
        if not answer:
            answer = defaultValue
        return answer
    finally:
        writec(NORMTXT)

def readMasked():
    value = ''
    while True:
        c = getch()
        if (c == '\n') or (c == '\r') or (c == '\x1B'):
            print('')
            break
        elif (c == '\x08'):
            if len(value) > 0:
                value = value[:-1]
                sys.stdout.write('\b \b')
        else:
            value += c
            sys.stdout.write('*')
    return value

def _is_yes(answer):
    return bool(answer) and 'ty1'.find(answer.lower()[0]) != -1

def prompt_bool(q, defaultValue):
    mode = prompter.get_mode()
    if mode == AUTOABORT_MODE:
        return False
    if mode == AUTOCONFIRM_MODE:
        return True
    answer = _is_yes(prompt(q, defaultValue))
    return answer

_MENU_HDR = '\n' + cwrap(APP_TITLE, TITLE_COLOR) + '\n' + cwrap('-'*78, DELIM_COLOR) + '\n'
_QUIT_PATTERN = re.compile('q|quit|exit', re.IGNORECASE)
def _use_menu(symbols):
    while True:
        printc(_MENU_HDR)
        printc(MENU)
        try:
            cmdline = prompt('Command ?', color=CMD_COLOR)
        except KeyboardInterrupt:
            printc('\n')
            break
        printc('')
        try:
            if not cmdline or _QUIT_PATTERN.match(cmdline):
                break
            args = shlex.split(cmdline)
            err = dispatch(symbols, args)
        except KeyboardInterrupt:
            printc('')
        except Exception:
            write_error()
    sys.exit(0)

# Display an interactive menu.
def interact(symbols):
    if not prompter.can_interact():
        return
    prompter.set_mode(INTERACTIVE_MODE)
    try:
        update_program_if_needed(silent=True)
    except SystemExit:
        sys.exit(0)
    except:
        write_error()
    prompter.has_shown_menu = True
    _use_menu(symbols)

def _validate_sandbox_choice(sb, selector, verb):
    if not (selector is None):
        if not selector(sb):
            if verb:
                print('%s is not eligible for %s right now.' % (sb.get_name(), verb))
            sb = None
    return sb

# Prompt the user to choose a sandbox, and validate their choice. Return tuple
# where first value is name of sandbox, and second is pid for that ctest+sandbox
# combo, if applicable.
def _prompt_for_sandbox(verb, sandboxes=None, selector=None, allow_multi_matches=False, msg=None, display_only_matches=False):
    if not prompter.can_interact():
        return
    prompter.set_mode(INTERACTIVE_MODE)
    if sandboxes is None:
        sandboxes = sandbox.list(config.sandbox_container_folder)
    if not sandboxes:
        print('No sandboxes defined.')
        return
    # If we're trying to allow selection of just a subset -- either ones
    # that have active ctest instances, or ones that don't -- then check
    # whether that is even valid.
    subset = not (selector is None)
    if subset:
        if count(sandboxes, selector) == 0:
            print('No sandboxes support %s right now.' % verb)
            return
    list_sandboxes(sandboxes, selector, choose=True, display_only_matches=display_only_matches)
    print('')
    if not msg:
        msg = 'Sandbox?'
        if allow_multi_matches:
            msg += ' (wildcards match name; * or "all"=all)'
    which = prompt(msg)
    if not which:
        return
    if which=='all':
        which='*'
    selected = []
    if which[0].isdigit():
        which = int(which)
        if which < 1 or which > len(sandboxes):
            invalid = True
        else:
            selected.append(sandboxes[which - 1])
    else:
        selected = get_by_name_pattern(sandboxes, which, allow_multi_matches)
    if not selected:
        print('No match for sandbox "%s".' % str(which))
    selected = [sb for sb in selected if _validate_sandbox_choice(sb, selector, verb)]
    if allow_multi_matches:
        return selected
    return selected[0]

_FUNC_TYPE = type(lambda x:x)
def choose_sandbox(verb, name=None, selector=None, enforce=True, allow_multi_matches=False, msg=None, display_only_matches=False):
    '''
    Figure out which sandbox(es) user wants to operate on.
    '''
    sb = None
    if name=='all':
        name='*'
    elif name == 'last':
        mostRecentlyStarted = sadm_sandbox.list_recent_starts(1)
        if not mostRecentlyStarted:
            return []
        name = mostRecentlyStarted[0][0]
    # Depending on how we're called, we might get either a name as the first
    # arg and a selector as the second, a name with no selector, or a selector
    # as the first arg and no name. In the latter case, swap args so we
    # interpret correctly.
    if (not (name is None)) and (type(name) == _FUNC_TYPE) and (selector is None):
        selector = name
        name = '*'
    sandboxes = sandbox.list(config.sandbox_container_folder)
    if not name:
        sb = _prompt_for_sandbox(verb, sandboxes, selector, allow_multi_matches, msg, display_only_matches)
    else:
        sb = sadm_sandbox.get_by_name_pattern(sandboxes, name, allow_multi_matches)
        if sb and enforce and (not (selector is None)):
            sb = [s for s in sb if _validate_sandbox_choice(s, selector, verb)]
        if sb and not allow_multi_matches:
            sb = sb[0]
    return sb

# Display a list of all our sandboxes.
def list_sandboxes(sandboxes=None, selector=None, choose=False, display_only_matches=False):
    # If we're not in interactive mode, there's no point in numbering
    # the sandboxes so they can be selected.
    if not prompter.can_interact():
        choose = False
    if choose:
        sep = DELIM_COLOR + ' - ' + NORMTXT
    else:
        sep = ''
    if not choose:
        runningMask = inertMask = ''
    if not sandboxes:
        sandboxes = sandbox.list(config.sandbox_container_folder)
    elif type(sandboxes) != type([]):
        sandboxes = choose_sandbox(None, sandboxes, allow_multi_matches=True)
    if not sandboxes:
        print('No sandboxes defined.')
    else:
        n = 1
        for sb in sandboxes:
            id = ''
            if choose:
                id = str(n)
                if selector and not selector(sb):
                    if display_only_matches:
                        n += 1
                        continue
                    id = ' '.rjust(len(id))
            row = ''
            if id:
                if n < 10:
                    row += ' '
                row += PARAM_COLOR + id
            if sep:
                row += sep
            row += PARAM_COLOR + sb.get_name().ljust(35)
            row += DELIM_COLOR +' - ' + NORMTXT
            if hasattr(sb, 'schedule') and (not (sb.schedule is None)):
                row += str(sb.schedule)
            else:
                if sb.get_sandboxtype().get_should_schedule() and not config.schedule_continuous_manually:
                    row += 'auto-scheduled'
                else:
                    row += 'unscheduled'
            if sb.get_sandboxtype().get_should_publish():
                row += '; publishing enabled'
            if sb.is_locked():
                row += ' (pid=%s)' % str(sb.get_lock_obj().pid)
            printc(row)
            n += 1

