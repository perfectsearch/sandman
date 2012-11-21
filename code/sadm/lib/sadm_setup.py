# $Id: sadm_setup.py 10647 2011-07-07 22:53:47Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

import sys
import urllib2
import urllib
import traceback
import time
import shutil
import ConfigParser

import buildinfo
import text_diff
import ioutil
import vcs
from check_tools import *
from sadm_config import config
from sadm_constants import *
from sadm_schedule import *
from sadm_util import *
import sadm_prompt

def _get_prompt_bool_repr(response):
    if response:
        return 'y'
    return 'n'

_SADM_BASH_CMDS_FILE = 'sadm-bash-commands.sh'
REMOTE_INFO_FILE = 'remoteInfo.txt'

def _update_bash_funcs():
    funcs = read_file(join_path(APP_FOLDER, 'templates/' + _SADM_BASH_CMDS_FILE))
    funcs = subst(funcs, 'app_path', APP_PATH)
    funcs = subst(funcs, 'app_folder', APP_FOLDER)
    funcs = subst(funcs, 'sandbox_container_folder', config.sandbox_container_folder)
    cmds_path = APP_FOLDER + '/' + _SADM_BASH_CMDS_FILE
    updated = ioutil.write_if_different(cmds_path, funcs, compare_func=text_diff.texts_differ_ignore_whitespace)
    return cmds_path, updated

def _setup_windows_path():
    from _winreg import HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, KEY_READ, KEY_WRITE, OpenKey, QueryValueEx, SetValueEx
    from win32con import HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG
    from win32gui import SendMessageTimeout

    def check_system_path():
        hive = HKEY_LOCAL_MACHINE
        key = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
        with OpenKey(hive, key, 0, KEY_READ) as regkey:
            path, type = QueryValueEx(regkey, 'PATH')
        path = [p.strip().rstrip('\\') for  p in path.split(';') if p.strip()]
        for p in path:
            if os.path.isfile(os.path.join(p, 'sadm.py')):
                eprintc('\nSadm is in the system path. It should be removed because the system path setting may conflict with the user path setting.', WARNING_COLOR)
                break

    def get_user_path():
        hive = HKEY_CURRENT_USER
        key = 'Environment'
        with OpenKey(hive, key, 0, KEY_READ) as regkey:
            path, type = QueryValueEx(regkey, 'PATH')
        return [p.strip().rstrip('\\') for  p in path.split(';') if p.strip()]

    def set_user_path(path):
        hive = HKEY_CURRENT_USER
        key = 'Environment'
        with OpenKey( hive, key, 0, KEY_WRITE) as regkey:
            SetValueEx(regkey, 'PATH', None, 2, ';'.join(path))
        SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 100)

    sadmpath = ioutil.os_norm_seps(APP_FOLDER).lower().rstrip('\\')
    sadm_in_path = False
    path = get_user_path()
    badsadm = []
    for p in path:
        if p.lower() == sadmpath:
            sadm_in_path = True
        elif os.path.isfile(os.path.join(p, 'sadm.py')):
            eprintc('\nA different copy of sadm was found in your path and will be removed: %s' % p, WARNING_COLOR)
            badsadm.append(p)

    path_needs_update = False
    for p in badsadm:
        path.remove(p)
        path_needs_update = True

    if sadm_in_path:
        print('\nSadm is in the path. Convenience features are available.\n')
    else:
        path.append(sadmpath)
        path_needs_update = True
        print('\nSadm has been added to your path. You will need to restart cmd.exe for it to become effective.')
    if path_needs_update:
        set_user_path(path)
    check_system_path()

