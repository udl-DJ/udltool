import pytest

from udldj.udlf.beatgrid import BeatgridRegion, Beatgrid, Beat, BeatgridRegionMeta

region = BeatgridRegion(start=10, bpm=120, length=10, fbi=3)

grid = Beatgrid(regions=[
    BeatgridRegion(start=10, bpm=120, length=10, fbi=0),
    BeatgridRegion(start=5, bpm=120, length=100, fbi=0), # Should be totally ignored (bc out of order)
    BeatgridRegion(start=20, bpm=120, length=12, fbi=2), # Should be cut short by the next region
    BeatgridRegion(start=25, bpm=120, length=1, fbi=2), # Should be remove to prioritize later region
    BeatgridRegion(start=25, bpm=60, length=5, fbi=0)
])

emptygrid = Beatgrid(regions=[])

def test_beat_inconsistency():
    b1 = Beat(index=0, position=10, is_downbeat=False)
    b2 = Beat(index=10, position=0, is_downbeat=False)
    with pytest.raises(ValueError) as exc_info: b1 > b2
    assert(str(exc_info.value) == 'Unable to get consistent comparison between index and position. Are these beats on the same grid?')

def test_region_consistency():
    region = BeatgridRegion(start=10, bpm=120, length=10, fbi=0)
    for i in range(-10, 20): # Can extend beyond region limits
        print(f'{i} -> {region.beatpos(i)} -> {region.beatindex(region.beatpos(i))}')
        assert(region.beatindex(region.beatpos(i)) == i)

def test_region_timelength(): assert(region.timelength == 4.5)
def test_region_end(): assert(region.end == 14.5)
def test_region_beatindex(): assert(region.beatindex(0.75) == 1.5)
def test_region_beatpos(): assert(region.beatpos(1.5) == 0.75)
def test_region_beatsafter():
    assert(region.beatsafter(pos=0.0, inclusive=False) == 9)
    assert(region.beatsafter(pos=0.0, inclusive=True) == 10)
    assert(region.beatsafter(pos=1.0, inclusive=False) == 7)
    assert(region.beatsafter(pos=1.0, inclusive=True) == 8)
def test_region_beatsbefore():
    assert(region.beatsbefore(pos=4.5, inclusive=False) == 9)
    assert(region.beatsbefore(pos=4.5, inclusive=True) == 10)
    assert(region.beatsbefore(pos=1.0, inclusive=False) == 2)
    assert(region.beatsbefore(pos=1.0, inclusive=True) == 3)
def test_region_downbeat():
    assert(not region.downbeat(0))
    assert(region.downbeat(1))
    assert(not region.downbeat(2))
    assert(not region.downbeat(3))
    assert(not region.downbeat(4))
    assert(region.downbeat(5))

def test_meta_beat_contains():
    meta = BeatgridRegionMeta(
        start=10, end=14.5, length=10,
        firstbeat=Beat(index=0, position=10, is_downbeat=True),
        lastbeat=Beat(index=9, position=14.5, is_downbeat=False)
    )
    assert(Beat(index=2, position=11, is_downbeat=False) in meta)
    assert(not Beat(index=-2, position=9, is_downbeat=False) in meta)
    assert(not Beat(index=10, position=15, is_downbeat=False) in meta)

def test_grid_consistency():
    for i in range(-10, 30):
        print(f'{i} -> {grid.beatpos(i)} -> {grid.beatindex(grid.beatpos(i))}')
        assert(grid.beatindex(grid.beatpos(i)) == i)
def test_grid_positions_correct():
    positions = [grid.beatpos(i) for i in range(-10, 26)]
    print(positions)
    assert(positions == [
        5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5,
        10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5,
        20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 24.5,
        25.0, 26.0, 27.0, 28.0, 29.0, 30.0
    ])
def test_grid_beat_iter():
    for beat in grid.beats(): print(beat)
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
def test_grid_beat_consistency_by_index():
    for beat in grid.beats():
        beat2 = grid.beat(index=beat.index)
        print(beat, '->', beat2)
def test_grid_beat_consistency_by_position():
    for beat in grid.beats():
        beat2 = grid.beat(position=beat.position)
        print(beat, '->', beat2)
def test_grid_beat_consistency_error():
    with pytest.raises(ValueError) as exc_info: grid.beat()
    assert(str(exc_info.value) == 'Exactly one of (index, position) can be None')
    with pytest.raises(ValueError) as exc_info: grid.beat(index=1, position=2)
    assert(str(exc_info.value) == 'Exactly one of (index, position) can be None')
def test_grid_meta():
    for (region, meta) in grid.meta(): print(f'{region}: {meta}')
    assert([*map(lambda v: v[1], grid.meta())] == [
        BeatgridRegionMeta(
            start=10, end=14.5, length=10,
            firstbeat=Beat(index=0, position=10, is_downbeat=True),
            lastbeat=Beat(index=9, position=14.5, is_downbeat=False)
        ),
        BeatgridRegionMeta(
            start=20, end=24.5, length=10,
            firstbeat=Beat(index=10, position=20, is_downbeat=False),
            lastbeat=Beat(index=19, position=24.5, is_downbeat=False)
        ),
        BeatgridRegionMeta(
            start=25, end=29.0, length=5,
            firstbeat=Beat(index=20, position=25, is_downbeat=True),
            lastbeat=Beat(index=24, position=29.0, is_downbeat=True)
        )
    ])
def test_grid_dictify():
    assert(grid.dictify() == {'regions': [
        [10.0, 120.0, 10, 0],
        [5.0, 120.0, 100, 0],
        [20.0, 120.0, 12, 2],
        [25.0, 120.0, 1, 2],
        [25.0, 60.0, 5, 0]
    ]})
def test_grid_clean():
    cleaned = grid.clean()
    assert(cleaned == Beatgrid(regions=[
        BeatgridRegion(start=10, bpm=120, length=10, fbi=0),
        BeatgridRegion(start=20, bpm=120, length=10, fbi=2),
        BeatgridRegion(start=25, bpm=60, length=5, fbi=0)
    ]))
def test_empty_grid():
    assert(not grid.empty)
    assert(emptygrid.empty)
    assert(emptygrid.beatindex(0) is None)
    assert(emptygrid.beatpos(0) is None)
    assert(emptygrid.beat(index=0) is None)
    assert([*emptygrid.beats()] == [])
    assert([*emptygrid.meta()] == [])
