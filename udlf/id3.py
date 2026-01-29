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
    
    def __setitem__(self, key, value):
        self.id3tags.setall(f'TXXX:{PREFIX}{key}', [
            TXXX(
                desc=f'{PREFIX}{key}',
                encoding=Encoding.UTF8,
                text=tagDump(value)
            )
        ])
    
    def tags(self):
        tags = self.id3tags.getall(f'TXXX')
        return filter(lambda t: t.desc.startswith(PREFIX), tags)
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
        
