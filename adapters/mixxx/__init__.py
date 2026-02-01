import os
import sqlite3
import pathlib
import platform
import logging
import struct

from .beats_pb2 import BeatGrid as BeatGridV2
from udlf.marker import TimedMarker, Beatgrid, BeatgridRegion
from udlf.trackinfo import TrackInfo
from udlf.utiltypes import Color

logger = logging.getLogger(__name__)

NAME = "Mixxx"
DESC = "Connects your Mixxx (https://mixxx.org/) library database to UDL."

def get_one(gen, warning = None):
    res = None
    for e in gen:
        if res is None: res = e
        elif not warning is None:
            logger.warn(warning)
    return res

def default_mixx_db():
    if 'APPDATA' in os.environ:
        mixxxdir = pathlib.Path(os.environ['APPDATA']) / "Local" / "Mixxx"
    else:
        if 'HOME' in os.environ:
            confighome = pathlib.Path(os.environ['HOME'])
        else:
            confighome = pathlib.Path.home()
        if platform.system() == 'Darwin':
            mixxxdir = confighome / "Library" / "Containers" / "org.mixxx.mixxx "
            mixxxdir = mixxxdir / "Data" / "Library" / "Application Support" / "Mixxx"
        else:
            mixxxdir = confighome / ".mixxx"
    return mixxxdir / "mixxxdb.sqlite"

def beatgrid2_processor(binary, samplerate, duration):
    bg2 = BeatGridV2()
    bg2.ParseFromString(binary)
    
    startpos = bg2.first_beat.frame_position / samplerate
    beatgrid = Beatgrid(
        start = startpos,
        regions=[BeatgridRegion(
            bpm = bg2.bpm.bpm,
            length = duration - startpos
        )]
    )
    return beatgrid

BEATGRID_PROCESSORS = {
    'BeatGrid-2.0': beatgrid2_processor
}

# Mixxx has more, but this is what I'm supporting for now
# https://github.com/mixxxdj/mixxx/blob/2647820e88754051b87dfec79d29f1180bec44e0/src/track/cueinfo.h#L11
CUE_MAIN = 2
CUE_HOT = 1
CUE_LOOP = 4

def setup_args(parser):
    parser.add_argument(
        '--mixxx-db',
        type=pathlib.Path,
        default=default_mixx_db(),
        help="Override Mixxx database location"
    )

class Connection:
    def __init__(self, args): self.args = args
    def __enter__(self):
        logger.debug("Attempting to open connection to Mixxx DB")
        self.con = sqlite3.connect(self.args.mixxx_db)
        return self
    def __exit__(self, exc_type, exc_value, exc_tb):
        logger.debug("Closing connection to Mixxx DB")
    
    def read_cues(self, track_id, cuetype, samplerate, n_channels):
        cur = self.con.execute(
            'SELECT hotcue,position,length,label,color ' \
            'FROM cues WHERE type = ? AND track_id = ?',
            (cuetype, track_id)
        )
        while True:
            cue = cur.fetchone()
            if cue is None: return

            (hotcue, position, length, label, color) = cue
            color = Color(*[int(c) for c in struct.pack('<I',color)[1:]])
            marker = TimedMarker(
                position = position / (n_channels*samplerate),
                length = length if cuetype == CUE_LOOP else None,
                name = label if label else None,
                color = color
            )

            yield (hotcue, marker) if cuetype == CUE_HOT else marker
                
    def read_tracks(self, library):
        if not len(library.paths): return
        sql = \
            'SELECT library.id,track_locations.location,library.beats,library.beats_version,library.samplerate,library.channels,library.duration ' \
            'FROM library INNER JOIN track_locations ON library.location = track_locations.id ' \
            'WHERE '
        sql += ' OR '.join('track_locations.location LIKE ?' for p in library.paths)
        sql += ';'
        cur = self.con.execute(sql, [f'{p}%' for p in library.paths])
        while True:
            track = cur.fetchone()
            if track is None: return
            
            (track_id, location, beats, beats_ver, samplerate, n_channels, duration) = track

            ti = TrackInfo(location)
            
            if beats is None:
                pass # no beatgrid
            elif beats_ver in BEATGRID_PROCESSORS:
                ti.setbeatgrid(BEATGRID_PROCESSORS[beats_ver](beats, samplerate, duration))
            else:
                logger.warn(f'Unknown beatgrid type {beats_ver} on {location}; Not loading')
            
            maincue = get_one(
                self.read_cues(track_id, CUE_MAIN, samplerate, n_channels),
                f'Found more than one main cue in {location}'
            )
            mainloop = get_one(
                self.read_cues(track_id, CUE_LOOP, samplerate, n_channels),
                f'Found more than one main loop in {location}'
            )
            hotcues = {t[0]: t[1] for t in self.read_cues(track_id, CUE_HOT, samplerate, n_channels)}
            cuerange = range(0, max(hotcues.keys())+1) if len(hotcues.keys()) else []
            hotcues = [hotcues[i] if i in hotcues else None for i in cuerange]

            if maincue: ti.setcuepoint(maincue)
            if mainloop: ti.setloops([mainloop])
            if len(hotcues): ti.sethotcues(hotcues)
            
            yield ti
