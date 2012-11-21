'''
Convert schedules, expressed in simple language, into cron jobs or windows
scheduled tasks.
'''
#
# $Id: sadm_schedule.py 9424 2011-06-13 18:42:04Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import re, os, time
from sadm_constants import *
from sadm_util import *

'''
Used to run unit-like tests without actually calling the OS scheduler.
'''
test_mode = False

_RANGE_PAT = re.compile(r'(\s*,\s*(from\s+)?|\s+from\s+)(\d{3,4}|\d\d?:\d\d)(\s*-\s*|\s+to\s+)(\d{3,4}|\d\d?:\d\d)', re.IGNORECASE)
_AT_PAT = re.compile(r'at\s+((\d{3,4}|\d\d?:\d\d)(\s*,\s*(\d{3,4}|\d\d?:\d\d))*)', re.IGNORECASE)
_EVERY_PAT = re.compile(r'every\s+((\d+)\s*([hm])[a-z]*)('+_RANGE_PAT.pattern+')?', re.IGNORECASE)
_SPEC_PAT = re.compile(r'\s*(never|'+_AT_PAT.pattern+'|'+_EVERY_PAT.pattern+')\s*', re.IGNORECASE)
_STRTYPE = type('')
_MULTIHOURS_PAT = re.compile(r'^\d{1,2}(\s*,\s*\d{1,2})*$')
_REPEAT_INTERVAL_PAT = re.compile(r'^\*/\d{1,4}$')
if os.name == 'nt':
    _CRONTAB_PAT = re.compile(r'\s*"\\?' + APP_CMD + r'\s*(?:~|\\)\s*(.*?)\s+((at|every)[^"]+).*', re.IGNORECASE)
    _LISTCRON_CMD = 'schtasks /query /fo csv'
    def _parseSpec(m):
        sb = m.group(1).replace(', ', '/')
        if (m.group(2) == '@'):
            hours = ','.join([x.strip()[0:-2] for x in m.group(2).split(',')])
            mins = m.group(2).split(',')[0].strip()[-2:]
        else:
            mins = '*/' + m.group(3)
        return spec.replace('x','*').replace(';','/')
    def _makeTaskName(sb):
        name = APP_CMD + ' ~ ' + sb.get_name().replace('/', ', ') + ' '
        if sb.schedule.is_periodic():
            name += 'every %s minutes' % sb.schedule.getInterval()
        else:
            name += '@ ' + sb.schedule.getTimes()
    def _milToColon(x):
        return x[0:2] + ':' + x[2:]
    def _lineIsForSandbox(ln, sb):
        keep = ln.endswith(sb.get_name()) or ln.find(' ' + sb.get_name() + ' ') != -1
        return keep
else:
    _MAILTO_PAT = re.compile(r'\s*mailto\s*=\s*([^ \t]+)\s*', re.IGNORECASE)
    _CRONTAB_PAT = re.compile(r'\s*#\s*' + APP_CMD + '\s+(.*)\s+' + _SPEC_PAT.pattern, re.IGNORECASE)
    _LISTCRON_CMD = 'crontab -l'
    def _lineIsForSandbox(ln, sb):
        keep = ln.endswith(sb.get_name()) or ln.find(' ' + sb.get_name() + ' ') != -1
        return keep

_STR_TYPE = type('')
# Convert a number to pure 4-digit military time
def _mil(t):
    if type(t) == _STR_TYPE:
        t = t.replace(':','')
    n = int(t)
    assert(n >= 0 and n < 2400)
    assert(n % 100 < 60)
    return str(n).rjust(4, '0')

def _incrmil(n, inc):
    currentMinutes = n % 100
    n -= currentMinutes
    inc += currentMinutes
    hrs = inc / 60
    mins = inc % 60
    n = n + (100 * hrs) + mins
    n = n % 2400
    return n

def _sortUnique(lst):
    if len(lst) > 1:
        lst.sort()
        i = 0
        while i < len(lst) - 1:
            if lst[i] == lst[i+1]:
                lst.remove(lst[i])
            i += 1
    return lst

