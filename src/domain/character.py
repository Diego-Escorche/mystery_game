from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Character:
    name: str
    role: str
    voice: str
    traits: List[str]
    tics: List[str]
    base_emotion: str

    @classmethod
    def from_dict(cls, name: str, data: Dict):
        return cls(
            name=name,
            role=data.get("role", ""),
            voice=data.get("voice", ""),
            traits=data.get("traits", []),
            tics=data.get("tics", []),
            base_emotion=data.get("base_emotion", "")
        )
