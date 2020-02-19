from collections import defaultdict
import datetime
import logging
import re

from . import patterns as p, tokenizer, utils

logger = logging.getLogger(__name__)


class Parser:

    def __init__(self, match):
        logger.info(f'{type(self).__name__}: {match.group().__repr__()}')


class Day(Parser):

    def __init__(self, match):
        super().__init__(match)
        month = match.group('day_month')
        month = utils.month(month)
        day = match.group('day_day')
        day = int(day)
        date = datetime.date(year=utils.TODAY.year, month=month, day=day)
        if date > utils.TODAY:
            date = date.replace(year=date.year - 1)
        total = match.group('day_total')
        if total:
            total = utils.duration(total)
        adjusted_total = match.group('day_adjusted_total')
        if adjusted_total:
            adjusted_total = utils.duration(adjusted_total)
        overage = match.group('day_overage')
        if overage:
            overage = utils.duration(overage)
        holiday = match.group('day_holiday')
        if holiday:
            holiday = utils.duration(holiday)
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
        overage = match.group('extra_overage')
        overage = utils.duration(overage)
        holiday = match.group('extra_holiday')
        if holiday:
            holiday = utils.duration(holiday)
        self.overage = overage
        self.holiday = holiday


class Interval(Parser):

    def __init__(self, match, date):
        super().__init__(match)
        start = match.group('interval_start')
        start = utils.time(start, date)
        end = match.group('interval_end')
        end = utils.time(end, date)
        if start > end:
            end += datetime.timedelta(days=1)
        total = match.group('interval_total')
        if total:
            total = utils.duration(total)
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
        matches = [re.match(p.SPLIT_CATEGORY_PATTERN, s) for s in strings]
        split = {
                m.group(4).lower(): utils.duration(m.group(1))
                for m in matches
        }
        self.split = split

    def __str__(self):
        return ', '.join(f'{total} {category}' for category, total in self.split.items())


def parse(path):
    tokens = tokenizer.tokenize(path)
    extra = None
    days = []
    for token in tokens:
        try:
            if token.type == tokenizer.DAY:
                day = Day(token.match)
                days += [day, ]
            elif token.type == tokenizer.INTERVAL:
                day = days[-1]
                interval = Interval(token.match, day.date)
                day.intervals += [interval, ]
            elif token.type == tokenizer.SPLIT:
                split = Split(token.match)
                day = days[-1]
                day.split = split
            elif token.type == tokenizer.EXTRA:
                extra = Extra(token.match)
            else:
                raise Exception(f'unexpected token: {token}')
        except Exception as error:
            logger.exception(error)
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
        used_extra = adjusted_total - total
        used_overage = running_overage - overage
        used_holiday = running_holiday - holiday
        if used_overage + used_holiday != used_extra:
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
    print('TOTAL:', utils.format_td(total))
    print('SPLIT:')
    for category, duration in split_totals.items():
        print(f'  {category}: {utils.format_td(duration)}')
    print('OVERAGE:', running_overage)
    print('HOLIDAY:', running_holiday)

    import csv
    import sys
    w = csv.writer(sys.stdout)
    w.writerow(['Date', 'Hours'])
    for day in days:
        w.writerow([day.date, utils.format_td_short(day.adjusted_total)])

    w.writerow(['Project', 'Class', 'Hours'])
    for category, duration in split_totals.items():
        w.writerow([category, '-', utils.format_td_short(duration)])

    rate = 35.5
    w.writerow([f'Total: {utils.format_td_short(total)}hr x {utils.format_usd(rate)}/hr = ...'])
