from typing import Dict, Optional
from ..engine.state import GameState, StatementEvent
from ..engine import rules

def quote_effect(gs: GameState, target: str, source: str, is_accusation: bool, is_support: bool) -> None:
    if is_accusation:
        gs.adjust_relationship(target, source, rules.RELATION_ACCUSATION_IMPACT)
    if is_support:
        gs.adjust_relationship(target, source, rules.RELATION_SUPPORT_IMPACT)

def interrogate(gs: GameState, character: Dict, question: str, model, quoted: Optional[StatementEvent]=None) -> str:
    name = character["name"]
    gs.question_limits[name] = max(0, gs.question_limits.get(name, gs.question_limit_per_phase) - 1)

    quoted_payload = None
    if quoted:
        quote_effect(gs, target=name, source=quoted.speaker, is_accusation=quoted.is_accusation, is_support=quoted.is_support)
        quoted_payload = {
            "source": quoted.speaker,
            "about": quoted.target,
            "is_accusation": quoted.is_accusation,
            "is_support": quoted.is_support,
            "content": quoted.content,
        }

    answer = model.generate(character, question, gs, quoted=quoted_payload)
    gs.record_statement(StatementEvent(speaker=name, target=None, content=answer))
    return answer
