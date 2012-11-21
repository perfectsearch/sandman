#!/usr/bin/env python
#
# $Id: ioutil.py 9318 2011-06-10 02:37:10Z nathan_george $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import os
import codecs
import stat
import sys
import re
import subprocess
import check_output
import shutil
import tempfile
import text_diff

import ospriv

if os.name == 'nt':
    # The name of the device that can be used to redirect stdout/stderr to bit bucket.
    NULL_DEVICE = 'nul'
else:
    # The name of the device that can be used to redirect stdout/stderr to bit bucket.
    NULL_DEVICE = '/dev/null'

def norm_seps(path, trailing=None):
    '''
    Force all segments of a path to be delimited by / (even on Windows). Force
    standard behavior for trailing slashes.

    @param trailing If None, ignore the issue of trailing slashes; whatever
           style comes into the function goes back out. This is appropriate
           if a path identifies a file. If True, force path to end with a
           trailing slash. If False, make sure path does not end with
           a trailing slash. Note that this may cause problems if it is the
           root path on linux; the caller should decide how to handle this.
    '''
    path = path.replace('\\', '/')
    if trailing is not None:
        last = path[-1]
        if trailing:
            if last != '/':
                path += '/'
        else:
            if last == '/':
                path = path[0:-1]
    return path

def os_norm_seps(path, trailing=None):
    '''
    Force all segments of a path to use the OS's separator.
    '''
    path = norm_seps(path, trailing)
    if os.name == 'nt':
        path = path.replace('/', '\\')
    return path

def norm_folder(folder):
    '''
    Convenience method; calls norm_seps(os.path.abspath(folder), trailing=True)
    '''
    return norm_seps(os.path.abspath(folder), trailing=True)

def read_file(path):
    '''
    Open a file and read its text into a byte string.
    '''
    txt = ''
    with open(path, 'rt') as f:
        txt = f.read()
    return txt

def read_file_as_unicode(path, encoding='utf-8'):
    '''
    Open a file and read its text into a unicode string.
    '''
    txt = u''
    f = codecs.open(path, 'r', encoding)
    if f:
        txt = f.read()
        f.close()
    return txt

def file_differs_from_text(path, txt, encoding='utf-8', compare_func=text_diff.texts_differ):
    '''
    Compare a file with some text, using an arbitrary function. Text is compared
    as unicode, meaning that diff will return False if the two forms of text
    are identical in unicode, even if they're not identical in their current
    encoding.
    '''
    if type(txt) != type(u''):
        txt = unicode(str(txt), encoding)
    exists = os.path.isfile(path)
    if exists:
        ftxt = read_file_as_unicode(path, encoding)
        return compare_func(ftxt, txt)
    return bool(txt)

def file_texts_differ(path1, path2, encoding1='utf-8', encoding2='utf-8', compare_func=text_diff.texts_differ):
    '''
    Compare two text files, using an arbitrary function. Text is compared
    as unicode, meaning that diff will return False if the two forms of text
    are identical in unicode, even if they're not identical in their current
    encoding.
    '''
    txt1 = read_file_as_unicode(path1, encoding1)
    txt2 = read_file_as_unicode(path2, encoding2)
    return compare_func(txt1, txt2)

def write_if_different(path, txt, encoding='utf-8', compare_func=text_diff.texts_differ):
    '''
    Write a file if the new content differs from existing content, or if the
    file does not already exist. Write is done safely (write to tmp, remove old,
    then rename tmp to old).

    @param txt The content for the file. May be unicode or a byte string.
    @param encoding If txt is unicode, governs how text is rendered on output.
    @param compare_func Function used to decide which differences matter. By
           default, cmp(str1, str2) is used, but this can be overridden to
           ignore whitespace, comments, and so forth.
    '''
    if type(txt) != type(u''):
        txt = unicode(str(txt), encoding)
    exists = os.path.isfile(path)
    if exists:
        if not compare_func:
            compare_func = text_diff.texts_differ
        oldTxt = read_file_as_unicode(path, encoding)
        if not compare_func(oldTxt, txt):
            return False
    tmpPath = path + '.tmp'
    tmp = codecs.open(tmpPath, 'w', encoding)
    tmp.write(txt)
    tmp.close()
    if exists:
        os.remove(path)
    os.rename(tmpPath, path)
    return True

def subdirs(path):
    '''
    Return a list of all subdirs of a folder.
    '''
    if not path:
        path = '.'
    items = os.listdir(path)
    return [x for x in items if os.path.isdir(os.path.join(path, x))]

class RegexesMatcher:
    '''
    In directory walking algorithms (e.g., the one used by nuke()), this class
    provides a convenient way to identify interesting items.
    '''
    def __init__(self, regexes):
        if type(regexes) == STRING_TYPE:
            regexes = [regexes]
        assert(type(regexes) == type([]))
        r2 = []
        for r in regexes:
            if type(r) == STRING_TYPE:
                try:
                    r = re.compile(r)
                except:
                    msg = '"%s" is not a valid regular expression. ' % r
                    raise Exception(msg + str(sys.exc_value))
            r2.append(r)
        self.regexes = r2
    def __call__(self, path):
        for r in self.regexes:
            if r.match(path):
                #print('"%s" matched "%s"' % (path, r.pattern))
                return True
        #print('Found no match for %s' % path)
        return False

