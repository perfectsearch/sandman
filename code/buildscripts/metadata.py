#
# $Id: filename 3521 2010-11-25 00:31:22Z svn_username $
#
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
#
import ConfigParser
import os
import sys
import string
import optparse
import traceback
import collections
import copy
from operator import attrgetter
try:
    import bzrlib
except:
    import platform
    if platform.uname()[0] == 'Darwin':
        sys.path.append('/Library/Python/2.6/site-packages')
        import bzrlib
import tempfile
import subprocess
import StringIO
import re

import component
import check_tools
import vcs
import codescan
import sandbox
import l10n.pslocale
from ioutil import *
from pprint import pprint

SAMPLE = '''
[misc]
targeted platforms=windows,linux
supported platforms=osx
current milestone=ui freeze

[build tools]
python: 2.6,windows|linux,python -V,Download from activestate.com
ant: 1.7,windows|linux,ant -version,download from apache web site or use one from eclipse IDE

[test tools]
nose-test: 1.0,windows,nose --v,use easy_install

[run tools]
nginx: 0.95,windows,nginx --version,download from nginx.org
nginx: 1.3,linux,nginx --version,yum install nginx

[component dependencies]
buildscripts: code
foo: built,tagX

[scanned paths]
exclude=data/.*|samples/.*

[ui]
ui: admin ui, search, ui

[admin ui]
path=console/htdocs
targeted locales=en,fr,de
supported locales=jp

[search ui]
path=search/htdocs
targeted locales=en,fr,de,it,es,pt,jp,zh
'''
_FROMCODE_PAT = re.compile('from_code_rev_(.*)', re.IGNORECASE)
_TAG_PAT = re.compile(r'[\w-]+\.[\w]+\.[\d]+\.[\d]+ use: reusable')
_TOOLS_SECTION_TEMPLATE = '%s tools'

METADATA_FILE = "metadata.txt"
DEPENDENCIES_SECTION = 'component dependencies'
BUILD_TOOLS_SECTION = _TOOLS_SECTION_TEMPLATE % 'build'
TEST_TOOLS_SECTION = _TOOLS_SECTION_TEMPLATE % 'test'
RUN_TOOLS_SECTION = _TOOLS_SECTION_TEMPLATE % 'run'
TOOLS_SECTIONS = [BUILD_TOOLS_SECTION, TEST_TOOLS_SECTION, RUN_TOOLS_SECTION]
MISC_SECTION = 'misc'
SCANNED_FOLDER_SECTION = 'scanned folders'
SCANNED_FILE_SECTION = 'scanned files'
TARGETED_PLATFORMS_OPTION = 'targeted platforms'
SUPPORTED_PLATFORMS_OPTION = 'supported platforms'
MILESTONE_OPTION = 'current milestone'
UI_FREEZE_MILESTONE = 'ui freeze'
LOCALIZATION_COMPLETE_MILESTONE = 'localization complete'
SCAN_SECTION = 'scanned paths'
INCLUDE_OPTION_PREFIX ='include'
EXCLUDE_OPTION_PREFIX ='exclude'
UI_SECTION_PREFIX = 'ui'
UI_PATH_OPTION = 'ui path'
TARGETED_LOCALES_OPTION = 'targeted locales'
SUPPORTED_LOCALES_OPTION = 'supported locales'
DO_NOT_INTEGRATE_OPTION = 'do not integrate'

INTERESTING_EXT_PAT = re.compile(r'.*\.(cpp|java|h|py|js)$')
NON_RECURSING_FOLDERS_PAT = re.compile(r'(\.bzr|data|ext(js)?|boost|sample-data|\.metadata|built.*|run|report|Archive|Dist|Install|bin|lib|Debug|Release|prebuilt|buildtools)$')

