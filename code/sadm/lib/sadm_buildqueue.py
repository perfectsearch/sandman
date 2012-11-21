#!/usr/bin/env python
#
# $Id: sadm_buildqueue.py 10486 2011-07-05 17:59:51Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import urllib2
import xml.dom.minidom
import datetime

from sadm_config import *
# From buildscripts...
from dateutils import *

def _get_friendly_time(when):
    if not when:
        return ''
    today = datetime.datetime.today()
    if (when.day == today.day) and (when.month == today.month) and (when.year == today.year):
        return 'today at ' + when.strftime('%I:%M %p')
    return when.strftime('%a, %d %b at %I:%M %p')

class OfficialBuildRequest(object):
    def __init__(self):
        self.request_id = ""             #Not Null
        self.requested_time = None         #Not Null
        self.requester  = ""             #Not Null
        self.component = ""              #Not Null
        self.branch = ""                 #Not Null
        self.style = ""                  #Not Null
        self.platform = ""               #Not Null
        self.bitness = ""                #Not Null
        self.requested_machine = ""      #Not Null
        self.assigned_machine = ""       #Nullable
        self.assigned_time = None        #Nullable
    def get_friendly_assigned_time(self):
        return _get_friendly_time(self.assigned_time)
    def get_friendly_request_time(self):
        return _get_friendly_time(self.requested_time)
    def get_sandbox_name(self):
        return '%s.%s.%s' % (self.component, self.branch, self.style)
    def __str__(self):
        ctx = '%s %s %s' % (self.get_sandbox_name(), self.platform, self.bitness)
        ret = self.request_id.ljust(5) + ctx
        ret += '\n' + INDENT + INDENT + '...requested by ' + self.requester + ' ' + self.get_friendly_request_time()
        ret += '\n' + INDENT + INDENT
        if self.assigned_machine:
            ret += '...assigned to ' + self.assigned_machine + ' ' + self.get_friendly_assigned_time()
        else:
            if self.requested_machine and self.requested_machine != '*':
                ret += '...waiting to be assigned to ' + self.requested_machine
            else:
                ret += '...not yet assigned'
        return ret

def _get_xml_text(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def _assign(req, tag, dom, member=None):
    if member is None:
        member = tag
    tags = dom.getElementsByTagName(tag)
    if tags:
        val = _get_xml_text(tags[0].childNodes).strip()
        setattr(req, member, val)
        return bool(val)

def _toLocal(t):
    d = datetime.datetime(int(t[0:4]), int(t[5:7]), int(t[8:10]), int(t[11:13]), int(t[14:16]), int(t[17:19]), tzinfo=UTC)
    return d.astimezone(LOCAL_TIMEZONE)

def get_build_requests(*args):
    response = ''
    url = config.build_queue_url + LIST_QUEUE_PAGE
    if len(args) > 0:
        url += "&platform=%s" % args[0]
        if len(args) > 1:
            url += "&bitness=%s" % args[1]
    response = urllib2.urlopen(url).read()
    dom = xml.dom.minidom.parseString(response)
    requests = dom.getElementsByTagName("request")
    requestObjects = []
    for x in requests:
        temp = OfficialBuildRequest()
        _assign(temp, 'id', x, 'request_id')
        if _assign(temp, 'requested_time', x):
            temp.requested_time = _toLocal(temp.requested_time)
        _assign(temp, 'requester', x)
        _assign(temp, 'project', x, 'component')
        _assign(temp, 'branch', x)
        _assign(temp, 'build_group', x, 'style')
        _assign(temp, 'platform', x)
        _assign(temp, 'bitness', x)
        _assign(temp, 'requested_machine', x)
        _assign(temp, 'assigned_machine', x)
        if _assign(temp, 'assigned_time', x):
            temp.assigned_time = _toLocal(temp.assigned_time)
        requestObjects.append(temp)
    return requestObjects

if __name__ == '__main__':
    print('\n'.join([str(req) for req in get_build_requests()]))
