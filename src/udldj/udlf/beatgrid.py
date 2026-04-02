import math
import itertools
from typing import List,Tuple,Union
from dataclasses import dataclass
from ..util.dictify import AutoDictify, undictify

""" Utility class for a single beat """
@dataclass
class Beat:
    index: int
    position: float
    is_downbeat: bool
    def cmp(self, other):
        if not type(other) == Beat: raise ValueError('Expected `Beat` type')
        
        by_index = -1 if self.index < other.index else (0 if self.index == other.index else 1)
        by_position = -1 if self.position < other.position else (0 if self.position == other.position else 1)
        
        if by_position == by_index: return by_index
        
        raise ValueError('Unable to get consistent comparison between index and position. Are these beats on the same grid?')
    def __gt__(self, other): return self.cmp(other) == 1
    def __ge__(self, other): return self.cmp(other) >= 0
    def __eq__(self, other): return self.cmp(other) == 0

def beatFloor(resolver, index=None, position=None):
    if (index is None) == (position is None): raise ValueError('Exactly one of (index, position) can be None')

    if index is None: index = resolver.beatindex(position)
    index = int(math.floor(index))
    position = resolver.beatpos(index)

    return (index, position)

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
    """ Index of beat at a position relative to the start of this region. """
    def beatindex(self, pos): return pos * (self.bpm / 60.0)
    """ Position of a beat at an index. """
    def beatpos(self, index): return index / (self.bpm / 60.0)
    """ Calculates the number of beats after a particular time relative to the start of this region """
    def beatsafter(self, pos, inclusive = True):
        if inclusive: return self.length - math.ceil(self.beatindex(pos))
        else: return self.length - math.floor(self.beatindex(pos)) - 1
    """ Calculates the number of beats before a particular time relative to the start of this region """
    def beatsbefore(self, pos, inclusive = True):
        if inclusive: return math.floor(self.beatindex(pos) + 1)
        else: return math.ceil(self.beatindex(pos) + 1) - 1
    """ Tests if a beat `index` (rounded down) relative to the start of the region is a downbeat """
    def downbeat(self, index): return ((int(math.floor(index)) + self.fbi) % self.bpb) == 0
    """
        Returns a beat object at a relative `position` or relative `index` (rounded down).
        Specify exactly one of `index`, `position` and leave the other None.
    """
    def beat(self, index=None, position=None):
        (index, position) = beatFloor(self, index, position)
        return Beat(index=index, position=position, is_downbeat=self.downbeat(index))

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
        return beat >= self.firstbeat and beat <= self.lastbeat
""" A beatgrid of one or more regions of constant tempo. """
@dataclass
class Beatgrid(AutoDictify):
    regions: List[BeatgridRegion]

    @property
    def empty(self): return len(self.regions) == 0
    
    """ Index of beat at a position. Returns None if the beatgrid is empty. """
    def beatindex(self, pos):
        if self.empty: return None
        if len(self.regions) and pos < self.regions[0].start:
            return self.regions[0].beatindex(pos - self.regions[0].start)

        last_end = 0.0
        beats_total = 0
        for (region, meta) in self.meta():
            if pos < meta.start: return beats_total + (pos - last_end) / (meta.start - last_end)
            if pos <= meta.end: return beats_total + region.beatindex(pos - meta.start)
            last_end = meta.end
            beats_total += meta.length
        return beats_total - meta.length + region.beatindex(pos - meta.start)
    
    """ Position of a beat at an index. Returns None if the beatgrid is empty. """
    def beatpos(self, index):
        if self.empty: return None
        if len(self.regions) and index < 0:
            return self.regions[0].start + self.regions[0].beatpos(index)
        
        last_end = 0.0
        for (region, meta) in self.meta():
            # This should not happen; Negative indicies should be caught above or in the last region
            assert(index >= 0)
            #if index < 0:
            #    return last_end + (meta.start - last_end) * (index + 1.0)
            
            beat_end = meta.length - 1
            if index <= beat_end:
                return meta.start + region.beatpos(index)
            
            last_end = meta.end
            index -= meta.length
        return last_end + region.beatpos(index + 1)
    
    """
        Returns a beat object at a `position` or `index` (rounded down).
        Specify exactly one of `index`, `position` and leave the other None.
        Returns None if the beatgrid is empty.
    """
    def beat(self, index=None, position=None):
        if self.empty: return None
        (index, position) = beatFloor(self, index, position)

        (lastregion, lastmeta) = self.meta().__next__()
        for (region, meta) in self.meta():
            if index < lastmeta.firstbeat.index: break
            (lastregion, lastmeta) = (region, meta)
        
        return lastregion.beat(index=index)
    
    """ Returns an iterator over all defined beats in a grid """
    def beats(self):
        index = 0
        last_end = 0.0
        for (region, meta) in self.meta():
            for i in range(0, meta.length):
                yield Beat(
                    index=index,
                    position=meta.start + region.beatpos(i),
                    is_downbeat=((i + region.fbi) % region.bpb) == 0
                )
                index += 1
            last_end = meta.end
    
    """ Iterate over valid regions and calculate the range they're valid over """
    def meta(self):
        if self.empty: return

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
                true_length = min(
                    current.beatsbefore(nextregion.start - current.start, inclusive=False),
                    current.length
                )
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
            ) for (region, meta) in self.meta()
        ])
