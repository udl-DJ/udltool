from typing import get_type_hints,get_origin,get_args
from typing import Optional,Union,List,Tuple,Dict

"""
    Gets `key` from `dict_to_access`; If `key` is not present, returns `dict_to_access[default_key]`.
"""
def defKey(dict_to_access, key, default_key=None):
    return dict_to_access[key] if key in dict_to_access else dict_to_access[default_key]
def get_clean_origin(tp):
    o = get_origin(tp)
    return o if not o is None else tp

def _dictifyDict(value, d):
    res = { dictify(k, d): dictify(v, d) for k,v in value.items() }
    return { k:v for k,v in res.items() if not v is None }
def _dictifyList(value, d): return [dictify(v, d) for v in value]
DICTIFIERS = {
    dict: _dictifyDict,
    list: _dictifyList,
    tuple: _dictifyList,
    set: _dictifyList,
    bool: lambda v, d: v,
    int: lambda v, d: v,
    float: lambda v, d: v,
    str: lambda v, d: v,
    type(None): lambda v, d: v,
    None: lambda v, d: v.dictify()
}

def enforceType(v, t):
    if not type(v) == t: raise ValueError(f'Expected {t.__name__}, got {type(v).__name__}')
    return v
def _undictifyUnion(type_tgt, v, u):
    types = get_args(type_tgt)
    errors = []
    for type_new in types:
        try:
            return undictify(type_new, v, u)
        except Exception as e: errors.append(e)
    raise ValueError(*errors)
def _undictifyList(type_tgt, l, u):
    types = get_args(type_tgt)
    #assert(type(l) == list, "Expected list type")
    return [undictify(types[0], v, u) for v in l]
def _undictifyTuple(type_tgt, l, u):
    types = get_args(type_tgt)
    enforceType(l, list)
    if len(types) == 2 and types[1] == Ellipsis:
        return _undictifyList(type_tgt, l, u)
    if not len(l) == len(types):
        raise ValueError(f'Expected tuple of length {len(types)}, got tuple of length {len(l)}')
    return [undictify(t, v, u) for (t,v) in zip(types,l)]
def _undictifyDict(type_tgt, d, u):
    types = get_args(type_tgt)
    #assert(type(l) == dict, "Expected dict type")
    assert(len(types) == 2)
    return {undictify(types[0], k, u): undictify(types[1], v, u) for (k,v) in d.items()}
UNDICTIFIERS = {
    Union: _undictifyUnion,
    list: lambda t, v, u: _undictifyList(t, enforceType(v, list), u),
    tuple: lambda t, v, u: _undictifyTuple(t, enforceType(v, list), u),
    dict: lambda t, v, u: _undictifyDict(t, enforceType(v, dict), u),
    bool: lambda t, v, u: enforceType(v, bool),
    int: lambda t, v, u: enforceType(v, int),
    float: lambda t, v, u: enforceType(v, float),
    str: lambda t, v, u: enforceType(v, str),
    type(None): lambda t, v, u: None,
    None: lambda t, v, u: t.undictify(v)
}

def dictify(data, dictifiers=None):
    if not type(dictifiers) == dict: dictifiers = {}
    dictifiers = {**DICTIFIERS, **dictifiers}
    return defKey(dictifiers,type(data))(data,dictifiers)
def undictify(type_tgt, data, undictifiers=None):
    if not type(undictifiers) == dict: undictifiers = {}
    undictifiers = {**UNDICTIFIERS, **undictifiers}
    return defKey(undictifiers,get_clean_origin(type_tgt))(type_tgt, data, undictifiers)

class AutoDictify:
    def dictify(self, dictifiers=None):
        hints = get_type_hints(self)
        res = {k: dictify(getattr(self, k), dictifiers) for k in hints.keys() if hasattr(self, k)}
        return { k:v for k,v in res.items() if not v is None }
    @classmethod
    def undictify(cls, v, undictifiers=None):
        hints = get_type_hints(cls)
        instance = cls.__new__(cls)
        if not isinstance(v, dict): raise ValueError(f"Got {v}, expected a dict of values")
        for k, t in hints.items(): setattr(instance, k, undictify(t, v[k] if k in v else None))
        return instance

def undictifyDictUnion(v, key, elements, undictifiers=None):
    enforceType(v, dict)
    if not key in v: raise ValueError(f"Union missing '{key}'")
    if not v[key] in elements: raise ValueError(f"Unknown '{key}' '{v[key]}'")
    return elements[v[key]].undictify(v, undictifiers)

class _UseDefault:
    def __init__(self, arg_tuple): (self.inner_type, self.default) = arg_tuple
    def __getitem__(self, i): return _UseDefault(i)
    def undictify(self, v, undictifiers=None):
        if v is None: return self.default
        else: return undictify(self.inner_type, v, undictifiers)
UseDefault = _UseDefault((None, None))
