import traceback, sys
from textui.colors import *
from textui.ansi import *

def write_error():
    ewritec(ERROR_COLOR)
    traceback.print_exc()
    #exc_type, exc_value, exc_traceback = sys.exc_info()
    #failure = [traceback.extract_tb(exc_traceback)[-1]]
    #lines = traceback.format_list(failure)
    #for line in lines:
    #    writec(line)
    #lines = traceback.format_exception_only(exc_type, exc_value)
    #for line in lines:
    #    ewritec(line)
    ewritec(NORMTXT)
