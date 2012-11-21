#!/bin/bash
svn up /home/oathizhi/sandboxes/all/trunk/copyscan
python /home/oathizhi/sandboxes/all/trunk/copyscan/code/buildscripts/check_disabled_tests.py --nag -c example@example.com