def get_revno_from_tag(working_repo, comp):
    cwd = os.getcwd()
    os.chdir(os.path.join(working_repo.local_reporoot, comp.branch, comp.name, comp.reused_aspect))
    p = subprocess.Popen(['bzr', 'tags'], stdout=subprocess.PIPE)
    taglines = p.stdout.readlines()
    tagtuples = [tag.rsplit(None, 1) for tag in taglines if tag]
    os.chdir(cwd)
    for tag in tagtuples:
        if comp.revision == tag[0]:
            return tag[1]
    else:
        raise Exception('%s is not a valid tag in %s' % (comp.revision, os.path.join(working_repo.local_reporoot, comp.name, comp.reused_aspect, comp.branch)))

def get_section_info_from_fp(section, fp):
    conf = ConfigParser.ConfigParser()
    try:
        conf.readfp(fp)
        if section in conf.sections():
            result = {}
            for option in conf.options(section):
                result[option] = conf.get(section, option)
            return result
    except ConfigParser.MissingSectionHeaderError:
        pass
    return {}

def get_section_info_from_disk(section, folder):
    try:
        with open(os.path.join(folder, METADATA_FILE)) as fp:
            return get_section_info_from_fp(section, fp)
    except IOError:
        print("%s does not exist in %s." % (METADATA_FILE, folder))
        return {}

def get_section_info_from_vcs(section, comp, working_repo, platform, use_master=False):
    revision = comp.revision
    if revision:
        m = _FROMCODE_PAT.match(revision)
        if m:
            revision = m.group(1)
    try:
        #print 'Checking dependencies for:', comp.name, comp.reused_aspect, comp.branch, METADATA_FILE, revision
        aspect = comp.reused_aspect
        if aspect == component.BUILT_ASPECT_NAME:
            built_aspects = [b for b in working_repo.branches
                             if b[1] == comp.name
                             and b[2].startswith(component.BUILT_ASPECT_NAME)
                             and b[0] == comp.branch]
            if not built_aspects:
                # This is only valid because the function is trying to fetch
                # dependencies, AND NOTHING ELSE. We can't generally substitute
                # code aspects for built ones.
                aspect = component.CODE_ASPECT_NAME
            else:
                # Prefer the built aspect that matches the current targeted platform.
                if platform:
                    tmp = [a for a in built_aspects if platform in a[2]]
                    if tmp:
                        built_aspects = tmp
                aspect = built_aspects[0][2]
        if use_master:
            txt = vcs.get_file_contents(working_repo.master_reporoot, comp.name, aspect, comp.branch, METADATA_FILE)
        else:
            txt = working_repo.get_file_contents(comp.name, aspect, comp.branch, METADATA_FILE, revision)
        fp = StringIO.StringIO()
        fp.write(txt)
        fp.seek(0)
        result = get_section_info_from_fp(section, fp)
        fp.close()
        return result
    except:
        print('Unable to get info about component %s from version control.' % comp)
        traceback.print_exc()
        return {}

def _get_deps(working_repo, platform, top_component, code_root, read_deps, already_analyzed, use_master=False, check_vcs=True):
    if top_component.name == 'buildscripts':
        top_component.reused_aspect = component.CODE_ASPECT_NAME

