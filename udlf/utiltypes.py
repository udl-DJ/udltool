from dataclasses import dataclass
from typing import Tuple

from .dictify import undictify

@dataclass
class Color:
    R: int
    G: int
    B: int
    def dictify(self, dictifiers=None): return [self.R, self.G, self.B]
    @staticmethod
    def undictify(v, undictifiers=None): return Color(*undictify(Tuple[int,int,int], v, undictifiers))

if __name__ == "__main__":
    print(Color(255,0,0))
    assert(Color(255, 0, 0) == Color(255, 0, 0))
    assert(Color(255, 0, 0) != Color(255, 255, 0))
    
    assert(Color(255, 0, 0) == Color.undictify([255,0,0]))
    assert(Color(255, 0, 0).dictify() == [255,0,0])
