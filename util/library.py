import os
import logging
from typing import List
from dataclasses import dataclass
from enum import Enum, auto

from udlf.trackinfo import TrackInfo,UnknownFormatError

logger = logging.getLogger(__name__)

IGNORE_FILES = ['System Volume Information', '$RECYCLE.BIN', 'thumbs.db', '.DS_Store', '.Spotlight-V100']

"""
    This is a workaround for argparser being rather limited in its capabilities.
    See https://stackoverflow.com/a/74492728. All subcommands that want to access the library
    must call this function on their parser.
"""
def library_cmdline_opt(parser):
    parser.add_argument(
        "library_path",
        nargs='*',
        help="Paths to search for library files. Defaults to searching the current directory"
    )

class MergeOverwriteMode(Enum):
    NEVER = auto()
    REPLACE = auto()
    CLEAR = auto()

@dataclass
class Library:
    paths: List[str]

    def __init__(self, paths = []):
        if len(paths) == 0: paths = ['.']
        self.paths = [os.path.abspath(p) for p in paths]
    
    def __iter__(self):
        for path in self.paths:
            for root, dirs, files in os.walk(path):
                if any(root.endswith(s) for s in IGNORE_FILES): continue
                for file in files:
                    if file.startswith('.'): continue
                    if any(file.endswith(s) for s in IGNORE_FILES): continue

                    track_path = os.path.join(root, file)
                    try:
                        yield TrackInfo.load(track_path)
                    except UnknownFormatError:
                        logger.error(f'Unknown file format for {track_path}')
                    except Exception as e:
                        logger.exception(f'Could not process track {track_path}')

class Cancel(Exception): pass
class CancellableUpdate:
    def __init__(self, enter_ret, callback):
        self.enter_ret = enter_ret
        self.callback = callback
    def __enter__(self): return self.enter_ret
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.callback(exc_type == Cancel, self.enter_ret)
        return exc_type == Cancel
