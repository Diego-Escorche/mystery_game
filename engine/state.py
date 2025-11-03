from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import deque

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
class CharacterMemory:
    """Memoria persistente por personaje para coherencia multi-ronda."""
    # Historial breve de Q/A recientes (para eco de “ya te dije”)
    last_questions: deque = field(default_factory=lambda: deque(maxlen=5))
    last_answers: deque = field(default_factory=lambda: deque(maxlen=5))
    # Hechos ya declarados (por intent)
    told_facts: Dict[str, Set[str]] = field(default_factory=dict)
    # Quién lo acusó / quién lo defendió
    accused_by: Set[str] = field(default_factory=set)
    supported_by: Set[str] = field(default_factory=set)
    # A quién acusó/apoyó este personaje (por si luego le preguntan y deba sostener)
    accused_others: Set[str] = field(default_factory=set)
    supported_others: Set[str] = field(default_factory=set)
    # Contador de evasivas (si evade mucho, el jugador puede presionar distinto)
    evasion_count: int = 0

    def remember_fact(self, intent: str, text: str) -> None:
        b = self.told_facts.setdefault(intent, set())
        b.add(text)

    def remember_qa(self, q: str, a: str) -> None:
        self.last_questions.append(q)
        self.last_answers.append(a)

    def mark_accused_by(self, name: str) -> None:
        self.accused_by.add(name)

    def mark_supported_by(self, name: str) -> None:
        self.supported_by.add(name)

    def mark_accused_other(self, name: str) -> None:
        self.accused_others.add(name)

    def mark_supported_other(self, name: str) -> None:
        self.supported_others.add(name)

    def increment_evasion(self) -> None:
        self.evasion_count += 1

@dataclass
class GameState:
    phase: Phase = Phase.INICIO
    suspects: List[str] = field(default_factory=list)
    victim: str = "Ñopin Desfijo"
    killer: Optional[str] = None
    question_limits: Dict[str, int] = field(default_factory=dict)
    question_limit_per_phase: int = 3
    statements_log: List[StatementEvent] = field(default_factory=list)
    evidence_revealed: List[str] = field(default_factory=list)
    knowledge_tracker: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relationship_matrix: Dict[Tuple[str, str], float] = field(default_factory=dict)
    rng_seed: Optional[int] = None

    # Nueva: memoria por personaje
    per_character_memory: Dict[str, CharacterMemory] = field(default_factory=dict)

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

    # ====== Helpers de memoria ======
    def mem(self, name: str) -> CharacterMemory:
        if name not in self.per_character_memory:
            self.per_character_memory[name] = CharacterMemory()
        return self.per_character_memory[name]

    def remember_qa(self, name: str, question: str, answer: str) -> None:
        self.mem(name).remember_qa(question, answer)

    def remember_fact(self, name: str, intent: str, fact_text: str) -> None:
        self.mem(name).remember_fact(intent, fact_text)

    def mark_accusation(self, target: str, source: str) -> None:
        self.mem(target).mark_accused_by(source)

    def mark_support(self, target: str, source: str) -> None:
        self.mem(target).mark_supported_by(source)

    def mark_character_accused_other(self, speaker: str, other: str) -> None:
        self.mem(speaker).mark_accused_other(other)

    def mark_character_supported_other(self, speaker: str, other: str) -> None:
        self.mem(speaker).mark_supported_other(other)

    def increment_evasion(self, name: str) -> None:
        self.mem(name).increment_evasion()
