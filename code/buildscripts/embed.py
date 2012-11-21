#!/usr/bin/env python
#
# $Id: build.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import sys
import os
import shutil
import optparse
import re

import ioutil
import pydep
import text_diff

def _define_options():
    defsrc = os.path.dirname(os.path.abspath(__file__))
    parser = optparse.OptionParser('Usage: %prog [options] modules\n\nEmbed a required subset of python modules from a src folder.')
    parser.add_option('--dest', dest="dest",
                      help="path to populate",
                      metavar="FLDR", default=None)
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
    parser.add_option('--flatten', dest="flatten", action='store_true',
                      help="flatten folder structure",
                      default=False)
    parser.add_option('--dry-run', dest='dry_run', action='store_true', \
                      help="simulate only", default=False)
    return parser

def _require(options, attr):
    x = getattr(options, attr)
    if not x:
        return 'Must specify --%s' % attr

def flatten_module_name(module, modnames):
    i = module.rfind('.')
    if i > -1:
        mod = module[i+1:]
        if mod in modnames:
            return mod
    return module

def flatten(fpath, modnames):
    txt = ''
    with open(fpath, 'r') as f:
        while True:
            line = f.readline()
            if not line:
                break
            l = line.rstrip()
            if pydep.LIKELY_IMPORT_PAT.match(l) and not pydep.COMMENT_PAT.match(l):
                m = pydep.IMPORT_PAT.match(l)
                if m:
                    items = pydep.get_imports_from_regex_match(m.group(1))
                    items = [flatten_module_name(m, modnames) for m in items]
                    line = 'import %s' % ', '.join(items)
                else:
                    m = pydep.FROM_IMPORT_PAT.match(l)
                    if m:
                        line = '%sfrom %s import %s' % (
                            l[0:m.start(1)],
                            flatten_module_name(m.group(1), modnames), m.group(2))
            txt += l + '\r\n'
    ioutil.write_if_different(fpath, txt, compare_func=text_diff.texts_differ_ignore_whitespace)

def main(argv):
    parser = _define_options()
    options, args = parser.parse_args(argv)
    errors = []
    if args:
        errors.append('Unrecognized args: ' + ' '.join(args))
    for x in 'dest|src|dep'.split('|'):
        err = _require(options, x)
        if err:
            errors.append(err)
    if errors:
        for err in errors:
            print(err)
        print('\nTry --help.')
        return 1
    if options.skipdep:
        options.skipdep = pydep.RegexFilter(options.skipdep)
    if options.skipsrc:
        options.skipsrc = pydep.RegexFilter(options.skipsrc)
    sources = [ioutil.norm_folder(x) for x in options.src.split(',')]
    options.dest = ioutil.norm_folder(options.dest)
    depinfo = pydep.get_deps(sources, options.dep.split(','), options.skipsrc, options.skipdep)
    #depinfo.show()
    for module in depinfo.get_all_module_names():
        path = depinfo.path_for_module(module)
        relpath = module + '.py'
        if not options.flatten:
            for src in sources:
                if path.startswith(src):
                    relpath = path[len(src):]
                    break
        target = os.path.join(options.dest, relpath)
        folder = os.path.dirname(target)
        if options.dry_run:
            print('%s --> %s' % (path, target))
        else:
            if not os.path.isdir(folder):
                os.makedirs(folder)
            shutil.copy2(path, target)
            if options.flatten:
                flatten(target, depinfo.get_all_module_names())

if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except:
        x, val, x = sys.exc_info()
        print(str(val))
        sys.exit(1)
