import collections
import logging
import re

from . import patterns as p

logger = logging.getLogger(__name__)

DAY = 'DAY'
EXTRA = 'EXTRA'
INTERVAL = 'INTERVAL'
SPLIT = 'SPLIT'

TOKENS = [
        (DAY, p.DAY_LINE),
        (EXTRA, p.EXTRA_LINE),
        (INTERVAL, p.INTERVAL_LINE),
        (SPLIT, p.SPLIT_LINE),
]

Token = collections.namedtuple('Token', [
        'match',
        'n',
        'type',
])


def tokenize(path):
    LOG_MSG = '{:>9} | {}'
    with open(path, 'r') as fp:
        lines = fp.readlines()
    line_re = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKENS)
    line_re = re.compile(line_re)
    tokens = []
    for n, line in enumerate(lines, 1):
        line = line.rstrip()
        match = line_re.match(line)
        if match:
            msg = LOG_MSG.format(match.lastgroup, match.group())
            logger.info(msg)
            token = Token(match=match, n=n, type=match.lastgroup)
            tokens += [token, ]
        else:
            msg = LOG_MSG.format('', line)
            logger.debug(msg)
    return tokens


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    parser.add_argument('--verbose', '-v', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(format='%(message)s', level=level)
    tokenize(args.path)


if __name__ == '__main__':
    main()
