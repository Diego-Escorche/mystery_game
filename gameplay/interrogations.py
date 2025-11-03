from typing import Dict, Optional
from engine.state import GameState, StatementEvent
from engine import rules

# ===== Colores ANSI (CLI) =====
USE_COLOR = True  # ponlo en False si tu terminal no soporta ANSI
RESET  = "\033[0m"  if USE_COLOR else ""
BOLD   = "\033[1m"  if USE_COLOR else ""
GREEN  = "\033[92m" if USE_COLOR else ""
YELLOW = "\033[93m" if USE_COLOR else ""
CYAN   = "\033[96m" if USE_COLOR else ""

# Intents que consideramos “pista” cuando son veraces
CLUE_INTENTS = {"PRUEBAS", "OBJETO", "LUGAR"}

def quote_effect(gs: GameState, target: str, source: str, is_accusation: bool, is_support: bool) -> None:
    if is_accusation:
        gs.adjust_relationship(target, source, rules.RELATION_ACCUSATION_IMPACT)
        gs.mark_accusation(target=target, source=source)
    if is_support:
        gs.adjust_relationship(target, source, rules.RELATION_SUPPORT_IMPACT)
        gs.mark_support(target=target, source=source)

def interrogate(gs: GameState, character: Dict, question: str, model, quoted: Optional[StatementEvent]=None) -> str:
    """
    Ejecuta un interrogatorio. Registra memoria y, si el personaje aporta una
    pista veraz (según intent), agrega la pista al registro, anota quién la aportó
    y devuelve el texto con la marca visual en CLI.
    """
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

    # Pedimos meta para saber intent/veracidad/payload
    answer, meta = model.generate(character, question, gs, quoted=quoted_payload, return_meta=True)

    # Log + memoria básica
    gs.record_statement(StatementEvent(speaker=name, target=None, content=answer))
    gs.remember_qa(name, question, answer)

    intent = meta.get("intent", "GENERAL")
    payload = meta.get("payload", "")
    truthful = meta.get("truthful", False)
    evasive = meta.get("evasive", False)

    # Guardar hecho declarado si fue veraz
    if truthful and payload:
        gs.remember_fact(name, intent, payload)
    if evasive:
        gs.increment_evasion(name)

    # --- Si el payload es veraz y el intent es de pista, registrarla y mostrar mensaje destacado ---
    if truthful and payload and intent in CLUE_INTENTS:
        if payload not in gs.evidence_revealed:
            gs.evidence_revealed.append(payload)
            gs.evidence_sources[payload] = name  # ← quién la aportó
            clue_line = f"{GREEN}{BOLD}Pista encontrada{RESET}: {payload} {BOLD}(aportada por {name}){RESET}"
            answer = f"{answer}\n{clue_line}"

    return answer
