import math
from typing import Optional,List,Tuple
from dataclasses import dataclass
from abc import ABC,abstractmethod
from .dictify import AutoDictify, UseDefault, enforceType, undictifyDictUnion

from .utiltypes import Color

class BeatgridElement(ABC):
    length: float
    bpb: int = 4 # Beats Per Bar
    @staticmethod
    def undictify(v, undictifiers=None): return undictifyDictUnion(v, "type", {
        "const": ConstBeatgridElement, "linear": LinearBeatgridElement
    })
    """ Number of beats (can be non-integer) in this element. """
    def beat_length(self): return self.beatindex(self.length)
    
    """ Returns a tuple of (length, beat_length) """
    def elapsed(self): return (self.length, self.beat_length())
    """ Index of beat at a position. Returns None if outside. """
    @abstractmethod
    def beatindex(self, pos): pass
    """ Position of a beat at an index. Returns None if outside. """
    @abstractmethod
    def beatpos(self, index): pass

""" Region of constant tempo. """
@dataclass
class ConstBeatgridElement(AutoDictify, BeatgridElement):
    length: float
    
    # New attribs
    bpm: float
    
    bpb: int = 4 # Beats Per Bar
    
    def dictify(self, dictifiers=None): return {"type": "const", **super().dictify(dictifiers)}
    #def beat_length(self): return self.length * (self.bpm / 60.0)
    
    def beatindex(self, pos):
        if pos < 0.0 or pos > self.length: return None
        return pos * (self.bpm / 60.0)
    def beatpos(self, index):
        if index < 0.0 or index > self.beat_length(): return None
        return index / (self.bpm / 60.0)

""" Region of linearly increasing/decreasing tempo. """
@dataclass
class LinearBeatgridElement(AutoDictify, BeatgridElement):
    length: float
    
    # New attribs
    bpm: Tuple[float, float]
    
    bpb: int = 4 # Beats Per Bar
    
    def dictify(self, dictifiers=None): return {"type": "linear", **super().dictify(dictifiers)}
    #def beat_length(self):
        # Test example in Desmos:
        # t_{elapsed}=2
        # b_{pm}\left(t\right)=\left(1-\frac{t}{t_{elapsed}}\right)120+\left(\frac{t}{t_{elapsed}}\right)180
        # p\left(t\right)=\frac{b_{pm}\left(t\right)}{60}
        # b_{elapsed}=\int_{0}^{t}p\left(T\right)dT
        # b_{total}=\int_{0}^{t_{elapsed}}p\left(T\right)dT
        # \left(t_{elapsed}-\frac{t_{elapsed}^{2}}{2t_{elapsed}}\right)120+\left(\frac{t_{elapsed}^{2}}{2t_{elapsed}}\right)180
        # 0.5\cdot\frac{120}{60}+0.5\cdot\frac{180}{60}
        #return self.length * sum(self.bpm) / 120.0
    
    def beatindex(self, pos):
        if pos < 0.0 or pos > self.length: return None
        return pos * ((1.0 - pos / (2.0 * self.length)) * self.bpm[0] + (pos / (2.0 * self.length)) * self.bpm[1]) / 60.0
    def beatpos(self, index):
        if index < 0.0 or index > self.beat_length(): return None
        a = (self.bpm[1] - self.bpm[0]) / (120.0*self.length)
        b = self.bpm[0] / 60.0
        c = -index
        return (-b + (b**2.0 - 4.0 * a * c)**0.5) / (2.0 * a)

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
    
    cb = ConstBeatgridElement(10.0, 120.0)
    assert(cb.beat_length() == cb.beatindex(cb.length))
    for i in range(0, 11):
        assert(abs(cb.beatpos(cb.beatindex(i)) - i) < 0.0001)
    
    lb = LinearBeatgridElement(10.0, [120.0, 180.0])
    assert(lb.beat_length() == lb.beatindex(cb.length))
    for i in range(0, 11):
        assert(abs(lb.beatpos(lb.beatindex(i)) - i) < 0.0001)
    
    grid = Beatgrid(5.0, [ConstBeatgridElement(10.0, 120.0), ConstBeatgridElement(10.0, 60.0)])
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
    
    grid = Beatgrid(5.0, [ConstBeatgridElement(10.0, 120.0), LinearBeatgridElement(10.0, [60.0, 120.0])])
    
    for i in range(5, 26):
        assert(grid.beatpos(grid.beatindex(i)) == i)

