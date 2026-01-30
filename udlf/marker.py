import math
from typing import Optional,List,Tuple,Union
from dataclasses import dataclass
from enum import Enum
from abc import ABC,abstractmethod
from .dictify import AutoDictify, undictify, undictifyDictUnion

from .utiltypes import Color

""" Region of constant tempo. """
@dataclass
class BeatgridElement:
    length: float
    bpm: float
    bpb: int = 4 # Beats Per Bar
    dbs: int = 0 # DownBeat Shift -- Shifts the downbeat counter
    
    @staticmethod
    def undictify(v, undictifiers=None): return BeatgridElement(
        *undictify(Union[Tuple[float, float],Tuple[float, float, int],Tuple[float, float, int, int]], v, undictifiers)
    )
    def dictify(self, dictifiers=None):
        if self.dbs != 0: return [self.length, self.bpm, self.bpb, self.dbs]
        elif self.bpb != 4: return [self.length, self.bpm, self.bpb]
        else: return [self.length, self.bpm]
    
    """ Number of beats (can be non-integer) in this element. """
    def beat_length(self): return self.beatindex(self.length)
    """ Returns a tuple of (length, beat_length) """
    def elapsed(self): return (self.length, self.beat_length())
    """ Index of beat at a position. Returns None if outside. """
    def beatindex(self, pos):
        if pos < 0.0 or pos > self.length: return None
        return pos * (self.bpm / 60.0)
    """ Position of a beat at an index. Returns None if outside. """
    def beatpos(self, index):
        if index < 0.0 or index > self.beat_length(): return None
        return index / (self.bpm / 60.0)

""" Utility class for a single beat """
@dataclass
class Beat:
    index: int
    position: float
    is_downbeat: bool
    """
        Creates a beat at the given `index` and `position` inside a bar of beat length `bpb` with a downbeat position of
        `dbi` (does not have to be nearby this beat, just needs to be *a* downbeat on the same grid as `bpb`).
    """
    @staticmethod
    def create(index, bpb, dbi, position):
        return Beat(index, position, (index - dbi) % bpb == 0)
""" Iterator over beats """
class Beats:
    beatgrid = None
    pos: float # Position of current element
    index: int = 0 # Beat index of iterator
    index_sum: float = 0 # Beat index of current element
    element_i: int = 0 # Index of current element
    dbi: int = 0 # Downbeat index
    def __init__(self, g):
        self.beatgrid = g
        self.pos = g.start
        if len(g.elements) and not g.elements[0].dbs is None:
            self.dbi = g.elements[0].dbs
    def __iter__(self): return Beats(self.beatgrid)
    def __next__(self):
        while True:
            element = self.beatgrid.elements[self.element_i]
            (el, eb) = element.elapsed()
            
            if self.index - self.index_sum <= eb: # We're still in this element
                beat = Beat.create(
                    self.index,
                    element.bpb,
                    self.dbi,
                    self.pos + element.beatpos(self.index - self.index_sum)
                )
                self.index += 1
                return beat
            
            self.pos += el
            self.index_sum += eb
            
            self.element_i += 1
            if self.element_i >= len(self.beatgrid.elements): raise StopIteration
            
            # Set the downbeat index to shift into the current element
            # If switching time signatures, this is necessary to ensure the time signature is done
            # relative to the shift, and not relative to the start of the track
            # Alignment is done to the LAST downbeat, so if the switch is done on an off beat, expect
            # beat alignment to be with respect to the last downbeat of the previous region
            self.dbi = self.index - ((self.index - self.dbi) % element.bpb) # Calculates LAST downbeat
            self.dbi -= self.beatgrid.elements[self.element_i].dbs

""" How to handle beats appearing exactly on the border between two elements """
class BorderBeatMode(Enum):
    """ Border beats appear in the left hand neighbor """
    LAST = -1
    """ Border beats appear in both bordering elements """
    BOTH = 0
    """ Border beats appear in right hand neighbor """
    NEXT = 1
""" Information about a beatgrid element """
@dataclass
class BeatgridElementMeta(object):
    """ Start position of beatgrid """
    start: float
    """ End position of beatgrid """
    end: float
    """ First beat in the beatgrid """
    firstbeat: Beat
    """ Last beat in the beatgrid """
    lastbeat: Beat
    """ Downbeat Index """
    dbi: int
""" Iterator over beatgrid elements """
class BeatgridElements:
    mode: BorderBeatMode # See `elements_meta` in beatgrid
    element_i: int = 0 # Index of current element
    pos: float = 0.0 # Position of current element
    index: float = 0.0 # Beat index of current element
    dbi: int = 0 # Downbeat index
    def __init__(self, g, mode):
        self.beatgrid = g
        self.mode = mode
        self.pos = g.start
        if len(g.elements) and not g.elements[0].dbs is None:
            self.dbi = g.elements[0].dbs
    def __iter__(self): return BeatgridElements(self.beatgrid, self.mode)
    def __next__(self):
        if self.element_i >= len(self.beatgrid.elements): raise StopIteration
        element = self.beatgrid.elements[self.element_i]
        (el, eb) = element.elapsed()
        
        is_first = self.element_i == 0
        is_last = self.element_i == (len(self.beatgrid.elements) - 1)
        
        start = self.pos
        end = self.pos + el
        
        fbi = int(math.ceil(self.index)) # First Beat Index
        lbi = int(math.floor(self.index + el)) # Last Beat Index
        self.dbi = fbi - ((self.index - fbi) % element.bpb) - element.dbs # Calculates LAST downbeat
        
        if not is_first and self.mode == BorderBeatMode.LAST and element.beatpos(fbi - self.index) == 0.0:
            fbi += 1
        firstbeat = Beat.create(fbi, element.bpb, self.dbi, self.pos + element.beatpos(fbi - self.index))
        
        if not is_last and self.mode == BorderBeatMode.NEXT and element.beatpos(lbi - self.index) == el:
            lbi -= 1
        lastbeat = Beat.create(lbi, element.bpb, self.dbi, self.pos + element.beatpos(lbi - self.index))
        
        # Downbeat index within the element
        dbi = (self.dbi - fbi) % element.bpb
        
        self.pos += el
        self.index += eb
        self.element_i += 1
        
        return (BeatgridElementMeta(start, end, firstbeat, lastbeat, dbi), element)

