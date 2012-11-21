import unittest, os, re, time, sys
import dateutils
from testsupport import checkin

@checkin
class DateUtilsTest(unittest.TestCase):
    def test_format_and_parse_tandard_date_with_tz_offset(self):
        when = round(time.time(), 3)
        x = dateutils.format_standard_date_with_tz_offset(when)
        if not re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?\s*[-+]\d\d:?\d\d', x):
            self.fail('Expected standard format; got "%s" instead.' % x)
        when2 = round(dateutils.parse_standard_date_with_tz_offset(x), 3)
        if when != when2:
            self.fail('Expected round trip to be lossless. Instead, started with %d and ended with %d (diff = %d)'
                 % (int(when), when2, when2-int(when)))
    def test_military_str_to_elapsed_minutes(self):
        self.assertEquals(205, dateutils.military_str_to_elapsed_minutes("0325"))
    def test_increment_military_num_by_elapsed_minutes(self):
        self.assertEquals(115, dateutils.increment_military_num_by_elapsed_minutes(1805, 430))
    def test_elapsed_minutes_to_military_str(self):
        self.assertEquals("0325", dateutils.elapsed_minutes_to_military_str(205))
    def test_elapsed_secs_to_duration_str(self):
        # 2 years, 1 week, 6 days, 2 hours, 59 minutes, 23 seconds
        # 2y 1w 6d 2h 59m 23s
        seconds = (60 * 60 * 24 * 7 * 52 * 2) + (60 * 60 * 24 * 7 * 1) + (60 * 60 * 24 * 6) + (60 * 60 * 2) + (60 * 59) + (1 * 23)
        self.assertEquals('2y 1w 6d 2h 59m 23s', dateutils.elapsed_secs_to_duration_str(seconds))
        self.assertEquals('2 year 1 week 6 day 2 hour 59 minute 23 second', dateutils.elapsed_secs_to_duration_str(seconds, [' year',' week',' day',' hour',' minute',' second']))
        self.assertEquals('2 years 1 week 6 days 2 hours 59 minutes 23 seconds', dateutils.elapsed_secs_to_duration_str(seconds, [' year',' week',' day',' hour',' minute',' second'], add_s=True))
        self.assertEquals('2 years, 1 week, 6 days, 2 hours, 59 minutes, 23 seconds', dateutils.elapsed_secs_to_duration_str(seconds, [' year',' week',' day',' hour',' minute',' second'], add_s=True, separator=', '))
    def test_elapsed_secs_to_duration_str(self):
        # 2 years, 1 week, 6 days, 2 hours, 59 minutes, 23 seconds
        # 2y 1w 6d 2h 59m 23s
        seconds = (60 * 60 * 24 * 7 * 52 * 2) + (60 * 60 * 24 * 7 * 1) + (60 * 60 * 24 * 6) + (60 * 60 * 2) + (60 * 59) + (1 * 23)
        self.assertEquals('2y 1w 6d 2h 59m 23s', dateutils.elapsed_secs_to_duration_str(seconds))
        self.assertEquals('2 year 1 week 6 day 2 hour 59 minute 23 second', dateutils.elapsed_secs_to_duration_str(seconds, [' year',' week',' day',' hour',' minute',' second']))
        self.assertEquals('2 years 1 week 6 days 2 hours 59 minutes 23 seconds', dateutils.elapsed_secs_to_duration_str(seconds, [' year',' week',' day',' hour',' minute',' second'], add_s=True))
        self.assertEquals('2 years, 1 week, 6 days, 2 hours, 59 minutes, 23 seconds', dateutils.elapsed_secs_to_duration_str(seconds, [' year',' week',' day',' hour',' minute',' second'], add_s=True, separator=', '))

if __name__ == '__main__':
    unittest.main()