##TODO julie why would we do this?
##    if top_component.reused_aspect == component.BUILT_ASPECT_NAME:
##        interesting_branches = [b for b in working_repo.branches if b[1] == top_component.name and b[2].startswith(component.BUILT_ASPECT_NAME) and b[0] == top_component.branch]
##        if not interesting_branches:
##            top_component.reused_aspect = component.CODE_ASPECT_NAME
    folder = ''
    if (not top_component.revision) and code_root:
        fldr = os.path.join(code_root, top_component.name)
        if os.path.isdir(fldr):
            if check_vcs and vcs.folder_is_tied_to_vcs(fldr):
                output = vcs.get_status(fldr, status_filter=lambda lbl: lbl == 'modified' or lbl == 'added')
                if output:
                    if 'modified' in output:
                        if METADATA_FILE in output['modified']:
                            folder = fldr
                    if 'added' in output:
                        if METADATA_FILE in output['added']:
                            folder = fldr
            else:
                folder = fldr
    if folder:
        if folder in already_analyzed:
            return top_component #sections = already_analyzed[folder]
        else:
            print('\nLoading %s from %s.' % (METADATA_FILE, folder))
            x = get_section_info_from_disk(MISC_SECTION, folder)
            if 'terminal dependency' in x and top_component.reused_aspect.startswith(component.BUILT_ASPECT_NAME):
                return top_component
            sections = get_section_info_from_disk(DEPENDENCIES_SECTION, folder)
            already_analyzed[folder] = sections
    elif check_vcs:
        key = '%s:%s' % (top_component.name, top_component.reused_aspect) #str(top_component)
        if key in already_analyzed:
            return top_component #sections = already_analyzed[key]
        else:
            x = get_section_info_from_vcs(MISC_SECTION, top_component, working_repo, platform, use_master)
            if 'terminal dependency' in x and top_component.reused_aspect.startswith(component.BUILT_ASPECT_NAME):
                return top_component
            sections = get_section_info_from_vcs(DEPENDENCIES_SECTION, top_component, working_repo, platform, use_master)
            already_analyzed[key] = sections
    else:
        return top_component

    compOldDeps = False
    for componentname, info in sections.iteritems():
        componentname = componentname.strip()
        aspect, revision, old = component.parse_component_info(info)
        if aspect == component.BUILT_ASPECT_NAME:
            aspect += "." + platform
        if old:
            compOldDeps = True
        componentname, ignored, branch, task = working_repo.normalize(componentname, aspect, top_component.branch)
        if revision:
            m = _TAG_PAT.match(revision)
            if not m:
                raise Exception('%s is not a valid tag for pinning dependencies.' % revision)
        assert(aspect)
        top_component.dependencies.append(component.Component(componentname, branch, revision, aspect, parent=top_component))
    if compOldDeps:
        print('''Component %s/%s/%s has the old format for dependencies.
Please update dependencies in metadata.txt to match format found at:
https:// ... /working-with-code/concepts/dependencies''' % (top_component.name,top_component.reused_aspect,top_component.branch)) # TODO KIM refer to doc site
    top_component.rank += len(top_component.dependencies)
    for dep in top_component.dependencies:
        if top_component.reused_aspect.startswith(component.BUILT_ASPECT_NAME):
            dep.reused_aspect = top_component.reused_aspect
        # We are suspicious that this optimization isn't working
        if str(dep) not in read_deps or read_deps[str(dep)] != dep:
            read_deps[str(dep)] = dep
            dep = _get_deps(working_repo, platform, dep, code_root, read_deps, already_analyzed, use_master, check_vcs)
        top_component.rank += dep.rank
    return top_component

def has_component(dep_tree, comp_name):
    if dep_tree.name == comp_name:
        return True
    for d in dep_tree.dependencies:
        if d.name == comp_name:
            return True
    for d in dep_tree.dependencies:
        if has_component(d, comp_name):
            return True

def get_components_inv_dep_order(working_repo, platform, top, code_root=None, branch='trunk', revision=None, aspect=component.CODE_ASPECT_NAME, debug=False, use_master=False, check_vcs=True):
    '''
    Return a list of components in inverse dependency order, using the specified
    component as the starting point of the dependency graph. Inverse dependency
    order means that the components with no dependencies (the leaves) are listed
    first, and the most dependent component is last. This is valid build order.

    @param top The name of the topmost component.
    @param code_root Optional. The fully qualified path to the code root of an
    existing sandbox. If specified, then the metadata.txt files for components
    in the coderoot are used to override/pre-empt the checked-in versions.
    @param branch The branch of the components. All components in the dependency
    tree must share this branch.
    @param revision The revision of the topmost component; None = latest.
    @param aspect The aspect of the topmost component.
    '''
    already_analyzed = {}
    comp = component.Component(top, branch, revision, aspect)
    dep_tree = _get_deps(working_repo, platform, comp, code_root, {str(comp): comp}, already_analyzed, use_master, check_vcs)
    # At this point dep_tree is a single Component object that has embedded child
    # nodes in its .dependencies member. If our topmost component is terminal,
    # we won't have buildscripts in the code folder unless we artificially
    # inject the dependency here...
    if not has_component(dep_tree, 'buildscripts'):
        c = component.Component('buildscripts', dep_tree.branch, None, component.CODE_ASPECT_NAME, parent=dep_tree)
        dep_tree.dependencies.append(c)

    if debug:
        tree = dep_tree
    _detect_conflicts(working_repo, dep_tree, branch, top, [], debug)
    components = _trim_tree(dep_tree)
    deps = sorted(components, key=attrgetter('rank', 'name'))
    if debug:
        print('\nDependencies:')
        for comp in deps:
            print comp
        print('-----------------------------------')
        print('\nFull dependence tree')
        print_tree(tree)
        print('-----------------------------------')
        unnecessary_dependencies(tree)
    return deps

