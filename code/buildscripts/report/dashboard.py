import os
import time
from collections import namedtuple
import shutil

import buildinfo
import dateutils

from eval_summary import *

SUMMARY_FILE = 'summary.txt'
STATUS_LOG = 'status-log.txt'

CONTINUOUS = 'CONTINUOUS'
OFFICIAL = 'OFFICIAL'
EXPERIMENTAL = 'EXPERIMENTAL'

#Revnos = namedtuple('Revnos', 'experimental continuous official')
Status = namedtuple('Status', 'result reasons when')
#StartTimes = namedtuple('StartTimes', 'experimental continuous official')

def _aggregate_status(summaries):
    reasons = []
    when = 0
    for s in summaries:
        if when < s.get_end_time():
            when = s.get_end_time()
        hostdescrip = s.os + ' ' + s.version + ' ' + s.bitness
        # To keep this from becoming too verbose, only display target if
        # it's different from the one implied by the OS.
        implied_variant = buildinfo.fuzzy_match_platform_variant(s.os + ' ' + s.bitness)
        if implied_variant != s.tpv:
            hostdescrip += ' targeting %s' % (s.os + ' ' + s.version + ' ' + s.bitness, s.tpv)
        reason = '%s (%s) on %s (%s): %s.' % (s.build_id, s.style, s.host, hostdescrip, s.failure_reason)
        reasons.append(reason)
    return Status(summaries[0].get_imputed_result(), reasons, when)

