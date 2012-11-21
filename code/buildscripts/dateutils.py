# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
'''
Contains various routines that make date manipulation easier. Python's date
and time support is already solid; this just adds some extra usability for
arbitrary timezone conversion and date formatting/parsing.

For timezone conversions, use code like the following:

    import datetime, timezone
    d = datetime.datetime(2003, 05, 17, 18, 22, 07, tzinfo=timezone.UTC)
    d = d.astimezone(timezone.LOCAL_TIMEZONE)
'''
import time, calendar, re
import datetime

_ZERO = datetime.timedelta(0)
_HOUR = datetime.timedelta(hours=1)

class _UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return _ZERO
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return _ZERO

_STDOFFSET = datetime.timedelta(seconds = -time.timezone)
if time.daylight:
    _DSTOFFSET = datetime.timedelta(seconds = -time.altzone)
else:
    _DSTOFFSET = _STDOFFSET
_DSTDIFF = _DSTOFFSET - _STDOFFSET

class _LocalTimezone(datetime.tzinfo):
    def utcoffset(self, dt):
        if self._isdst(dt):
            return _DSTOFFSET
        else:
            return _STDOFFSET
    def dst(self, dt):
        if self._isdst(dt):
            return _DSTDIFF
        else:
            return _ZERO
    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]
    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0

'''
A tzinfo object with UTC (aka GMT aka Zulu) timezone semantics, that can be
passed to datetime functions that are timezone-aware.
'''
UTC = _UTC()
'''
A tzinfo object with local timezone semantics, that can be passed to datetime
functions that are timezone-aware.
'''
LOCAL_TIMEZONE = _LocalTimezone()

STANDARD_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
_TZ_OFFSET_PAT = re.compile(r'\s*([-+]\d\d:?\d\d)\s*$')
_MICROSEC_PAT = re.compile(r':\d\d(\.\d+)')

def parse_standard_date_with_tz_offset(txt):
    '''
    Given a date like "2007-05-29 19:23:07-0600", convert to seconds since
    epoch. Slight format variations are tolerated, such as a 'T' between date
    and time, microsecond precision, and/or a colon between hours and minutes
    in timezone offset.
    '''
    if txt:
        m = _TZ_OFFSET_PAT.search(txt)
        if m:
            x = m.group(1)
            txt = txt[0:m.start(1)].rstrip()
            offset = 3600 * int(x[1:3]) + 60 * int(x[3:].rstrip().replace(':', ''))
            if x[0] == '+':
                offset *= -1
        else:
            offset = 0
        m = _MICROSEC_PAT.search(txt)
        if m:
            ms = float('0' + m.group(1))
            txt = txt.replace(m.group(1), '')
        else:
            ms = 0
        value = time.strptime(txt, STANDARD_DATE_FORMAT)
        value = calendar.timegm(value)
        value += offset
        value += ms
    return value

def format_standard_date_with_tz_offset(value, tz=None):
    '''
    Given datetime, 9-tuple time_struct in UTC, or seconds since epoch, convert
    to a string like "2007-05-29 19:23:07-0600" or "2007-05-29 19:23:07.294847-0600"
    (depending on precision of input).

    @param tz Timezone in which formatted string should be expressed.
    '''
    if tz is None:
        tz = LOCAL_TIMEZONE
    if isinstance(value, int) or isinstance(value, float):
        dt = datetime.datetime.fromtimestamp(value, tz)
    elif isinstance(value, time.struct_time):
        dt = datetime.datetime(value.tm_year, value.tm_mon, value.tm_mday,
                      value.tm_hour, value.tm_min, value.tm_sec, tzinfo=UTC)
        dt = dt.astimezone(tz)
    else:
        assert(isinstance(value, datetime.datetime))
        dt = value
        if dt.tzinfo:
            dt = dt.astimezone(tz)
        else:
            dt.tzinfo = tz
    txt = str(dt)
    if txt[-3] == ':':
        txt = txt[0:-3] + txt[-2:]
    return txt

def time_str_to_military_str(time_str):
    '''
    Convert an hour:minute string (e.g., "3:25") to a military time string
    (e.g., "0325").
    '''
    if isinstance(time_str, unicode):
        time_str = str(time_str)
    else:
        assert(isinstance(time_str, str))
    time_str = time_str.replace(':','')
    return military_num_to_military_str(int(time_str))

def military_num_to_military_str(num):
    '''
    Convert a number like 325 to a military string like "0325".
    '''
    assert(num >= 0 and num < 2400)
    assert(num % 100 < 60)
    return str(num).rjust(4, '0')

def military_str_to_elapsed_minutes(mil):
    '''
    Convert a military time str (e.g., "0325") to elapsed minutes (e.g., 205).
    '''
    if isinstance(mil, unicode):
        mil = str(mil)
    else:
        assert(isinstance(mil, str))
    mil = int(mil)
    assert(mil >= 0 and mil < 2400)
    assert(mil % 100 < 60)
    return 60 * (mil / 100) + (mil % 100)

def elapsed_secs_to_duration_str(secs, suffixes=['y','w','d','h','m','s'], add_s=False, separator=' '):
    """
    Takes an amount of seconds and turns it into a human-readable amount of time.
    """
    # the formatted time string to be returned
    time = []
    seconds = int(secs)

    # the pieces of time to iterate over (days, hours, minutes, etc)
    # - the first piece in each tuple is the suffix (d, h, w)
    # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
    parts = [(suffixes[0], 60 * 60 * 24 * 7 * 52),
          (suffixes[1], 60 * 60 * 24 * 7),
          (suffixes[2], 60 * 60 * 24),
          (suffixes[3], 60 * 60),
          (suffixes[4], 60),
          (suffixes[5], 1)]

    # for each time piece, grab the value and remaining seconds, and add it to
    # the time string
    for suffix, length in parts:
        value = seconds / length
        if value > 0:
            seconds = seconds % length
            time.append('%s%s' % (str(value),
                           (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
        if seconds < 1:
            break

    return separator.join(time)

def elapsed_minutes_to_military_str(elmin):
    '''
    Convert elapsed minutes (e.g., 205) to a military time str (e.g., "0325").
    '''
    elmin = int(elmin)
    elmin = elmin % (60 * 24)
    hrs = elmin / 60
    elmin = elmin % 60
    return str(hrs).rjust(2, '0') + str(elmin).rjust(2, '0')

def increment_military_num_by_elapsed_minutes(num, minute_count):
    '''
    Given military time expressed as a number (e.g., 325 is the number for 3:25
    a.m.), add the specified number of minutes and return new military time,
    possibly wrapped.
    '''
    current_minutes = num % 100
    num -= current_minutes
    minute_count += current_minutes
    hrs = minute_count / 60
    mins = minute_count % 60
    num = num + (100 * hrs) + mins
    num = num % 2400
    return num

if __name__ == '__main__':
    help(format_standard_date_with_tz_offset)
