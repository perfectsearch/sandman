import os
import shutil

import ioutil

CUSTOM_INIs = ['development.ini','test.ini']
RUNROOT_NUKE_EXCEPTIONS = [r'(development|test)\.ini$', r'\.ini\.unedited$']

def filter_build_phase(item):
    if item.endswith('.bzr/'):
        return False
    fname = os.path.basename(item)
    keep = not (fname.endswith('.pyc') or
            fname == '_build.py' or
            fname.endswith('_tmpl'))
    return keep

def convert_template_if_doesnt_exist(ini):
    if not os.path.isfile(ini):
        shutil.copy2(ini + '_tmpl', ini)

def filter_assemble_phase(item):
    if item.endswith('.if_top/'): 
        return False
    # Exclude both .bzrignore and .bzr
    if '.bzr' in item: 
        return False
    # We do special handling of any .ini files other than "deployment.ini"...
    if item.endswith('.ini'): 
        return not item.endswith('deployment.ini')
    return True

def del_if_exists(fpath):
    try:
        os.remove(fpath)
    except:
        pass

def get_unedited_ini_path(ini):
    return os.path.join(os.path.dirname(ini), '.' + os.path.basename(ini) + '.unedited')

def ini_is_generic(ini):
    if not os.path.isfile(ini):
        return True
    unedited = get_unedited_ini_path(ini)
    if not os.path.isfile(unedited):
        return True
    if ioutil.file_stats_differ(ini, unedited, stat_compare_func=ioutil.sizes_differ):
        return False
    return not ioutil.file_texts_differ(ini, unedited)

def update_inis(my_built, run_root):
    for f in CUSTOM_INIs:
        dest = os.path.join(run_root, f)
        if ini_is_generic(dest):
            src = os.path.join(my_built, f)
            shutil.copy2(src, dest)
            shutil.copy2(src, get_unedited_ini_path(dest))
        else:
            print('    Leaving run/%s alone; it appears to have been hand-edited.' % f)

