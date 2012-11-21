#
# $Id: filename 3521 2010-11-25 00:31:22Z svn_username $
#
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
#
'''
Encapsulate information about individual components.
'''
import re, buildinfo

'''
The name of the source code aspect of a component. This name is used as a
constant in dependency declarations, to specify that a component is re-used as
source. It is reflected in the name of the "code root" folder.
'''
CODE_ASPECT_NAME = 'code'
'''
The name of the build/binary aspect of a component. This name is used as a
constant in dependency declarations, to specify that a component is re-used in
prebuilt form. It is reflected in the name of the "built root" folder.
'''
BUILT_ASPECT_NAME = 'built'
BUILT_ASPECT_SUFFIXES = buildinfo.get_known_platform_variants()
BUILT_ASPECT_VARIANTS = ['.'.join([BUILT_ASPECT_NAME, suffix]) for suffix in BUILT_ASPECT_SUFFIXES]
'''
The name of the test aspect of a component. It is reflected in the "test root"
folder.
'''
TEST_ASPECT_NAME = 'test'
'''
The name of the runnable aspect of the top component. It is reflected in the "run
root" folder. Unlike other aspects, this one only relates to the top component
in the sandbox and does not have a subdir named for the component.
'''
RUNNABLE_ASPECT_NAME = 'run'
'''
The name of the report aspect of the top component. It is reflected in the "report
root" folder. Unlike other aspects, this one only relates to the top component
in the sandbox and does not have a subdir named for the component.
'''
REPORT_ASPECT_NAME = 'report'
'''
A list of all valid aspects of a component. Contains "built", which is never
actually used by itself in folder names.
'''
ASPECTS = [CODE_ASPECT_NAME, BUILT_ASPECT_NAME, TEST_ASPECT_NAME, RUNNABLE_ASPECT_NAME, REPORT_ASPECT_NAME]
'''
A list of all folder names that reflect an aspect of a component. Contains all
the variations of "built".
'''
ASPECT_BRANCH_NAMES = [CODE_ASPECT_NAME, TEST_ASPECT_NAME, RUNNABLE_ASPECT_NAME, REPORT_ASPECT_NAME] + BUILT_ASPECT_VARIANTS
'''
A list of aspects that only contain data associated with the top level component.
These aspects are not manifest in the file system with a subdir per component.
'''
TOP_COMPONENT_ONLY_ASPECTS = [RUNNABLE_ASPECT_NAME, REPORT_ASPECT_NAME]
'''
A list of aspects that are manifest in the file system with a subdir per component.
'''
ASPECTS_WITH_COMPONENT_SUBDIR = [a for a in ASPECTS if a not in TOP_COMPONENT_ONLY_ASPECTS]
'''
Aspects that can be specified in a dependency.
'''
VALID_REUSED_ASPECTS = [CODE_ASPECT_NAME, BUILT_ASPECT_NAME]

_VALID_COMP_NAME_PAT = re.compile('[a-z][-_a-z0-9]*', re.IGNORECASE)
_DOUBLE_COMP_PUNCT_PAT = re.compile('[-_][-_]')
def get_component_name_validation_error(proposed):
    '''
    Return None if the proposed component name satisfies our naming convention,
    or a string describing problem otherwise.

    Currently, our constraints require the component name to start with a
    letter and be followed by any sequence of letters, digits, underscores,
    or hyphens--but must end with alphanum. The dot, @, ~, and other punctuation
    chars are not allowed.
    '''
    if not _VALID_COMP_NAME_PAT.match(proposed):
        return 'Component name must start with alpha and consist of alphas, digits, hyphen, and underscore.'
    if proposed[-1] in '-_':
        return 'Component name must end with alpha or digit.'
    if _DOUBLE_COMP_PUNCT_PAT.search(proposed):
        return 'Component name cannot contained double hyphen/underscore.'
    return None

_VALID_BR_NAME_PAT = re.compile('[a-z][-_a-z0-9]*', re.IGNORECASE)
_DOUBLE_BR_PUNCT_PAT = re.compile('[-_.][-_.]')
def get_branch_name_validation_error(proposed):
    '''
    Return None if the proposed branch name satisfies our naming convention,
    or a string describing problem otherwise.

    Currently, our constraints require the branch name to start with a letter
    and be followed by any sequence of dot, letters, digits, underscores, or
    hyphens--but must end with alphanum. The @, ~, and other punctuation chars
    are not allowed.
    '''
    if not _VALID_BR_NAME_PAT.match(proposed):
        return 'Branch name must start with alpha and consist of alphas, digits, dot, hyphen, and underscore.'
    if proposed[-1] in '-_.':
        return 'Branch name must end with alpha or digit.'
    if _DOUBLE_BR_PUNCT_PAT.search(proposed):
        return 'Branch name cannot contained double dot/hyphen/underscore.'
    return None

def parse_component_info(info):
    info = info.split(',')
    if len(info) == 3:
        old = True
        revision = info[1].strip()
        if revision.lower() in ('none', ''):
            revision = None
        aspect = info[2].strip().lower()
    else:
        old = False
        aspect = info[0].strip().lower()
        if len(info) > 1 and info[1] != '':
            revision = info[1].strip()
        else:
            revision = None
    return aspect, revision, old

def parse_component_line(line, branch):
    '''
    Create a Component object from a line of text. Raise an exception for
    format errors.
    '''
    if line.find(':') != line.rfind(':'):
        name, rest, parent = line.split(':', 2)
    else:
        name, rest = line.split(':')
    aspect, revision, old = parse_component_info(rest)
    return Component(name.strip(), branch, revision, aspect)

class Component:
    def __init__(self, name, branch, revision, aspect, parent=None):
        errors = []
        err = get_component_name_validation_error(name)
        if err:
            errors.append(err)
        err = get_branch_name_validation_error(name)
        if err:
            errors.append(err)
##TODO fix julie
##        if aspect not in VALID_REUSED_ASPECTS:
##            errors.append('Bad aspect.')
        if errors:
            raise Exception(('With %s: %s, %s, %s: ' % (name, branch, revision, aspect)) + ' '.join(errors))
        self.name = name
        self.branch = branch
        if revision in (None, ''):
            self.revision = None
        else:
            self.revision = revision
        self.reused_aspect = aspect
        self.parent = parent
        self.rank = 0
        self.dependencies = []
    def get_repo_folder(self, aspect):
        '''
        Get the name that should be used for a repo containing the specified
        aspect of the component. For example, if component is named "x", then
        the repo name for its test aspect would be "x/test"
        '''
        return self.name + '/' + aspect
    def get_name(self):
        return '%s' % (self.name)
    def get_branch(self):
        return '%s' % (self.branch)
    def get_aspect(self):
        return '%s' % (self.reused_aspect)
    def __str__(self):
        rev = ''
        if self.revision:
            rev = str(self.revision)
        return '%s: %s,%s :Parent %s' % (self.name, self.reused_aspect, rev, self.parent) #+ str([str(x) for x in self.dependencies])
    def __eq__(self, other):
        return (self.name == other.name and self.branch == other.branch and
                self.revision == other.revision and
                self.reused_aspect == other.reused_aspect)
    def __ne__(self, other):
        return not self == other
    def __hash__(self):
        return hash((self.name, self.branch, self.revision, self.reused_aspect))
