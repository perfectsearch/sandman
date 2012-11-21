#
# $Id: build_ansi.py 9736 2011-06-20 16:49:22Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys
import getch

def prompt(msg, choices=None, default='', normfunc=None, readline=None):
    '''
    Ask user a question and read their response.

    @param choices A string that enumerates possible answers.
    @param default A string that will be returned if the user presses Enter. If
           default is None (as opposed to the empty string), the empty string
           will not be considered a valid answer, and the user will be
           re-prompted until they satisfy the function.
    @param normfunc A function that will be used to normalize the answer.
           Takes a string and returns an answer in any data type.
    @param readline A function that will be used to read the user's answer.
           Normally this is sys.stdin.readline, but it can also be
           readline_masked() if prompting for a password.
    '''
    txt = msg
    showDefault = not (default is None) and not (default == '')
    if choices:
        if showDefault:
            txt += ' (%s; =%s)' % (choices, str(default))
        else:
            txt += ' (%s)' % choices
    elif showDefault:
        txt += ' ( =%s)' % str(default)

    txt += ' '

    # We can't bind this value in the function prototype, because then it would
    # be bound once, forever. In that case any attempt to override/redirect
    # stdin would fail...
    if readline is None:
        readline = sys.stdin.readline

    while True:
        sys.stdout.write(txt)
        answer = readline().rstrip()
        if normfunc:
            answer = normfunc(answer)
        if not answer:
            if default is None:
                continue
            answer = default
        return answer

def prompt_bool(msg, default=None):
    '''
    Ask user for a yes/no answer.

    @param default If None, don't default and keep asking until either 'y'
           or 'n' is received. Otherwise, use this value when user presses
           Enter.
    '''
    while True:
        sys.stdout.write(msg)
        if default is None:
            sys.stdout.write(' (y/n) ')
        elif default:
            sys.stdout.write(' (Y/n) ')
        else:
            sys.stdout.write(' (y/N) ')
        answer = sys.stdin.readline().strip().lower()
        if not answer or (not (answer[0] in ['y','n'])):
            if not (default is None):
                return default
        else:
            return answer[0] == 'y'

def readline_masked(mask_char='*'):
    '''
    Read keystrokes from stdin until Enter is pressed, but don't display those
    keystrokes. Useful in password prompts.

    @param mask_char Char to display with each keystroke. If None, nothing is
           displayed and cursor doesn't move.
    '''
    value = ''
    while True:
        c = getch.getch()
        if (c == '\n') or (c == '\r') or (c == '\x1B'):
            print('')
            break
        elif (c == '\x08'):
            if len(value) > 0:
                value = value[:-1]
                sys.stdout.write('\b \b')
        else:
            value += c
            if not (mask_char is None):
                sys.stdout.write(mask_char)
    return value