def _setup_convenience_funcs():
    if os.name == 'nt':
        _setup_windows_path()
    else:
        bash_profile = '.bashrc'
        machineInfo = buildinfo.BuildInfo()
        if machineInfo.os == 'OSX':
            bash_profile = '.bash_profile'
        bash_profile = join_path(HOMEDIR, bash_profile)
        txt = ''
        if os.path.isfile(bash_profile):
            txt = read_file(bash_profile)
            if txt.find(_SADM_BASH_CMDS_FILE) > -1:
                print('\nConvenience functions appear to be installed in %s.\n' % bash_profile)
                linked_path, updated = _update_bash_funcs()
                if updated:
                    eprintc('\nContent in %s has been updated. Restart bash to get updates.\n' % linked_path, WARNING_COLOR)
                return
        print('')
        if sadm_prompt.prompt_bool('Add convenience functions like "sb cr" and "sb build" to %s' % bash_profile, 'y'):
            print('')
            cmds_path, updated = _update_bash_funcs()
            txt = read_file(bash_profile).rstrip()
            txt += '\n\n# Convenience functions installed by sadm\ntest -r %s && source %s\n\n' % (cmds_path, cmds_path)
            save(bash_profile, txt)
            eprintc('Restart bash to get updates.\n', WARNING_COLOR)

def _update_bzr_plugin():
    plugindir = os.path.join(vcs.PRIVATE_VCS_FOLDER, 'plugins', 'example') ## TODO what should example be?
    if not os.path.isdir(plugindir):
        os.makedirs(plugindir)
    if not os.path.isdir(BUILDSCRIPTS_FOLDER):
        print( 'ERROR: unable to find buildscripts folder')
    else:
        # First remove any old files used by the plugin.
        shutil.rmtree(plugindir)
        # Now copy all files currently used by the plugin.
        src = os.path.join(BUILDSCRIPTS_FOLDER, '..', 'bzr-plugins')
        items_not_to_copy = lambda root, items:['.bzr', '_build.py']
        shutil.copytree(src, plugindir, ignore=items_not_to_copy)
        # the plugin is configured by default to run on the server so reconfigure it
        with open(plugindir + '/__init__.py') as f:
            lines = f.readlines()
        with open(plugindir + '/__init__.py', 'w') as f:
            for l in lines:
                if 'clientplugin' in l:
                    l = l[1:]
                if 'serverplugin' in l:
                    l = "#" + l
                f.write(l)
        plugin_buildscripts_dir = os.path.join(plugindir, 'buildscripts')
        # Normally, we'll be installing from a built sadm and a built bzr-plugins folder,
        # which will automatically put a buildscripts subdir under the plugin. However,
        # if we're installing from source, we have to go the extra mile...
        if not os.path.isdir(plugin_buildscripts_dir):
            shutil.copytree(BUILDSCRIPTS_FOLDER, plugin_buildscripts_dir, ignore=items_not_to_copy)
        print('\nInstalled latest version of bzr plugin to %s.' % plugindir)

def _set_bzr_default_ignore():
    if os.name == 'nt':
        ignoreFilePath = os.path.join(HOMEDIR, 'APPDATA', 'Roaming', 'bazaar', '2.0', 'ignore')
    else:
        ignoreFilePath = os.path.join(HOMEDIR, '.bazaar', 'ignore')
    if not os.path.isfile(ignoreFilePath):
        return
    with open(ignoreFilePath, 'r+') as ignoreFile:
        lines = ignoreFile.readlines()
        do_not_ignore = ['*.so']
        for line in lines[:]:
            for item in do_not_ignore:
                if line.find(item) > -1:
                    lines.remove(line)
                    break
        ignoreFile.seek(0)
        ignoreFile.writelines(lines)

def _check_required_tools():
    print('\nChecking tools required by sadm...\n')
    rtools = []
    for path in [APP_FOLDER, BUILDSCRIPTS_FOLDER]:
        section = metadata.get_section_info_from_disk(metadata.RUN_TOOLS_SECTION, path)
        if section:
            for tool, info in section.iteritems():
                rtools.append(ReqTool.from_pair(tool, info))
    check_tools(rtools)

