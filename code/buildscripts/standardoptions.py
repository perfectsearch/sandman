import logging
import logging.handlers
import argparse
import os

LOG_FORMAT_FOR_CONSOLE = '%(asctime)s %(name)-12s %(levelname)-8s\t%(message)s'
LOG_FORMAT_FOR_FILE = '%(asctime)s %(name)s[%(process)d] %(levelname)-10s %(message)s'

_LOG_LEVELS = (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL)
_NUMBER_OF_LOGGING_LEVELS = len(_LOG_LEVELS)
_DEFAULT_LEVEL = _LOG_LEVELS.index(logging.WARNING)

def add_standard_arguments(parser):
    class MoreVerbose(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            newval = getattr(namespace, self.dest, _DEFAULT_LEVEL) - 1
            newval = max(newval, 0)
            setattr(namespace, self.dest, newval)

    class LessVerbose(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            newval = getattr(namespace, self.dest, _DEFAULT_LEVEL) + 1
            newval = min(_NUMBER_OF_LOGGING_LEVELS-1, newval)
            setattr(namespace, self.dest, newval)

    parser.add_argument('-q', '--quiet', dest='verbosity', help='run quieter',
                        nargs=0, type=int, action=LessVerbose, default=_DEFAULT_LEVEL)
    parser.add_argument('-v', '--verbose', dest='verbosity', help='show verbose output',
                        nargs=0, type=int, action=MoreVerbose, default=_DEFAULT_LEVEL)
    parser.add_argument('--logfile', dest="logfile",  default=None,
                        help="Log to file instead of console")


def set_up_logging(options):
    if options.logfile is None:
        logging.basicConfig(level=_LOG_LEVELS[options.verbosity], format=LOG_FORMAT_FOR_CONSOLE)
    else:
        logfilename = os.path.normpath(options.logfile)
        root = logging.getLogger('')
        root.setLevel(_LOG_LEVELS[options.verbosity])
        handler =logging.handlers.RotatingFileHandler(logfilename, maxBytes=1000000, backupCount=5)
        handler.setFormatter(logging.Formatter(LOG_FORMAT_FOR_FILE))
        root.addHandler(handler)

