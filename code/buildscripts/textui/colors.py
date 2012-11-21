# 
# $Id: build_colors.py 9054 2011-06-06 16:33:53Z ahartvigsen $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 
import ansi

TITLE_COLOR = ansi.GREEN
DELIM_COLOR = ansi.LIGHT_GRAY
LINENUM_COLOR = ansi.DARK_GRAY
CMD_COLOR = ansi.GREEN
PARAM_COLOR = ansi.YELLOW
ERROR_COLOR = ansi.RED
WARNING_COLOR = ansi.BOLD_YELLOW

if __name__ == '__main__':
    def disp(color, lbl, explanation = ''):
        build_ansi.printc(color + lbl.rjust(8) + build_ansi.NORMTXT + ' ' + explanation)
    print('')
    disp(TITLE_COLOR,   'Title')
    disp(DELIM_COLOR,   '-------', 'delimiters'  )
    disp(LINENUM_COLOR, '    123', 'line numbers')
    disp(CMD_COLOR,     'command'                )
    disp(PARAM_COLOR,   'param'                  )
    disp(ERROR_COLOR,   'errors'                 )
    disp(WARNING_COLOR, 'warnings'               )