def _check_canonical():
    if config.could_be_canonical_machine():
        print('''
Canonical build machines are managed by CM. They have a specific set of tools
installed (nothing extra), meet a minimal hardware spec, use standard
credentials and network config, and do nothing besides evaluate sandboxes.
When a build fails on a canonical build machine, the owner of the box and the
owner of the svn project cooperate to fix it. Many sadm settings are hard-coded
for such machines.
''')
        config.is_canonical_machine = sadm_prompt.prompt_bool('Treat this box as a canonical build machine?', _get_prompt_bool_repr(config.is_canonical_machine))
        if config.is_canonical_machine:
            config.auto_add_sandboxes = sadm_prompt.prompt_bool('Automatically add sandboxes?', _get_prompt_bool_repr(config.auto_add_sandboxes))
            config.branches_to_auto_add = sadm_prompt.prompt('Which branches would you like to add sandboxes from.(Give a list seperated by commas e.i. trunk,push_feature,... or all for all branches.)', config.branches_to_auto_add)
        else:
            config.auto_add_sandboxes = False
    else:
        config.is_canonical_machine = False
        config.auto_add_sandboxes = False

def _check_remoting_info():
    if sadm_prompt.prompter.get_mode() == sadm_prompt.AUTOCONFIRM_MODE:
        return
    if not config.needs_remoting_info():
        return
    descr = buildinfo.BuildInfo()
    remoteInfo = ''
    print('''
Machines that automate sandbox operations should be remotely accessible for
configuration and troubleshooting purposes. Please provide the following
information to facilitate this.
''')
    config.username_for_remote_access = sadm_prompt.prompt('Username for remote login', config.username_for_remote_access)
    config.ipaddr = sadm_prompt.prompt('IP address', config.ipaddr)
    config.ssh_port = sadm_prompt.prompt('Port for ssh', config.ssh_port)
    config.remote_desktop_port = sadm_prompt.prompt('Port for remote desktop', config.remote_desktop_port)
    config.remoting_instructions = sadm_prompt.prompt('''
Other instructions for accessing this machine remotely (such as where to get the password etc.)''', config.remoting_instructions)
    if config.ssh_port:
        remoteInfo += 'ssh to %s:%s as %s\n' % (config.ipaddr, config.ssh_port, config.username_for_remote_access)
    if config.remote_desktop_port:
        remoteInfo += 'remote desktop to %s:%s\n' % (config.ipaddr, config.remote_desktop_port)
    if config.remoting_instructions:
        remoteInfo += '%s' % config.remoting_instructions
    build_machines = tempfile.mkdtemp()
    wr = vcs.get_working_repository()
    vcs.checkout(os.path.join(wr.master_reporoot, 'BuildMachines').replace('\\','/'), build_machines)
    if os.name == 'nt':
        site = os.environ['COMPUTERNAME'].lower()
    else:
        site = os.environ['HOSTNAME'].lower()
    fldr = os.path.join(build_machines, site)
    if not os.path.isdir(fldr):
        os.makedirs(fldr)
    fp = open(os.path.join(fldr, REMOTE_INFO_FILE), 'w')
    fp.write(remoteInfo)
    fp.close()
    vcs.add(build_machines)
    try:
        vcs.checkin(build_machines, 'Update remote info for %s' % site, quiet=True)
    except:
        pass

def _check_loc(config, prop_name, msg, validator=None, default_func=None):
    is_location = False
    current_val = getattr(config, prop_name)
    default_val = current_val
    if (not default_val) and default_func:
        default_val = default_func()
    while (not is_location):
        location = sadm_prompt.prompt(msg, default_val)
        if location and (location.lower() == 'none'):
            location = None
        if validator is None:
            is_location = make_dir(location)
        else:
            is_location = validator(location)
        if (not is_location):
            eprintc('%s is invalid.\n' % location, ERROR_COLOR)
    setattr(config, prop_name, location)

def _validate_smart_repo(url):
    if url and (url.find('//') > -1):
        return url.startswith('bzr+ssh:')
    return True