def _trim_tree(tree):
    components = set([tree])
    queue = []
    for d in tree.dependencies:
        queue.append(d)
    i = 0
    while i < len(queue):
        dep = queue[i]
        components.add(dep)
        for d in dep.dependencies:
            queue.append(d)
        i += 1
    return [c for c in components]

def _detect_conflicts(working_repo, tree, branch, top, components=[], debug=False):
    components = {tree.name:[tree]}
    queue = []
    for d in tree.dependencies:
        queue.append(d)
    i = 0
    while i < len(queue):
        dep = queue[i]
        if dep.name in components:
            components[dep.name].append(dep)
        else:
            components[dep.name] = [dep]
        for d in dep.dependencies:
            queue.append(d)
        i += 1
    for comp, conflicts in components.iteritems():
        uses_code = []
        used_built = []
        other_revisions = []
        diff_revision = False
        if len(conflicts) > 1:
            highest_revision = -1
            code = False
            for conflict in conflicts:
                if conflict.reused_aspect == component.CODE_ASPECT_NAME:
                    code = True
                    uses_code.append(conflict)
                else:
                    used_built.append(conflict)
                if highest_revision is not None:
                    if type(highest_revision) != type(conflict):
                        highest_revision = conflict
                    elif conflict.revision is None:
                        if highest_revision.revision is not None:
                            diff_revision = True
                        highest_revision = conflict
                    elif get_revno_from_tag(working_repo, conflict) > get_revno_from_tag(working_repo, highest_revision):
                        diff_revision = True
                        highest_revision = conflict
                    elif get_revno_from_tag(working_repo, conflict) != get_revno_from_tag(working_repo, highest_revision):
                        diff_revision = True
            for conflict in conflicts:
                if code:
                    conflict.reused_aspect = component.CODE_ASPECT_NAME
                if conflict.revision != highest_revision.revision:
                    other_revisions.append(conflict)
                conflict.revision = highest_revision.revision
        if debug:
            if (uses_code and used_built) or diff_revision:
                print('%s had conflicts that were resolved.' % comp)
            if uses_code and used_built:
                print('\nThese components used the built aspect')
                for ub in used_built:
                    print ub
                print('\nThere were changed to code because these components use the code aspect')
                for uc in uses_code:
                    print uc
            if diff_revision:
                if highest_revision.revision is None:
                    print('\n%s is unpinned.' % highest_revision)
                else:
                    print('%s is the highest revision at %s %s' % (highest_revision, highest_revision.revision, get_revno_from_tag(working_repo, highest_revision)))
                print('Other revision considered.')
                for other in other_revisions:
                    print highest_revision.revision, get_revno_from_tag(working_repo, highest_revision)
            if (uses_code and used_built) or diff_revision:
                print('-----------------------------------\n')
    '''conflicts = []
    for c in components:
        if c.name == tree.name and c != tree:
            conflicts.append(c)
    if conflicts:
        # Resolve conflicts. Use highest revision number and source code over pre-built.
        revision = tree
        code = tree.reused_aspect == 'code'
        for c in conflicts:
            if c.reused_aspect == 'code':
                code = True
            if (revision.revision is not None) and get_revno_from_tag(working_repo, c) > get_revno_from_tag(working_repo, revision):
                revision = c
        if code:
            aspect = 'code'
        else:
            aspect = tree.reused_aspect
        resolved = component.Component(conflicts[0].name, tree.branch, revision.revision, aspect)
        if resolved == tree:
            resolved = tree
        else:
            for c in conflicts:
                if c == resolved:
                    resolved = c
            tree.revision = resolved.revision
            tree.reused_aspect = resolved.reused_aspect
            tree.rank = resolved.rank
            tree.dependencies = resolved.dependencies
        for c in conflicts:
            if not c == resolved:
                c.revision = resolved.revision
                c.reused_aspect = resolved.reused_aspect
                c.rank = resolved.rank
                c.dependencies = resolved.dependencies
    components.append(tree)
    for d in tree.dependencies[:]:
        _detect_conflicts(working_repo, d, branch, top, components)'''

