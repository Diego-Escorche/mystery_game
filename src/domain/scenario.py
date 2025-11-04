from dataclasses import dataclass
from typing import Dict, List

@dataclass
class Scenario:
    killer: str
    motive: str
    modus: str
    precrime: Dict[str, str]
    emotional_state: Dict[str, str]
    clues: List[str]