class Dashboard:
    def __init__(self, root_folder):
        self._root = os.path.abspath(root_folder)
        self._hosts = None
        self._pretend_time = None
        self._data = None
        self._code_revnos = None
        self._start_times = None
        self._hosts
        self._hosts_by_revno = None
        self._hosts_by_style = None
        self._status = None
        self._build_groups = None
        self._load_all = False
        self._horizon_seconds = MAX_RETAINED_SECONDS
        self.debug = False
    def get_horizon_seconds(self):
        '''
        How far back, maximum, should the dashboard look as it's loading
        history? If load_all property is False, this limit is rarely hit,
        since we stop as soon as we are no longer looking at results for the
        latest code revision. (Default = 2 weeks)
        '''
        return self._horizon_seconds
    def set_horizon_seconds(self, value):
        self._horizon_seconds = int(value)
    def get_load_all(self):
        '''
        Should the dashboard load all data back to its retention limit, or only
        enough to calculate current status? (Default = load minimum)
        '''
        return self._load_all 
    def set_load_all(self, value):
        self._load_all = bool(value)
    def get_root(self):
        return self._root
    def get_status(self):
        self._load_if_needed()
        # Lazy calculation.
        if self._status is None:
            if self.debug: print('Calculating status for %s.' % self._root)
            if not self._data:
                if self.debug: print('No data loaded, so status is UNKNOWN')
                self._status = Status(EvalResult.UNKNOWN, ['No machines have reported results recently.'], 0)
            else:
                code_revnos = self.get_code_revnos()
                start_times = self.get_start_times()
                if self.debug: print('code_revnos = ' + str(code_revnos))
                # First, look at most recent revnos for canonical machines.
                hbs = self.get_recent_hosts_by_style()
                hbr = self.get_recent_hosts_by_revno()
                if abs(start_times[OFFICIAL] - start_times[CONTINUOUS]) < 3600:
                    canonical_revno = max(code_revnos[OFFICIAL], code_revnos[CONTINUOUS])
                    if code_revnos[OFFICIAL] == code_revnos[CONTINUOUS]:
                        canonical_time = max(start_times[OFFICIAL], start_times[CONTINUOUS])
                    elif canonical_revno == code_revnos[OFFICIAL]:
                        canonical_time = start_times[OFFICIAL]
                    else:
                        canonical_time = start_times[CONTINUOUS]
                elif start_times[OFFICIAL] > start_times[CONTINUOUS]:
                    canonical_revno = code_revnos[OFFICIAL]
                    canonical_time = start_times[OFFICIAL]
                else:
                    canonical_revno = code_revnos[CONTINUOUS]
                    canonical_time = start_times[CONTINUOUS]
                if self.debug: print('canonical_revno = ' + str(canonical_revno))
                canonical_hosts_at_latest_revno = []
                for style in [CONTINUOUS, OFFICIAL]:
                    if style in hbs and hbs[style]:
                        latest = [host for host in hbs[style] if host in hbr[canonical_revno]]
                        #print('latest = ' + str(latest))
                        canonical_hosts_at_latest_revno.extend(latest)
                # Eliminate dups; the same host can do both official and continuous
                # builds...
                canonical_hosts_at_latest_revno = set(canonical_hosts_at_latest_revno)
                if self.debug: print('canonical_hosts_at_latest_revno = ' + str(canonical_hosts_at_latest_revno))
                # Now, find any failures among canonical machines.
                canonical_failures = []
                most_recent_summaries = [self._data[h][0] for h in canonical_hosts_at_latest_revno]
                if most_recent_summaries:
                    canonical_failures = [s for s in most_recent_summaries if s.get_reported_result() == EvalResult.FAILED]
                if canonical_failures:
                    self._status = _aggregate_status(canonical_failures)
                    if self.debug: print('canonical failures found')
                else:
                    if self.debug: print('no canonical failures found')
                    # If we get here, then as far as the canonical build machines are concerned,
                    # the build is clean. The only way we would contradict that is if we find
                    # a failed experimental build that's as new or newer than the canonical stuff.
                    if EXPERIMENTAL in hbs:
                        experimental_hosts = []
                        if ((code_revnos[EXPERIMENTAL] > canonical_revno and start_times[EXPERIMENTAL] > canonical_time) or code_revnos[EXPERIMENTAL] == canonical_revno) and hbs[EXPERIMENTAL]:
                            ex_failures = [self._data[h][0] for h in hbs[EXPERIMENTAL]]
                            ex_failures = [s for s in ex_failures if s.get_reported_result() == EvalResult.FAILED]
                            ex_failures = [s for s in ex_failures if s.build_id.code_revno >= canonical_revno]
                            if ex_failures:
                                self._status = _aggregate_status(ex_failures)
                if not self._status:
                    if self.debug: print('no failures')
                    # We already know how many canonical hosts contributed to this result.
                    # Find out how many experimental ones did as well.
                    if EXPERIMENTAL in hbs:
                        ex_summaries = [self._data[h][0]]
                        ex_summaries = [es for es in ex_summaries if es.build_id.code_revno >= canonical_revno]
                        ex_hosts = [es.host for es in ex_summaries]
                    else:
                        ex_hosts = []
                        ex_summaries = []
                    contributors = list(canonical_hosts_at_latest_revno) + ex_hosts
                    if self.debug: print('contributors = ' + str(contributors))
                    if self.debug: print('ex_summaries = ' + ';'.join([str(x) for x in ex_summaries]))
                    if len(contributors) == 1:
                        msg = '1 machine passed (%s)' % contributors[0]
                    else:
                        msg = '%d machines passed (%s).' % (len(contributors), ', '.join(contributors))
                    # Figure out date of most recent info.
                    when = 0
                    for s in most_recent_summaries:
                        if s.get_end_time() > when:
                            when = s.get_end_time()
                    for s in ex_summaries:
                        if s.get_end_time() > when:
                            when = s.get_end_time()
                    self._status = Status(EvalResult.OK, [msg], when)
        if self.debug: print('returning status = %s' % str(self._status))
        return self._status
    def _get_cutoff_date(self):
        base = self._pretend_time
        if not base:
            base = time.time()
        return base - self.get_horizon_seconds()
    def _load_host(self, h):
        summaries = []
        path = os.path.join(self._root, h, RESULTS_FILE)
        if self.debug: print('Loading data for %s from %s.' % (h, path))
        with open(path, 'r') as f:
            lines = [l.strip() for l in f.readlines()]
        cutoff = self._get_cutoff_date()
        if self.debug: print('Cutoff date = %.2f (%s)' % (cutoff, dateutils.format_standard_date_with_tz_offset(cutoff)))
        code_revno = 0
        n = 0
        for l in lines:
            if not l:
                continue
            try:
                n += 1
                es = parse_eval_summary_line(l)
                if es.get_start_time() < cutoff:
                    if self.debug: print('Passed cutoff date after %d lines (line=%s)' % (n, l))
                    break
                if not self.get_load_all():
                    # We only want to load build results for the most recent
                    # revno; for a given machine, anything other than its most
                    # recent results don't impact our analysis of status.
                    if es.build_id.code_revno < code_revno:
                        if self.debug: print('Passed revno of %d after %d lines (line=%s)' % (code_revno, n, l))
                        break
                    else:
                        code_revno = es.build_id.code_revno
                summaries.append(es)
            except:
                if self.debug: print('Unable to parse line %s' % l)
                pass
        if self.debug: print('Loaded %d summaries.' % n)
        if summaries:
            for es in summaries:
                if es.build_id not in self._build_groups:
                    self._build_groups[es.build_id] = []
                self._build_groups[es.build_id].append(es)
            self._data[h] = summaries
            rno = summaries[0].build_id.code_revno
            if not rno in self._hosts_by_revno:
                self._hosts_by_revno[rno] = []
            self._hosts_by_revno[rno].append(h)
            style = summaries[0].style
            if not style in self._hosts_by_style:
                self._hosts_by_style[style] = []
            self._hosts_by_style[style].append(h)
    def _load_if_needed(self):
        if self._data is None:
            if self.debug: print('Loading data for %s' % self._root)
            self._data = {}
            self._hosts_by_revno = {}
            self._hosts_by_style = {}
            self._build_groups = {}
            for h in self.get_hosts():
                self._load_host(h)
            # Figure out what the highest revno is for each of the three
            # eval styles.
            revs = {OFFICIAL: 0, CONTINUOUS: 0, EXPERIMENTAL: 0}
            start_times = {OFFICIAL: 0, CONTINUOUS: 0, EXPERIMENTAL: 0}
            rh = self._data.keys()
            for h in rh:
                summary = self._data[h][0]
                # pipe in other sandbox types
                if not summary.style in revs:
                    revs[summary.style] = 0
                    start_times[summary.style] = 0

                if revs[summary.style] < summary.build_id.code_revno  or summary.start_time - start_times[summary.style] > 3600:
                    revs[summary.style] = summary.build_id.code_revno
                    start_times[summary.style] = summary.start_time

            for h in rh:
                summary = self._data[h][0]
                # pipe in other sandbox types
                if not summary.style in revs:
                    revs[summary.style] = 0
                    start_times[summary.style] = 0

                if revs[summary.style] == summary.build_id.code_revno and summary.start_time > start_times[summary.style]:
                    start_times[summary.style] = summary.start_time
            # Convert from array to immutable tuple.
            self._code_revnos = revs
            self._start_times = start_times
    def get_code_revnos(self):
        '''
        Return the most recent bzr revnos for the code aspect of the component
        described by this dashboard. Uses a named tuple (experimental, continuous, official)
        to describe the revno for each of the different eval styles.
        '''
        self._load_if_needed()
        return self._code_revnos
    def get_start_times(self):
        '''
        Return the most recent start times for the diffenet build styles.
        Uses a named tuple (experimental, continuous, official)
        to describe the revno for each of the different eval styles.
        '''
        self._load_if_needed()
        return self._start_times
    def get_hosts(self):
        '''
        Get a list of all hosts that have ever reported results. Some of these
        hosts may not have contributed results recently enough to be relevant;
        contrast get_recent_hosts().
        '''
        if self._hosts is None:
            fldr = self._root
            self._hosts = [m for m in os.listdir(fldr) if
                 os.path.isfile(os.path.join(fldr, m, RESULTS_FILE))]
            self._hosts.sort()
            if self.debug: print('Calculated hosts for %s to be %s.' % (self._root, str(self._hosts)))
        return self._hosts
    def get_recent_hosts(self):
        '''
        Get a list of all hosts that have reported results in the recent past.
        '''
        self._load_if_needed()
        rh = self._data.keys()
        rh.sort()
        return rh
    def get_recent_hosts_by_style(self):
        '''
        Return a dict of style-->list of recent hosts evaluating in that style.
        '''
        self._load_if_needed()
        return self._hosts_by_style
    def get_recent_hosts_by_revno(self):
        '''
        Return a dict of revno-->list of recent hosts reporting for that revno.
        '''
        self._load_if_needed()
        return self._hosts_by_revno
    def get_recent_hosts_platform_styles(self):
        '''
        Return a dict of host-->[platform, [styles]]
        '''
        self._load_if_needed()
        host_summary = {}
        for host in self.get_recent_hosts():
            host_summary[host] = ['', []]
            for summary in self._data[host]:
                host_summary[host][0] = summary.tpv
                if summary.style not in host_summary[host][1]:
                    host_summary[host][1].append(summary.style)
