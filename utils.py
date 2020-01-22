import datetime

NOW = datetime.datetime.now()
TODAY = NOW.date()


def td_hms(td, fmt='{hours:d}:{minutes:02d}:{seconds:02d}'):
    seconds = td.total_seconds()
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    d = {
            'hours': round(hours),
            'minutes': round(minutes),
            'seconds': round(seconds),
    }
    return fmt.format(**d)