_def_site_repo = False
def _get_default_site_repo_root():
    print('in gdsrr')
    if _def_site_repo != False:
        print('returning %s' % str(_def_site_repo))
        return _def_site_repo
    if config.host_is_on_internal_network():
        return "bzr+ssh://10.10.10.100/reporoot"
    return None

def _check_locations():
    print('''
Sadm normally stores sandboxes under <your home dir>/sandboxes. You can
override this if you like. Paths with spaces in them are not recommended.
''')
    _check_loc(config, 'sandbox_container_folder', 'Where should sandboxes be stored?')
    print('''
Source code should be stored in a repo root close to, or on, the local machine.
A common location is <your home dir>/reporoot. If this is a VM, you may want
to point to a folder shared from the host OS.
''')
    _check_loc(config, 'working_repo_root', 'Where is your working (local) bzr repository?')
    printc('\nUsing master repo at ' + PARAM_COLOR + config.master_repo_root + NORMTXT + '.')
    print('''
Your local repo root can optionally pull from a site repo root that mirrors the
master repo root in the cloud as an optimization.
''')
    if os.path.isfile(vcs.VCS_CONF_PATH):
        try:
            conf = ConfigParser.ConfigParser()
            with open(vcs.VCS_CONF_PATH, 'r') as f:
                conf.readfp(f)
            if conf.has_section(vcs.SETTINGS_SECTION):
                try:
                    x = conf.get(vcs.SETTINGS_SECTION, vcs.SITE_REPO_ROOT_KEY)
                    global _def_site_repo
                    _def_site_repo = x
                    config.site_repo_root = x
                except:
                    pass
        except:
            pass
    _check_loc(config, 'site_repo_root',
            'If you are using a site repo, where is it (e.g., sitebzr/reporoot or "none")?',
            _validate_smart_repo, default_func=_get_default_site_repo_root)
    if config.site_repo_root:
        config.site_repo_root.replace('\\', '/')
        if not config.site_repo_root.startswith('bzr+ssh://'):
            config.site_repo_root = 'bzr+ssh://' + config.site_repo_root
        if not config.site_repo_root.endswith('/reporoot'):
            config.site_repo_root = config.site_repo_root.rstrip('/') + '/reporoot'
    # Persist these same settings to a conf file that the plugin can read.
    conf = ConfigParser.ConfigParser()
    conf.add_section(vcs.SETTINGS_SECTION)
    conf.set(vcs.SETTINGS_SECTION, vcs.MASTER_REPO_ROOT_KEY, config.master_repo_root)
    conf.set(vcs.SETTINGS_SECTION, vcs.LOCAL_REPO_ROOT_KEY, config.working_repo_root)
    conf.set(vcs.SETTINGS_SECTION, vcs.SITE_REPO_ROOT_KEY, config.site_repo_root)
    with open(vcs.VCS_CONF_PATH, 'w') as fp:
        conf.write(fp)

def _check_auto_update():
    originalValue = bool(config.auto_update)
    if config.is_canonical_machine:
        print('\nSadm will be scheduled to auto-update itself each night.')
        config.auto_update = True
    else:
        config.auto_update = sadm_prompt.prompt_bool('\nSchedule %s to auto-update itself each night?' % APP_CMD, _get_prompt_bool_repr(config.auto_update))
    if config.auto_update != originalValue:
        taskName = 'update %s' % APP_CMD
        cmd = '%s --no-color --auto-confirm update' % APP_INVOKE
        sched = Schedule(DEFAULT_UPDATE_TIME)
        Schedule.apply_to_arbitrary_command(cmd, taskName, sched, removeOnly=(not config.auto_update))

