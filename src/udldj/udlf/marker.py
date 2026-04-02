from typing import Optional,List
from dataclasses import dataclass
import itertools
from ..util.dictify import AutoDictify, UseDefault, dictify, undictify

from .baselibrary import BaseMarkerSet
from .utiltypes import Color
from .utiltypes import CompareContext as cc

""" A point or region within a song. """
@dataclass
class Marker(AutoDictify):
    """ Location of the marker in seconds """
    position: float
    """ Length of the marker in seconds, or None if the marker is a single point """
    length: Optional[float] = None
    """ If true, the marker is locked to the beatgrid (and updates should shift its position) """
    beatlocked: UseDefault[bool, False] = False
    """ Label of the marker """
    name: Optional[str] = None
    """ Color of the marker displayed in UIs """
    color: Optional[Color] = None
    def __eq__(self, other):
        return (
            cc.time_eq(self.position, other.position) and cc.time_eq(self.length, other.length) and
            cc.meta_eq(self.beatlocked, other.beatlocked) and cc.meta_eq(self.name, other.name) and
            cc.meta_eq(self.color, other.color)
        )
    def dictify(self, dictifiers=None):
        d = super().dictify(dictifiers)
        d_res = {**d}
        for k in d:
            if not d[k] and not k == 'position': del d_res[k]
        return d_res

class MarkerSet(BaseMarkerSet):
    markers: {int: Marker}

    def __init__(self, *markers):
        self.markers = {k: v for (k, v) in zip(range(0, len(markers)), markers) if not v is None}

    def load(self, index): return self.markers[index] if index in self.markers else None
    def save(self, index, marker):
        if marker is None:
            if index in self.markers: del self.markers[index]
        else:
            self.markers[index] = marker
    @property
    def stored(self): return max(itertools.chain([0], (i + 1 for i in self.markers)))
    @property
    def max(self): return -1

    def dictify(self, dictifiers=None):
        return {'markers': [dictify(m, dictifiers) for m in self]}
    @classmethod
    def undictify(cls, v, undictifiers=None):
        assert('markers' in v)
        return MarkerSet(*undictify(List[Optional[Marker]], v['markers'], undictifiers))
