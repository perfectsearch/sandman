#!/usr/bin/env python
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

from __future__ import print_function
import sys
import os
import shutil
import optparse
import re
from collections import namedtuple

ModuleInfo = namedtuple('ModuleInfo', 'full_path dependent_files')
DependencyInfo = namedtuple('DependencyInfo', 'module_info_by_module_name module_names_by_importer')

_debug = False

def _get_directly_dependent_files(depinfo, module):
    return depinfo.module_info_by_module_name[module].dependent_files

def _path_for_module(depinfo, module):
    return depinfo.module_info_by_module_name[module].full_path

def _get_all_module_names(depinfo):
    names = depinfo.module_info_by_module_name.keys()
    names.sort()
    return names

def _show(depinfo):
    names = depinfo.get_all_module_names()
    hdr = '\n-- All Required Modules (%d) ' % len(names)
    print(hdr.ljust(79, '-'))
    for n in names:
        print('    ' + n)
    print('\n-- Imported Modules '.ljust(79, '-'))
    for module in names:
        dependents = depinfo.get_directly_dependent_files(module)
        fnames = [os.path.basename(f) for f in dependents]
        print('    %s <-- %s (%d files)' % (module, ', '.join(fnames), len(dependents)))
    print('\n-- Importing Files '.ljust(79, '-'))
    for importer in depinfo.module_names_by_importer:
        imports = depinfo.module_names_by_importer[importer]
        print('    %s --> %s (%d modules)' % (os.path.basename(importer), ', '.join(imports), len(imports)))

DependencyInfo.get_directly_dependent_files = _get_directly_dependent_files
DependencyInfo.path_for_module = _path_for_module
DependencyInfo.get_all_module_names = _get_all_module_names
DependencyInfo.show = _show

import ioutil

def _define_options():
    parser = optparse.OptionParser('Usage: %prog [options] modules\n\nCalculate local dependencies for python module(s).')
    return parser

def find_all_modules(sources):
    all = {}
    for root in sources:
        for folder, dirs, files in os.walk(root):
            for f in files:
                if f != '__init__.py' and f.endswith('.py'):
                    all[f[0:-3]] = os.path.join(folder, f)
    return all

AS_PAT = re.compile(r'(.*)\s+as\s+.*')
def get_imports_from_regex_match(txt):
    x = []
    y = [i.strip() for i in txt.split(',')]
    for i in y:
        m = AS_PAT.match(i)
        if m:
            x.append(m.group(1))
        else:
            x.append(i)
    y = []
    for i in x:
        if '.' in i:
            y.append(i[i.rfind('.') + 1:])
        else:
            y.append(i)
    return y

COMMENT_PAT = re.compile(r'\s*#')
LIKELY_IMPORT_PAT = re.compile(r'(^|(.*\s+))import($|\s+)')
IMPORT_PAT = re.compile(r'^\s*import\s+(.*)$')
FROM_IMPORT_PAT = re.compile(r'^\s*from\s+(.*?)\s+import\s+(.*)$')
def get_local_imports_from_file(path, possible_modules):
    refs = []
    with open(path, 'r') as f:
        lines = [l.strip() for l in f.readlines() if LIKELY_IMPORT_PAT.match(l)]
    lines = [l for l in lines if not COMMENT_PAT.match(l)]
    if _debug:
        print('Found these imports in %s:' % path)
    for l in lines:
        if _debug:
            print('    %s ... ' % l, end='')
        items = []
        m = IMPORT_PAT.match(l)
        if m:
            items = get_imports_from_regex_match(m.group(1))
        else:
            m = FROM_IMPORT_PAT.match(l)
            if m:
                items = get_imports_from_regex_match(m.group(1)) + \
                      get_imports_from_regex_match(m.group(2))
        added = []
        for i in items:
            if i in possible_modules:
                added.append(i)
                refs.append(i)
        if _debug:
            if added:
                print('added %s' % ', '.join(added))
            else:
                print('ignored')
    if _debug:
        print('')
    return set(refs)

