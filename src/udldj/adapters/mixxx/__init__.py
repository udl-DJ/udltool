import os
import sqlite3
import pathlib
import platform
import struct
import itertools

from . import beats_pb2
from udlf.marker import Marker
from udlf.beatgrid import Beatgrid, BeatgridRegion
from udlf.utiltypes import Color

from udlf.baselibrary import BaseTrackInfo, BaseLibrary

# ---------- MISC SETUP ----------- #

NAME = "Mixxx"
DESC = "Connects your Mixxx (https://mixxx.org/) library database to UDL."

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

# ---------- BEATGRID PROCESSING ----------- #
# Mixxx has several different types of beatgrids
# For now, we're interested in the Beatgrid2 format
# TODO: Support others...

def beatgrid2_parser(binary, samplerate):
    bg2 = beats_pb2.BeatGrid()
    bg2.ParseFromString(binary)

    if bg2.first_beat is None or bg2.first_beat.frame_position is None: return None
    if bg2.bpm is None or bg2.bpm.bpm is None: return None

    return Beatgrid(
        regions=[BeatgridRegion(
            start = bg2.first_beat.frame_position / samplerate,
            bpm = bg2.bpm.bpm,
            length = 1, # Only need the downbeat; Remaining beats are implicit
            fbi = 0,
            bpb = 0
        )]
    )
def beatgrid2_serializer(beatgrid, samplerate):
    bg2 = beats_pb2.BeatGrid(
        bpm=beats_pb2.Bpm(
            source = beats_pb2.Source.USER,
            bpm = beatgrid.regions[0].bpm
        ),
        first_beat=beats_pb2.Beat(
            enabled = True,
            source = beats_pb2.Source.USER,
            frame_position = int(beatgrid.regions[0].start * samplerate)
        )
    )
    
    return bg2.SerializeToString()

BEATGRID_PROCESSORS = {
    'BeatGrid-2.0': (beatgrid2_parser, beatgrid2_serializer)
}
def beatgrid_serializer(beatgrid, samplerate):
    if beatgrid is None: return (None, None)
    regions = len(beatgrid.regions)
    proc = None
    if regions == 0: proc = None
    elif regions == 1: proc = 'BeatGrid-2.0'
    else: raise ValueError('Currently, variable beatgrids are not supported by the Mixxx adapter')
    return None if proc is None else (proc, BEATGRID_PROCESSORS[proc][1](beatgrid, samplerate))

# ---------- GENERAL TRACK/LIBRARY INFO ----------- #

# Mixxx has more, but this is what I'm supporting for now
# https://github.com/mixxxdj/mixxx/blob/2647820e88754051b87dfec79d29f1180bec44e0/src/track/cueinfo.h#L11
CUE_MAIN = 2
CUE_HOT = 1
CUE_LOOP = 4

