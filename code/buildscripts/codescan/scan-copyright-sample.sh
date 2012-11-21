#!/bin/bash
/usr/bin/svn up /trunk/copyscan/code
/home/oathizhi/bin/mailout -t example@example.com -f "Copyright Scanner <code.scan@example.com>" -s "copyright scan on example::example-product" "python check_copyright.py"
