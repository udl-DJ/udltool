from udldj.udlf.marker import Marker, MarkerSet
from udldj.udlf.utiltypes import Color
from udldj.util.dictify import undictify

def test_marker_dictify_simple(): assert(Marker(3.0).dictify() == {'position': 3.0})
def test_marker_dictify_with_meta():
    m = Marker(1.0, name='Hotcue 1', color=Color(255,0,0))
    assert(m.dictify() == {'position': 1.0, 'name': 'Hotcue 1', 'color': [255,0,0]})
def test_marker_dictify_with_beatlock():
    assert(Marker(2.0, beatlocked=True).dictify() == {'position': 2.0, 'beatlocked': True})
def test_marker_undictify():
    m1 = Marker(1.0, name='Hotcue 1', color=Color(255,0,0))
    m2 = Marker(2.0, name='Hotcue 2', beatlocked=True, color=Color(0,255,0))
    print(Marker.undictify(m1.dictify()) == m1)
    print(Marker.undictify(m2.dictify()) == m2)

def test_markerset_dictify():
    s = MarkerSet(Marker(1.0), None, Marker(2.0))
    assert(s.dictify() == {'markers': [{'position': 1.0}, None, {'position': 2.0}]})
def test_markerset_assign_dictify():
    s = MarkerSet(Marker(1.0), None, Marker(2.0))
    s[1] = Marker(3.0)
    s[0] = None
    assert(s.dictify() == {'markers': [None, {'position': 3.0}, {'position': 2.0}]})
def test_markerset_lengths():
    s1 = MarkerSet(Marker(1.0), None, Marker(2.0))
    s2 = MarkerSet(Marker(1.0), None, Marker(2.0))
    s2[1] = Marker(3.0)
    s2[0] = None
    assert(len(s1) == 3)
    assert(len(s2) == 3)
    assert(s1.max == -1)
    assert(s2.max == -1)
def test_markerset_undictify():
    s1 = MarkerSet(Marker(1.0), None, Marker(2.0))
    s2 = undictify(MarkerSet, s1.dictify())
    assert(s1 == s2)
