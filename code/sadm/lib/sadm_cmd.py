# $Id: sadm_prompt.py 10030 2011-06-24 20:29:25Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

class Command:
    def __init__(self, syntax, descrip, tags='adv cm'):
        self.syntax = syntax
        self.descrip = descrip
        self.tags = tags.split(' ')
        i = syntax.find(' ')
        if i >= 1:
            self.verb = syntax[0:i]
        else:
            self.verb = self.syntax
        self.abbrev = self.verb
    def __str__(self):
        return self.verb
    def operates_on_sandbox(self):
        return self.descrip.find('sandbox') > -1

_CMDS = [
    Command('foreach sandbox do cmd',  'Run cmd in each matching sandboox root.'),
    Command('history sandbox',         'Show when sandbox has started.'),
    Command('init',                    'Prepare sandbox for first use.', 'dev'),
    Command('BuildAbove',              'Build all of the requirements in the local sandboxes and then this component.','dev'),
    Command('BuildAboveSim',           'Simulate Build all of the requirements in the local sandboxes and then this component.','dev'),
    Command('BuildUpTo',               'Build this component, and then everything in the local sandboxes that depends upon this component.','dev'),
    Command('BuildUpToSim',            'Simulate Build this component, and then everything in the local sandboxes that depends upon this component.','dev'),
    Command('configure sandbox',       'Confiugre a sandbox.'),
    Command('last sandbox',            'Show when sandbox last started.'),
    Command('latest component',        'Show vcs rev for latest official build of component.'),
    Command('list',                    'List sandboxes and associated settings.', 'dev'),
    Command('logs sandbox',            'View latest ctest logs for a sandbox.'),
    Command('next',                    'Start the next continuous sandbox.'),
    Command('path sandbox',            'Print full path for a sandbox.'),
    Command('pin sandbox comp N',      'Make sandbox use rev N of component comp.'),
    Command('remove sandbox',          'Permanently remove a sandbox.', 'dev'),
    Command('request',                 'Submit request to official build queue.', 'dev'),
    Command('reset sandbox',           'Make sandbox pristine (nuke code, build root).'),
    Command('showqueue platform',      'Show offical build request queue.'),
    Command('service',                 'Service next item in official build queue.'),
    Command('setup',                   'Setup or verify correct environment.'),
    Command('start sandbox',           'Start eval of a sandbox.', 'dev'),
    Command('StartAndWait sandbox',    'Start eval of a sandbox and wait for it to finish and replicate.','dev'),
    Command('stop sandbox',            'Stop eval of a sandbox.', 'dev'),
    Command('status sandbox',          'Display dashboard for sandbox.', 'dev'),
    Command('tail',                    'Tail last few events.'),
    Command('tools',                   'Check if required tools for sandbox are on machine.', 'dev'),
    Command('update',                  'Apply latest patches to this tool.'),
    Command('verify',                  'Verify a sandbox builds cleanly.', 'dev'),
    Command('version',                 'Display sadm version.', 'dev'),
    Command('where',                   'Tell where sadm is installed.'),
    ]

def _calc_abbrevs():
    global _CMDS
    # Figure out the shortest unique name for each command.
    for cmd in _CMDS:
        # How many chars does this command have in common with any others?
        max_common_char_count = 0
        others = [x for x in _CMDS if x != cmd]
        for other in others:
            common_char_count = 0
            # Which verb is shorter? We only have to compare that many chars...
            end = min(len(cmd.verb), len(other.verb))
            for k in range(end):
                if cmd.verb[k] != other.verb[k]:
                    #print('%s and %s have %d letters in common' % (verb, otherVerb, common_char_count))
                    break
                common_char_count += 1
            if max_common_char_count < common_char_count:
                max_common_char_count = common_char_count
        abbrev = cmd.verb[0:max_common_char_count+1]
        #print("%s = %s" % (verb, abbrev))
        cmd.abbrev = abbrev

_abbrevs_calculated = False

def commands():
    '''
    Return a list of all sadm Command objects.
    '''
    global _CMDS
    if not _abbrevs_calculated:
        _calc_abbrevs()
    return _CMDS

def find_command(partial_name):
    '''
    Given a possibly abbreviated name for a command, return the corresponding
    Command object.
    '''
    partial_name = partial_name.lower()
    for cmd in commands():
        # The easy algorithm is to just find the first (and only) command that
        # has an abbrev that's a subset of partial_name. However, this can give
        # false positives. Suppose user types "startle" (a word that's not a
        # true sadm command) and cmd.abbrev is "sta" (derived from "start")...
        if partial_name.startswith(cmd.abbrev):
            if cmd.verb.startswith(partial_name):
                return cmd
    return None

