import os
import math
import urllib.parse
import json
import shutil
from typing import Dict,List,Tuple

from udldj.udlf.marker import Marker
from udldj.udlf.beatgrid import Beatgrid, BeatgridRegion
from udldj.udlf.utiltypes import Color, CompareContext
import udldj.util.filetools as ft

from udldj.udlf.baselibrary import BaseTrackInfo, BaseLibrary

NAME = "Audacity"
DESC = "Allows you to import/export Audacity label files. While Audacity isn't DJ software " \
        "it has a very simple label file format and is useful for debugging."

AUDACITY_DIGITS_PRECISION = 0.000001

"""
    Calculates the number of beat markers between `start` and `end`.
"""
def beatsinside(start, end, bpm):
    length = end - start
    beats = (bpm / 60.0) * length
    if beats - math.floor(beats) < AUDACITY_DIGITS_PRECISION: # Audacity has 6 digits of precision
        # We're ON the next beat; Don't include it
        return int(math.floor(beats))# + 1 - 1
    else:
        return int(math.floor(beats)) + 1 # Count the first beat

"""
    Returns a function that filters for marker data dicts with `type` `t` and `index` `i`.
    `i` may be none, in which case `index` will not be filtered.
"""
def _makemarkerfilter(t, i):
    if i is None: # Non-indexed marker; Find the marker with type `t`
        return lambda d: 'type' in d and d['type'] == t
    else: # Indexed marker; We have to match `t` and `i`
        return lambda d: 'type' in d and d['type'] == t and 'index' in d and d['index'] == str(i)

class TrackInfo(BaseTrackInfo):
    """ Audacity .txt label file data. Dict of filename -> list of (start, end, label dict) """
    label_data: Dict[str, Tuple[float, float, Dict[str, str]]]
    """ JSON datafiles for extra data. Dict of filename -> arbitrary JSON-compatible data """
    json_data: Dict[str, object]

    def __init__(self):
        self.label_data = {}
        self.json_data = {}

    def loadbeatgrid(self):
        if not 'beatgrid' in self.label_data: return None
        # TODO: Assumes Audacity exports regions in order
        return Beatgrid(regions=[
            BeatgridRegion(
                start=start,
                length=beatsinside(start, end, float(data['bpm'])),
                bpm = float(data['bpm']),
                fbi = int(data['fbi']),
                bpb = int(data['bpb']) if 'bpb' in data else 4
            ) for (start, end, data) in self.label_data['beatgrid']
        ])
    def savebeatgrid(self, grid):
        if grid is None:
            del self.label_data['beatgrid']
            return

        def makeDict(region):
            if region.bpb == 4: return {'bpm': region.bpm, 'fbi': region.fbi}
            else: return {'bpm': region.bpm, 'fbi': region.fbi, 'bpb': region.bpb}
        
        # Create beatgrid region markers
        # 60.0 / r.bpm adds another beat space to the end
        self.label_data['beatgrid'] = [
            (m.start, m.end + (60.0 / r.bpm), makeDict(r)) for (r, m) in grid.meta()
        ]
    
    """ Store a `beats` marker file that indicates the position of beats """
    def genbeats(self):
        beatgrid = self.beatgrid
        if beatgrid is None:
            del self.label_data['beats']
            return
        
        self.label_data['beats'] = [
            (
                beat.position, beat.position, {'downbeat': str(beat.is_downbeat), 'index': str(beat.index)}
            ) for beat in beatgrid.beats()
        ]
    """ Clear the beats marker file """
    def clearbeats(self): del self.label_data['beats']
    
    """
        Find a marker object with type `t` and index `i`.
        Index may be None -- In this case, an object with no index is found.
    """
    def _loadmarkergeneric(self, t, i):
        if not 'markers' in self.label_data: return None

        filt = _makemarkerfilter(t, i)
        markers = [line for line in self.label_data['markers'] if filt(line[2])]

        if len(markers) > 1:
            raise ValueError(f'More than one marker with type "{t}" at index "{i}"')
        elif len(markers) == 1:
            marker_line = markers[0] # Marker line tuple (start, end, data dict)
            marker_data = marker_line[2] # data dict
            length = marker_line[1] - marker_line[0]

            return Marker(
                position=marker_line[0],
                length=None if length < AUDACITY_DIGITS_PRECISION else length, # Ensure zero -> None
                beatlocked=bool(marker_data['beatlocked']) if 'beatlocked' in marker_data else False,
                name=str(marker_data['name']) if 'name' in marker_data else None,
                color=Color.fromhex(marker_data['color']) if 'color' in marker_data else None
            )
        else: return None
    """
        Find a marker object with type `t` and index `i`, which may be None
    """
    def _savemarkergeneric(self, t, i, m):
        if not 'markers' in self.label_data:
            self.label_data['markers'] = []
        else:
            filt = _makemarkerfilter(t, i)
            self.label_data['markers'] = [line for line in self.label_data['markers'] if not filt(line[2])]
        
        if m is None: return # Nothing to do; We've removed the old entry
        
        # Construct the additional data dict
        label_dict = {
            'type': str(t),
            'index': str(i),
            'beatlocked': str(True) if m.beatlocked else None,
            'name': None if m.name is None else str(m.name),
            'color': None if m.color is None else m.color.tohex()
        }
        # Remove any keys that have a None value
        label_dict = {k: v for (k, v) in label_dict.items() if not v is None}

        self.label_data['markers'].append((
            m.position,
            m.position if m.length is None else m.position + m.length,
            label_dict
        ))
    """ Counts the number maximum index plus one for marker type `t`. """
    def _storedmarkergeneric(self, t):
        if not 'markers' in self.label_data: return 0
        # Filter all markers with type `t`
        filt = _makemarkerfilter(t, None)
        markers = [int(line[2]['index']) for line in self.label_data['markers'] if filt(line[2])]
        # Now compute the max index stored
        return max(markers)+1 if len(markers) else 0
    
    def loadcue(self): return self._loadmarkergeneric('cue', None)
    def savecue(self, marker): return self._savemarkergeneric('cue', None, marker)

    def loadhotcues(self, i): return self._loadmarkergeneric('hotcue', i)
    def savehotcues(self, i, marker): return self._savemarkergeneric('hotcue', i, marker)
    def maxhotcues(self): return -1
    def storedhotcues(self): return self._storedmarkergeneric('hotcue')

    def loadmemorycues(self, i): return self._loadmarkergeneric('memory', i)
    def savememorycues(self, i, marker): return self._savemarkergeneric('memory', i, marker)
    def maxmemorycues(self): return -1
    def storedmemorycues(self): return self._storedmarkergeneric('memory')

    def loadsavedloops(self, i): return self._loadmarkergeneric('savedloop', i)
    def savesavedloops(self, i, marker): return self._savemarkergeneric('savedloop', i, marker)
    def maxsavedloops(self): return -1
    def storedsavedloops(self): return self._storedmarkergeneric('savedloop')

    def loadphrases(self, i): return self._loadmarkergeneric('phrase', i)
    def savephrases(self, i, marker): return self._savemarkergeneric('phrase', i, marker)
    def maxphrases(self): return -1
    def storedphrases(self): return self._storedmarkergeneric('phrase')

