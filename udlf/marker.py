import math
import itertools
from typing import Optional,List,Tuple,Union
from dataclasses import dataclass
from enum import Enum
from abc import ABC,abstractmethod
from .dictify import AutoDictify, undictify, undictifyDictUnion

from .utiltypes import Color
from .utiltypes import CompareContext as cc

""" Region of constant tempo. """
@dataclass
class BeatgridRegion:
    """ Start position in seconds """
    start: float
    """ Beats per minute in this region """
    bpm: float
    """ Length in beats """
    length: int
    """ First Beat Index -- Index of first beat in this region relative to the current bar """
    fbi: int
    """ Beats Per Bar; Zero indicates no downbeats reported and `fbi` is meaningless """
    bpb: int = 4
    
    @staticmethod
    def undictify(v, undictifiers=None): return BeatgridRegion(*undictify(Union[
            Tuple[float, float, int, int],
            Tuple[float, float, int, int, int]
        ], v, undictifiers))
    def dictify(self, dictifiers=None):
        if self.bpb != 4: return [self.start, self.bpm, self.length, self.fbi, self.bpb]
        else: return [self.start, self.bpm, self.length, self.fbi]
    
    """ Calculates the length in seconds of the region """
    @property
    def timelength(self): return 60.0 * (self.length - 1) / self.bpm
    """ Calculates the ending time """
    @property
    def end(self): return self.start + self.timelength
    """ Index of beat at a position. """
    def beatindex(self, pos): return pos * (self.bpm / 60.0)
    """ Position of a beat at an index. """
    def beatpos(self, index): return index / (self.bpm / 60.0)
    """ Calculates the number of beats after a particular time """
    def beatsafter(self, pos, inclusive = True):
        if inclusive: return self.length - math.ceil(self.beatindex(pos))
        else: return self.length - math.floor(self.beatindex(pos)) - 1
    """ Calculates the number of beats before a particular time """
    def beatsbefore(self, pos, inclusive = True):
        if inclusive: return math.floor(self.beatindex(pos))
        else: return math.ceil(self.beatindex(pos)) - 1

""" Utility class for a single beat """
@dataclass
class Beat:
    index: int
    position: float
    is_downbeat: bool
    """
        Creates a beat at the given `index` and `position` inside a bar of beat length `bpb` with a downbeat position of
        `global_dbi` (does not have to be nearby this beat, just needs to be *a* downbeat on the same grid as `bpb`).
    """
    @staticmethod
    def create(index, bpb, global_dbi, position):
        return Beat(index, position, (index - global_dbi) % bpb == 0)
    def cmp(self, other):
        if not type(other) == Beat: raise ValueError('Expected `Beat` type')
        
        if self.index is None or other.index is None:
            by_index = None
        else:
            by_index = -1 if self.index < other.index else (0 if self.index == other.index else 1)
        
        if self.position is None or other.position is None:
            by_position = None
        else:
            by_position = -1 if self.position < other.position else (0 if self.position == other.position else 1)
        
        # Ok, ok, *technically* neither can be none, but I do kindof have unofficial support for partially specified
        # beats... for internal use... they really shouldn't be passed around. Yes, I know it's messed up.
        if by_index is None: return by_position
        if by_position is None: return by_index
        
        if by_position == by_index: return by_index
        
        raise ValueError('Unable to get consistent comparison between index and position. Are these beats on the same grid?')
    def __gt__(self, other): return self.cmp(other) == 1
    def __ge__(self, other): return self.cmp(other) >= 0
    def __eq__(self, other): return self.cmp(other) == 0

def filterAllowed(regions):
    last_start = 0.0
    for region in regions:
        if region.start <= last_start:
            last_start = region.start
            continue
        yield region
        last_start = region.start
def removeDuplicates(regions):
    f1, f2 = itertools.tee(regions)
    f2.__next__()
    for (current, nextregion) in itertools.zip_longest(f1, f2, fillvalue=None):
        if not nextregion is None and nextregion.start == current.start: continue
        yield current

""" Calculated information about a beatgrid region """
@dataclass
class BeatgridRegionMeta(object):
    """ Start position of beatgrid in seconds """
    start: float
    """ End position of beatgrid in seconds """
    end: float
    """ Adjusted beat length """
    length: int
    """ First beat in the beatgrid """
    firstbeat: Beat
    """ Last beat in the beatgrid """
    lastbeat: Beat
    def __contains__(self, beat):
        return not self.empty() and beat >= self.firstbeat and beat <= self.lastbeat
