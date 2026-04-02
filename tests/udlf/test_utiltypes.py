from udldj.udlf.utiltypes import Color, CompareContext

def test_color_eq():
    print(Color(255,0,0))
    assert(Color(255, 0, 0) == Color(255, 0, 0))
    assert(Color(255, 0, 0) != Color(255, 255, 0))
def test_color_undictify(): assert(Color(255, 0, 0) == Color.undictify([255,0,0]))
def test_color_dictify(): assert(Color(255, 0, 0).dictify() == [255,0,0])

def test_comparectx():
    ctx1 = CompareContext(tolerance_time=0.1, tolerance_bpm=0.001, compare_meta=True)
    ctx2 = CompareContext(tolerance_time=0.01, tolerance_bpm=0.01, compare_meta=False)
    ctx3 = CompareContext(tolerance_time=0.1, tolerance_bpm=0.01, compare_meta=False)
    ctx4 = CompareContext(tolerance_time=1.0, tolerance_bpm=1.0, compare_meta=None)
    ctx5 = CompareContext(tolerance_time=1.0, tolerance_bpm=1.0, compare_meta=False)

    print(ctx1 | ctx2)
    print(ctx3 | ctx4)
    assert(ctx1 | ctx2 == ctx3)
    assert(ctx3 | ctx4 == ctx5)

    with CompareContext(tolerance_time=0.1):
        assert(CompareContext.top.tolerance_time == 0.1)
        assert(CompareContext.top.tolerance_bpm == 0.0)
        assert(CompareContext.top.compare_meta == True)
        assert(CompareContext.time_eq(4, 3.9))
        assert(CompareContext.time_eq(4, 4.1))
        assert(not CompareContext.time_eq(4, 4.15))
        assert(not CompareContext.time_eq(4, 3.85))
        with CompareContext(tolerance_time=1.0, compare_meta=False):
            assert(CompareContext.top.tolerance_time == 1.0)
            assert(CompareContext.top.tolerance_bpm == 0.0)
            assert(CompareContext.top.compare_meta == False)
        assert(CompareContext.top.tolerance_time == 0.1)
        assert(CompareContext.top.tolerance_bpm == 0.0)
        assert(CompareContext.top.compare_meta == True)
    assert(CompareContext.top.tolerance_time == 0.0)
    assert(CompareContext.top.tolerance_bpm == 0.0)
    assert(CompareContext.top.compare_meta == True)