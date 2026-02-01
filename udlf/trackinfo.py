import os

from typing import List,Optional
from mutagen import MutagenError
from mutagen.id3 import ID3
from mutagen.id3._util import ID3NoHeaderError

from .id3 import UDL_ID3
from .dictify import dictify,undictify
from .marker import Beatgrid,Marker

class UnknownFormatError(ValueError): pass

class TrackInfo(UDL_ID3):
    def __init__(self, track_location, tags = None):
        if tags is None: tags = ID3()
        super().__init__(tags)
        self.track_location = track_location
    @staticmethod
    def load(track_location):
        fmt = track_location.split('.')[-1].lower()
        if fmt == 'mp3':
            t = ID3()

            try:
                try: t.load(track_location)
                except MutagenError as e:
                    # Mutagen does not properly set __cause__
                    # I don't want to throw MutagenErrors out because the outside code
                    # should be independent of Mutagen
                    # Mutagen also sometimes encapsulates its own errors inside MutagenErrors
                    # So I need to first break the encapsulation with the outer try
                    raise e.args[0] if e.args and isinstance(e.args[0], Exception) else e
            except ID3NoHeaderError: pass # We may not have a header yet

            return TrackInfo(track_location, t)
        else:
            raise UnknownFormatError(f'Unknown file format {fmt}')
    def save(self):
        fmt = self.track_location.split('.')[-1].lower()
        if fmt == 'mp3':
            self.id3tags.save(self.track_location)
        else:
            raise UnknownFormatError(f'Unknown file format {fmt}')
    
    def getbeatgrid(self):
        beatgrid = self["beatgrid"]
        if beatgrid is None: return None
        return undictify(Beatgrid, beatgrid)
    def setbeatgrid(self, beatgrid):
        if type(beatgrid) != Beatgrid: raise ValueError('Not a beatgrid')
        self["beatgrid"] = dictify(beatgrid)
    
    def getmarkers(self, name):
        markers = self[f"markers/{name}"]
        return undictify(List[Optional[Marker]], markers)
    def setmarkers(self, name, markers):
        if not isinstance(markers, list): raise ValueError('Not a list')
        for marker in markers:
            if not isinstance(marker, Marker) and not marker is None:
                raise ValueError('Found non-marker type in list')
        self[f"markers/{name}"] = dictify(markers)
    def getcuepoint(self):
        cues = self.getmarkers("cue")
        return cues[0] if len(cues) else None
    def setcuepoint(self, cuepoint): self.setmarkers("cue", [cuepoint])
    def gethotcues(self): return self.getmarkers("hotcue")
    def sethotcues(self, cues): self.setmarkers("hotcue", cues)
    def getmemoryCues(self): return self.getmarkers("memory")
    def setmemoryCues(self, cues): self.setmarkers("memory", cues)
    def getloops(self): return self.getmarkers("loop")
    def setloops(self, cues): self.setmarkers("loop", cues)
    def getphrases(self): return self.getmarkers("phrase")
    def setphrases(self, cues): self.setmarkers("phrase", cues)
