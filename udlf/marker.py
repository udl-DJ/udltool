from typing import Optional,List,Tuple,Union
from dataclasses import dataclass
from abc import ABC,abstractmethod
from .dictify import AutoDictify, undictify, undictifyDictUnion

from .utiltypes import Color

""" Region of constant tempo. """
@dataclass
class BeatgridElement:
    length: float
    bpm: float
    bpb: int = 4 # Beats Per Bar
    dbs: Optional[int] = None # DownBeat Set -- Changes the downbeat position to the nth beat in this grid
    
    @staticmethod
    def undictify(v, undictifiers=None): return BeatgridElement(
        *undictify(Union[Tuple[float, float],Tuple[float, float, int],Tuple[float, float, int, int]], v, undictifiers)
    )
    def dictify(self, dictifiers=None):
        if not self.dbs is None: return [self.length, self.bpm, self.bpb, self.dbs]
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
    
    cb = BeatgridElement(10.0, 120.0)
    assert(cb.beat_length() == cb.beatindex(cb.length))
    for i in range(0, 11):
        assert(abs(cb.beatpos(cb.beatindex(i)) - i) < 0.0001)
    
    grid = Beatgrid(5.0, [BeatgridElement(10.0, 120.0), BeatgridElement(10.0, 60.0)])
    assert(grid.beatindex(10.0) == 10.0)
    assert(grid.beatindex(20.0) == 25.0)
    assert(grid.beatindex(25.0) == 30.0)
    assert(grid.beatindex(30.0) is None)
    assert(grid.beatindex(0.0) is None)
    
    assert(grid.beatpos(10.0) == 10.0)
    assert(grid.beatpos(25.0) == 20.0)
    assert(grid.beatpos(30.0) == 25.0)
    
    for i in range(5, 26):
        assert(grid.beatpos(grid.beatindex(i)) == i)

