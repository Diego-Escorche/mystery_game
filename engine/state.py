from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

class Phase(Enum):
    INICIO = auto()
    DESARROLLO = auto()
    CONCLUSION = auto()

@dataclass
class StatementEvent:
    speaker: str
    target: Optional[str]
    content: str
    is_accusation: bool = False
    is_support: bool = False
    timestamp: float = 0.0

@dataclass
class GameState:
    phase: Phase = Phase.INICIO
    suspects: List[str] = field(default_factory=list)
    victim: str = "Canelitas"
    killer: Optional[str] = None
    question_limits: Dict[str, int] = field(default_factory=dict)
    question_limit_per_phase: int = 3
    statements_log: List[StatementEvent] = field(default_factory=list)
    evidence_revealed: List[str] = field(default_factory=list)
    knowledge_tracker: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relationship_matrix: Dict[Tuple[str, str], float] = field(default_factory=dict)
    rng_seed: Optional[int] = None

    def set_phase(self, new_phase: Phase) -> None:
        self.phase = new_phase

    def record_statement(self, event: StatementEvent) -> None:
        self.statements_log.append(event)

    def adjust_relationship(self, a: str, b: str, delta: float) -> None:
        key = (a, b)
        cur = self.relationship_matrix.get(key, 0.0)
        self.relationship_matrix[key] = max(-1.0, min(1.0, cur + delta))

    def get_relationship(self, a: str, b: str) -> float:
        return self.relationship_matrix.get((a, b), 0.0)
