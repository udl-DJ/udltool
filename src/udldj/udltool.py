import sys
import argparse
import logging
from commands import COMMANDS
from util.library import Library
from util.info import NAME,DESC,VERSION

class CustomFormatter(logging.Formatter):
    cyan = "\x1b[36;20m"
    it_cyan = "\x1b[36;3m"
    grey = "\x1b[37;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(name)s] %(levelname)s: %(message)s"

    FORMATS = {
        logging.DEBUG: it_cyan + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

logger = logging.getLogger(__name__)
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(CustomFormatter())
logging.getLogger().addHandler(log_handler)

parser = argparse.ArgumentParser(prog=NAME, description=DESC, epilog=f'Version {VERSION}')

parser.add_argument('-v', '--verbose', action='count', default=0)

subparsers = parser.add_subparsers(
    dest="subcommand",
    help="Subcommand to run. Pass '-h' to a subcommand for more information."
)

for (k, v) in COMMANDS.items():
    v.setup_args(subparsers.add_parser(k))

args = parser.parse_args()
logging.getLogger().setLevel(logging.INFO - args.verbose * 10)

assert(args.subcommand)
library = Library(paths=args.library_path) if 'library_path' in args else None
COMMANDS[args.subcommand].run(args, library)
