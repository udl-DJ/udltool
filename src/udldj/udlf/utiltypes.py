from dataclasses import dataclass
from typing import Tuple, Optional

from ..util.dictify import undictify

def parsehex_16bit(digits):
    assert(len(digits) < 3)
    n = int(digits, 16)
    return n * 0x11 if len(digits) == 1 else n

@dataclass
class Color:
    R: int
    G: int
    B: int
    def dictify(self, dictifiers=None): return [self.R, self.G, self.B]
    @staticmethod
    def undictify(v, undictifiers=None): return Color(*undictify(Tuple[int,int,int], v, undictifiers))
    @staticmethod
    def fromhex(hexstr):
        if not type(hexstr) is str: raise ValueError('Not a string')
        if len(hexstr) == 6:
            return Color(*[parsehex_16bit(s) for s in [hexstr[0:2], hexstr[2:4], hexstr[4:6]]])
        elif len(hexstr) == 3:
            return Color(*[parsehex_16bit(s) for s in [hexstr[0:1], hexstr[1:2], hexstr[3:4]]])
        else: raise ValueError('Invalid number of hex digits')
    def tohex(self): return f'{self.R:02x}{self.G:02x}{self.B:02x}'

def _maxtol(a, b):
    if a is None: return b
    if b is None: return a
    return max(a, b)
def _eq_err(a, b, t):
    if a == b: return True
    if a is None: return False
    if b is None: return False
    return (a-t <= b and b <= a+t) or (b-t <= a and a <= b+t)
class CompareContextMeta(type):
    stack = []
    @property
    def top(cls): return cls.stack[-1] if len(cls.stack) else cls(0, 0, True)
    def push(cls, ctx): cls.stack.append(cls.top | ctx)
    def pop(cls): cls.stack.pop()
    def time_eq(cls, a, b): return _eq_err(a, b, cls.top.tolerance_time)
    def bpm_eq(cls, a, b): return abs(a-b) <= cls.top.tolerance_bpm
    def meta_eq(cls, a, b): return (not cls.top.compare_meta) or a == b
@dataclass
class CompareContext(metaclass=CompareContextMeta):
    tolerance_time: Optional[float] = None
    tolerance_bpm: Optional[float] = None
    compare_meta: Optional[bool] = None
    def __or__(self, other): return CompareContext(
        tolerance_time=_maxtol(self.tolerance_time, other.tolerance_time),
        tolerance_bpm=_maxtol(self.tolerance_bpm, other.tolerance_bpm),
        compare_meta=self.compare_meta if other.compare_meta is None else other.compare_meta
    )
    def __enter__(self): CompareContext.push(self)
    def __exit__(self, exc_type, exc_value, exc_tb): CompareContext.pop()
    def __str__(self):
        return f'CompareContext(tolerance_time={self.tolerance_time}, tolerance_bpm={self.tolerance_bpm}, compare_meta={self.compare_meta})'
    def __repr__(self): return str(self)