def unnecessary_dependencies(tree):
    components = {(tree.name, tree.reused_aspect, tree.revision):[str(tree.parent)]}
    queue = []
    for d in tree.dependencies:
        queue.append(d)
    i = 0
    while i < len(queue):
        dep = queue[i]
        if (dep.name, dep.reused_aspect, dep.revision) in components:
            components[(dep.name, dep.reused_aspect, dep.revision)].append(str(dep.parent))
        else:
            components[(dep.name, dep.reused_aspect, dep.revision)] = [str(dep.parent)]
        for d in dep.dependencies:
            queue.append(d)
        i += 1
    unnecessary = {}
    for comp, parents in components.iteritems():
        if len(parents) > 1:
            for parent in parents:
                for p in parents[parents.index(parent)+1:]:
                    if parent in p:
                        if comp in unnecessary:
                            unnecessary[comp].add(parent)
                        else:
                            unnecessary[comp] = set([parent])
    if unnecessary:
        print('\nThese dependencies may be redundant.')
    for comp, parent in unnecessary.iteritems():
        for p in parent:
            if comp[2] is None:
                revision = ''
            else:
                revision = comp[2]
            print('%s: %s, %s : %s' % (comp[0], comp[1], revision, p))

def _normLocales(locales):
    if not locales:
        return None
    locales = [l10n.pslocale.bestFit(x) for x in _splitList(locales)]
    locales = _uniquify(locales)
    locales.sort()
    return locales

def visit(path, visitor, recurser=None, report=True, excludePrograms=False, debug=False):
    visitedFolders = 1
    visitedFiles = 0
    for folder, dirs, files in os.walk(path):
        if debug:
            print('For folder %s, original dirs=%s' % (folder, str(dirs)))
        folder = norm_folder(folder)
        if '.bzr' in dirs:
            dirs.remove('.bzr')
        # On top-level folder, if we're excluding programs (e.g., utilities),
        # eliminate any folders that have components that build exe's.
        if excludePrograms:
            i = len(dirs) - 1
            while i >= 0:
                thisDir = dirs[i]
                if (thisDir.lower() != 'test') and isProgramDir(folder + thisDir):
                    dirs.remove(thisDir)
                i -= 1
            excludePrograms = False
        if not recurser is None:
            dirs = recurser.select(folder, dirs)
        if debug:
            print('For folder %s, recurse candidates=%s' % (folder, str(dirs)))
        # Does this folder have anything that overrides?
        if METADATA_FILE in files:
            files.remove(METADATA_FILE)
            conf = Conf(folder, report=report, debug=debug)
        else:
            truncated = folder
            if path[-1] == '/':
                startFolder = path[0:path.rfind('/')]
            else:
                startFolder = path
            while truncated != startFolder:
                truncated = truncated[0:truncated.rfind('/')]
                if METADATA_FILE in os.listdir(truncated):
                    conf = Conf(truncated, report=report, debug=debug)
                    break
            else:
                conf = None
        relativePath = folder[len(path):]
        i = len(dirs) - 1
        while i >= 0:
            thisDir = dirs[i]
            if debug:
                print('evaluating recursion for %s' % thisDir)
            if conf:
                if not conf.shouldRecurse(thisDir):
                    if debug:
                        print('Not recursing into %s%s' % (folder, thisDir))
                    dirs.remove(thisDir)
                else:
                    if debug:
                        print('recursing into %s%s' % (folder, thisDir))
            else:
                m = NON_RECURSING_FOLDERS_PAT.match(thisDir)
                if m:
                    if debug:
                        print('Not recursing into %s%s' % (folder, thisDir))
                    dirs.remove(thisDir)
            i -= 1
        visitedFolders += len(dirs)
        for f in files:
            if conf:
                if conf.shouldCheck(f):
                    visitor.visit(folder, f, relativePath)
                    visitedFiles += 1
                else:
                    if debug:
                        print('not checking %s' % f)
            else:
                if shouldCheck(f, debug=debug):
                    visitor.visit(folder, f, relativePath)
                    visitedFiles += 1
                else:
                    if debug:
                        print('not checking %s' % f)
    return visitedFiles, visitedFolders