""" A beatgrid of one or more regions of constant tempo. """
@dataclass
class Beatgrid:
    start: float
    elements: List[BeatgridElement]
    
    """ Index of beat at a position. Returns None if outside. """
    def beatindex(self, pos):
        pos -= self.start
        if pos < 0.0: return None
        index = 0.0
        for element in self.elements:
            (el, eb) = element.elapsed()
            if pos <= el: return index + element.beatindex(pos)
            index += element.beat_length()
            pos -= element.length
        return None
    """ Position of a beat at an index. Returns None if outside. """
    def beatpos(self, index):
        if index < 0.0: return None
        pos = self.start
        for element in self.elements:
            (el, eb) = element.elapsed()
            if index <= eb: return element.beatpos(index) + pos
            pos += el
            index -= eb
    
    def beat(self, index): pass
    def beats(self): return Beats(self)
    def elements_meta(self, mode=BorderBeatMode.NEXT): return BeatgridElements(self, mode)

""" A point or region within a song. """
class Marker(ABC):
    name: Optional[str] = None
    color: Optional[Color] = None
    @abstractmethod
    def absolute(self): pass
    @staticmethod
    def undictify(v, undictifiers=None): return undictifyDictUnion(v, "type", {
        "timed": TimedMarker, "beatgrid": BeatgridMarker
    })
    """ Find the position (in seconds) of a marker on a beatgrid. """
    @abstractmethod
    def resolve(self, beatgrid): pass

""" A marker tied to a particular time value. """
@dataclass
class TimedMarker(AutoDictify, Marker):
    position: float
    length: Optional[float] = None
    # Workaround https://stackoverflow.com/a/53085935
    name: Optional[str] = None
    color: Optional[Color] = None
    
    def absolute(self): return True
    def dictify(self, dictifiers=None): return {"type": "timed", **super().dictify(dictifiers)}
    def resolve(self, beatgrid): return self.position

""" A marker tied to a particular beat on the beatgrid. """
@dataclass
class BeatgridMarker(AutoDictify, Marker):
    beat: int
    beats: Optional[int] = None
    # Workaround https://stackoverflow.com/a/53085935
    name: Optional[str] = None
    color: Optional[Color] = None
    
    def absolute(self): return False
    def dictify(self, dictifiers=None): return {"type": "beatgrid", **super().dictify(dictifiers)}
    def resolve(self, beatgrid): return beatgrid.beatpos(self.beat)

if __name__ == "__main__":
    d1 = TimedMarker(1.0, name='Hotcue 1', color=Color(255,0,0)).dictify()
    d2 = BeatgridMarker(1, name='Hotcue 2', color=Color(0,255,0)).dictify()
    print(d1)
    print(d2)
    print(Marker.undictify(d1))
    print(Marker.undictify(d2))
    
    print()
    
    cb = BeatgridElement(10.0, 120.0)
    # Test for consistency
    for i in range(0, 11):
        assert(cb.beatpos(cb.beatindex(i)) == i)
    
    print()
    
    grid = Beatgrid(5.0, [BeatgridElement(10.0, 120.0), BeatgridElement(10.0, 60.0, 3)])
    # Test using known values
    assert(grid.beatindex(10.0) == 10.0)
    assert(grid.beatindex(20.0) == 25.0)
    assert(grid.beatindex(25.0) == 30.0)
    assert(grid.beatindex(30.0) is None)
    assert(grid.beatindex(0.0) is None)
    
    assert(grid.beatpos(10.0) == 10.0)
    assert(grid.beatpos(25.0) == 20.0)
    assert(grid.beatpos(30.0) == 25.0)
    
    # Consistency test
    for i in range(5, 26):
        assert(grid.beatpos(grid.beatindex(i)) == i)
    
    for beat in grid.beats():
        print(beat)
    
    print()
    grid = Beatgrid(4.0, [BeatgridElement(4.0, 60.0), BeatgridElement(3.0, 60.0, 3), BeatgridElement(4.0, 60.0, 3, 1)])
    for beat in grid.beats():
        print(beat)
    assert([*grid.beats()] == [
        Beat(index=0, position=4.0, is_downbeat=True),
        Beat(index=1, position=5.0, is_downbeat=False),
        Beat(index=2, position=6.0, is_downbeat=False),
        Beat(index=3, position=7.0, is_downbeat=False),
        Beat(index=4, position=8.0, is_downbeat=True),
        Beat(index=5, position=9.0, is_downbeat=False),
        Beat(index=6, position=10.0, is_downbeat=False),
        Beat(index=7, position=11.0, is_downbeat=True),
        Beat(index=8, position=12.0, is_downbeat=False),
        Beat(index=9, position=13.0, is_downbeat=True),
        Beat(index=10, position=14.0, is_downbeat=False),
        Beat(index=11, position=15.0, is_downbeat=False)
    ])
    
    print()
    for (meta, el) in grid.elements_meta(BorderBeatMode.NEXT):
        print(meta)