# We've changed to allow multiple types of styles.
#                if [1,2,3] in host_summary[host]:
#                    break
        return host_summary
    def get_build_groups(self):
        '''
        Return a dict of build_id-->summaries.
        '''
        self._load_if_needed()
        return self._build_groups
    def get_build_group_ids(self):
        '''
        Return a list of build ids that this dashboard knows about, sorted in
        descending order.
        '''
        bgroups = [bid for bid in self.get_build_groups()]
        bgroups.sort(reverse=True)
        return bgroups
    def linked_to_vcs(self):
        return os.path.isdir(self._root + '.bzr')
    def update_status_log(self):
        if self.linked_to_vcs():
            os.system('bzr up "%s"' % self._root)
        add_needed = False
        self._data = None
        self._load_if_needed()
        status = self.get_status()
        result_name = enum_to_str(EvalResult, status.result)
        status_line = '%s,%s,%s' % (
            dateutils.format_standard_date_with_tz_offset(status.when),
            result_name,
            ' '.join(status.reasons))
        log_path = os.path.join(self._root, STATUS_LOG)
        if os.path.isfile(log_path):
            with open(log_path, 'r') as f:
                first_line = f.readline().strip()
                if result_name not in first_line:
                    lines = [status_line]
                else:
                    lines = []
                lines.append(first_line)
                lines.extend([l.strip() for l in f.readlines()])
                if len(lines) > 1000:
                    lines = lines[0:1000]
        else:
            if not os.path.isdir(self._root):
                os.makedirs(self._root)
            else:
                add_needed = self.linked_to_vcs()
            lines = [status_line]
        with open(log_path, 'w') as f:
            for l in lines:
                f.write(l + '\r\n')
        if add_needed:
            os.system('bzr add "%s"' % self._root)
    def add_summary(self, eval_summary):
        '''
        Record an individual eval's outcome for later use by the dashboard.
        '''
        fldr = os.path.join(self._root, eval_summary.host)
        if not os.path.isdir(fldr):
            os.makedirs(fldr)
        fname = os.path.join(fldr, RESULTS_FILE)
        add_needed = (not os.path.isfile(fname)) and self.linked_to_vcs()
        fname = os.path.join(fldr, RESULTS_FILE)
        summaries = [eval_summary]
        if os.path.isfile(fname):
            date_cutoff = eval_summary.get_start_time() - MAX_RETAINED_SECONDS
            with open(fname, 'r') as f:
                lines = [l.strip() for l in f.readlines()]
            for line in lines:
                if line:
                    try:
                        es = parse_eval_summary_line(line)
                        if es.get_start_time() < date_cutoff:
                            break
                        else:
                            summaries.append(es)
                    except:
                        pass
        # As a safety mechanism, sort descending. This should normally not be
        # necessary, but it compensates for weird corner cases like the system
        # time being reset.
        summaries.sort(key=lambda summary: summary.get_start_time(), reverse=True)
        with open(fname, 'w') as f:
            for s in summaries:
                #print('writing %s' % s)
                f.write(str(s) + '\r\n')
        # Copy log file if appropriate.
        if eval_summary.failure_reason:
            try:
                # We might have a sharing problem, because I think eval-log.txt is
                # still open at this point...
                shutil.copy(sb.get_root() + 'eval-log.txt', os.path.join(fldr, 'log.txt'))
            except:
                print('Could not copy log.')
        if add_needed:
            os.system('bzr add "%s"' % fldr)
        self.update_status_log()