def get_friendly_name_for_path(path):
    #print('getting friendly name for %s' % path)
    path = norm_folder(path)
    i = path.find('/sandboxes/')
    if i > -1:
        path = path[i+11:]
    while path.endswith('/'):
        path = path[0:-1]
    return path

class Conf:
    def _findInConf(self, txt, pat):
        m = pat.search(txt)
        if m:
            name = '_' + _keyToAttr(m.group(1))
            setattr(self, name, m.group(2))
            if self.report:
                val = getattr(self, name)
                if type(val) == _REGEX_TYPE:
                    val = val.pattern
                #print('For %s, %s=%s' % (self.getRelativePath(), name, val))
    def getRelativePath(self):
        x = self.path
        i = x.find('/code/')
        if i > -1:
            x = x[i + 6:]
        return x
    def __init__(self, path, report=True, debug=False):
        self.path = norm_folder(path)
        self.report = report
        self.debug = debug
    def getTargetedPlatforms(self):
        pass
    def getSupportedPlatforms(self):
        pass
    def getTargetedLocales(self, component=''):
        tl = []
        section = get_section_info_from_disk(UI_SECTION_PREFIX, os.path.join(self.path, component))
        if UI_SECTION_PREFIX in section:
            for ui in section[UI_SECTION_PREFIX].split(','):
                uiSection = get_section_info_from_disk(ui, os.path.join(self.path, component))
                if TARGETED_LOCALES_OPTION in uiSection:
                    locales = uiSection[TARGETED_LOCALES_OPTION].split(',')
                    for loc in locales:
                        if loc not in tl:
                            tl.append(loc)
        return _normLocales(tl)
    def getSupportedLocales(self):
        pass
    def getMilestone(self, component=''):
        misc = get_section_info_from_disk(MISC_SECTION, os.path.join(self.path, component))
        return misc.get(MILESTONE_OPTION)
    def getExceptFolders(self):
        section = get_section_info_from_disk(SCANNED_FOLDER_SECTION, self.path)
        if EXCLUDE_OPTION_PREFIX in section:
            return re.compile(section[EXCLUDE_OPTION_PREFIX])
        return NON_RECURSING_FOLDERS_PAT
    def getIncludeFolders(self):
        section = get_section_info_from_disk(SCANNED_FOLDER_SECTION, self.path)
        if INCLUDE_OPTION_PREFIX in section:
            return re.compile(section[INCLUDE_OPTION_PREFIX])
        return None
    def getExceptFiles(self):
        section = get_section_info_from_disk(SCANNED_FOLDER_SECTION, self.path)
        if EXCLUDE_OPTION_PREFIX in section:
            return re.compile(section[EXCLUDE_OPTION_PREFIX])
        return None
    def getIncludeFiles(self):
        section = get_section_info_from_disk(SCANNED_FILE_SECTION, self.path)
        if INCLUDE_OPTION_PREFIX in section:
            return re.compile(section[INCLUDE_OPTION_PREFIX])
        return INTERESTING_EXT_PAT
    def getUiPaths(self):
        paths = {}
        uis = self.getUis()
        if UI_SECTION_PREFIX in uis:
            for ui in uis[UI_SECTION_PREFIX].split(','):
                uiSection = get_section_info_from_disk(ui, self.path)
                if UI_PATH_OPTION in uiSection:
                    paths[ui] = uiSection[UI_PATH_OPTION]
        return paths
    def getUis(self):
        return get_section_info_from_disk(UI_SECTION_PREFIX, self.path)
    def getUi(self, relpath):
        paths = self.getUiPaths()
        for ui in paths:
            if relpath.find(paths[ui]) > -1:
                return ui
    def shouldRecurse(self, folder):
        if folder == '.bzr':
            return False
        if self.debug:
            print('deciding whether to recurse into %s' % folder)
        exf = self.getExceptFolders()
        if exf:
            if exf.match(folder):
                return False
            else:
                if self.debug:
                    print('doesnt match regex "%s"' % exf.pattern)
        inf = self.getIncludeFolders()
        if inf:
            return bool(inf.match(folder))
        return True
    def shouldCheck(self, file):
        answer = None
        exf = self.getExceptFiles()
        if exf:
            if exf.match(file):
                answer = False
                if self.debug:
                    print('%s matched except pattern %s; should not check' % (file, exf.pattern))
        if answer is None:
            inf = self.getIncludeFiles()
            if inf:
                answer = bool(inf.match(file))
                if self.debug:
                    print('re.match(regex["%s"], "%s") returned %s' % (inf.pattern, file, str(answer)))
        return bool(answer)