def _check_automated_builds():
    if not config.is_canonical_machine:
        config.build_queue_schedule = 'never'
    originalCfg = str(config.allow_official_builds) + config.build_queue_schedule
    if config.is_canonical_machine:
        print('''
On canonical build machines, official builds are allowed. However, some such
machines may not wish to do them, since they can complicate the scheduling of
continuous builds...
''')
        config.allow_official_builds = sadm_prompt.prompt_bool('Allow official builds?', _get_prompt_bool_repr(config.allow_official_builds))
    else:
        config.allow_official_builds = False
    email_list = ''
    if config.allow_official_builds:
        config.archiveRepo = sadm_prompt.prompt('\nArchive repo url', config.archiveRepo)
    if config.is_canonical_machine:
        config.build_queue_url = prompt('\nBase url for build queue', config.build_queue_url)
        queueSched = sadm_prompt.prompt('\nCheck build queue for new requests ("never" to disable)', config.build_queue_schedule)
        queueSched = Schedule(queueSched)
        email_list = sadm_prompt.prompt('\nEmails to notify of official build results (comma-separated)', config.email_list)
    else:
        queueSched = Schedule("never")
    if email_list:
        if type(email_list).__name__ == 'list':
            config.email_list = email_list
        else:
            config.email_list = [x for x in email_list.split(',').strip()]
            config.email_list.append(config.mailto)
    else:
        config.email_list = [config.mailto]
    newCfg = str(config.allow_official_builds) + str(queueSched)
    if newCfg != originalCfg:
        config.build_queue_schedule = str(queueSched)
        taskName = "check official build queue"
        cmd = '%s service' % APP_INVOKE
        Schedule.apply_to_arbitrary_command(cmd, taskName, queueSched, removeOnly=(not config.allow_official_builds))

def _check_autoget_dev():
    oldAutoUpdateDev = bool(config.auto_update_dev_sandboxes)
    if config.machine_role.startswith('dev'):
        print('''
If you have a lot of dev sandboxes, it can be useful to have them updated
automatically before you come in in the morning. This guarantees that you are
never working off of stale versions of the code, and it makes unexpected merge
conflicts less likely to occur when you check in. However, it can also be
problematic, because code that you mostly have working when you go home one
day can be merged into a different state when you come in the next day.
''')
        config.auto_update_dev_sandboxes = sadm_prompt.prompt_bool('Auto-get code in *dev before work each morning?', _get_prompt_bool_repr(config.auto_update_dev_sandboxes))
    newAutoUpdateDev = bool(config.auto_update_dev_sandboxes)
    if oldAutoUpdateDev != newAutoUpdateDev:
        taskName = "get dev sandboxes"
        cmd = '%s get *dev' % APP_INVOKE
        sched = Schedule(DEFAULT_AUTO_GET_TIME)
        Schedule.apply_to_arbitrary_command(cmd, taskName, sched)

_NAME_PLUS_ADDR_PAT = re.compile(r"\s*(.+?)\s*<([a-z].*@.+)>\s*")
_ADDR_ONLY_PAT = re.compile(r"\s*([a-z].*@.+)\s*")
def _check_whoami():
    email, code = run('bzr whoami', acceptFailure=True)
    if (not code) and email:
        m = _NAME_PLUS_ADDR_PAT.match(email)
        if m:
            email = m.group(2)
        else:
            m = _ADDR_ONLY_PAT.match(email)
            if m:
                email = m.group(1)
    if not email:
        config.mailto = sadm_prompt.prompt('\nYour email address?', config.mailto)
    else:
        config.mailto = email
    if config.mailto:
        if Schedule.mailto is None:
            Schedule.mailto = config.mailto
        # If we failed to get email from bzr, tell bzr about our identity as well.
        if code:
            run('bzr whoami %s' % email)

