# engine/state.py
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Any
import re
import unicodedata

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _norm(s: str) -> str:
    return _strip_accents(s.lower().strip())

def _norm_tokens(s: str) -> List[str]:
    return [t for t in re.split(r"\s+|_", _norm(s)) if t]

class Phase(Enum):
    INICIO = auto()
    DESARROLLO = auto()
    CONCLUSION = auto()

@dataclass
class CharacterMemory:
    accused_by: Set[str] = field(default_factory=set)
    supported_by: Set[str] = field(default_factory=set)
    evasion_count: int = 0
    told_facts: Dict[str, Set[str]] = field(default_factory=lambda: {})

@dataclass
class GameState:
    suspects: List[str]
    victim: str
    killer: Optional[str] = None
    phase: Phase = Phase.INICIO

    relations: Dict[str, Dict[str, float]] = field(default_factory=lambda: {})
    per_character_memory: Dict[str, CharacterMemory] = field(default_factory=lambda: {})

    evidence_revealed: List[str] = field(default_factory=list)
    evidence_sources: Dict[str, str] = field(default_factory=dict)

    question_limits: Dict[str, int] = field(default_factory=dict)

    alias_index: Dict[str, str] = field(default_factory=dict)

    knowledge_tracker: Dict[str, Any] = field(default_factory=dict)

    # ---------- Fase ----------
    def set_phase(self, p: Phase):
        self.phase = p

    # ---------- Relaciones ----------
    def get_relationship(self, a: str, b: Optional[str]) -> float:
        if not b or a not in self.relations:
            return 0.0
        return float(self.relations.get(a, {}).get(b, 0.0))

    # ---------- Memoria ----------
    def remember_qa(self, name: str, intent: str, payload: str):
        _ = self.per_character_memory.setdefault(name, CharacterMemory())

    def remember_fact(self, name: str, intent: str, payload: str):
        mem = self.per_character_memory.setdefault(name, CharacterMemory())
        bucket = mem.told_facts.setdefault(intent, set())
        bucket.add(payload)

    def increment_evasion(self, name: str):
        mem = self.per_character_memory.setdefault(name, CharacterMemory())
        mem.evasion_count += 1

    # ---------- Alias / Canónicos ----------
    def build_alias_index(self, characters: Dict[str, Any]):
        idx: Dict[str, str] = {}
        for canonical, data in characters.items():
            base = _norm(canonical)
            idx[base] = canonical
            # tokens individuales (incluye separar por guiones bajos)
            for token in _norm_tokens(canonical):
                idx[token] = canonical
            # alias declarados
            for alias in data.get("aliases", []) or []:
                a = _norm(alias)
                idx[a] = canonical
                for token in _norm_tokens(alias):
                    idx[token] = canonical
            # versión “sin guión bajo” como alias
            if "_" in canonical:
                idx[_norm(canonical.replace("_", " "))] = canonical

        # alias manuales útiles
        manual = {
            "ñopin": "Ñopin desfijo",
            "ñopin desfijo": "Ñopin desfijo",
            "bombita": "Mefisto",
            "mefisto": "Mefisto",
            "madame": "Madame Seraphine",
            "seraphine": "Madame Seraphine",
        }
        for k, v in manual.items():
            idx[_norm(k)] = v

        self.alias_index = idx

    def resolve_alias(self, text: str) -> Optional[str]:
        if not self.alias_index:
            return None
        norm_txt = _norm(text)
        # 1) match exacto
        if norm_txt in self.alias_index:
            return self.alias_index[norm_txt]
        # 2) búsqueda por token como palabra completa
        keys = sorted(self.alias_index.keys(), key=len, reverse=True)
        for k in keys:
            pattern = r"(?<!\w)" + re.escape(k) + r"(?!\w)"
            if re.search(pattern, norm_txt):
                return self.alias_index[k]
        return None

    def canonicalize_name(self, name: str) -> Optional[str]:
        if not name:
            return None
        # exacto
        if name in self.suspects:
            return name
        # por alias
        resolved = self.resolve_alias(name)
        if resolved and resolved in self.suspects:
            return resolved
        # exacto normalizado
        n = _norm(name)
        for s in self.suspects:
            if _norm(s) == n:
                return s
        # match por tokens (ej. "jack" -> "jack_domador")
        n_tokens = set(_norm_tokens(name))
        best = None
        best_score = 0
        for s in self.suspects:
            s_tokens = set(_norm_tokens(s))
            score = len(n_tokens & s_tokens)
            if score > best_score:
                best_score = score
                best = s
        if best and best_score > 0:
            return best
        return None

    # ---------- Relaciones desde YAML ----------
    def ingest_yaml_relations(self, characters: Dict[str, Any], symmetric: bool = False, sym_blend: float = 0.5):
        self.relations = self.relations or {}
        for a_name in self.suspects:
            self.relations.setdefault(a_name, {})

        for a_name, data in characters.items():
            if a_name not in self.suspects:
                continue
            relmap = data.get("relations") or {}
            if not isinstance(relmap, dict):
                continue
            for b_raw, score in relmap.items():
                b_name = self.canonicalize_name(b_raw)
                if not b_name or b_name == a_name:
                    continue
                try:
                    val = max(-1.0, min(1.0, float(score)))
                except Exception:
                    continue
                self.relations.setdefault(a_name, {})[b_name] = val

        if not symmetric:
            return

        for a in self.suspects:
            for b in self.suspects:
                if a == b:
                    continue
                av = self.relations.get(a, {}).get(b, None)
                bv = self.relations.get(b, {}).get(a, None)
                if av is None and bv is None:
                    continue
                if av is None:
                    self.relations.setdefault(a, {})[b] = float(bv) * sym_blend
                elif bv is None:
                    self.relations.setdefault(b, {})[a] = float(av) * sym_blend
                else:
                    m = (float(av) * (1.0 - sym_blend) + float(bv) * sym_blend)
                    self.relations[a][b] = max(-1.0, min(1.0, m))
                    self.relations[b][a] = max(-1.0, min(1.0, m))
