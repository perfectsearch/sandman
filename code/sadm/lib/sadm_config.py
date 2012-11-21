#
# $Id: sadm_config.py 10561 2011-07-06 17:54:37Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys, os, re, socket, platform
from sadm_constants import *
from sadm_util import *
from check_tools import *

_KEY_VERSION_SUFFIX = '-version'

_CONFIG_FILE = APP_FOLDER + '/sadm.conf'
_REQUIRED_TOOLS = {}
_REQUIRED_TOOLS['bzr'] = ReqTool('bzr', '2.3', ['windows', 'linux'], 'bzr --version')
if os.name == 'nt':
    _REQUIRED_TOOLS['taskkill'] = ReqTool('taskkill', None, ['windows'], 'taskkill /?')
    _REQUIRED_TOOLS['tasklist'] = ReqTool('tasklist', None, ['windows'], 'tasklist /?')
    #_REQUIRED_TOOLS['schtasks'] = ReqTool('schtasks', None, ['windows'], 'schtasks /?')
else:
    #_REQUIRED_TOOLS['crontab'] = ReqTool('crontab', None, ['linux'], 'crontab -l',)
    _REQUIRED_TOOLS['ps'] = ReqTool('ps', None, ['linux'], 'ps --version')

def _read_val(txt):
    txt = txt.strip()
    if txt.lower() in ['1','0','true','yes','false','no']:
        return (txt.lower() in ['1','true','yes'])
    return txt

_INTERNAL_NET_HOST = '10.10.10.20'
_INTERNAL_NET_PORT = 22222
_HOST_IS_ON_INTERNAL_NETWORK = -1
def _check_whether_host_is_on_internal_network():
    global _HOST_IS_ON_INTERNAL_NETWORK
    if _HOST_IS_ON_INTERNAL_NETWORK == -1:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(2.5)
            sock.connect((_INTERNAL_NET_HOST, _INTERNAL_NET_PORT))
            _HOST_IS_ON_INTERNAL_NETWORK = 1
        except:
            _HOST_IS_ON_INTERNAL_NETWORK = 0
    return bool(_HOST_IS_ON_INTERNAL_NETWORK)

class Config:
    def __init__(self, txt=None):
        self._persisted = False
        self.load(txt)
    def set_complete_perf_db_url(self, value):
        self.perf_log_db_url = None
        self.perf_log_password = None
        if value:
            i = value.find('password=')
            if i > -1:
                pwd = value[i+9:]
                j = pwd.find('&')
                if j > -1:
                    pwd = pwd[0:j]
            self.perf_log_db_url = value.replace('password=%s' % pwd, 'password=%s')
            self.perf_log_password = pwd
    def allow_perf_tests(self):
        return bool(self.perf_log_db_url) and bool(self.perf_log_password) and bool(self.default_continuous_range)
    def get_complete_perf_db_url(self):
        x = self.perf_log_db_url
        if x:
            if x.find('%s') > -1:
                pwd = self.perf_log_password
                if not pwd:
                    pwd = ''
                x = x % str(pwd)
        else:
            x = None
        return x
    def comes_from_disk(self):
        return self._persisted
    def could_be_canonical_machine(self):
        if config.machine_role == 'build' or config.machine_role == 'custom':
            u = platform.uname()
            if os.name == 'nt':
                return (u[2] == '2008ServerR2' or u[2] == '2008Server')
            elif u[0] == 'Linux':
                return (u[2].find('.el6') > -1) or (u[2].find('.el5') > -1)
        return False
    def load(self, txt = None):
        self.machine_role = 'dev'
        self.is_canonical_machine = False
        self.auto_add_sandboxes = False
        self.branches_to_auto_add = None
        self.memcheck_available = None
        self.run_mem_test = None
        self.perf_log_db_url = None
        self.perf_log_password = None
        self.set_complete_perf_db_url(os.getenv('PERFLOG_DBURL'))
        self.auto_update = True
        self.auto_update_dev_sandboxes = None
        self.allow_official_builds = None
        self.continuous_interval = None
        self.build_queue_url = DEFAULT_BUILD_QUEUE
        self.automated_vcs_user = None
        self.dev_vcs_user = None
        self.sandbox_container_folder = SANDBOXES
        self.mailto = None
        self.default_continuous_range = None
        self.schedule_continuous_manually = False
        self.path = None
        self.hioin = None # not intended for public consumption; wrapped by host_is_on_internal_network()
        self.test_mode = False
        self.email_list = None
        self.username = None
        self.ipaddr = None
        self.ssh_port = None
        self.remote_desktop_port = None
        self.remoting_instructions = None
        self.working_repo_root = LOCAL_REPOROOT
        self.site_repo_root = None
        self.master_repo_root = DEFAULT_MASTER_REPOROOT
        self.ssh_keys_ok = None
        self.uac_disabled = None
        self.username_for_remote_access = None
        if txt == None:
            if os.path.isfile(_CONFIG_FILE):
                txt = read_file(_CONFIG_FILE)
        if txt:
            self._persisted = True
            lines = [l.strip() for l in txt.split('\n') if l.find('=') > -1 and not l.strip().startswith('#')]
            for l in lines:
                i = l.find('=')
                key = l[0:i].lower().strip()
                value = _read_val(l[i+1:])
                if hasattr(self, key):
                    setattr(self, key, value)
        if not self.build_queue_url.endswith('/'):
            self.build_queue_url += '/'
        if self.automated_vcs_user is None:
            if self.host_is_on_internal_network(False):
                self.automated_vcs_user = 'buildmaster'
            else:
                self.automated_vcs_user = DEFAULT_VCS_USER
        if self.email_list:
            self.email_list = self.email_list.split(',')
    def needs_remoting_info(self):
        return not self.machine_role.startswith('dev')
    def needs_automated_vcs_user(self):
        return bool(self.allow_official_builds)
    def host_is_on_internal_network(self, autosave = True):
        if self.hioin is None:
            self.hioin = _check_whether_host_is_on_internal_network()
            if autosave:
                self.save()
        return self.hioin
    def _save_item(self, name, lines):
        val = getattr(self, name)
        if not (val is None):
            val = str(val)
            if val != '0.0':
                lines.append(name + '=' + str(val))
    def save(self, f = None):
        lines = []
        for item in dir(self):
            # Don't persist anything hidden, and don't persist the perfLog
            # stuff, since that has to be reflected in an environment variable
            # to be useful.
            if (item[0] != '_') and (not item.startswith('perf_log')):
                member = getattr(self, item)
                memberType = type(member)
                if memberType in [STRING_TYPE, BOOL_TYPE]:
                    self._save_item(item, lines)
        lines.sort()
        if f is None:
            save(_CONFIG_FILE, '\n'.join(lines))
        else:
            f.write('\n'.join(lines))
    def tool_version_ok(self, tool):
        ret = verify_command_in_path(_REQUIRED_TOOLS[tool], quiet=True)
        return ret == 0
    def scheduling_supported(self):
        if os.name == 'nt':
            return self.tool_version_ok('tasklist') and self.tool_version_ok('taskkill') and self.tool_version_ok('schtasks')
        else:
            return self.tool_version_ok('ps') and self.tool_version_ok('crontab')

config = Config()
