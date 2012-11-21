#
# $Id: build_ansi.py 9736 2011-06-20 16:49:22Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import os, re, sys

# Track information about how we're using ANSI escape sequences.
class _Ansi:
    def __init__(self):
        self._useColors = True
    def set_use_colors(self, value):
        self._useColors = bool(value)
    def get_use_colors(self):
        return self._useColors

# Create a single instance of ANSI state that applies
# to the whole app.
ansi = _Ansi()

# Define our colors.
def c(x,y):
    return chr(27) + '[' + str(x) + ';' + str(y) + 'm'

NORMTXT = chr(27) + '[0m'
BLACK = c(0,30)
DARK_GRAY = c(1,30)
RED = c(0,31)
BOLD_RED = c(1,31)
GREEN = c(0,32)
BOLD_GREEN = c(1,32)
YELLOW = c(0,33)
BOLD_YELLOW = c(1,33)
BLUE = c(0,34)
BOLD_BLUE = c(1,34)
PURPLE = c(0,35)
BOLD_PURPLE = c(1,35)
CYAN = c(0,36)
BOLD_CYAN = c(1,36)
LIGHT_GRAY = c(0,37)
WHITE = c(1,37)

# Don't need c() anymore; remove it from global symbols
del(c)

COLORS = [BLACK,RED,GREEN,YELLOW,BLUE,PURPLE,CYAN,LIGHT_GRAY,
DARK_GRAY,BOLD_RED,BOLD_GREEN,BOLD_YELLOW,BOLD_BLUE,BOLD_PURPLE,BOLD_CYAN,WHITE]
COLOR_NAMES = str('BLACK,RED,GREEN,YELLOW,BLUE,PURPLE,CYAN,LIGHT_GRAY,'
    + 'DARK_GRAY,BOLD_RED,BOLD_GREEN,BOLD_YELLOW,BOLD_BLUE,BOLD_PURPLE,BOLD_CYAN,WHITE').split(',')

_SEQ = chr(27) + '['
_COLOR_PAT = re.compile('(' + chr(27) + r'\[([01]);3([0-7])m).*')
_LEN_NORMTXT = len(NORMTXT)
_LEN_SEQ = len(_SEQ)

# Read text that has embedded ANSI escape sequences, and write it to the
# specified handle, taking into account our current settings regarding
# use of color. On platforms that support ANSI escape sequences directly,
# this function is only called when colors have been turned off (as a way
# to rip the escape sequences out).
def _writec(handle, txt):
    colorize = ansi.get_use_colors()
    while txt:
        i = txt.find(_SEQ)
        if i == -1:
            handle.write(txt)
            break
        else:
            if i > 0:
                handle.write(txt[0:i])
                txt = txt[i:]
            if txt.startswith(NORMTXT):
                if colorize:
                    _resetc(handle)
                txt = txt[_LEN_NORMTXT:]
            else:
                m = _COLOR_PAT.match(txt)
                if m:
                    if colorize:
                        _changec(handle, m)
                    txt = txt[m.end(3)+1:]
                else:
                    handle.write(_SEQ)
                    txt = txt[_LEN_SEQ:]

