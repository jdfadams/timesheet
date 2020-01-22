from collections import defaultdict
import datetime
from decimal import Decimal
import logging
import re
import os

from . import utils

logger = logging.getLogger(__name__)

MONTHS = [
    r'Jan(uary)?',
    r'Feb(ruary)?',
    r'Mar(ch)?',
    r'Apr(il)?',
    r'May',
    r'June?',
    r'July?',
    r'Aug(ust)?',
    r'Sep(t(ember)?)?',
    r'Oct(ober)?',
    r'Nov(ember)?',
    r'Dec(ember)?',
]

HHMM_PATTERN = r'\d\d?(?::\d\d)?'
TIME_PATTERN = fr'{HHMM_PATTERN}(?:am|pm)'
DURATION_PATTERN = fr'({HHMM_PATTERN}|\d+\.\d+)(hr)?'

MONTH_PATTERN = r'|'.join(MONTHS)
DAY_LINE = (
    fr'^(?P<month>{MONTH_PATTERN})\s+(?P<day>\d\d?)(\s*\((?P<comment>.*?)\))?\s*:('
        fr'\s*(?P<total>{DURATION_PATTERN})'
        fr'(\s*-->\s*(?P<adjusted_total>{DURATION_PATTERN})(\s*,\s*(?P<overage>{DURATION_PATTERN})\s+overage)?(\s*,\s*(?P<holiday>{DURATION_PATTERN})\s+holiday)?)?'
    r')?.*$'  # REMOVE THE TRAILING .* AT THE END.
)

SPLIT_CATEGORY_PATTERN = fr'({DURATION_PATTERN})\s*(?!hr|am|pm)(\w[\w\-_/]*)'
SPLIT_LINE = fr'^\s*{SPLIT_CATEGORY_PATTERN}\s*(,\s*{SPLIT_CATEGORY_PATTERN}\s*)*$'

INTERVAL_LINE = fr'^(?P<start>{TIME_PATTERN})\s*-\s*(?P<end>{TIME_PATTERN})(\s+(?P<total>{DURATION_PATTERN}))?\s*$'

EXTRA_LINE = fr'^OVERAGE\s+(?P<overage>{DURATION_PATTERN})\s*(,\s*HOLIDAY\s+(?P<holiday>{DURATION_PATTERN})\s*)?$'


def month_to_int(string):
    for i, pattern in enumerate(MONTHS):
        if re.match(pattern, string):
            return i + 1
    raise Exception(f'{string.__repr__()} is not a month')


def parse_duration(string):
    match = re.match(fr'^{DURATION_PATTERN}$', string)
    if not match:
        raise Exception(f'{string.__repr__()} is not a duration.')
    if string.endswith('hr'):
        string = string[:-2]
    if ':' in string:
        hour, minute = string.split(':')
        hour = int(hour)
        minute = int(minute)
    else:
        x = Decimal(string)
        hour = int(x)
        minute = round((x - hour) * 60)
    assert 0 <= hour
    assert 0 <= minute < 60
    timedelta = datetime.timedelta(hours=hour, minutes=minute)
    logger.debug(f'parsed duration: {string.__repr__()} --> {timedelta}')
    return timedelta


def parse_time(string, date=utils.TODAY):
    match = re.match(fr'^{TIME_PATTERN}$', string)
    if not match:
        raise Exception(f'{string.__repr__()} is not a time.')
    hhmm = string[:-2]
    try:
        hour, minute = hhmm.split(':')
    except:
        hour, minute = hhmm, 0
    hour = int(hour)
    assert 1 <= hour <= 12
    minute = int(minute)
    assert 0 <= minute < 60
    meridian = string[-2:]
    assert meridian in ['am', 'pm', ]
    if hour == 12 and meridian == 'am':
        hour = 0
    elif hour < 12 and meridian == 'pm':
        hour += 12
    time = datetime.time(hour=hour, minute=minute)
    logger.debug(f'parsed time: {string.__repr__()} --> {time}')
    return datetime.datetime.combine(date, time)


class Parser:

    def __init__(self, match):
        logger.info(f'{type(self).__name__}: {match.group().__repr__()}')


