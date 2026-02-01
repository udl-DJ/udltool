import os
import sqlite3
import pathlib
import platform
import logging
import struct
from pyrekordbox.rbxml import RekordboxXml

from udlf.marker import TimedMarker, Beatgrid, BeatgridRegion
from udlf.trackinfo import TrackInfo
from udlf.utiltypes import Color
from util.library import CancellableUpdate
from util.info import NAME as APP_NAME,VERSION as APP_VER

logger = logging.getLogger(__name__)

NAME = "Rekordbox XML"
DESC = "Connects your Rekordbox (https://rekordbox.com/en/) library database to UDL. " \
        "This adapter works using the Rekordbox XML import method, which is the safest " \
        "method available and is the only officially supported method."

def setup_args(parser):
    parser.add_argument(
        '--rekordbox-xml',
        type=pathlib.Path,
        help="Rekordbox XML path"
    )

def load_track_info(rk_track, udl_track): pass

def save_track_info(rk_track, udl_track):
    beatgrid = udl_track.getbeatgrid()
    if not beatgrid is None and len(beatgrid.regions):
        rk_track.tempos = []
        for (meta, el) in beatgrid.regions_meta():
            rk_track.add_tempo(
                Inizio=meta.start,
                Bpm=el.bpm,
                Metro=f'{el.bpb}/4',
                Battito=el.bpb-meta.dbi
            )
    
    maincue = udl_track.getcuepoint()
    if not maincue is None:
        resolved = maincue.resolve(beatgrid)
        if not resolved is None:
            rk_track.marks = [mark for mark in rk_track.marks if mark.Type != 'cue']
            rk_track.add_mark(
                Name=maincue.name or '',
                Type="load",
                Start=resolved[0]
            )
        else:
            logger.debug('Could not resolve main cue')
    
    loops = udl_track.getloops()
    if len(loops) and not loops[0] is None:
        resolved = loops[0].resolve(beatgrid)
        if not resolved is None:
            rk_track.marks = [mark for mark in rk_track.marks if mark.Type != 'loop']
            rk_track.add_mark(
                Name=loops[0].name or '',
                Type="loop",
                Start=resolved[0],
                End=resolved[1]
            )
        else:
            logger.debug('Could not resolve loop')
    
    hotcues = udl_track.gethotcues()
    for i in range(0, len(hotcues)):
        hotcue = hotcues[i]
        if hotcue is None: continue
        resolved = hotcue.resolve(beatgrid)
        if not resolved is None:
            rk_track.marks = [mark for mark in rk_track.marks if mark.Type != 'loop']
            rk_track.add_mark(
                Name=hotcue.name or '',
                Type="cue",
                Start=resolved[0],
                Num=i
            )
        else:
            logger.debug(f'Could not resolve hotcue {i}')

class Connection:
    def __init__(self, args): self.args = args
    def __enter__(self):
        if not self.args.rekordbox_xml:
            raise ValueError("Rekordbox XML file not specified. This isn't actually optional, that's just a limitation of argparse")
        logger.debug("Attempting to open connection to the Rekordbox XML")
        self.xmlpath = os.path.abspath(self.args.rekordbox_xml)
        try:
            self.xml = RekordboxXml(self.xmlpath, name=APP_NAME + '-pyrekordbox', version=APP_VER)
        except FileNotFoundError:
            self.xml = RekordboxXml(name=APP_NAME + '-pyrekordbox', version=APP_VER)
        return self
    def __exit__(self, exc_type, exc_value, exc_tb):
        logger.debug("Closing connection to Rekordbox")
        self.xml.save(self.xmlpath)
                
    def read_tracks(self, library):
        if False: yield # TODO yes I'm that lazy
    
    def open_track(self, track_path):
        track = TrackInfo(track_path)
        try:
            rk_track = self.xml.get_track(Location=f'{track_path}')
        except TypeError:
            rk_track = None
        
        if not rk_track is None:
            load_track_info(rk_track, track)

        def on_complete(is_cancelled, _):
            if not is_cancelled:
                save_track_info(
                    self.xml.add_track(track_path) if rk_track is None else rk_track,
                    track
                )
        
        return CancellableUpdate(track, on_complete)
        