class Library(BaseLibrary):
    def __init__(self, lib_path, fatal_partial_loads=True):
        self.lib_path = lib_path
        self.fatal_partial_loads = fatal_partial_loads
    def open(self): pass
    def close(self): pass
    
    def emptytrack(self): return TrackInfo()

    def __iter__(self):
        # List all directories endering in .udl
        # We assume these are directories containing marker files
        # Note that we only look for lower case .udl
        for root in ft.walk_filtered(self.lib_path, yield_dirs=True):
            if root.endswith('.udl'):
                # Get the file path w/o the .udl -- This is the location of the corresponding track
                track_loc = root[:-4]
                yield (track_loc, self[track_loc])
    
    def __getitem__(self, track_location):
        ti = self.emptytrack()
        track_location = track_location + '.udl'

        # Scan all files in the track's corresponding .udl folder
        for file in ft.walk_filtered(track_location, yield_files=True, use_relpath=True):
            try:
                if file.endswith('.txt'): # Audacity label list file
                    udlname = file[:-4] # Get the name we want to use as a key in our KV dict
                    with open(os.path.join(track_location, file)) as f:
                        ti.label_data[udlname] = []
                        # Read out each Audacity label
                        for line in f:
                            line = line.split('\t')
                            if len(line) == 1 and line[0].strip() == '': continue

                            start = float(line[0])
                            end = float(line[1])
                            if not math.isfinite(start) or not math.isfinite(end):
                                raise ValueError('Bad float in Audacity label file')

                            # Parse the comment data into a KV dict
                            comment = urllib.parse.parse_qs('\t'.join(line[2:]).strip())
                            for (k, v) in comment.items():
                                if len(v) != 1: raise ValueError('Got label with multiple values for key')
                            # Ensure keys and values are one-to-one
                            comment = {k: v[0] for (k, v) in comment.items()}
                            
                            ti.label_data[udlname].append((start, end, comment))
                elif file.endswith('.json'): # Generic JSON stored data
                    udlname = file[:-5] # Get the name we want to use as a key in our KV dict
                    with open(os.path.join(track_location, file)) as f:
                        ti.json_data[udlname] = json.load(f)
                else:
                    raise ValueError(f'Got unexpected file extension parsing {file}')
            except Exception as e:
                if self.fatal_partial_loads: raise e
        return ti
    
    def __setitem__(self, track_location, track_info):
        if track_info is None: raise ValueError('Must explicitly call del to delete track data')

        # Make sure the track data is actually in Audacity format...
        if not isinstance(track_info, TrackInfo):
            (track_info, track_info_old) = (self.emptytrack(), track_info)
            track_info.assign(track_info_old)
        
        # Clean out existing files (to ensure we don't keep old data)
        del self[track_location]
        os.mkdir(track_location + '.udl')
        
        # Write out Audacity label files
        for (fname, lines) in track_info.label_data.items():
            lines = sorted(lines, key=lambda l: l[0])
            with open(os.path.join(track_location + '.udl', fname + '.txt'), 'w') as f:
                for (s, e, d) in lines:
                    f.write(f'{s:.6f}\t{e:.6f}\t{urllib.parse.urlencode(d)}\n')
        # Write out raw JSON data
        for (fname, data) in track_info.json_data.items():
            with open(os.path.join(track_location + '.udl', fname + '.json'), 'w') as f:
                json.dump(data, f)
        
    def __delitem__(self, track_location):
        udl_dir = track_location + '.udl'
        if not os.path.exists(udl_dir): return

        if os.path.islink(udl_dir) or not os.path.isdir(udl_dir):
            # File or symbolic link
            os.unlink(udl_dir)
        else:
            # Directory; Need recursion
            shutil.rmtree(track_location + '.udl')