def _check_continuous_activity_window():
    cmd = '%s --no-color next' % APP_INVOKE
    sched = DEFAULT_NEXT_SCHEDULE
    rng = ''
    defValue = config.default_continuous_range
    if not defValue:
        if config.is_canonical_machine:
            defValue = "0400 to 2200"
        else:
            defValue = '*'
    print('''
Continuous builds can be constrained to an activity window so that during off
hours, system resources can be used elsewhere. This is important if you plan to
run performance tests, among other things.
''')
    rng = sadm_prompt.prompt('Hours for running continuous sandboxes (e.g., 0100 to 2200; "*" = all)', defValue)
    if rng and (rng == '*' or rng == 'all'):
        rng = ''
    config.schedule_continuous_manually = sadm_prompt.prompt_bool('\nSchedule continuous sandboxes manually?', _get_prompt_bool_repr(config.schedule_continuous_manually))
    if not config.schedule_continuous_manually:
        # Remove any manually-scheduled, continuous sandboxes from the schedule.
        unschedule = [sb for sb in Sandbox.list() if (sb.get_sandboxtype().get_should_schedule() and sb.schedule)]
        for sb in unschedule:
            sb.schedule = None
            sb.applySchedule()
    # Only allow overriding standard interval on non-canonical machines.
    if not config.is_canonical_machine:
        if config.continuous_interval:
            # Make sure we only have the interval part, not the range.
            sched = str(Schedule(config.continuous_interval))
        sched = sadm_prompt.prompt('\nIf idle, start next continuous sandbox ("never" to disable)', sched)
    # Again, make sure we only have the interval part.
    if sched:
        sched = Schedule(sched)
        if sched.is_periodic():
            sched = 'every ' + sched.every
        else:
            sched = 'never'
    else:
        sched = DEFAULT_NEXT_SCHEDULE
    # Add the range part on, regardless of where the interval came from.
    if rng:
        if sched != 'never':
            sched += ", " + rng
        else:
            rng = ''
    sched = Schedule(sched)
    Schedule.apply_to_arbitrary_command(cmd, 'run next continuous sandbox', sched, removeOnly=(config.schedule_continuous_manually))
    if rng:
        rng = '%s to %s' % (sched.range[0], sched.range[1])
    if not rng:
        print('''
Performance tests are disallowed on this box, since unconstrained continuous
builds might invalidate results.
''')
    config.default_continuous_range = rng


def _check_perf_test_config():
    rng = config.default_continuous_range
    if not rng:
        return
    print('''
In order to run performance tests, you must be prepared to save result data
in a JDBC database. Normally, the db is on db1.example.com, the
''')
    defValue = config.perf_log_db_url
    if defValue == STD_PERFTEST_DBURL:
        defValue = 'std'
    x = sadm_prompt.prompt('URL for perf test db ("std", custom value, or "none" to disable)', defValue)
    if x:
        if x == 'std':
            x = STD_PERFTEST_DBURL
        elif x.find('%s') == -1:
            x = None
    changed = (str(config.perf_log_db_url) != str(x))
    config.perf_log_db_url = x
    if x:
        x = sadm_prompt.prompt('Password for perf test db', config.perf_log_password)
        if x != config.perf_log_password:
            changed = True
            config.perf_log_password = x
    if changed:
        if config.perf_log_password and config.perf_log_db_url:
            if os.name == 'nt':
                printc('You need to manually set an environment variable:', WARNING_COLOR)
                print('    PERFLOG_URL=%s' % (config.perf_log_db_url % config.perf_log_password))
            else:
                printc('You need to add this line to ~/.bashrc and/or crontab:', WARNING_COLOR)
                print('    export PERFLOG_URL="%s"' % (config.perf_log_db_url % config.perf_log_password))
        else:
            if os.name == 'nt':
                printc('You need to manually undefine the PERFLOG_URL environment variable.', WARNING_COLOR)
            else:
                printc('You need to remove the export PERFLOG_URL= line from ~/.bashrc and/or crontab.', WARNING_COLOR)

def _check_role():
    print('''
Some sadm features are useful only on dedicated build machines. Others are
mainly interesting to developers. To simplify setup and program behaviors,
please choose the role that best describes this machine:

    dev      -- This is the primary machine of a developer or tester.
    devguest -- This is a VM hosted on a dev machine. It is used to test or
                cross-compile code developed on the dev machine.
    build    -- This machine is dedicated to automated builds. It may or may not
                be canonical.
    test     -- This machine is dedicated to automated testing. (Unlike a build
                machine, it may not have lots of compile tools installed, and
                should not service requests from the build queue.)
    custom   -- None of the above apply.
''')
    while True:
        machine_role = sadm_prompt.prompt('Machine role?', config.machine_role)
        if machine_role:
            machine_role = machine_role.strip().lower()
        if machine_role in ['custom','dev','devguest','build','test']:
            config.machine_role = machine_role
            return

