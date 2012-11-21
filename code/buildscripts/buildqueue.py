import tempfile
import pickle
import time
import os
import shutil
import datetime
import subprocess

def _get_friendly_time(when):
    if not when:
        return ''
    today = datetime.datetime.today()
    when = datetime.datetime.fromtimestamp(when)
    if (when.day == today.day) and (when.month == today.month) and (when.year == today.year):
        return 'today at ' + when.strftime('%I:%M %p')
    return when.strftime('%a, %d %b at %I:%M %p')

class BuildRequest(object):
    def __init__(self, requester, component, branch, style, platform, bitness, requested_machine, clean):
        self.request_time = time.time()
        self.requester = requester
        self.component = component
        self.branch = branch
        self.style = style
        self.platform = platform
        self.bitness = bitness
        self.requested_machine = requested_machine
        self.clean = clean
        self.assigned_machine = ''
        self.assigned_time = None
    def assign_machine(self, machine):
        self.assigned_machine = machine
        self.assigned_time = time.time()
    def get_sandbox_name(self):
        if self.bitness == '32':
            return '%s32.%s.%s' % (self.component, self.branch, self.style)
        return '%s.%s.%s' % (self.component, self.branch, self.style)
    def _get_friendly_assigned_time(self):
        return _get_friendly_time(self.assigned_time)
    def _get_friendly_request_time(self):
        return _get_friendly_time(self.request_time)
    def __eq__(self, request):
        return (self.branch == request.branch and self.component == request.component and self.platform == request.platform 
               and self.bitness == request.bitness and self.style == request.style and self.requested_machine == request.requested_machine)
    def __str__(self):
        ret = '%s.%s.%s %s %s' % (self.component, self.branch, self.style, self.platform, self.bitness)
        ret += '\n\t...requested by %s %s\n\t' % (self.requester, self._get_friendly_request_time())
        if self.assigned_machine:
            ret += '...assigned to %s %s' % (self.assigned_machine, self._get_friendly_assigned_time())
        else:
            if self.requested_machine and self.requested_machine != '*':
                ret += '...waiting to be assigned to %s' % self.requested_machine
            else:
                ret += '...not yet assigned'
        return ret

def get_build_request_info(reporoot):
    cmd = 'bzr cat %s' % os.path.join(reporoot, 'buildqueue', 'buildqueue.txt')
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = p.stdout.read()
    if len(output) > 0:
        return pickle.loads(output)
    return []

def add_build_request(reporoot, request):
    remove_requests(reporoot)
    requests = get_build_request_info(reporoot)
    exists = False
    for req in requests[:]:
        if request == req and req.assigned_time == None:
            exists = True
        if time.time() - req.request_time > 43200:
            requests.remove(req) 
    if not exists:
        requests.append(request)
        _save(reporoot, requests)
        return 'Request added.'
    return 'Redundant request not added.'

def remove_requests(requests, request=None):
    for req in requests[:]:
        if (request is not None and request == req) or (time.time() - req.request_time > 43200):
            requests.remove(req)

def _save(reporoot, requests):
    tempdir = tempfile.mkdtemp()
    cmd = 'bzr co --lightweight %s %s' % (os.path.join(reporoot, 'buildqueue').replace('\\', '/'), tempdir)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = p.stdout.read()
    pklf = os.path.join(tempdir, 'buildqueue.txt')
    pkl_file = open(pklf, 'w')
    pickle.dump(requests, pkl_file)
    pkl_file.close()
    cmd = 'bzr ci %s -m "Updating requets."' % tempdir
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = p.stdout.read()
    shutil.rmtree(tempdir)

def assign_build_machine(reporoot, request, machine):
    remove_requests(reporoot)
    requests = get_build_request_info(reporoot)
    for req in requests:
        if req.assigned_time is None and req == request:
            req.assign_machine(machine)
            break
    _save(reporoot, requests)
