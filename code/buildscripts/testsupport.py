#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Proprietary and confidential.
# Copyright 2011 Perfect Search Corporation.
# All rights reserved.
#
""" This module provide support for tests in our framework.
SBROOT, TESTROOT and BUILTROOT allow
tests to correctly find support files etc.

The built/buildscripts directory is added to the python path.

Standard test tags are defined as decorators for use by the build system.
"""

'''
new test tags should have the attribute all added to them so that they can be run when
the command "sb test -A all" is used
'''

import os
import sys
        
def skipUnlessLocationAt(*locations):
    '''this decorator skips a test if it is not run from a machine 
    with a setup file that has a location configured to a location in locations
    this is useful for connector tests that require a machine on the internal network'''
    import global_vars
    #if isinstance(locations, (str, unicode)):
        #if global_vars.location == locations
            #return lambda func: func
    if global_vars.location in locations:
        return lambda func: func
    return unittest.skip('location not one of the following %s or you have not configured ' \
                         + 'your location with sb test --setup' % locations)

def checkin(test):
    ''' super short tests that must pass before check-in occurs '''
    setattr(test, 'checkin', True)
    setattr(test, 'all', True)
    return test
    
def officialbuild(test):
    ''' short tests that must pass before a publish occurs '''
    setattr(test, 'officialbuild', True)
    setattr(test, 'all', True)
    return test
    
def refinement(test, ticketNumber=None):
    ''' longer tests that run regularly (nightly) 
    the system test team will work on a way of reporting and dealing with failed refinement tests
    if a test is known to fail a ticket number can be associated with it'''
    setattr(test, 'refinement', True)
    setattr(test, 'ticketNumber', ticketNumber)
    setattr(test, 'all', True)
    return test

def advanced(test):
    '''This test tag is for stress tests and other long tests. these tests must be started manually.
    when these tests are run and what is expected of these tests is determined during a team's 
    planning and during interlock '''
    setattr(test, 'advanced', True)
    setattr(test, 'all', True)
    return test

def release(test):
    ''' tests that verify that the release was sucessfull
    for example testing that the mirrors were correctly updated'''
    setattr(test, 'release', True)
    setattr(test, 'all', True)
    return testing
    
def performance(test):
    '''This test tag is for performance tests
    shorter performance tests that record their results in a file or database
    should be tagged as reusable in addition to being tagged as performance'''
    setattr(test, 'performance', True)
    setattr(test, 'all', True)
    return test

def interactive(test):
    '''This test tag is for tests that need user interaction to run'''
    setattr(test, 'interactive', True)
    setattr(test, 'all', True)
    return test

def modesensitive(test):
    '''This test tag is for tests that are sensitive to mode'''
    setattr(test, 'modesensitive', True)
    setattr(test, 'all', True)
    return test


def shareable(test):
    raise DeprecationWarning('use checkin tag instead of shareable tag')

def reusable(test):
    raise DeprecationWarning('use officialbuild tag instead of reusable tag')

def releaseable(test):
    raise DeprecationWarning('use refinement tag instead of releaseable tag')





_my_dir = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
SBROOT = os.path.abspath(os.path.join(_my_dir, '../..')).replace('\\', '/')
TESTROOT = SBROOT + '/test'
RUNROOT = SBROOT + '/run'
CODEROOT = SBROOT + '/code'