class Schedule:
    if os.name == 'nt':
        password = None
        mailto = ''
    else:
        password = ''
        mailto = None
    def __init__(self, spec):
        m = _SPEC_PAT.match(spec)
        assert(m)
        at = every = rng = None
        spec = m.group(1).lower()
        if spec == 'never':
            pass
        elif spec[0] == 'a':
            m = _AT_PAT.match(spec)
            at = _sortUnique([_mil(t.strip()) for t in m.group(1).split(',') if len(t.strip())])
        else:
            m = _EVERY_PAT.match(spec)
            interval = int(m.group(2))
            assert(interval > 0)
            scale = m.group(3).lower()
            if scale == 'm':
                # For simplicity, round weird numbers to the nearest 15 minutes.
                if not ((interval <= 60) and ((60 % interval == 0) or (interval < 15))):
                    remainder = interval % 15
                    if remainder != 0 and (interval % 20 != 0) and (interval % 10 != 0):
                        if remainder < 8:
                            interval -= remainder
                        else:
                            interval = interval + 15 - remainder
                        print('Rounded interval to every %d minutes for simplicity.' % interval)
            every = str(interval) + ' ' + m.group(3).lower()
            rng = m.group(4)
            if rng:
                m = _RANGE_PAT.match(rng)
                rng = [_mil(t) for t in [m.group(3), m.group(5)]]
                if rng[0] == rng[1]:
                    rng = None
        self.at = at
        self.every = every
        self.range = rng
    def isNever(self):
        return not (bool(self.at) or bool(self.every))
    def getInterval(self):
        if not self.every:
            return 0
        return int(self.every.split(' ')[0])
    def getUnits(self):
        if not self.every:
            return None
        return self.every[-1:]
    def isInRange(self, when = None):
        if self.range:
            if when is None:
                when = time.localtime()
                when = _mil(when.tm_hour * 100 + when.tm_min)
            else:
                when = _mil(when)
            if self.range[0] < self.range[1]:
                return (when >= self.range[0]) and (when < self.range[1])
            else:
                return (when >= self.range[0]) or (when < self.range[1])
        return False
    def toTasks(self):
        lines = []
        if self.isNever():
            return lines
        if os.name == 'nt':
            pwdargs = ''
            if Schedule.password:
                user = os.getenv("USERNAME")
                pwdargs = '/ru "%s" /rp "%s" ' % (user, Schedule.password)
            if self.is_periodic():
                if self.getUnits() == 'm':
                    period = 'minute'
                else:
                    period = 'hourly'
                when = '/sc %s /mo %s' % (period, self.getInterval())
                # On windows, it appears that if you provide a start and end time,
                # you cause the task to expire, instead of just giving it an activity
                # window. Therefore, ignore the range setting.
                #if self.range:
                #    start = _milToColon(self.range[0])
                #    end = _milToColon(self.range[1])
                #    when += ' /st %s /et %s' % (start + ":00", end + ":00")
                #else:
                if True:
                    # Set an explicit start time so task starts in 1 minute instead
                    # of waiting for the full interval to elapse before first run.
                    soon = time.localtime()
                    soon = soon.tm_hour * 100 + soon.tm_min
                    soon = _milToColon(str(_incrmil(soon, 1)).rjust(4, '0'))
                    when += ' /st %s' % (soon + ":00")
                lines.append(pwdargs + when)
            else:
                for st in self.at:
                    when = '/sc daily /st "%s"' % (_milToColon(st) + ":00")
                    lines.append(pwdargs + when)
        else:
            if self.at:
                suffixes = {}
                for t in self.at:
                    suf = t[2:]
                    if not (suf in suffixes):
                        suffixes[suf] = []
                    suffixes[suf].append(t[0:2])
                keys = suffixes.keys()[:]
                keys.sort()
                for suf in keys:
                    hrs = suffixes.get(suf)
                    hrs.sort()
                    lines.append('%s %s * * *' % (suf, ','.join(suffixes.get(suf))))
            else:
                interval = self.getInterval()
                txt = '*/%d ' % interval
                if self.every[-1:] == 'm':
                    # The simple form works well if we have a number evenly divisible
                    # by 60, or if our interval is small enough that we can round
                    # and start our repetition all over at the top of each hour.
                    # However, if we have a number like 45, we can't simply create
                    # one crontab line that begins with "/45 *", because that would
                    # launch on the 45th minute of every hour -- once an hour instead
                    # of once every 45 minutes.
                    simpleInterval = (interval <= 60) and ((60 % interval == 0) or (interval < 15))
                    simpleMinutes = not self.range or (self.range[0][2:] == '00' and self.range[1][2:] == '00')
                    if simpleInterval and simpleMinutes:
                        if self.range:
                            begin = int(self.range[0]) / 100
                            end = int(self.range[1]) / 100
                            # Ranges that we receive and store are half-open (meaning that
                            # the end of the range is not part of the valid set of values),
                            # but in cron they are inclusive, so we have to subtract 1 hour
                            # from the end.
                            endInclusive = end - 1
                            if begin < end:
                                if begin < endInclusive:
                                    txt += '%d-%d ' % (begin, endInclusive)
                                else:
                                    txt = '%d ' % begin
                            else:
                                if endInclusive == 0:
                                    txt += '%d-23,0 ' % begin
                                else:
                                    txt += '%d-23,0-%d ' % (begin, endInclusive)
                        else:
                            txt += '* '
                    else:
                        txt = ''
                        if self.range:
                            begin = int(self.range[0])
                            end = int(self.range[1])
                        else:
                            begin = 0
                            end = 2359
                        minutesByHour = {}
                        n = begin
                        # If begin is already less than end, then pretend we
                        # already wrapped.
                        wrapped = begin < end
                        while not (wrapped and (n >= end)):
                            hour = n / 100
                            if not (hour in minutesByHour):
                                minutesByHour[hour] = []
                            minutesByHour[hour].append(str(n % 100))
                            next = _incrmil(n, interval)
                            if next < n:
                                if not wrapped:
                                    wrapped = True
                                else:
                                    break
                            n = next
                        hoursByMinutes = {}
                        for hour in minutesByHour.keys():
                            spec = ','.join(minutesByHour[hour])
                            if not (spec in hoursByMinutes):
                                hoursByMinutes[spec] = []
                            hoursByMinutes[spec].append(str(hour))
                        for spec in hoursByMinutes.keys():
                            lines.append(spec + ' ' + ','.join(hoursByMinutes[spec]) + ' * * *')
                            lines.sort(cmp=lambda x,y: cmp(x[x.find(' ') + 1:], y[y.find(' ') + 1:]))
                else:
                    nextMinute = time.localtime().tm_min + 1
                    if nextMinute > 59:
                        nextMinute = 1
                    txt = str(nextMinute) + ' ' + txt
                if txt:
                    txt += '* * *'
                    lines.append(txt)
        return lines
    def is_periodic(self):
        return bool(self.every)
    def __str__(self):
        if self.at:
            return 'at ' + ', '.join(self.at)
        if self.every:
            t = 'every ' + self.every
            if self.range:
                t += ', %s-%s' % (self.range[0], self.range[1])
            return t
        return "never"
    @staticmethod
    def promptForOsPasswordIfNeeded():
        if Schedule.password is None:
            print('''
Sadm needs your OS password to interact with Task Scheduler. This info is not
saved by sadm. (Depending on your machine's security configuration, you may
need to launch a command prompt using Windows' "Run as administrator" command
before Task Scheduler will allow sadm to control it.)
''')
            Schedule.password = sadm_prompt.prompt('Password for ' + os.getenv('USERNAME'), mask=True)
    @staticmethod
    def list():
        sch = []
        stdout, error = run(_LISTCRON_CMD, acceptFailure = True)
        if (not error) and stdout:
            lines = stdout.split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    if os.name == 'nt':
                        m = None
                    else:
                        m = _MAILTO_PAT.match(line)
                    if m:
                        Schedule.mailto = m.group(1)
                    else:
                        m = _CRONTAB_PAT.match(line)
                        if m:
                            sb = m.group(1)
                            schedule = m.group(2)
                            if os.name == 'nt':
                                sb = sb.replace(', ', '/')
                                i = schedule.find('#')
                                if i != -1:
                                    if schedule[i+1:i+2] != '1':
                                        add = False
                                    else:
                                        schedule = schedule[0:i]
                            schedule = Schedule(schedule)
                            sch.append((sb, schedule, m.group(2)))
        return sch
    @staticmethod
    def applyToSandbox(sb):
        Schedule.promptForOsPasswordIfNeeded()
        if not config.test_mode:
            if os.name == 'nt':
                taskname = APP_CMD + ' ~ ' + sb.get_name().replace('/', ', ')
                current = Schedule.list()
                if current:
                    for item in current:
                        if item[0] == sb.get_name():
                            tn = taskname + ' ' + item[2]
                            cmd = 'schtasks /delete /tn "%s" /f' % tn
                            #print(cmd)
                            stdout, error = run(cmd, acceptFailure = True)
                            if (stdout.find('SUCCESS') == -1):
                                print(cmd)
                                raise Exception(stdout)
                if sb.schedule:
                    taskname += ' ' + str(sb.schedule)
                    basecmd = '%s \\"%s\\" --no-color start \\"%s\\"' % (FQPYTHON, APP_PATH, sb.get_name())
                    i = 1
                    for task in sb.schedule.toTasks():
                        if i == 1:
                            offset = ''
                        else:
                            offset = '#%d' % i
                        cmd = 'schtasks /create %s /tn "%s" /tr "%s"' % (task, taskname + offset, basecmd)
                        stdout, error = run(cmd)
                        if stdout.find('SUCCESS') == -1:
                            print(cmd)
                            raise Exception(stdout)
                        i += 1
            else:
                ftmpName = os.path.join(sb.location, 'crontab-' + str(time.time()) + '.txt')
                ftmp = open(ftmpName, 'wt')
                stdout, error = run('crontab -l', acceptFailure = True)
                if Schedule.mailto:
                    ftmp.write('MAILTO=%s\n' % Schedule.mailto)
                if (not error) and stdout:
                    lines = stdout.split('\n')
                    for line in lines:
                        ln = line.strip()
                        keep = bool(ln)
                        if keep and (_lineIsForSandbox(line, sb) or bool(_MAILTO_PAT.match(line))):
                            keep = False
                        if keep:
                            ftmp.write(ln + '\n')
                if sb.schedule:
                    ftmp.write('# %s start %s %s\n' % (APP_CMD, sb.get_name(), sb.schedule))
                    for t in sb.schedule.toTasks():
                        # For builds that run on an interval, run at lower priority.
                        # For builds that run at a specific time, run at normal priority, on the assumption
                        # that the user picked that time for a reason and would prefer to not have the build
                        # yielding cpu time just to be nice.
                        cmd = t
                        if bool(sb.schedule.every):
                            cmd += ' nice'
                        ftmp.write(cmd + ' %s --no-color start %s' % (APP_INVOKE, sb.get_name()) + ' >/dev/null\n')
                ftmp.close()
                subprocess.check_call('crontab %s' % ftmpName, shell=True)
                #print('wrote ' + ftmpName)
                os.remove(ftmpName)
    @staticmethod
    def apply_to_arbitrary_command(cmd, taskName, sched, removeOnly=None):
        Schedule.promptForOsPasswordIfNeeded()
        if not test_mode:
            if removeOnly is None:
                removeOnly = ((not bool(sched)) or sched.isNever())
            if os.name == 'nt':
                stdout, error = run(_LISTCRON_CMD, acceptFailure = True)
                if (not error) and stdout:
                    i = 1
                    lines = stdout.split('\n')
                    # Read a schedule that has up to 20 individual components (sub-commands).
                    while i < 20:
                        found = False
                        for line in lines:
                            if i == 1:
                                offset = ''
                            else:
                                offset = '#%d' % i
                            if line.find(taskName + offset) != -1:
                                found = True
                                cmdToRun = 'schtasks /delete /tn "%s" /f' % taskName + offset
                                stdout, error = run(cmdToRun, acceptFailure = True)
                                i += 1
                                if stdout.find('SUCCESS') == -1:
                                    print(cmdToRun)
                                    raise Exception(stdout)
                                break
                        if not found:
                            break
                if not removeOnly:
                    i = 1
                    for task in sched.toTasks():
                        if i == 1:
                            offset = ''
                        else:
                            offset = '#%d' % i
                        cmdToRun = 'schtasks /create %s /tn "%s" /tr "%s"' % (task, taskName + offset, cmd.replace('"', '\\"'))
                        i += 1
                        stdout, error = run(cmdToRun)
                        if stdout.find('SUCCESS') == -1:
                            print(cmdToRun)
                            raise Exception(stdout)
            else:
                ftmpName = os.path.join(HOMEDIR, 'crontab-' + str(time.time()) + '.txt')
                ftmp = open(ftmpName, 'wt')
                stdout, error = run('crontab -l', acceptFailure = True)
                if Schedule.mailto:
                    ftmp.write('MAILTO=%s\n' % Schedule.mailto)
                cmdline = ''
                # For tasks that run on an interval, run at lower priority.
                if bool(sched.every):
                    cmdline += 'nice '
                cmdline += cmd + ' >/dev/null'
                if (not error) and stdout:
                    lines = stdout.split('\n')
                    for line in lines:
                        ln = line.strip()
                        keep = bool(ln)
                        if keep:
                            if (ln.find('# ' + taskName) != -1) or ln.endswith(cmdline) or bool(_MAILTO_PAT.match(line)):
                                keep = False
                        if keep:
                            ftmp.write(ln + '\n')
                if not removeOnly:
                    ftmp.write('# %s %s\n' % (taskName, sched))
                    for t in sched.toTasks():
                        ftmp.write(t + ' ' + cmdline + '\n')
                ftmp.close()
                subprocess.check_call('crontab %s' % ftmpName, shell='True')
                os.remove(ftmpName)

# These imports have to come at end of file to avoid circular import errors
import sadm_prompt