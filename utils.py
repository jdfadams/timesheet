import collections
import datetime
from decimal import Decimal
import logging
import re

from . import patterns as p

logger = logging.getLogger(__name__)

NOW = datetime.datetime.now()
TODAY = NOW.date()


_Duration = collections.namedtuple('_Duration', [
        'hours',
        'minutes',
        'seconds',
        'sign',
])


class Error(Exception):
    pass


def duration(string):
    print(f'DURATION: {string}')
    match = re.match(fr'^{p.DURATION_PATTERN}$', string)
    if not match:
        raise Error(f'{string.__repr__()} is not a duration.')
    if string.startswith('-'):
        sign = -1
        string = string[1:]
    else:
        sign = 1
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
    timedelta = sign * datetime.timedelta(hours=hour, minutes=minute)
    logger.debug(f'duration: {string.__repr__()} --> {timedelta}')
    return timedelta


def month(string):
    for n, pattern in enumerate(p.MONTHS, 1):
        if re.match(pattern, string):
            return n
    raise Error(f'{string.__repr__()} is not a month')


def time(string, date=TODAY):
    match = re.match(fr'^{p.TIME_PATTERN}$', string)
    if not match:
        raise Error(f'{string.__repr__()} is not a time.')
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
    logger.debug(f'time: {string.__repr__()} --> {time}')
    return datetime.datetime.combine(date, time)


def _format_td(td):
    seconds = td.total_seconds()
    if seconds < 0:
        seconds = -seconds
        sign = '-'
    else:
        sign = '';
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    d = {
            'hours': round(hours),
            'minutes': round(minutes),
            'seconds': round(seconds),
            'sign': sign,
    }
    return _Duration(**d)


def format_td(td, fmt='{sign}{hours:d}:{minutes:02d}:{seconds:02d}'):
    d = _format_td(td)
    return fmt.format(**d._asdict())


def format_td_short(td):
    d = _format_td(td)
    seconds = f':{d.seconds:02d}' if d.seconds else ''
    return f'{d.sign}{d.hours:d}:{d.minutes:02d}{seconds}'
