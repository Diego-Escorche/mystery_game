from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Character:
    name: str
    role: str
    personality_key: str
    knowledge: Dict[str, Any] = field(default_factory=dict)
    relations: Dict[str, float] = field(default_factory=dict)
    is_killer: bool = False
    truthfulness: float = 0.85
    hostility: float = 0.0
    focus: float = 1.0

    def view_of(self, other: str) -> float:
        return self.relations.get(other, 0.0)

    def shift_relation(self, other: str, delta: float) -> None:
        self.relations[other] = max(-1.0, min(1.0, self.relations.get(other, 0.0) + delta))
