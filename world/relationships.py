from typing import Dict, Tuple, List

def seed_relationships(names: List[str]) -> Dict[Tuple[str,str], float]:
    rel = {}
    for a in names:
        for b in names:
            if a == b:
                continue
            rel[(a,b)] = 0.0
    return rel