def expand(modules, path, possible_modules, module_names_by_importer, dependent_files_by_module_name):
    limps = get_local_imports_from_file(path, possible_modules)
    if limps:
        module_names_by_importer[path] = limps
        for limp in limps:
            # First time we've seen "import X"?
            if limp not in dependent_files_by_module_name:
                dependent_files_by_module_name[limp] = []
            # First time we've concluded that file Y depends on module X?
            if path not in dependent_files_by_module_name[limp]:
                dependent_files_by_module_name[limp].append(path)
        # See if the imports in this file imply that we need to recurse.
        new_modules = [limp for limp in limps if limp not in modules]
        if new_modules:
            modules += new_modules
            for new_mod in new_modules:
                expand(modules, possible_modules[new_mod], possible_modules, module_names_by_importer, dependent_files_by_module_name)

def is_in_sources(folder, sources):
    folder = ioutil.norm_folder(folder)
    for src in sources:
        if folder.startswith(src):
            return True
    return False

def get_deps(rough_sources, rough_dependent_items, rough_source_filter=None, rough_dependent_filter=None):
    '''
    Get direct and indirect dependencies of all enumerated items on python
    modules in sources folders.

    @param rough_sources A folder, or a list of folders, that contain modules of
    interest (that might or might not be depended *on*).

    @param rough_dependent_items One or more items that have dependencies on the
    source. These items can be specific files, folders, or python module names
    within the source. They serve as the starting point of the dependency
    analysis. Can be either a sequence or a string.

    @param rough_source_filter A callable that takes a path to a python module.
    The module is a potential source module, and will be included in our analysis
    (though not necessarily in the final dependency graph) unless the callable
    returns False. Example of use: Suppose a folder of python code contains a
    subdirectory of unit tests that should be ignored in transitive dependency
    analysis. You could exclude this subdirectory with rough_source_filter.

    @param rough_dependent_filter A callable that takes a path to a python module.
    The module is a candidate for analysis to decide if it depends on any source
    modules. The callable returns True if the file should be included in our
    analysis and False if not. Example of use: suppose python folder D (dependent)
    depends somewhat on files in python folder S (source). Suppose further that
    most dependencies are run-time dependencies, but 2 scripts in D have build-
    time dependencies instead. If you only wanted a picture of run-time
    dependencies, you could pass D as one of the rough_dependent_items to this
    function, and use rough_dependent_filter to exclude the 2 scripts with
    build-time dependencies.

    Return a DependencyInfo named tuple:

        .module_info_by_module_name = dict of depended-on-module-name -->
            ModuleInfo named tuple:
                .full_path = path to depended-on-module
                .dependent_files = full paths of files dependent on the module

        .module_names_by_importer = dict of full-path-of-dependent-file -->
            depended-on module name

        Note that although DependencyInfo is a read-only, named tuple, it has
        a number of useful methods; it is not just a raw data container. See
        top of module for details.
    '''
    sources = rough_sources
    # Allow a single string/unicode as sources as well as a list.
    if hasattr(sources, 'lower'): #string or unicode
        sources = [sources]
    if not sources:
        raise Exception('Must specify at least one folder of python source.')
    dependent_items = rough_dependent_items
    # Allow a single string/unicode as dependent_items as well as a list.
    if hasattr(sources, 'lower'): #string or unicode
        dependent_items = [dependent_items]
    if rough_dependent_filter:
        dependent_items = [di for di in dependent_items if rough_dependent_filter(di)]
    if not dependent_items:
        raise Exception('Must specify at least one folder, file, or module name to start the dependency analysis.')
    if _debug:
        print('sources = %s\n' % str(sources))
        print('dependent_items = %s\n' % str(dependent_items))
    sources = [os.path.abspath(src) for src in sources]
    bad = []
    for src in sources:
        if not os.path.isdir(src):
            bad.append(src)
    if bad:
        raise Exception('The following source items are not folders:\n    ' + '\n    '.join(bad))
    sources = [ioutil.norm_seps(src, trailing=True) for src in sources]
    possible_modules = find_all_modules(sources)
    if _debug:
        print('possible modules = %s\n' % ', '.join(sorted(possible_modules.keys())))
    if rough_source_filter:
        for key in possible_modules.keys()[:]:
            if not rough_source_filter(possible_modules[key]):
                del(possible_modules[key])
    start_folders = [di for di in dependent_items if os.path.isdir(di)]
    start_files = [di for di in dependent_items if os.path.isfile(di)]
    start_modules = [di for di in dependent_items if di not in start_folders and di not in start_files]
    bad = [x for x in start_modules if x not in possible_modules]
    if bad:
        raise Exception('The following start dependencies are neither folders, files, nor python modules:\n    ' + '\n    '.join(bad))
    start_folders = [ioutil.norm_folder(sf) for sf in start_folders]
    start_files = [ioutil.norm_seps(os.path.abspath(sf)) for sf in start_files]
    # Guarantee uniqueness. Shouldn't be a problem unless someone was careless
    # on cmdline -- but just in case...
    modules = list(set(start_modules[:]))
    module_names_by_importer = {}
    dependent_files_by_module_name = {}
    for m in start_modules:
        expand(modules, possible_modules[m], possible_modules, module_names_by_importer, dependent_files_by_module_name)
    for sf in start_folders:
        for folder, dirs, files in os.walk(sf):
            for f in files:
                if f.endswith('.py'):
                    start_files.append(ioutil.norm_seps(os.path.abspath(os.path.join(folder, f))))
    for sf in start_files:
        if (not rough_dependent_filter) or rough_dependent_filter(sf):
            # If we haven't already analyzed a particular start file because we
            # saw it while expanding dependencies of something in start_modules...
            if sf not in module_names_by_importer:
                expand(modules, sf, possible_modules, module_names_by_importer, dependent_files_by_module_name)
                # If this file is in one of the sources directories, then include it
                # as a depended-on file. Otherwise, we just treat the file as a
                # source of dependencies, but not a depended on file itself.
                folder, fname = os.path.split(sf)
                #print('split yielded %s, %s' % (folder, fname))
                #print('sources = %s' % sources)
                if is_in_sources(folder, sources):
                    module, ext = os.path.splitext(fname)
                    if module not in dependent_files_by_module_name:
                        modules.append(module)
                        dependent_files_by_module_name[module] = []
                        if '' not in module_names_by_importer:
                            module_names_by_importer[''] = []
                        module_names_by_importer[''].append(module)
    # Convert data to output format.
    mibmn = {}
    for name in modules:
        mi = ModuleInfo(possible_modules[name], dependent_files_by_module_name.get(name, []))
        mibmn[name] = mi
    return DependencyInfo(mibmn, module_names_by_importer)