""" A beatgrid of one or more regions of constant tempo. """
@dataclass
class Beatgrid(AutoDictify):
    regions: List[BeatgridRegion]
    
    """ Index of beat at a position. Returns None if outside. """
    def beatindex(self, pos):
        if len(self.regions) and pos < self.regions[0].start:
            return self.regions[0].beatindex(pos - self.regions[0].start)
        last_end = 0.0
        beats_total = 0
        for (region, meta) in self.regions_meta():
            if pos < meta.start: return beats_total + (pos - last_end) / (meta.start - last_end)
            if pos <= meta.end: return beats_total + region.beatindex(pos - meta.start)
            last_end = meta.end
            beats_total += meta.length
        return beats_total - meta.length + region.beatindex(pos - meta.start)
    
    """ Position of a beat at an index. Returns None if outside. """
    def beatpos(self, index):
        if len(self.regions) and index < 0:
            return self.regions[0].start + self.regions[0].beatpos(index)
        
        last_end = 0.0
        for (region, meta) in self.regions_meta():
            if index < 0:
                return last_end + (meta.start - last_end) * (index + 1.0)
            
            beat_end = meta.length - 1
            if index <= beat_end:
                return meta.start + region.beatpos(index)
            
            last_end = meta.end
            index -= meta.length
        return last_end + region.beatpos(index + 1)
    
    def beat(self, index=None, position=None):
        if (index is None) == (position is None): raise ValueError('Exactly one of (index, position) can be None')
        if index is None:
            beat = Beat(index = index, position = self.beatpos(index))
        else:
            beat = Beat(index = self.beatindex(position), position = position)
        for (region, meta) in self.regions_meta():
            pass
        return None
    
    """ Returns an iterator over all defined beats in a grid """
    def beats(self):
        index = 0
        last_end = 0.0
        for (region, meta) in self.regions_meta():
            for i in range(0, meta.length):
                yield Beat(
                    index=index,
                    position=meta.start + region.beatpos(i),
                    is_downbeat=((i + region.fbi) % region.bpb) == 0
                )
                index += 1
            last_end = meta.end
    
    """ Iterate over valid regions and calculate the range they're valid over """
    def regions_meta(self):
        f1, f2 = itertools.tee(filterAllowed(removeDuplicates(self.regions)))
        f2.__next__()
        beatindex = 0
        for (current, nextregion) in itertools.zip_longest(f1, f2, fillvalue=None):
            if nextregion is None:
                yield (current, BeatgridRegionMeta(
                    start = current.start,
                    length = current.length,
                    end = current.end,
                    firstbeat=Beat(
                        index=beatindex,
                        position=current.start,
                        is_downbeat=current.fbi == 0
                    ),
                    lastbeat=Beat(
                        index=beatindex + current.length - 1,
                        position=current.end,
                        is_downbeat=((current.length + current.fbi - 1) % current.bpb) == 0
                    )
                ))
            else:
                true_length = min(current.beatsbefore(nextregion.start - current.start), current.length)
                assert(true_length > 0)
                yield (current, BeatgridRegionMeta(
                    start = current.start,
                    length = true_length,
                    end = current.start + current.beatpos(true_length - 1),
                    firstbeat=Beat(
                        index=beatindex,
                        position=current.start,
                        is_downbeat=current.fbi == 0
                    ),
                    lastbeat=Beat(
                        index=beatindex + true_length - 1,
                        position=current.start + current.beatpos(true_length - 1),
                        is_downbeat=((true_length + current.fbi - 1) % current.bpb) == 0
                    )
                ))
                beatindex += true_length
    
    """ Remove invalid and overlapped beatgrid regions """
    def clean(self):
        return Beatgrid(regions=[
            BeatgridRegion(
                start=region.start, bpm=region.bpm, length=meta.length, fbi=region.fbi, bpb=region.bpb
            ) for (region, meta) in self.regions_meta()
        ])

""" A point or region within a song. """
@dataclass
class Marker(AutoDictify):
    """ Location of the marker in seconds """
    position: float
    """ Length of the marker in seconds, or None if the marker is a single point """
    length: Optional[float] = None
    """ If true, the marker is locked to the beatgrid (and updates should shift its position) """
    locked: bool = False
    """ Label of the marker """
    name: Optional[str] = None
    """ Color of the marker displayed in UIs """
    color: Optional[Color] = None
    def __eq__(self, other):
        return (
            cc.time_eq(self.position, other.position) and cc.time_eq(self.length, other.length) and
            cc.meta_eq(self.locked, other.locked) and cc.meta_eq(self.name, other.name) and
            cc.meta_eq(self.color, other.color)
        )

