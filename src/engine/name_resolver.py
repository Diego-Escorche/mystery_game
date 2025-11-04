from src.utils.text import normalize

class NameResolver:
    def __init__(self, aliases_map):
        # aliases_map: dict canonical -> [aliases...]
        self.index = {}
        for canonical, aliases in aliases_map.items():
            self.index[normalize(canonical)] = canonical
            for a in aliases:
                self.index[normalize(a)] = canonical

    def resolve(self, raw: str):
        key = normalize(raw)
        return self.index.get(key)