# Platform-specific stuff.
if os.name == 'nt':
    from ctypes import windll, Structure, c_short, c_ushort, byref

    SHORT = c_short
    WORD = c_ushort

    class COORD(Structure):
        """struct in wincon.h."""
        _fields_ = [
          ("X", SHORT),
          ("Y", SHORT)]

    class SMALL_RECT(Structure):
        """struct in wincon.h."""
        _fields_ = [
          ("Left", SHORT),
          ("Top", SHORT),
          ("Right", SHORT),
          ("Bottom", SHORT)]

    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
        """struct in wincon.h."""
        _fields_ = [
          ("dwSize", COORD),
          ("dwCursorPosition", COORD),
          ("wAttributes", WORD),
          ("srWindow", SMALL_RECT),
          ("dwMaximumWindowSize", COORD)]

    # winbase.h
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12

    # On Windows, we need to write to a python-style handle, but call the OS
    # with a numeric pseudo-file-handle to modify console tributes. On other
    # platforms, the second handle is unnecessary. However, to keep our code
    # uniform, create a class that encapsulates this complexity.
    class _Handle:
        def __init__(self, file, console):
            self.file = file
            self.console = console
        def write(self, txt):
            self.file.write(txt)

    _STDOUT = _Handle(sys.stdout, windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE))
    _STDERR = _Handle(sys.stderr, windll.kernel32.GetStdHandle(STD_ERROR_HANDLE))

    # Don't need our constants anymore; remove from namespace.
    del(STD_OUTPUT_HANDLE)
    del(STD_ERROR_HANDLE)

    # wincon.h
    _FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

    def _get_text_attr(handle):
        """Returns the character attributes (colors) of the console screen
        buffer."""
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        windll.kernel32.GetConsoleScreenBufferInfo(handle.console, byref(csbi))
        return csbi.wAttributes

    _NORMTXT_ATTRIBUTES = _get_text_attr(_STDOUT)

    def _set_text_attr(handle, color):
        """Sets the character attributes (colors) of the console screen
        buffer. Color is a combination of foreground and background color,
        foreground and background intensity."""
        windll.kernel32.SetConsoleTextAttribute(handle.console, color)

    # Convert from ANSI color constants to Windows color constants.
    def _mapc(color):
        if color == 1:
            return 4
        if color == 6:
            return 3
        if color == 3:
            return 6
        if color == 4:
            return 1
        return color

    # Change the active color for a handle.
    def _changec(handle, m):
        attr = _mapc(int(m.group(3)))
        if m.group(2) == '1':
            attr |= _FOREGROUND_INTENSITY
        _set_text_attr(handle, attr)

    def _resetc(handle):
        _set_text_attr(handle, _NORMTXT_ATTRIBUTES)

    # Write colorized text to a handle. On Windows, this function
    # is just an alias for the cross-platform _writec() function.
    _hwritec = _writec

else:
    _STDOUT = sys.stdout
    _STDERR = sys.stderr

    def _changec(handle, m):
        handle.write(m.group(1))

    def _resetc(handle):
        handle.write(NORMTXT)

    # Write colorized text to a handle.
    def _hwritec(handle, txt):
        # If we're using colors, then don't bother writing through our
        # slow function -- just output the escape sequences directly.
        if ansi.get_use_colors():
            handle.write(txt)
        else:
            # Use the cross-platform function to rip out the escape sequences.
            _writec(handle, txt)

# Wrap text in a begin color and end color, if colors are active.
def cwrap(txt, beginColor, endColor = NORMTXT):
    if ansi.get_use_colors():
        if beginColor:
            txt = beginColor + txt
        if endColor and (beginColor and beginColor != endColor):
            txt = txt + endColor
    return txt

# Write text to stdout that contains embedded ANSI escape sequences.
# If beginColor is set, wrap the text in that color and immediately
# revert to the end color when finished..
def writec(txt, beginColor = None, endColor = NORMTXT):
    txt = cwrap(txt, beginColor, endColor)
    _hwritec(_STDOUT, txt)

# Write text to stderr that contains embedded ANSI escape sequences.
# If beginColor is set, wrap the text in that color and immediately
# revert to the end color when finished..
def ewritec(txt, beginColor = None, endColor = NORMTXT):
    txt = cwrap(txt, beginColor, endColor)
    _hwritec(_STDERR, txt)

# Print line to stdout that contains embedded ANSI escape sequences.
# If beginColor is set, wrap the text in that color and immediately
# revert to the end color when finished..
def printc(txt, beginColor = None, endColor = NORMTXT):
    txt = cwrap(txt, beginColor, endColor)
    writec(txt + '\n')

# Print line to stderr that contains embedded ANSI escape sequences.
# If beginColor is set, wrap the text in that color and immediately
# revert to the end color when finished..
def eprintc(txt, beginColor = None, endColor = NORMTXT):
    txt = cwrap(txt, beginColor, endColor)
    ewritec(txt + '\n')