""" SQL columns that we update on track save """
TRACK_DATA_KEYS_SAVE = ['beats', 'beats_version']
""" SQL columns that we want in track data """
TRACK_DATA_KEYS = [*TRACK_DATA_KEYS_SAVE, 'id', 'samplerate', 'channels', 'duration']
""" SQL columns that we update on cuepoint save """
CUES_DATA_SAVE = ['position', 'length', 'label', 'color']
""" SQL columns that we want in cuepoint data """
CUES_DATA = [*CUES_DATA_SAVE, 'type', 'hotcue']
class TrackInfo(BaseTrackInfo):
    """ Dict of SQL column name -> value """
    track_data = {}
    """ Dict of (cue type, hotcue ID) -> dict of SQL column name -> value """
    cue_data = {}

    def loadbeatgrid(self):
            (beats, beats_ver) = (self.track_data['beats'], self.track_data['beats_version'])
            if beats is None:
                return None
            elif beats_ver in BEATGRID_PROCESSORS:
                return BEATGRID_PROCESSORS[beats_ver][0](beats, self.track_data['samplerate'])
            else:
                raise ValueError(f'Unsupported beatgrid type {beats_ver}')
    def savebeatgrid(self, grid):
        (proc, grid) = beatgrid_serializer(grid, self.track_data['samplerate'])
        self.track_data['beats_version'] = proc
        self.track_data['beats'] = grid

    """ Marker positions are scaled by this factor; Represents sample position in audio """
    @property
    def posdivisor(self): return self.track_data['samplerate'] * self.track_data['channels']
    """ Load any cue by type and hotcue index; Called by specific cue methods below """
    def _loadcuegeneric(self, cue_type, cue_index=-1):
        selector = (cue_type, cue_index)
        if selector in self.cue_data:
            data = self.cue_data[selector]
            return Marker(
                position = data['position'] / self.posdivisor,
                length = (data['length'] / self.posdivisor) if data['length'] > 0 else None,
                name = data['label'] if data['label'] else None,
                color = Color(*[int(c) for c in struct.pack('<I',data['color'])[1:]])
            )
        return None
    """ Save any cue by type and hotcue index; Called by specific cue methods below """
    def _savecuegeneric(self, cue, cue_type, cue_index=-1):
        selector = (cue_type, cue_index)
        if cue is None:
            if selector in self.cue_data: del self.cue_data[selector]
            return

        self.cue_data[selector] = {
            'position': cue.position * self.posdivisor,
            'length': (cue.length or 0) * self.posdivisor,
            'label': cue.name or '',
            'color': 0 if cue.color is None else struct.unpack('<I', bytes([0,cue.color.R,cue.color.G,cue.color.B]))[0]
        }

    def loadcue(self): return self._loadcuegeneric(cue_type=CUE_MAIN)
    def savecue(self, marker): return self._savecuegeneric(marker, cue_type=CUE_MAIN)

    # TODO: Is there a limitation on the number of hotcues in Mixxx?
    def loadhotcues(self, i): return self._loadcuegeneric(cue_type=CUE_HOT, cue_index=i)
    def savehotcues(self, i, marker):
        if i < 0: raise ValueError('Invalid cue index')
        return self._savecuegeneric(marker, cue_type=CUE_HOT, cue_index=i)
    def maxhotcues(self): return -1
    def storedhotcues(self):
        return max(itertools.chain([0], (i + 1 for (t, i) in self.cue_data if t == CUE_HOT)))

    # Mixxx doesn't have memory cues
    def loadmemorycues(self, i): pass
    def savememorycues(self, i, marker): pass
    def maxmemorycues(self): return 0
    def storedmemorycues(self): return 0

    # Mixxx has a single saved loop
    def loadsavedloops(self, i): return self._loadcuegeneric(cue_type=CUE_LOOP, cue_index=-1) if i == 0 else None
    def savesavedloops(self, i, marker):
        if i != 0: raise ValueError('Invalid loop index')
        return self._savecuegeneric(marker, cue_type=CUE_LOOP, cue_index=-1)
    def maxsavedloops(self): return 1
    def storedsavedloops(self): return 1 if (CUE_LOOP, -1) in self.cue_data else 0

    # Mixxx doesn't have aribtrary phrases
    def loadphrases(self, i): pass
    def savephrases(self, i, marker): pass
    def maxphrases(self): return 0
    def storedphrases(self): return 0

