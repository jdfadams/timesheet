import logging
import sys

if not __package__:
    import os
    path = os.path.abspath(__file__)
    path = os.path.dirname(path)
    __package__ = os.path.basename(path)
    path = os.path.dirname(path)
    sys.path.append(path)

from timesheet import parser

logger = logging.getLogger(__name__)


def _configure_logging(verbosity):
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    log_levels = [
            logging.ERROR,
            logging.INFO,
            logging.DEBUG,
    ]
    log_level = log_levels[min(verbosity, len(log_levels) - 1)]
    handler.setLevel(log_level)
    logger.setLevel(log_level)


def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(description='parse a timesheet')
    parser.add_argument('timesheet', help='a path to a timesheet')
    parser.add_argument('-v', action='count', default=0, dest='verbosity', help='repeat to increase verbosity')
    args = parser.parse_args()
    return args


def main():
    args = _parse_args()
    _configure_logging(args.verbosity)
    parser.parse(args.timesheet)
    return 0


if __name__ == '__main__':
    sys.exit(main())
