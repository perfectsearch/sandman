#!/usr/bin/env python
#
# $Id: sadm_help.py 9300 2011-06-09 23:06:19Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sadm_prompt
from sadm_constants import APP_CMD, APP_TITLE
# From buildscripts...
from textui.colors import *
from textui.ansi import *

class Help:
    def show(self):
        printc('\n' + CMD_COLOR + APP_CMD + NORMTXT + ' -- ' + TITLE_COLOR + APP_TITLE + NORMTXT)
        printc(DELIM_COLOR + '-'*78)
        printc(TITLE_COLOR + APP_CMD + NORMTXT + ' [' + PARAM_COLOR
              + 'switches' + NORMTXT + '] [' + CMD_COLOR + 'action'
              + NORMTXT + ' [' + PARAM_COLOR + 'sandbox' + NORMTXT
              + ' [' + PARAM_COLOR + 'parameters' + NORMTXT + ']]')

        printc('''
This program runs in scripted mode if it receives a logically complete command
line. Otherwise, it prompts to gather parameters.

Switches include:

    '''
        + PARAM_COLOR + '--no-color' + NORMTXT
         + '''               - Disable ANSI colors. Useful when redirecting
                               stdout or stderr to a log file.
    '''
        + PARAM_COLOR + '--auto-abort' + NORMTXT
           + '''             - Abort any time a prompt is needed after an
                               action is invoked. This guarantees scripted
                               mode, and prevents the program from doing
                               dangerous things without confirmation. If
                               actions are launched from the menu, this flag
                               is ignored.
    '''
        + PARAM_COLOR + '--auto-confirm' + NORMTXT
             + '''           - Answer 'y' to any yes/no question after an
                               action is invoked. Like --auto-abort, this
                               guarantees scripted mode. However, it is more
                               dangerous and should not be used casually.

Possible actions and their parameters include:
''')
        menu = '    ' + sadm_prompt.MENU.replace('\n', '\n    ')
        printc(menu)
        printc(
'''Action names may be abbreviated to any length that remains unambiguous.
While sandboxes are usually selected by number in prompts, the command line
identifies them by name or python lambda function. Multiple actions may be
performed with a single command line by turning the action into a comma-
delimited list. (In such cases, all actions share any parameters that
follow.)

Standard globbing wildcards (*, ?) can be used to select multiple sandboxes
on the command line (or in a prompt). However, be aware that the shell may
expand wildcards, so issuing a command like "'''
    + TITLE_COLOR + 'sadm ' + CMD_COLOR + 'xauto' + PARAM_COLOR + ' *' + NORMTXT
                                                    + '''" may have no effect.
For this reason, the key word "''' + PARAM_COLOR + 'all' + NORMTXT
    + '" is available as a synonym for "' + PARAM_COLOR + '*' + NORMTXT + '''". Also,
sandboxes can be identified by the key word "''' + PARAM_COLOR + 'last' + NORMTXT
    + '''", meaning the most recent
sandbox to be started, and by relative path. This means that if your current
working directory is anywhere within sandbox X, and you type a command like
"''' + TITLE_COLOR + 'sadm ' + CMD_COLOR + 'xauto' + PARAM_COLOR + ' .'  + NORMTXT
    + '''", sandbox X will be the target of your command.

Examples:

    ''' + CMD_COLOR + 'sadm xauto' + NORMTXT + ',' + CMD_COLOR + 'reset '
        + PARAM_COLOR + '*daily' + NORMTXT + '''
        Unschedule and then reset all sandboxes with names ending in "daily".

    ''' + CMD_COLOR + 'sadm build' + NORMTXT + ',' + CMD_COLOR + 'test '
        + NORMTXT + '"' + PARAM_COLOR + 'lambda x: not bool(x.schedule)' + NORMTXT + '''"
        Build and test all sandboxes that don't have a schedule.

    ''' + CMD_COLOR + 'sadm remove' + NORMTXT + '''
        Prompt for sandbox(es); remove whichever ones are selected.

    ''' + CMD_COLOR + 'sadm link' + PARAM_COLOR + r' \\vboxsrv\shr\foo\trunk\dev foo*dev2'
        + NORMTXT + '''
        Provides a code root from a virtual box shared folder to the foo*dev2
        sandbox. Creates a symbolic link so more than one sandbox can share
        identical code.

    ''' + CMD_COLOR + 'sadm foreach' + PARAM_COLOR + ' *dev ' + CMD_COLOR + 'do' + PARAM_COLOR + ' ls -l ./code'+ NORMTXT + '''
        Change to root of each dev sandbox; list contents of its code folder.

    ''' + CMD_COLOR + 'sadm' + PARAM_COLOR + ' --auto-confirm ' + CMD_COLOR + 'auto '
        + PARAM_COLOR + 'all ' + NORMTXT + '"' + PARAM_COLOR + 'every 15 m' + NORMTXT + '''"
        Schedule all sandboxes to evaluate every 15 m. Automatically agree to
        any requests for confirmation.

In addition to the main sadm functions, "''' +
        TITLE_COLOR + 'sadm ' + CMD_COLOR + 'path' + NORMTXT + '''" can be used to implement
convenience functions for power shell users. See bash-aliases.txt-sample, in
the sadm folder.

See https://... for more details. ## TODO FIX ME point to proper site
''')

# Create a global instance of Help that anybody can call.
help = Help()

if __name__ == '__main__':
    help.show()
