#
# $Id: sadm_constants.py 10580 2011-07-06 21:42:11Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import os, re, sys
# From buildscripts...
from textui.ansi import *

_x = os.path.dirname(os.path.abspath(__file__))
APP_FOLDER = os.path.abspath(os.path.join(_x, '..'))
del(_x)
BUILDSCRIPTS_FOLDER = os.path.join(APP_FOLDER, 'buildscripts')
if not os.path.isdir(BUILDSCRIPTS_FOLDER):
    BUILDSCRIPTS_FOLDER = os.path.abspath(os.path.join(APP_FOLDER, '..', 'buildscripts'))
APP_FNAME = os.path.basename(__file__).replace('_constants', '').replace('.pyc', '.py')
APP_PATH = os.path.join(APP_FOLDER, APP_FNAME)
APP_CMD = os.path.splitext(APP_FNAME)[0]
APP_TITLE = 'Sandbox Admin'
FQPYTHON = sys.executable
if FQPYTHON.find(' ') > -1:
    FQPYTHON = '"%s"' % FQPYTHON
APP_INVOKE = '%s "%s"' % (FQPYTHON, APP_PATH)
APP_VERSION = '2.0'

if os.name == 'nt':
    EOL = '\r\n'
else:
    EOL = '\n'
    # On RHEL and CentOS, we need to invoke sadm differently in the scheduler,
    # due to the way the environment is configured when cron runs.
    import platform
    x = platform.uname()
    if x[0] == 'Linux' and x[2].find('.el') > -1:
        APP_INVOKE = 'bash -l "%s"' % APP_PATH[0:-3]
INDENT = '    '
ANT_STYLE = 'ant'
CMAKE_STYLE = 'cmake'
ARBITRARY_STYLE = 'arbitrary'
ANT_SCRIPT = 'build.xml'
CMAKE_SCRIPT = 'CMakeLists.txt'
ARBITRARY_SCRIPT = 'make.py'
CTESTTESTFILE_CMAKE = 'CTestTestfile.cmake'
CTESTCUSTOM_CMAKE = 'CTestCustom.cmake'
ALT_CTESTCUSTOM_CMAKE = 'CTestCustom.ctest'
STEER_SCRIPT = 'steer.cmake'
STEERDEFS_SCRIPT = 'defs.cmake'
CHECKEDIN_TEMPLATE_SUFFIX = '-template'
LOGS_FOLDER = 'Testing/Temporary'
CTESTCONFIG_CMAKE = 'CTestConfig.cmake'
INITIAL_CMAKE_CACHE = 'InitialCMakeCache.txt'
CONTINUOUS_FOLDER = 'continuous'
OFFICIAL_FOLDER = 'official'
DAILY_FOLDER = 'daily'
NIGHTLY_FOLDER = 'nightly'
ECLIPSE_METADATA_ARCHIVE = 'metadata.tar.gz'
ECLIPSE_METADATA_FOLDER = '.metadata'
ANT_ROOTPROP_PAT = re.compile(r'\s*property\.(code|build)\.root\s*=.*')
TEST_SCRIPTS_PAT = re.compile(r'(.*)Tests?\.cmake(' + CHECKEDIN_TEMPLATE_SUFFIX + ')?')
HOOKS_PAT = re.compile(r'(pre|post)(get|configure|build|test|publish)\.(cmake|py)(' + CHECKEDIN_TEMPLATE_SUFFIX + ')?')
INCLUDE_TEST_SCRIPTS_PAT = re.compile(r'^\s*include\s*\(\s*"(.*?Tests\.cmake)"\s*\)', re.MULTILINE | re.DOTALL)
DEV_FOLDER = 'dev'
PERF_FOLDER = 'perf'
STD_LABEL = '*'
STD_VARIANTS = [CONTINUOUS_FOLDER, OFFICIAL_FOLDER, DEV_FOLDER]
INFO_FOLDER = '.info'
CODE_FOLDER = 'code'
BUILD_FOLDER = 'build'
TEMPLATES_FOLDER = os.path.join(APP_FOLDER, 'templates')
CYGWIN = False
if os.name == 'nt':
    HOMEDIR = os.path.join(os.getenv("HOMEDRIVE"), os.getenv("HOMEPATH"))
else:
    HOMEDIR = os.path.abspath(os.getenv("HOME"))
if HOMEDIR.find('cygwin') > -1:
    HOMEDIR = os.getenv("USERPROFILE")
    CYGWIN = True
SANDBOXES = os.path.join(HOMEDIR, "sandboxes").replace('\\', '/')
LOCAL_REPOROOT = os.path.join(HOMEDIR, "reporoot").replace('\\', '/')
TEST_SANDBOXES = HOMEDIR #os.path.abspath(os.path.join(APP_FOLDER, "../../test/sadm/test-sandboxes"))
CMD_LOG = HOMEDIR + '/' + APP_CMD + '-log.txt'

DEFAULT_BRANCH = "trunk"
DEFAULT_REPO = "share"
DEFAULT_REPO_PREFIX = "https://subversion.assembla.com/svn/"
DEFAULT_ARCHIVE_REPO = "deliver"
DEFAULT_VCS_USER = "build" ## TODO fix consts
DEFAULT_START_TIME = "04:00:00 GMT"
DEFAULT_DROP_METHOD = "http"
DEFAULT_DROP_SITE = "bazaar.example.com" ## TOD fix consts
DEFAULT_MASTER_REPOROOT = "bzr+ssh://bazaar.example.com/reporoot" ## TODO fix consts
DEFAULT_DROP_URL = "/submit.php?project=^[prj]"
DEFAULT_BUILD_QUEUE = 'https://' + DEFAULT_DROP_SITE + '/bdash/'
LIST_QUEUE_PAGE = 'content/pickled_list'
SUBMIT_REQUEST_PAGE = 'content/build_request'
ASSIGN_QUEUE_PAGE = 'content/assign_machine'
DEFAULT_UPDATE_TIME = 'at 0000'
DEFAULT_AUTO_GET_TIME = 'at 0730'
DEFAULT_NEXT_SCHEDULE = 'every 6 m'

KNOWN_PSA_PROJECTS = ['all', 'core', 'product'] ## TODO Fix me

STD_PERFTEST_DBURL = 'jdbc:mysql://db1.example.com/perftest?user=perftest-writer&password=%s' ## TODO fix me

STRING_TYPE = type('')
LIST_TYPE = type([])
BOOL_TYPE = type(True)