if __name__ == "__main__":
    d1 = Marker(1.0, name='Hotcue 1', color=Color(255,0,0)).dictify()
    d2 = Marker(2.0, name='Hotcue 2', locked=True, color=Color(0,255,0)).dictify()
    print(d1)
    print(d2)
    print(Marker.undictify(d1))
    print(Marker.undictify(d2))
    
    print()
    
    cb = BeatgridRegion(start=10, bpm=120, length=10, fbi=0)
    # Test for consistency
    for i in range(0, 10):
        assert(cb.beatindex(cb.beatpos(i)) == i)
    
    grid = Beatgrid(regions=[
        BeatgridRegion(start=10, bpm=120, length=10, fbi=0),
        BeatgridRegion(start=5, bpm=120, length=100, fbi=0), # Should be totally ignored (bc out of order)
        BeatgridRegion(start=20, bpm=120, length=12, fbi=2), # Should be cut short by the next region
        BeatgridRegion(start=25, bpm=120, length=1, fbi=2), # Should be remove to prioritize later region
        BeatgridRegion(start=25, bpm=60, length=5, fbi=0)
    ])

    print(*map(lambda v: v[1], grid.regions_meta()), sep='\n')
    print(*grid.beats(), sep='\n')
    
    assert([*map(lambda v: v[1], grid.regions_meta())] == [
        BeatgridRegionMeta(start=10, end=14.5, length=10, firstbeat=Beat(index=0, position=10, is_downbeat=True), lastbeat=Beat(index=9, position=14.5, is_downbeat=False)),
        BeatgridRegionMeta(start=20, end=24.5, length=10, firstbeat=Beat(index=10, position=20, is_downbeat=False), lastbeat=Beat(index=19, position=24.5, is_downbeat=False)),
        BeatgridRegionMeta(start=25, end=29.0, length=5, firstbeat=Beat(index=20, position=25, is_downbeat=True), lastbeat=Beat(index=24, position=29.0, is_downbeat=True))
    ])

    # Test for consistency
    for i in range(-10, 30):
        assert(grid.beatindex(grid.beatpos(i)) == i)
    
    positions = [grid.beatpos(i) for i in range(-10, 26)]
    assert(positions == [
        5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5,
        10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5,
        20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 24.5,
        25.0, 26.0, 27.0, 28.0, 29.0, 30.0
    ])

    assert([*grid.beats()] == [
        Beat(index=0, position=10.0, is_downbeat=True),
        Beat(index=1, position=10.5, is_downbeat=False),
        Beat(index=2, position=11.0, is_downbeat=False),
        Beat(index=3, position=11.5, is_downbeat=False),
        Beat(index=4, position=12.0, is_downbeat=True),
        Beat(index=5, position=12.5, is_downbeat=False),
        Beat(index=6, position=13.0, is_downbeat=False),
        Beat(index=7, position=13.5, is_downbeat=False),
        Beat(index=8, position=14.0, is_downbeat=True),
        Beat(index=9, position=14.5, is_downbeat=False),
        Beat(index=10, position=20.0, is_downbeat=False),
        Beat(index=11, position=20.5, is_downbeat=False),
        Beat(index=12, position=21.0, is_downbeat=True),
        Beat(index=13, position=21.5, is_downbeat=False),
        Beat(index=14, position=22.0, is_downbeat=False),
        Beat(index=15, position=22.5, is_downbeat=False),
        Beat(index=16, position=23.0, is_downbeat=True),
        Beat(index=17, position=23.5, is_downbeat=False),
        Beat(index=18, position=24.0, is_downbeat=False),
        Beat(index=19, position=24.5, is_downbeat=False),
        Beat(index=20, position=25.0, is_downbeat=True),
        Beat(index=21, position=26.0, is_downbeat=False),
        Beat(index=22, position=27.0, is_downbeat=False),
        Beat(index=23, position=28.0, is_downbeat=False),
        Beat(index=24, position=29.0, is_downbeat=True)
    ])

    print()
    print(grid.dictify())
    assert(grid.dictify() == {'regions': [
        [10.0, 120.0, 10, 0],
        [5.0, 120.0, 100, 0],
        [20.0, 120.0, 12, 2],
        [25.0, 120.0, 1, 2],
        [25.0, 60.0, 5, 0]
    ]})

    print()
    print(grid.clean())
