from typing import Dict, Optional
from engine.state import GameState, StatementEvent
from engine import rules
from ai.guardrails import classify_intent

def quote_effect(gs: GameState, target: str, source: str, is_accusation: bool, is_support: bool) -> None:
    if is_accusation:
        gs.adjust_relationship(target, source, rules.RELATION_ACCUSATION_IMPACT)
        gs.mark_accusation(target=target, source=source)
    if is_support:
        gs.adjust_relationship(target, source, rules.RELATION_SUPPORT_IMPACT)
        gs.mark_support(target=target, source=source)

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

    answer, meta = model.generate(character, question, gs, quoted=quoted_payload, return_meta=True)
    # meta puede contener: {"intent": str, "truthful": bool, "payload": str, "evasive": bool}

    # Log + memoria
    gs.record_statement(StatementEvent(speaker=name, target=None, content=answer))
    gs.remember_qa(name, question, answer)

    intent = meta.get("intent", "GENERAL")
    payload = meta.get("payload", "")
    truthful = meta.get("truthful", False)
    evasive = meta.get("evasive", False)

    if truthful and payload:
        gs.remember_fact(name, intent, payload)
    if evasive:
        gs.increment_evasion(name)

    return answer
