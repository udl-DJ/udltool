import pytest

import os

from udldj.adapters.audacity import TrackInfo, Library
from udldj.udlf import Beatgrid, BeatgridRegion, Marker, Color

REFERENCE_DIR = os.path.join(os.path.split(__file__)[0], '_reference')
MP3_PATH = os.path.join(REFERENCE_DIR, 'basic.mp3')
MP3_PATH2 = os.path.join(REFERENCE_DIR, 'advanced.mp3')

track_reference_expected = TrackInfo()
track_reference_expected.beatgrid = Beatgrid(
    regions = [
        BeatgridRegion(start = 1.0, bpm=120, length = 64, bpb = 4, fbi = 0)
    ]
)
track_reference_expected.cue = Marker(position=1.0)
track_reference_expected.hotcues[0] = Marker(position=1.0, beatlocked=True, name='Test', color=Color(255, 0, 0))
track_reference_expected.hotcues[1] = Marker(
    position=4.397730,
    name='Label Misaligned With Beatgrid',
    color=Color(0, 255, 0)
)
track_reference_expected.hotcues[2] = Marker(
    position=7.0,
    length=2.0,
    beatlocked=True,
    name='Loop',
    color=Color(0, 0, 255)
)
track_reference_expected.genbeats()

track_reference_expected2 = TrackInfo()
track_reference_expected2.beatgrid = Beatgrid(
    regions = [
        BeatgridRegion(start = 1.0, bpm=120, length = 64, bpb = 4, fbi = 0),
        BeatgridRegion(start = 35.0, bpm=240, length = 128, bpb = 8, fbi = 4),
        BeatgridRegion(start = 67.0, bpm=120, length = 128, bpb = 8, fbi = 1)
    ]
)
track_reference_expected2.genbeats()

def test_basic_load():
    with Library(REFERENCE_DIR) as lib:
        track = lib[MP3_PATH]
        print('Loaded:', track)
        print('Expected:', track_reference_expected)
        assert(track == track_reference_expected)
def test_basic_load_beats():
    with Library(REFERENCE_DIR) as lib:
        track = lib[MP3_PATH]
        assert(track.label_data['beats'] == track_reference_expected.label_data['beats'])
def test_basic_gen_beats():
    track = TrackInfo()
    track.assign(track_reference_expected)
    track.genbeats()
    assert(track.label_data['beats'] == track_reference_expected.label_data['beats'])
def test_basic_save(tmp_path):
    print(f'Temp library is {tmp_path}')
    with Library(tmp_path) as lib:
        lib[f'{tmp_path}/test.mp3'] = track_reference_expected
        track = lib[f'{tmp_path}/test.mp3']
        print('Loaded:', track)
        print('Expected:', track_reference_expected)
        assert(track == track_reference_expected)

def test_advanced_load():
    with Library(REFERENCE_DIR) as lib:
        track = lib[MP3_PATH2]
        print('Loaded:', track)
        print('Expected:', track_reference_expected2)
        assert(track == track_reference_expected2)
def test_advanced_load_beats():
    with Library(REFERENCE_DIR) as lib:
        track = lib[MP3_PATH2]
        assert(track.label_data['beats'] == track_reference_expected2.label_data['beats'])
def test_advanced_gen_beats():
    track = TrackInfo()
    track.assign(track_reference_expected2)
    track.genbeats()
    assert(track.label_data['beats'] == track_reference_expected2.label_data['beats'])
def test_advanced_save(tmp_path):
    print(f'Temp library is {tmp_path}')
    with Library(tmp_path) as lib:
        lib[f'{tmp_path}/test.mp3'] = track_reference_expected2
        track = lib[f'{tmp_path}/test.mp3']
        print('Loaded:', track)
        print('Expected:', track_reference_expected2)
        assert(track == track_reference_expected2)
