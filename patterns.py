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

HHMM_PATTERN = r'-?\d\d?(?::\d\d)?'
TIME_PATTERN = fr'{HHMM_PATTERN}(?:am|pm)'
DURATION_PATTERN = fr'({HHMM_PATTERN}|\d+\.\d+)(hr)?'

MONTH_PATTERN = r'|'.join(MONTHS)
DAY_LINE = (
    fr'^(?P<day_month>{MONTH_PATTERN})\s+(?P<day_day>\d\d?)(\s*\((?P<day_comment>.*?)\))?\s*:('
        fr'\s*(?P<day_total>{DURATION_PATTERN})'
        fr'(\s*-->\s*(?P<day_adjusted_total>{DURATION_PATTERN})(\s*,\s*(?P<day_overage>{DURATION_PATTERN})\s+overage)?(\s*,\s*(?P<day_holiday>{DURATION_PATTERN})\s+holiday)?)?'
    r')?.*$'  # REMOVE THE TRAILING .* AT THE END.
)

EXTRA_LINE = fr'^OVERAGE\s+(?P<extra_overage>{DURATION_PATTERN})\s*(,\s*HOLIDAY\s+(?P<extra_holiday>{DURATION_PATTERN})\s*)?$'

INTERVAL_LINE = fr'^(?P<interval_start>{TIME_PATTERN})\s*-\s*(?P<interval_end>{TIME_PATTERN})(\s+(?P<interval_total>{DURATION_PATTERN}))?\s*$'

SPLIT_CATEGORY_PATTERN = fr'({DURATION_PATTERN})\s*(?!hr|am|pm)(\w[\w\-_/]*)'
SPLIT_LINE = fr'^\s*{SPLIT_CATEGORY_PATTERN}\s*(,\s*{SPLIT_CATEGORY_PATTERN}\s*)*$'
