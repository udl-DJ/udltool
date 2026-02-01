import os
from typing import List
from dataclasses import dataclass
from enum import Enum, auto

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