class RegexFilter:
    def __init__(self, regex):
        self.regex = re.compile(regex, re.IGNORECASE)
    def __call__(self, item):
        if _debug:
            print('Evaluating %s against "%s"' % (item, self.regex.pattern))
        keep = not self.regex.match(item)
        if _debug and not keep:
            print('Not keeping %s' % item)
        return keep

def _define_options():
    defsrc = os.path.dirname(os.path.abspath(__file__))
    parser = optparse.OptionParser('Usage: %prog [options] modules\n\nShow the python modules used by source(s).')
    parser.add_option('--dep', dest="dep",
                      help="comma-sep list of files/folders/modules to seed dep analysis",
                      metavar="ITEMS", default=None)
    parser.add_option('--skip-dep', dest="skipdep",
                      help="regex to exclude a small subset of items in --dep",
                      metavar="REGEX", default=None)
    parser.add_option('--src', dest="src",
                      help="comma-sep list of folders to pull from; default=%s" % defsrc,
                      metavar="FLDRs", default=defsrc)
    parser.add_option('--skip-src', dest="skipsrc",
                      help="regex to exclude a small subset of items in --src",
                      metavar="REGEX", default=None)
    parser.add_option('--debug', dest="debug", help="debug analysis",
                      action='store_true', default=False)
    return parser

def main(argv):
    import optparse
    parser = _define_options()
    options, args = parser.parse_args(argv)
    if not options.dep:
        print('Use --dep to seed dependency analysis.')
        sys.exit(1)
    if options.skipdep:
        options.skipdep = RegexFilter(options.skipdep)
    if options.skipsrc:
        options.skipsrc = RegexFilter(options.skipsrc)
    if options.debug:
        _debug = True
    depinfo = get_deps(options.src, options.dep.split(','), options.skipsrc, options.skipdep)
    depinfo.show()
    print('')

if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except:
        x, val, x = sys.exc_info()
        print(str(val))
        sys.exit(1)
