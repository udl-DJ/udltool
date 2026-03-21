import os
import itertools
from abc import ABC, ABCMeta, abstractmethod

"""
    A virtual collection of markers. Assign `load`, `save`, `stored`, and `max` to override the default behavior.
    Returned from specific library implementations as a utility type to easily edit lists of markers.
"""
class BaseMarkerSet:
    """
        Loads the marker at `index` from track data.
        Should throw error if load fails, but should return None if the marker does not exist/is out of bounds.
        Needs override.
    """
    def load(self, index): pass
    """
        Saves the marker at `index` to track data. Pass None to delete marker.
        May throw error if the save fails or the index is out of bounds (<0 or >max).
        Needs override.
    """
    def save(self, index, marker): pass
    """
        Returns 1+ the maximum index of stored markers (for use in iteration).
        This is the length, but not necessarily the count of markers since some indicies may
        be `None` (have no marker).
        Needs override.
    """
    @property
    def stored(self): return self._stored()
    """ Returns the maximum number of markers that can be stored, or -1 if infinite. Needs override. """
    @property
    def max(self): return self._max()
    
    """ Alias for `stored()`. Do not override. """
    def __len__(self): return self.stored
    """ Alias for `load()`. Do not override. """
    def __getitem__(self, i): return self.load(i)
    """ Alias for `save()`. Do not override. """
    def __setitem__(self, i, m): return self.save(i, m)
    """ Alias for `save()`. Do not override. """
    def __delitem__(self, i): return self.save(i, None)
    """ Alias for `load()` and `stored()`. Do not override. """
    def __iter__(self):
        for i in range(0, self.stored): yield self.load(i)
    """ Overwrites this marker set with values from another marker set. Do not override. """
    def assign(self, other):
        other_stored = 0 if other is None else other.stored
        self_canstore = other_stored if self.max < 0 else self.max
        # First, copy over all the entries from the other object that we can
        for i in range(0, min(self_canstore, other_stored)):
            self.save(i, other.load(i))
        # Next, clear out any extra markers
        for i in range(other_stored, self.stored):
            self.save(i, None)
    """ Remove all markers from this set. Do not override. """
    def clear(self):
        for i in range(0, self.stored): self.save(i, None)
    """ Compares this marker set with another marker set. Do not override. """
    def __eq__(self, other):
        if not self.stored == other.stored: return False
        for (s, o) in zip(self, other):
            if not s == o: return False
        return True

# Utility functions for generating getters
def _loadfn(name): return lambda self: getattr(self, 'load'+name)()
def _savefn(name): return lambda self, v: getattr(self, 'save'+name)(v)
def _delfn(name): return lambda self, v: getattr(self, 'save'+name)(None)
def _getmarkerfn(name):
    def getmarkerset(self):
        s = BaseMarkerSet()
        s.load = getattr(self, 'load'+name)
        s.save = getattr(self, 'save'+name)
        s._stored = getattr(self, 'stored'+name)
        s._max = getattr(self, 'max'+name)
        return s
    return getmarkerset
def _setmarkerfn(name):
    getfn = _getmarkerfn(name)
    return lambda self, v: getfn(self).assign(v)
def _delmarkerfn(name):
    getfn = _getmarkerfn(name)
    return lambda self: getfn(self).assign(None)
