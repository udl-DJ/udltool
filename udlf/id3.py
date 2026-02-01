import json
from mutagen.id3 import ID3,TXXX,Encoding

PREFIX = "UDLF:"

def tagDump(obj):
    if isinstance(obj, list):
        if len(obj) == 0: return ['','']
        elif len(obj) == 1: return [json.dumps(obj[0]),'']
        else: return [json.dumps(v) for v in obj]
    else:
        return [json.dumps(obj)]

def safeTagParse(tag):
    try:
        if len(tag.text) > 1:
            return [json.loads(t) for t in tag.text if t]
        else:
            return json.loads(tag.text[0])
    except Exception:
        return None

class UDL_ID3:
    def __init__(self, id3tags):
        self.id3tags = id3tags
    
    # TODO: Handle bad data better than just returning None
    def __getitem__(self, key):
        tags = self.id3tags.getall(f'TXXX:{PREFIX}{key}')
        for tag in tags:
            res = safeTagParse(tags[0])
            if not res is None: return res
        return None
    def __contains__(self, key):
        tags = self.id3tags.getall(f'TXXX:{PREFIX}{key}')
        return len(tags) > 0
    
    def __setitem__(self, key, value):
        if value is None:
            self.__delitem__(key)
        else:
            self.id3tags.setall(f'TXXX:{PREFIX}{key}', [
                TXXX(
                    desc=f'{PREFIX}{key}',
                    encoding=Encoding.UTF8,
                    text=tagDump(value)
                )
            ])
    def __delitem__(self, key):
        self.id3tags.delall(f'TXXX:{PREFIX}{key}')
    
    def assign(self, other, overwrite=False):
        if not isinstance(other, UDL_ID3): raise ValueError('Not UDF ID3')
        for k in other:
            if overwrite or (not k in self):
                tn = f'TXXX:{PREFIX}{k}'
                self.id3tags.setall(tn, other.id3tags.getall(tn))
    def clear(self):
        for t in self: del self[t]
    
    def tags(self):
        tags = self.id3tags.getall(f'TXXX')
        return filter(lambda t: t.desc.startswith(PREFIX), tags)
    def tags_sorted_tuples(self): return sorted(map(lambda t: (t.desc, t.text), self.tags()))
    def items(self):
        return map(
            lambda t: (t.desc[len(PREFIX):],safeTagParse(t)),
            self.tags()
        )
    def keys(self):
        return map(
            lambda t: t.desc[len(PREFIX):],
            self.tags()
        )
    def values(self): return map(safeTagParse, self.tags())
    def __iter__(self): return set(self.keys()).__iter__()
    def __eq__(self, other): return self.tags_sorted_tuples() == other.tags_sorted_tuples()

    def __str__(self): return '\n'.join('='.join([str(o) for o in v]) for v in self.items())

if __name__ == '__main__':
    from mutagen.id3 import ID3
    from udlf.id3 import UDL_ID3

    t = ID3()
    t.load("440hz_tone.mp3")

    kv = UDL_ID3(t)

    kv["test"] = "hello"
    kv["json"] = {"yeet":"hi"}
    kv["test"] = "world"
    kv["array1"] = ['a']
    kv["array2"] = ['a','b']
    kv["a"] = "a"
    kv["b"] = "b"

    print(t.pprint())
    print()
    print(kv["json"])
    print(t.getall('TXXX:UDLF:array1'))
    print(t.getall('TXXX:UDLF:array2'))

    for tag in kv:
        print(tag)

    print(*kv.items())

    del kv["a"]
    kv["b"] = None

    for tag in kv:
        print(tag)

    print(*kv.items())

    t.save()

    print()
    kv.clear()
    print(t.pprint())

    print()
    
    kv1 = UDL_ID3(ID3())
    kv1['a'] = 'a'
    kv1['b'] = 'b1'
    
    kv2 = UDL_ID3(ID3())
    kv2['b'] = 'b2'
    kv2['c'] = 'c'

    kv1.assign(kv2, overwrite=False)
    print(kv1)
    print()

    kv1.assign(kv2, overwrite=True)
    print(kv1)