def _should_skip(path, root, item, skip):
    shouldSkip = False
    if skip:
        expr = norm_seps(os.path.join(root, item))[len(path):]
        shouldSkip = bool(skip(expr))
    return shouldSkip

def ignore_errors(item, failedFunc):
    return True

STRING_TYPE = type('')
LIST_TYPE = type([])

def nuke(path, contents_only=False, skip=None, continuer=ignore_errors):
    '''
    Remove a folder and all of its contents -- or remove a subset thereof.
    Return True if all portions of the operation succeed. (This may not mean the
    the folder is gone if items were skipped or contents_only is True.)

    Read-only files that are targeted for deletion are automatically changed to
    read-write first.

    Like shutil.rmtree, but provides more control. However, does not recurse
    into symlink'ed folders.

    @param path The folder where nuking should begin.
    @param contents_only If True, nuke everything *inside* a folder, but not
           the folder itself.
    @param skip An object or function that is called with a fully qualified path
           for each item. Returns True if item should be skipped/left behind.
    @param continuer An object or function that is called with a fully qualified
           path and a function that failed on an item, immediately after
           each item is processed. If the item deleted successfully, the second
           param is None; otherwise it is one of {os.path.islink(), os.listdir(),
           os.remove(), or os.rmdir()}. This call should returns True to
           continue or False to stop.
    '''

    # If skip is a string or a list of strings then convert it to a RegexMatcher
    #  object that we can call into.
    if skip and (type(skip) == STRING_TYPE or type(skip) == LIST_TYPE):
        skip = RegexesMatcher(skip)

    # Optimization on *nix -- faster and more reliable; can be used in
    # some cases. The equiv command on Windows ("rd <folder> /s /q") appears to
    # be just as slow and unreliable as our own code.
    if os.name != 'nt':
        if (not contents_only) and (skip is None) and (continuer is None or
            continuer == ignore_errors):
            return not bool(os.system('rm -rf "%s"' % os.path.abspath(path)))
    if os.path.isdir(path):
        uberOk = True
        path = norm_folder(path)
        tryRemove = not contents_only
        for root, dirs, files in os.walk(path, topdown=False):
            for f in files:
                if _should_skip(path, root, f, skip):
                    tryRemove = False
                else:
                    item = os.path.join(root, f)
                    os.chmod(item, stat.S_IWRITE)
                    ok = True
                    try:
                        os.remove(item)
                    except:
                        uberOk = ok = False
                    if continuer:
                        if not continuer(item, ok):
                            return uberOk
            for d in dirs:
                if _should_skip(path, root, d, skip):
                    tryRemove = False
                else:
                    ok = True
                    item = os.path.join(root, d)
                    if os.path.islink(item):
                        if not continuer(item, os.path.islink):
                            return uberOk
                    else:
                        try:
                            os.rmdir(item)
                        except:
                            uberOk = ok = False
                        if continuer:
                            if not continuer(item + '/', ok):
                                return uberOk
        if tryRemove:
            ok = True
            if os.path.islink(path):
                continuer(path, os.path.islink)
                uberOk = False
            else:
                try:
                    os.rmdir(path)
                except:
                    uberOk = ok = False
                    continuer(path, os.path.islink)
    else:
        uberOk = False
    return uberOk

def get_tail(path, count=5, selector=None):
    '''
    Get the tail of a file as a list of lines.

    @param count How many lines to return.
    @param selector A function that filters which lines are returned. It must
           take a string and return True/False.
    '''
    lines = []
    if os.path.isfile(path):
        for i in range(count):
            lines.append(None)
        f = open(path, 'rt')
        i = 0
        while True:
            line = f.readline()
            if not line:
                break
            if (selector is None) or (selector(line)):
                lines[i % count] = line
                i += 1
        if i == 0:
            lines = []
        else:
            if i > count:
                i = i % count
                end = i + count
            else:
                end = i
                i = 0
            retained = []
            for j in range(i, end):
                retained.append(lines[j % count])
            lines = retained
    return lines

def compare_paths(a, b):
    '''
    Compare two paths, ignoring differences that are irrelevant from the file
    system's perspective. On all platforms, the \ and / segment separators are
    treated as equivalent, and trailing segment separators are ignored. On
    Windows, case is also ignored. (Mac is case-preserving but case-insensitive
    by default; not sure if it should ignore case as well...)
    '''
    if not a:
        a = ''
    if not b:
        b = ''
    if os.name == 'nt':
        a = a.lower()
        b = b.lower()
    a = norm_seps(a)
    b = norm_seps(b)
    if a and a[-1] == '/':
        a = a[0:-1]
    if b and b[-1] == '/':
        b = b[0:-1]
    return cmp(a, b)