SQL_SELTRCK = 'library.location = (SELECT id FROM track_locations WHERE track_locations.location = ?)'
SQL_SELCUE = f'cues.track_id = (SELECT id FROM library WHERE {SQL_SELTRCK})'
class Library(BaseLibrary):
    def __init__(self, db_loc): self.db_loc = db_loc
    def open(self): self.con = sqlite3.connect(self.db_loc)
    def close(self): self.con.close()

    """ Iterates over matching entries in the library database. Used to get all or individual tracks. """
    def _libiter(self, query_suffix, args):
        sql = 'SELECT track_locations.location,' + ','.join(f'library.{s}' for s in TRACK_DATA_KEYS) + ' FROM library'
        sql += ' INNER JOIN track_locations ON library.location = track_locations.id' + query_suffix
        cur = self.con.execute(sql, args)
        while True:
            resp_raw = cur.fetchone()
            if resp_raw is None: return
            location = resp_raw[0]
            resp_dict = {k: v for (k, v) in zip(TRACK_DATA_KEYS, resp_raw[1:])}

            cues_raw = self.con.execute(
                'SELECT ' + ','.join(CUES_DATA) + ' FROM cues WHERE track_id = ?',
                (str(resp_dict['id']),)
            ).fetchall()
            cues_raw_dicts = [{k: v for (k, v) in zip(CUES_DATA, cue)} for cue in cues_raw]
            cues_dict = {(c['type'], c['hotcue']): c for c in cues_raw_dicts}

            ti = TrackInfo()
            ti.track_data = resp_dict
            ti.cue_data = cues_dict
            yield (location, ti)
    
    def emptytrack(self):
        # Limitation: We'd have to query the sample rate and channel count from the audio file itself
        raise ValueError('Currently only able to modify existing tracks')
        #return TrackInfo()

    def __iter__(self): return self._libiter('', [])
    def __getitem__(self, track_location):
        for (name, track) in self._libiter(
            ' WHERE track_locations.location = ?',
            (track_location,)
        ): return track
        return None
    def __setitem__(self, track_location, track_info):
        if track_info is None: raise ValueError('Must explicitly call del to delete track data')

        existing_ti = self[track_location]
        if existing_ti is None:
            # Limitation: We'd have to query the sample rate and channel count from the audio file itself
            raise ValueError('Mixxx adapter currently only supports updating existing tracks, not inserting new ones')

        # Make sure the track data is actually in Mixxx format...
        # That way we can access the raw SQL column data
        if not isinstance(track_info, TrackInfo):
            existing_ti.assign(track_info)
            track_info = existing_ti
        
        cur = self.con.cursor()

        ph = ','.join(f'{k} = ?' for k in TRACK_DATA_KEYS_SAVE)
        cur.execute(
            f'UPDATE OR FAIL library SET {ph} WHERE {SQL_SELTRCK}',
            [*(track_info.track_data[k] for k in TRACK_DATA_KEYS_SAVE), track_location]
        )
        assert(cur.rowcount > 0)

        def make_cue_sql(cur, t, i, data_store):
            data = data_store[(t, i)] if (t,i) in data_store else None
            if data is None:
                cur.execute(
                    f'DELETE FROM cues WHERE {SQL_SELCUE} AND cues.type = {t} AND cues.hotcue = {i}',
                    (track_location,)
                )
            else:
                ph = ','.join(CUES_DATA_SAVE)
                ky = ','.join('?' for k in CUES_DATA_SAVE)
                sel = f'WHERE {SQL_SELCUE} AND cues.type = {t} AND cues.hotcue = {i}'
                cur.execute(
                    f'INSERT OR REPLACE INTO cues (id,track_id,type,hotcue,{ph})'+
                    f' VALUES ((SELECT id FROM cues {sel}),(SELECT id FROM library WHERE {SQL_SELTRCK}),{t},{i},{ky})',
                    [track_location, track_location, *(data[k] for k in CUES_DATA_SAVE)]
                )

        make_cue_sql(cur, CUE_MAIN, -1, track_info.cue_data)
        make_cue_sql(cur, CUE_LOOP, -1, track_info.cue_data)

        for i in range(0, track_info.hotcues.stored): make_cue_sql(cur, CUE_HOT, i, track_info.cue_data)
        cur.execute(
            f'DELETE FROM cues WHERE {SQL_SELCUE} AND cues.type = {CUE_HOT} AND cues.hotcue >= {track_info.hotcues.stored}',
            (track_location,)
        )

        self.con.commit()

        return track_info
    def __delitem__(self, track_location):
        cur = self.con.cursor()
        cur.execute(f'DELETE FROM cues WHERE {SQL_SELCUE}', (track_location,))
        cur.execute(f'DELETE FROM library WHERE {SQL_SELTRCK}', (track_location,))
        cur.execute('DELETE FROM track_locations WHERE location = ?', (track_location,))
        self.con.commit()
