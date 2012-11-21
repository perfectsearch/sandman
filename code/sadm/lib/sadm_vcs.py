'''
This module manages sandbox-wide operations that interact with the version
control system. It doesn't actually know much about the VCS--it depends on
the vcs module in buildscripts for that--but neither does the vcs module know
anything about sandboxes, dependencies, or the semantics of particular sadm
verbs. This module is the bridge among those domains.
'''
#
# $Id: sadm_svn.py 9484 2011-06-14 19:30:52Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

from sadm_constants import INDENT, APP_FOLDER
import sadm_prompt
# From buildscripts...
from textui.colors import *
from textui.ansi import *
import metadata
import vcs
import component
import aggregate_vcs
import sandbox
import ioutil

def update_program_if_needed(silent=False):
    '''
    See if sadm itself needs to be updated.
    '''
    # Don't do anything if we're running from within a sandbox.
    if sandbox.find_root_from_within(APP_FOLDER):
        return
    # If this folder has any kind of relationship with a repo...
    if vcs.folder_is_tied_to_vcs(APP_FOLDER):
        try:
            status = vcs.get_status(APP_FOLDER, status_filter=lambda lbl: lbl!= 'unknown', revision=-1)
        except:
            eprintc("Status of sadm can't be determined (is the network down?). Skipping update.", WARNING_COLOR)
            return
        if status:
            # See if there are any items at a status that will prevent success of update.
            bad_status = [x for x in status.keys() if x not in 'modified|removed|added|renamed|kind changed']
            if bad_status:
                eprintc('''
The master version of sadm has changed, but automatic update is impossible. Do
a manual bzr up to resolve the following issues:
''', ERROR_COLOR)
                print(aggregate_vcs.format_aspect_status(None, None, "sadm", status))
                return
            err = vcs.update_checkout(APP_FOLDER)
            if err:
                print('Unable to update sadm; exit code %d from "bzr up" command. Try running "bzr up" manually.' % err)
                return
            return True
        elif not silent:
            print("Sadm is up to date.")
    else:
        if not silent:
            print("This copy of %s doesn't run from a directory that's connected to bzr." % APP_CMD)