def make_symbolic_link(desired_link, existing_path):
    '''
    Create a symbolic link to a file or folder, or raise an exception if it
    can't be done.

    On Windows, this call always requires admin privileges.
    '''
    if os.name == 'nt':
        desired_link = os_norm_sep(desired_link)
        existing_path = os_norm_sep(existing_path)
    if not os.path.exists(existing_path):
        raise Exception('%s does not exist.' % existing_path)
    if os.path.exists(desired_link):
        raise Exception('%s already exists.' % desired_link)
    if os.name == 'nt':
        # Creating symbolic links on Win7 and similar is a privileged
        # operation that can't be done unless a user is explicitly running
        # in administrator mode...
        if not ospriv.user_has_admin_privileges():
            raise Exception('User needs admin privileges.')
        if os.path.isdir(existing_path):
            # We could use a junction instead of a directory symbolic link
            # in some cases. This does not require admin mode (surprisingly).
            # However, junctions only work within the boundaries of the same
            # file system, so they are inadequate for the general case.
            flag = '/D'
        else:
            flag = '/F'
        cmd = 'mklink %s "%s" "%s"' % (flag, desired_link, existing_path)
        #print(cmd)
    else:
        cmd = 'ln -s "%s" "%s"' % (existing_path, desired_link)
    stdout = subprocess.check_output(cmd, shell=True)

class TempDir:
    '''
    A temporary directory that is created at the top of Python's "with" statement
    and deleted at the end of the block.
    '''
    def __init__(self, path=None, disable=False):
        if path is not None:
            path = os.path.abspath(path)
        self.path = path
        self._disabled = disable
    def __enter__(self):
        if self.path:
            assert(not os.path.isdir(self.path))
            os.makedirs(self.path)
        else:
            self.path = tempfile.mkdtemp()
        return self
    def __exit__(self, type, value, traceback):
        if not self._disabled:
            shutil.rmtree(self.path)

class WorkingDir:
    '''
    A class that changes directory for the duration of a Python "with" statement.
    '''
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.restore_path = os.getcwd()
    def __enter__(self):
        os.chdir(self.path)
        return self
    def __exit__(self, type, value, traceback):
        os.chdir(self.restore_path)

class FakeFile:
    '''
    fix_ When I wrote this class I didn't know about StringIO. Please remove all
    references to this class and then delete the class itself.
    '''
    def __init__(self):
        self.txt = ''
    def write(self, txt):
        self.txt += txt
    def flush(self):
        pass
    def read(self):
        return self.txt

_LOW_TEXT_BYTES = [ord(x) for x in '\t\r\n']
def is_binary_file(path, max_scanned_bytes=100):
    with open(path, 'r') as f:
        first_bytes = f.read(max_scanned_bytes)
    return bytes_are_binary(first_bytes)

def bytes_are_binary(bytes):
    for byte in bytes:
        if byte < 32:
            if byte not in _LOW_TEXT_BYTES:
                return True
    return False

def sizes_differ(stat_a, stat_b):
    return stat_a.st_size != stab_b.st_size

def mtimes_differ(stat_a, stat_b):
    return round(stat_a.st_mtime, 1) != round(stab_b.st_mtime, 1)

def sizes_or_mtimes_differ(stat_a, stat_b):
    return sizes_differ(stat_a, stat_b) or mtimes_differ(stat_a, stab_b)

def file_stats_differ(path_a, path_b, stat_compare_func=sizes_or_mtimes_differ):
    try:
        astat = os.stat(path_a)
        bstat = os.stat(path_b)
        if stat_compare_func(astat, bstat):
            return True
    except OSError:
        return True

def copy_file_only_if_new_dest(src, dest):
    if os.path.isfile(dest):
        return
    shutil.copy2(src, dest)

def transform_tree(src, dest, item_filter=None, path_transformer=None, save_func=shutil.copy2):
    if not os.path.isdir(src):
        raise Exception('Source tree %s is not a directory.' % src)
    if os.path.exists(dest) and not os.path.isdir(dest):
        raise Exception('Dest tree %s is not a directory.' % dest)
    src = norm_seps(os.path.abspath(src), trailing=True)
    dest = norm_seps(os.path.abspath(dest), trailing=True)
    if not os.path.isdir(dest):
        os.makedirs(dest)
    for folder, dirs, files in os.walk(src):
        folder = norm_seps(folder, trailing=True)
        relative_path = folder[len(src):]
        # Eliminate items as appropriate.
        if item_filter:
            # Removing dirs prevents recursion into them.
            for d in dirs[:]:
                if not item_filter(relative_path + d + '/'):
                    dirs.remove(d)
            for f in files[:]:
                if not item_filter(relative_path + f):
                    files.remove(f)
        if files:
            # Default behavior is to clone the tree structure from src to dest.
            # However, if user has provided path_transformer, we can remap names
            # very flexibly.
            if not path_transformer:
                path_transformer = lambda x: x
            target_paths = {}
            for f in files:
                target_paths[f] = dest + path_transformer(relative_path + f)
            for f in files:
                fldr = os.path.dirname(target_paths[f])
                if not os.path.exists(fldr):
                    os.makedirs(fldr)
                save_func(src + relative_path + f, target_paths[f])
    return 0
