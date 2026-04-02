import pytest
from dataclasses import dataclass

from udldj.util.dictify import AutoDictify, undictify, UseDefault, undictifyDictUnion
from typing import Optional, Union, List, Tuple, Dict

class KwargsSet:
    def __init__(self, **kwargs):
        for (k,v) in kwargs.items():
            setattr(self, k, v)

def test_dictify_basic():
    class Test(AutoDictify, KwargsSet):
        a: int
        b: str
        c: float
        
    t = Test(a=1, b="2", c=3.0)
    print(t.dictify())
    assert(Test.undictify(t.dictify()).dictify() == t.dictify())
    assert(t.dictify() == {'a': 1, 'b': '2', 'c': 3.0})

def test_dictify_error_basic():
    class Test(AutoDictify, KwargsSet):
        a: int
        b: str
        c: float
    
    with pytest.raises(ValueError) as exc_info: Test.undictify({ 'a': '1', 'b': '2', 'c': 3.0 })
    assert(str(exc_info.value) == 'Expected int, got str')
    with pytest.raises(ValueError) as exc_info: Test.undictify({ 'a': 1, 'b': 2, 'c': 3.0 })
    assert(str(exc_info.value) == 'Expected str, got int')
    with pytest.raises(ValueError) as exc_info: Test.undictify({ 'a': 1, 'b': '2', 'c': '3' })
    assert(str(exc_info.value) == 'Expected float, got str')

def test_dictify_optional():
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

def test_dictify_usedefault():
    class Test(AutoDictify, KwargsSet):
        a: UseDefault[int, 1]
    
    print(Test.undictify({}).dictify())
    assert(Test.undictify({}).dictify() == {'a': 1})

def test_dictify_list():
    class Test(AutoDictify, KwargsSet):
        a: List[str]
        b: List[str]
        
    t = Test(a=["hello","world","test"],b=[])
    print(t.dictify())
    assert(Test.undictify(t.dictify()).dictify() == t.dictify())
    assert(t.dictify() == {'a': ['hello', 'world', 'test'], 'b': []})

def test_dictify_tuple():
    class Test(AutoDictify, KwargsSet):
        a: Tuple[str, int]
        b: Tuple[str, ...]
        
    t = Test(a=("hello", 1),b=("world", "2"))
    print(t.dictify())
    assert(Test.undictify(t.dictify()).dictify() == t.dictify())
    assert(t.dictify() == {'a': ['hello', 1], 'b': ['world', '2']})

    with pytest.raises(ValueError) as exc_info: Test.undictify({'a': ['hello'], 'b': ['world']})
    assert(str(exc_info.value) == 'Expected tuple of length 2, got tuple of length 1')

def test_dictify_dict():
    class Test(AutoDictify, KwargsSet):
        a: Dict[str, int]
        
    t = Test(a={"hello": 1, "world": 2})
    print(t.dictify())
    assert(Test.undictify(t.dictify()).dictify() == t.dictify())
    assert(t.dictify() == {'a': {'hello': 1, 'world': 2}})
    print(t.dictify())

def test_dictify_error_advanced():
    class Test(AutoDictify, KwargsSet):
        a: List[int]
        b: Dict[int, int]
    
    with pytest.raises(ValueError) as exc_info: Test.undictify({ 'a': '123', 'b': {} })
    assert(str(exc_info.value) == 'Expected list, got str')
    with pytest.raises(ValueError) as exc_info: Test.undictify({ 'a': [], 'b': '123' })
    assert(str(exc_info.value) == 'Expected dict, got str')
    
    class Test(AutoDictify, KwargsSet):
        a: Union[int, float]
    
    with pytest.raises(ValueError) as exc_info: Test.undictify({ 'a': '123' })
    assert(len(exc_info.value.args) == 2)
    assert(isinstance(exc_info.value.args[0], ValueError))
    assert(str(exc_info.value.args[0]) == 'Expected int, got str')
    assert(isinstance(exc_info.value.args[1], ValueError))
    assert(str(exc_info.value.args[1]) == 'Expected float, got str')

def test_dictify_union_auto():
    class Test(AutoDictify, KwargsSet):
        a: Union[int, List[int]]
        b: Union[int, List[int]]
        
    t = Test(a=1,b=[2,3])
    print(t.dictify())
    assert(Test.undictify(t.dictify()).dictify() == t.dictify())
    assert(t.dictify() == {'a': 1, 'b': [2, 3]})

def test_undictify_union_manual():
    @dataclass
    class Test1(AutoDictify, KwargsSet):
        hello: int
    @dataclass
    class Test2(AutoDictify, KwargsSet):
        world: int
    
    key = 'key'
    elements = { 'Test1': Test1, 'Test2': Test2 }
    
    print(undictifyDictUnion({ 'key' : 'Test1', 'hello': 1 }, key, elements))
    assert(undictifyDictUnion({ 'key' : 'Test1', 'hello': 1 }, key, elements) == Test1(1))
    print(undictifyDictUnion({ 'key' : 'Test2', 'world': 2 }, key, elements))
    assert(undictifyDictUnion({ 'key' : 'Test2', 'world': 2 }, key, elements) == Test2(2))

def test_undictify_union_manual_error():
    key = 'key'
    elements = {}

    with pytest.raises(ValueError) as exc_info: undictifyDictUnion({ 'hello': 1 }, key, elements)
    assert(str(exc_info.value) == "Union missing 'key'")

    with pytest.raises(ValueError) as exc_info: undictifyDictUnion({ 'key' : '...', 'hello': 1 }, key, elements)
    assert(str(exc_info.value) == "Unknown 'key' '...'")

def test_dictify_nested():
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

def test_dictify_nested_manual():
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