class Day(Parser):

    def __init__(self, match):
        super().__init__(match)
        month = match.group('month')
        month = month_to_int(month)
        day = match.group('day')
        day = int(day)
        date = datetime.date(year=utils.TODAY.year, month=month, day=day)
        if date > utils.TODAY:
            date = date.replace(year=date.year - 1)
        total = match.group('total')
        if total:
            total = parse_duration(total)
        adjusted_total = match.group('adjusted_total')
        if adjusted_total:
            adjusted_total = parse_duration(adjusted_total)
        overage = match.group('overage')
        if overage:
            overage = parse_duration(overage)
        holiday = match.group('holiday')
        if holiday:
            holiday = parse_duration(holiday)
        self.date = date
        self.total = total
        self.adjusted_total = adjusted_total
        self.overage = overage
        self.holiday = holiday
        self.intervals = []
        self.split = None

    def __str__(self):
        line = f'{self.date}: {self.total}'
        if self.adjusted_total:
            line += f' --> {self.adjusted_total}'
        if self.overage:
            line += f', {self.overage} overage'
        if self.holiday:
            line += f', {self.holiday} holiday'
        lines = [line, ]
        lines += [f'  {interval}' for interval in self.intervals]
        lines += [f'  {self.split}', ]
        return '\n'.join(lines)

    def validate(self):
        total = datetime.timedelta()
        for interval in self.intervals:
            print(interval)
            interval.validate()
            total += interval.total
        if total != self.total:
            raise Exception(f'{self.date}: The intervals sum to {total}, not {self.total}.')
        total = datetime.timedelta()
        if not self.split:
            raise Exception(f'{self.date}: The split is missing.')
        for value in self.split.split.values():
            total += value
        if self.adjusted_total and total != self.adjusted_total:
            raise Exception(f'{self.date}: The split sums to {total}, not {self.adjusted_total}.')


class Extra(Parser):

    def __init__(self, match):
        super().__init__(match)
        overage = match.group('overage')
        overage = parse_duration(overage)
        holiday = match.group('holiday')
        if holiday:
            holiday = parse_duration(holiday)
        self.overage = overage
        self.holiday = holiday


class Interval(Parser):

    def __init__(self, match, date):
        super().__init__(match)
        start = match.group('start')
        start = parse_time(start, date)
        end = match.group('end')
        end = parse_time(end, date)
        if start > end:
            end += datetime.timedelta(days=1)
        total = match.group('total')
        if total:
            total = parse_duration(total)
        self.start = start
        self.end = end
        self.total = total

    def __str__(self):
        return f'{self.start.time()}-{self.end.time()} ({self.total})'

    def validate(self):
        if self.start == self.end:
            raise Exception(f'The end time must be later than the start time {self.start.time()}.')
        total = self.end - self.start
        if total != self.total:
            raise Exception(f'The elapsed time between {self.start.time()} and {self.end.time()} is {total}, not {self.total}.')


class Split(Parser):

    def __init__(self, match):
        super().__init__(match)
        strings = match.group().split(',')
        strings = [s.strip() for s in strings]
        strings = [s for s in strings if s]
        matches = [re.match(SPLIT_CATEGORY_PATTERN, s) for s in strings]
        split = {
                m.group(4).lower(): parse_duration(m.group(1))
                for m in matches
        }
        self.split = split

    def __str__(self):
        return ', '.join(f'{total} {category}' for category, total in self.split.items())


def parse(path):
    with open(path, 'r') as fp:
        lines = fp.readlines()
    extra = None
    days = []
    for line in lines:
        try:
            match = re.match(DAY_LINE, line)
            if match:
                day = Day(match)
                days += [day, ]
                continue
            match = re.match(INTERVAL_LINE, line)
            if match:
                day = days[-1]
                interval = Interval(match, day.date)
                day.intervals += [interval, ]
                continue
            match = re.match(SPLIT_LINE, line)
            if match:
                split = Split(match)
                day = days[-1]
                day.split = split
                continue
            match = re.match(EXTRA_LINE, line)
            if match:
                extra = Extra(match)
                continue
        except Exception as error:
            logger.exception(error)
            logger.error(f'line: {line}')
            raise

    for day in days:
        day.validate()

    running_overage = extra.overage or datetime.timedelta()
    running_holiday = extra.holiday or datetime.timedelta()
    for day in days:
        total = day.total
        adjusted_total = day.adjusted_total
        overage = day.overage or datetime.timedelta()
        holiday = day.holiday or datetime.timedelta()
        # hack
        if not adjusted_total:
            print(f'SKIPPING {day.date}')
            print(day)
            continue
        # end hack
        used_extra = adjusted_total - total
        used_overage = running_overage - overage
        used_holiday = running_holiday - holiday
        if False and used_overage + used_holiday != used_extra:
            raise Exception(
                f'{day.date}: The recorded overage ({overage}) and holiday ({holiday}) hours'
                f' are inconsistent with the {used_extra} hours used.'
                f' I suggest used_overage={used_extra - used_holiday} (not {used_overage})'
                f' and used_holiday={used_holiday}.'
            )
        running_overage = overage
        running_holiday = holiday

    split_totals = defaultdict(datetime.timedelta)
    for day in days:
        for category, duration in day.split.split.items():
            split_totals[category] += duration

    for day in days:
        print(str(day))
    total = sum((day.adjusted_total or datetime.timedelta() for day in days), datetime.timedelta())
    print('TOTAL:', utils.td_hms(total))
    print('SPLIT:')
    for category, duration in split_totals.items():
        print(f'  {category}: {utils.td_hms(duration)}')
    print('OVERAGE:', running_overage)
    print('HOLIDAY:', running_holiday)
