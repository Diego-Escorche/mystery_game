from dataclasses import dataclass, field
from typing import Dict, Any, List

MAX_QUESTIONS_PER_CHARACTER = 5

@dataclass
class GameState:
    world: Dict[str, Any]
    characters: Dict[str, Any]
    scenarios: Dict[str, Any]
    relations: Dict[str, Any]
    active_scenario: str
    revealed_clues: Dict[str, List[str]] = field(default_factory=dict)
    qa_log: List[Dict[str, str]] = field(default_factory=list)
    question_counts: Dict[str, int] = field(default_factory=dict)
    in_final_stage: bool = False

    def log_qa(self, who: str, q: str, a: str):
        self.qa_log.append({"who": who, "q": q, "a": a})

    def add_clue(self, clue: str):
        scen = self.active_scenario
        self.revealed_clues.setdefault(scen, [])
        if clue not in self.revealed_clues[scen]:
            self.revealed_clues[scen].append(clue)

    def get_scenario(self) -> Dict[str, Any]:
        return self.scenarios[self.active_scenario]

    def inc_questions(self, character: str):
        self.question_counts[character] = self.question_counts.get(character, 0) + 1

    def remaining_questions(self, character: str) -> int:
        return MAX_QUESTIONS_PER_CHARACTER - self.question_counts.get(character, 0)

    def is_char_exhausted(self, character: str) -> bool:
        return self.remaining_questions(character) <= 0

    def all_characters_exhausted(self) -> bool:
        # Consideramos sólo los personajes definidos en characters.yaml
        all_chars = list(self.characters["characters"].keys())
        return all(self.is_char_exhausted(c) for c in all_chars)

    def all_clues_found(self) -> bool:
        scen = self.get_scenario()
        total = len(scen.get("clues", []))
        found = len(self.revealed_clues.get(self.active_scenario, []))
        return total > 0 and found >= total