def shouldCheck(file, debug=False):
    answer = None
    inf = INTERESTING_EXT_PAT
    answer = bool(inf.match(file))
    if debug:
        print('re.match(regex["%s"], "%s") returned %s' % (inf.pattern, file, str(answer)))
    return bool(answer)

_STR_TYPE = type('')
_USTR_TYPE = type(u'')
_LST_TYPE = type([])
_REGEX_TYPE = type(INTERESTING_EXT_PAT)
def _splitList(lst):
    ltype = type(lst)
    if ltype == _STR_TYPE or ltype == _USTR_TYPE:
        lst = str(lst).replace(';',',').split(',')
    elif ltype == _LST_TYPE:
        lst = [str(x) for x in lst]
    return lst

def _uniquify(lst):
    x = {}
    for item in lst:
        x[item] = 1
    return x.keys()

def _normPlat(plat):
    '''Normalizes a platform name to something like "Windows 32-bit". This
    name matches, by design, the name of the os and bitness returned by
    buildinfo.py.'''
    plat = str(plat).lower()
    bitness = ''
    if plat.find('win') > -1:
        os = 'Windows'
    elif plat.find('lin') > -1:
        os = 'Linux'
    elif (plat.find('darwin') > -1) or (plat.find('mac') > -1) or (plat.find('osx') > -1):
        os = 'OSX'
    if plat.find('64') > -1:
        bitness = '64'
    elif (plat.find('32') > -1) or (plat.find('86')):
        bitness = '32'
    plat = os
    if bitness:
        plat = plat + ' %s-bit' % bitness
    return plat

def _normPlatforms(plats):
    if plats is None:
        return None
    plats = [_normPlat(x) for x in _splitList(plats)]
    plats = _uniquify(plats)
    plats.sort()
    return plats

_PROGRAM_PAT = re.compile(r'^\s*add_executable', re.IGNORECASE | re.MULTILINE)
def isProgramDir(path):
    cmakelists = os.path.join(path, 'CMakeLists.txt')
    if os.path.isfile(cmakelists):
        txt = read_file(cmakelists)
        return bool(_PROGRAM_PAT.search(txt))
    return False

def print_tree(tree):
    queue = [tree]
    i = 0
    parent = str(tree.parent)
    while i < len(queue):
        dep = queue[i]
        for d in dep.dependencies:
            queue.append(d)
        if str(queue[i].parent) != parent:
            parent = str(queue[i].parent)
            print ''
        print queue[i]
        i += 1

ComponentInfo = collections.namedtuple('ComponentInfo', ['name', 'aspect', 'dependencies'])