def _check_writable_app_folder():
    tmp = os.path.join(APP_FOLDER, ".tmp")
    try:
        with open(tmp, 'w') as f:
            f.write('this is just a test to see if sadm has write access to its own folder')
            f.close()
            time.sleep(0.1)
            os.remove(tmp)
        print('\nSadm folder is writable, as it should be.')
    except:
        eprintc('''
Sadm must be installed to a folder where ordinary processes for the current user
have write access. Otherwise it cannot update itself.''', ERROR_COLOR)
        sys.exit(1)

def _check_app_checked_out():
    if not os.path.isdir(os.path.join(APP_FOLDER, '.bzr')):
        eprintc('''
Sadm has not been installed with a bzr checkout command. This will prevent sadm
from updating itself. Recommended install command for sadm is:
    bzr co --lightweight %s/sadm/built.%s/trunk <installdir>''' % (
                DEFAULT_MASTER_REPOROOT, buildinfo.get_natural_platform_variant()),
                                                                ERROR_COLOR)
        sys.exit(1)
    else:
        print('\nSadm has been installed correctly with a bzr checkout.')

def _check_ssh_keys(reporoot=None):
    if not config.ssh_keys_ok:
        if reporoot is None:
            _check_ssh_keys(config.master_repo_root)
            if config.ssh_keys_ok and config.site_repo_root:
                # Temporarily change so recursion will work.
                config.ssh_keys_ok = False
                config.ssh_keys_ok = _check_ssh_keys(config.site_repo_root)
        else:
            command = 'bzr info {0}/trunk/buildscripts/code'.format(reporoot)
            proc = subprocess.Popen(command,
                                    shell=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            start = time.time()
            end = time.time() + 10
            while True:
                result = proc.poll()
                if result is not None:
                    print('\nLogin to %s with ssh keys is working.' % reporoot)
                    config.ssh_keys_ok = True
                    return
                if time.time() >= end:
                    eprintc('\nLogin to %s with ssh keys seems broken.' % reporoot, ERROR_COLOR)
                    print('\n  This is normally a network error. To debug the issue run the following')
                    print('  command to validate proper communication:')
                    print('\n  ' + command)
                    proc.kill()
                    sys.exit(1)
                time.sleep(0.25)

def _check_uac():
    if os.name == 'nt':
        if config.uac_disabled is None:
            if user_has_admin_privileges():
                config.uac_disabled = sadm_prompt.prompt_bool(
'''You're currently running in a command prompt with elevated privileges. Is
this because you disabled UAC permanently?''', 'y')
            else:
                config.uac_disabled = False

def _print_and_run(cmd):
    print(cmd)
    os.system(cmd)

def do_setup(only_if_needed, *args):
    try:
        if only_if_needed and config.persisted:
            return
        _check_app_checked_out()
        _check_writable_app_folder()
        _check_whoami()
        _check_role()
        _check_canonical()
        _check_required_tools()
        _check_locations()
        _update_bzr_plugin()
        _set_bzr_default_ignore()
        _check_ssh_keys()
        _check_uac()
        _check_remoting_info()
        # TODO fix this stuff for windows
        #_check_auto_update()
        #_check_automated_builds()
        #_check_autoget_dev()
        #fix_ _check_continuous_activity_window()
        #fix_ _check_perf_test_config()
        print('')
        config.save()
        log('setup')
    except KeyboardInterrupt:
        eprintc('\n\nConfiguration not saved.\n', WARNING_COLOR)
        pass
    except SystemExit:
        pass
    except:
        traceback.print_exc()
    try:
        _setup_convenience_funcs()
    except:
        traceback.print_exc()

if __name__ == '__main__':
    _setup_convenience_funcs()