"""
    Automatically defines attributes in the BaseTrackInfo class that call the corresponding abstract functions.
    BaseTrackInfo has two sets of functions/attributes:
      - The verbose loadxyz, savexyz, storedxyz, maxxyz, etc. that are abstract
      - Easy attributes (like ".beatgrid") that call the above methods
    Implementations of library loaders should override the load/save/stored methods.
    End users should always use the easy attributes.
    This allows some generic high-level logic to be implemented below to minimize boilerplate in library loader
    implementations while keeping a clean interface for the end users.
    For example, deleting an attribute simply sets it to None. There's a whole bunch of boilerplate __del
    functions that no longer have to be written...
"""
class BaseTrackInfoMeta(ABCMeta):
    """ Simple load/save attributes """
    simpleprops = {
        "beatgrid": "Access the track's stored beatgrid",
        "cue": "The track's main cue point"
    }
    """
        Attributes which return a BaseMarkerSet, which in turn calls the corresponding methods on the
        BaseTrackInfo class. This allows you do keep all of your read/write logic in the main class without
        passing copies of it around.
    """
    markersetprops = {
        "hotcues": "Track hotcue markers",
        "memorycues": "Track memory cues",
        "savedloops": "Stored loop markers (if different than hotcues)",
        "phrases": "Track phrase information"
    }
    def __new__(self, name, bases, namespace):
        if self not in map(type, bases):
            abstract_fns_to_define = []
            
            for (name, doc) in self.simpleprops.items():
                namespace[name] = property(fget=_loadfn(name), fset=_savefn(name), fdel=_delfn(name), doc=doc)
                abstract_fns_to_define.append('load'+name)
                abstract_fns_to_define.append('save'+name)
            
            for (name, doc) in self.markersetprops.items():
                namespace[name] = property(
                    fget=_getmarkerfn(name),
                    fset=_setmarkerfn(name),
                    fdel=_delmarkerfn(name),
                    doc=doc
                )
                abstract_fns_to_define.append('load'+name)
                abstract_fns_to_define.append('save'+name)
                abstract_fns_to_define.append('stored'+name)
                abstract_fns_to_define.append('max'+name)
            
            for attribute in abstract_fns_to_define:
                namespace[attribute] = abstractmethod(lambda x: None)
            
            namespace["_data_attrs"] = [*self.simpleprops, *self.markersetprops]
            
        return super().__new__(self, name, bases, namespace)

"""
    Abstract base class for track information in a implementation-defined format.
    Implementations should store data in memory, but in their native format. I.e, elements of an XML file or
    columns of a SQL database. This allows a generic interface to access data in any format.
"""
class BaseTrackInfo(metaclass=BaseTrackInfoMeta):
    # Data attributes defined in meta class...
    def assign(self, other):
        for attr in self._data_attrs:
            setattr(self, attr, getattr(other, attr))
    def __eq__(self, other):
        for attr in self._data_attrs:
            if getattr(self, attr) != getattr(other, attr): return False
        return True
    def __str__(self):
        parts = []
        def appendall(label, items):
            if len(items) == 0:
                parts.append(label + 'Empty')
                return
            parts.append(label)
            for (i, item) in zip(itertools.count(), items):
                parts.append(f'  {i} {item}')
        parts.append('Beatgrid=' + str(self.beatgrid))
        parts.append('Main Cue=' + str(self.cue))
        appendall('Hotcues=', self.hotcues)
        appendall('Memory Cues=', self.memorycues)
        appendall('Saved Loops=', self.savedloops)
        appendall('Phrases=', self.phrases)
        return f'TrackInfo(\n  ' + '\n  '.join(parts) + '\n)'
"""
    Abstract base class for 
"""
class BaseLibrary(ABC):
    """ Open must be called before performing operations on the library. Use to open files. """
    @abstractmethod
    def open(self): pass
    """ Close must be called before performing operations on the library. Use to close files. """
    @abstractmethod
    def close(self): pass
    def __enter__(self):
        self.open()
        return self
    def __exit__(self, exc_type, exc_value, exc_tb): self.close()

    """ Create an empty track for storing new information """
    @abstractmethod
    def emptytrack(self): pass
    """
        Read a track into memory.
        Creates a new object that can be safely edited without modifying original data.
        Subsequent reads to the same location should not be linked in any way; Changes to one should not
        change values in another object. Use the setter to update the info once you modify it.
        Returns a subclass of BaseTrackInfo or None if the track cannot be found.
        May throw if a read has failed.
    """
    @abstractmethod
    def __getitem__(self, track_location): pass
    """
        Save a track from memory to disk.
        This method must be able to handle any subclass of BaseTrackInfo, not just the ones returned by
        this respective subclass. To convert to compatible TrackInfo objects, implementations should use
        the `assign` method on their respective BaseTrackInfo implementation to copy details into a
        compatible format.
        Should not delete a track if None is assigned. For extra safety, track info may only be deleted
        with an explicit `del`.
        May throw if a write failed or invalid content supplied for the track.
    """
    @abstractmethod
    def __setitem__(self, track_location, new): pass
    """ Deletes track info by location. Must not delete the actual track file """
    @abstractmethod
    def __delitem__(self, track_location): pass
    """ Iterate over all tracks in this library. Returns a tuple of (track_location, track_info) """
    @abstractmethod
    def __iter__(self): pass