class Components:
    def __init__(self, working_repo, branch, componentname, excludes={'components':[],'tree':[]}):
        self.omit_sandbox = excludes['components']
        self.omit_tree = excludes['tree']
        self.branch = branch
        self.infos = {}
        self.componentorder = [componentname]
        self.top = componentname
        self.infos[componentname] = ComponentInfo(componentname, 'code', [])
        self.add_dependencies(working_repo, componentname)

    def add_dependencies(self, working_repo, componentname):
##        print('calculating dependencies for %s' % componentname)
        deps = self.lookup_dependencies(working_repo, componentname, returnList=True)
        wr = vcs.get_working_repository()
        deps = [wr.normalize(comp, 'code', self.branch)[0] for comp in deps]
##        print '\t', deps
        for comp in deps:
            self.infos[componentname].dependencies.append(comp)
            if not comp in self.infos:
                self.componentorder.append(comp)
                if not comp in self.omit_tree:
                    self.infos[comp] = ComponentInfo(comp, 'code',[])
                    self.add_dependencies(working_repo, comp)

    def lookup_dependencies(self, working_repo, componentname, returnList=False):
        src = '%s/%s/%s/code/metadata.txt' % (working_repo.source_reporoot, self.branch, componentname)
        p = subprocess.Popen(['bzr', 'cat', src], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if 0 != p.wait():
            print 'unable to get deps for %s' % componentname
            print p.stderr.read()
            return []

        conf = ConfigParser.ConfigParser()
        conf.readfp(p.stdout)
        deps = {}
        comps = []
        if DEPENDENCIES_SECTION in conf.sections():
            for option in conf.options(DEPENDENCIES_SECTION):
                comps.append(option)
                deps[option] = conf.get(DEPENDENCIES_SECTION, option)
        if MISC_SECTION in conf.sections():
            for option in conf.options(MISC_SECTION):
                if option.lower() == 'no buildupto sandbox':
                    self.omit_sandbox.append(componentname)
        if returnList:
            return comps
        return deps

    def dependency_order(self):
        infos = copy.deepcopy(self.infos)
        processed = []
        while infos:
            for name in self.componentorder:
                if name in infos and (not infos[name].dependencies or set(self.omit_tree).intersection(infos[name].dependencies)):
                    info = infos[name]
                    processed.append(name)
                    del infos[name]
                    break
            for name in self.componentorder:
                if name in infos and processed[-1] in infos[name].dependencies:
                    infos[name].dependencies.remove(processed[-1])
        return [name for name in processed if not name in self.omit_sandbox]


def get_components_in_product(working_repo, branch, topcomponent, excludes={'components':[],'tree':[]}):
    components = Components(working_repo, branch, topcomponent, excludes)
    return components.dependency_order()


def _define_options():
    parser = optparse.OptionParser('Usage: %prog [options]\n\nEvaluate sandbox and record results.')
    parser.add_option('--sandbox', dest="sandbox",
                      help="path to sandbox to build",
                      metavar="FLDR", default=sandbox.current.get_root())
    parser.add_option('--dry-run', dest="dry_run", action='store_true', help="simulate and return success", default=False)

    return parser

if __name__ == '__main__':
    parser = _define_options()
    options, args = parser.parse_args(sys.argv)
    try:
        sb = sandbox.create_from_within(options.sandbox)
        if not sb:
            print('%s does not appear to be inside a sandbox.' % os.path.abspath(options.sandbox))
            err = 1
        else:
            if 1:
                import pprint
                pprint.pprint(get_components_in_product(branch=sb.get_branch(), topcomponent=sb.get_top_component()))
            else:
                deps, tree = get_components_inv_dep_order(vcs.get_working_repository(), sb.get_top_component(), code_root=sb.get_code_root(),
                                                         branch=sb.get_branch(), aspect=sb.get_component_reused_aspect(sb.get_top_component()), debug=True)
                print('Dependencies:')
                for comp in deps:
                    print comp
                print('-----------------------------------')
                print('Full dependance tree')
                print_tree(tree)
            err = 0
    except:
        traceback.print_exc()
        err = 1
    sys.exit(err)
