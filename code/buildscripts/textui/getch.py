#!/usr/bin/env python
# 
# $Id: sadm_getch.py 9424 2011-06-13 18:42:04Z ahartvigsen $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 

def getch():
    """Gets a single character from stdin. Does not echo to the screen."""
    return _impl()

class _getchUnix:
    def __init__(self):
        import tty, sys, termios # import termios now or else you'll get the Unix version on the Mac

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class _getchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()
        
class _getchMacCarbon:
    """
    A function which returns the current ASCII key that is down;
    if no ASCII key is down, the null string is returned.  The
    page http://www.mactech.com/macintosh-c/chap02-1.html was
    very helpful in figuring out how to do this.
    """
    def __init__(self):
        # Depending on which version of python we have, and which
        # version of OSX, this implementation may or may not be
        # available. The Unix impl appears to work on the mac,
        # in my testing, so we can fall back to that one if need be.
        import Carbon
        Carbon.Evt #see if it has this (in Unix, it doesn't)

    def __call__(self):
        import Carbon
        if Carbon.Evt.EventAvail(0x0008)[0]==0: # 0x0008 is the keyDownMask
            return ''
        else:
            #
            # The event contains the following info:
            # (what,msg,when,where,mod)=Carbon.Evt.GetNextEvent(0x0008)[1]
            #
            # The message (msg) contains the ASCII char which is
            # extracted with the 0x000000FF charCodeMask; this
            # number is converted to an ASCII character with chr() and
            # returned
            #
            (what,msg,when,where,mod)=Carbon.Evt.GetNextEvent(0x0008)[1]
            return chr(msg & 0x000000FF)
try:
    _impl = _getchWindows()
except ImportError:
    _impl = None
    try:
        _impl = _getchMacCarbon()
    except AttributeError:
        pass
    except ImportError:
        pass
    if not _impl:
        _impl = _getchUnix()
        
if __name__ == '__main__': # a little test
    print 'Press a key'
    while True:
        k=getch()
        if k <> '':
            break
    print 'you pressed ',str(ord(k))
