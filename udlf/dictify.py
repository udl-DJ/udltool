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
    def dictify(self, dictifiers=None):
        raise Exception("Called dictify on UseDefault... This doesn't make sense")
    def undictify(self, v, undictifiers=None):
        if v is None: return self.default
        else: return undictify(self.inner_type, v, undictifiers)
UseDefault = _UseDefault((None, None))

if __name__ == "__main__":
    import traceback
    class KwargsSet:
        def __init__(self, **kwargs):
            for (k,v) in kwargs.items():
                setattr(self, k, v)
    
    TESTS = []
    def test(name):
        def _(fn):
            global TESTS
            TESTS.append((name, fn))
            return fn
        return _
    
    def getException(cb):
        try:
            cb()
        except Exception as e: return e
        return None
    def compareExceptions(e1, e2): return type(e1) == type(e2) and str(e1) == str(e2)
    def assertThrows(cb, e):
        exc = getException(cb)
        print(exc)
        assert(compareExceptions(exc, e))
    
    @test("Basic")
    def _():
        class Test(AutoDictify, KwargsSet):
            a: int
            b: str
            c: float
            
        t = Test(a=1, b="2", c=3.0)
        print(t.dictify())
        assert(Test.undictify(t.dictify()).dictify() == t.dictify())
        assert(t.dictify() == {'a': 1, 'b': '2', 'c': 3.0})
    
    @test("Basic Errors")
    def _():
        class Test(AutoDictify, KwargsSet):
            a: int
            b: str
            c: float
        
        assertThrows(lambda: Test.undictify({ 'a': '1', 'b': '2', 'c': 3.0 }), ValueError('Expected int, got str'))
        assertThrows(lambda: Test.undictify({ 'a': 1, 'b': 2, 'c': 3.0 }), ValueError('Expected str, got int'))
        assertThrows(lambda: Test.undictify({ 'a': 1, 'b': '2', 'c': '3' }), ValueError('Expected float, got str'))
    
    @test("Optional")
    def _():
        class Test(AutoDictify, KwargsSet):
            a: Optional[int]
            b: Optional[int] = None
            c: Optional[int] = 1
        
        t = Test(a=1, b=2, c=3)
        print(t.dictify())
        assert(Test.undictify(t.dictify()).dictify() == t.dictify())
        assert(t.dictify() == {'a': 1, 'b': 2, 'c': 3})
        
        t = Test(a=None, b=None, c=None)
        assert(Test.undictify(t.dictify()).dictify() == t.dictify())
        assert(t.dictify() == {})
    
    @test("UseDefault")
    def _():
        class Test(AutoDictify, KwargsSet):
            a: UseDefault[int, 1]
        
        print(Test.undictify({}).dictify())
        assert(Test.undictify({}).dictify() == {'a': 1})
    
    @test("List")
    def _():
        class Test(AutoDictify, KwargsSet):
            a: List[str]
            b: List[str]
            
        t = Test(a=["hello","world","test"],b=[])
        print(t.dictify())
        assert(Test.undictify(t.dictify()).dictify() == t.dictify())
        assert(t.dictify() == {'a': ['hello', 'world', 'test'], 'b': []})
    
    @test("Tuple")
    def _():
        class Test(AutoDictify, KwargsSet):
            a: Tuple[str, int]
            b: Tuple[str, ...]
            
        t = Test(a=("hello", 1),b=("world", "2"))
        print(t.dictify())
        assert(Test.undictify(t.dictify()).dictify() == t.dictify())
        assert(t.dictify() == {'a': ['hello', 1], 'b': ['world', '2']})
    
    @test("Dict")
    def _():
        class Test(AutoDictify, KwargsSet):
            a: Dict[str, int]
            
        t = Test(a={"hello": 1, "world": 2})
        print(t.dictify())
        assert(Test.undictify(t.dictify()).dictify() == t.dictify())
        assert(t.dictify() == {'a': {'hello': 1, 'world': 2}})
        print(t.dictify())
    
    @test("Advanced Errors")
    def _():
        class Test(AutoDictify, KwargsSet):
            a: List[int]
            b: Dict[int, int]
        
        assertThrows(lambda: Test.undictify({ 'a': '123', 'b': {} }), ValueError('Expected list, got str'))
        assertThrows(lambda: Test.undictify({ 'a': [], 'b': '123' }), ValueError('Expected dict, got str'))
        
        class Test(AutoDictify, KwargsSet):
            a: Union[int, float]
        assertThrows(
            lambda: Test.undictify({ 'a': '123' }),
            ValueError(ValueError('Expected int, got str'),ValueError('Expected float, got str'))
        )
    
    @test("Auto Union")
    def _():
        class Test(AutoDictify, KwargsSet):
            a: Union[int, List[int]]
            b: Union[int, List[int]]
            
        t = Test(a=1,b=[2,3])
        print(t.dictify())
        assert(Test.undictify(t.dictify()).dictify() == t.dictify())
        assert(t.dictify() == {'a': 1, 'b': [2, 3]})
    
    @test("Nested Objects")
    def _():
        class Nested(AutoDictify, KwargsSet):
            b: str
            c: float
        class Test(AutoDictify, KwargsSet):
            a: int
            o: Nested
            
        t = Test(a=1,o=Nested(b="2",c=3.0))
        print(t.dictify())
        assert(Test.undictify(t.dictify()).dictify() == t.dictify())
        assert(t.dictify() == {'a': 1, 'o': {'b': '2', 'c': 3.0}})
    
    @test("Nested Manual Dictification")
    def _():
        class Nested(AutoDictify, KwargsSet):
            b: str
            c: float
            def dictify(self): return [self.b, self.c]
            @staticmethod
            def undictify(o):
                assert(len(o) == 2)
                return Nested(b=o[0],c=o[1])
        class Test(AutoDictify, KwargsSet):
            a: int
            o: Nested
            
        t = Test(a=1,o=Nested(b="2",c=3.0))
        print(t.dictify())
        assert(Test.undictify(t.dictify()).dictify() == t.dictify())
        assert(t.dictify() == {'a': 1, 'o': ['2', 3.0]})
    
    for (name, cb) in TESTS:
        print(name)
        _print = print
        print = lambda *args,**kwargs: _print('   ', *args, **kwargs)
        try:
            cb()
            print = _print
            print("Test Passed")
        except Exception:
            print = _print
            traceback.print_exc()
            print("Test Failed")
        print()

