import logging

from adapters import ADAPTERS
from util.library import library_cmdline_opt,MergeOverwriteMode
from udlf.trackinfo import TrackInfo,UnknownFormatError

logger = logging.getLogger(__name__)

def setup_args(parser):
    parser.add_argument(
        'adapter',
        choices=ADAPTERS,
        help="Adapter to import from. See options below.",
        metavar='adapter'
    )
    parser.add_argument(
        '-o', '--overwrite',
        choices=('never', 'replace', 'clear'),
        help="Never (default) does not overwrite UDL tags; Replace replaces UDL tags with tags " \
            "from this source; Clear removes all existing tags present on any file in this " \
            "source, even if there is no data available. Use with caution.",
        default="never"
    )
    for (n,a) in ADAPTERS.items():
        a.setup_args(parser.add_argument_group(f"{a.NAME} Adapter ('{n}')", a.DESC))
    
    library_cmdline_opt(parser)

def run(args, library):
    adapter = ADAPTERS[args.adapter]
    mode = MergeOverwriteMode[args.overwrite.upper()]
    with adapter.Connection(args) as con:
        for info in con.read_tracks(library):
            try:
                tosave_info = TrackInfo.load(info.track_location)

                # Keep a reference copy around
                _original_info = TrackInfo(info.track_location)
                _original_info.assign(tosave_info)

                if mode == MergeOverwriteMode.CLEAR:
                    logger.debug(f'Clearing info on {info.track_location}')
                    tosave_info.clear()
                
                tosave_info.assign(info, overwrite=mode == MergeOverwriteMode.REPLACE)

                if _original_info == tosave_info:
                    logger.debug(f'No changes made to {info.track_location}; Skipping write...')
                else:
                    tosave_info.save()
                    logger.info(f'Wrote to {info.track_location}')
            except FileNotFoundError:
                # This is only a warning since Mixxx seems to leave deleted or moved files
                # hanging around
                logger.warn(f'Could not find {info.track_location}')
            except UnknownFormatError:
                logger.error(f'Unknown file format for {info.track_location}')
            except Exception as e:
                logger.exception(f'Could not process track {info.track_location}')
