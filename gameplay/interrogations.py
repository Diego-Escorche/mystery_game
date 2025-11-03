from typing import Optional, Dict, Any
from ai.model import CLUE_INTENTS

# Colores CLI
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"

def _mark_clue(gs, speaker: str, payload: str) -> str:
    """
    Agrega la pista a game_state si no estaba; devuelve la línea decorada para imprimir.
    """
    if not payload:
        return ""
    if payload not in gs.evidence_revealed:
        gs.evidence_revealed.append(payload)
        gs.evidence_sources[payload] = speaker
        return f"\n{GREEN}{BOLD}Pista encontrada:{RESET} {payload} {CYAN}(aportada por {speaker}){RESET}"
    return ""

def interrogate(gs, character: Dict[str, Any], question: str, model, quoted: Optional[Any] = None) -> str:
    """
    Orquesta la llamada al modelo y aplica la lógica de detección/registro de pistas.
    """
    name = character["name"]

    # Llama al modelo y recupera meta
    answer, meta = model.generate(character, question, gs, quoted=quoted, return_meta=True)

    # Consumo de “turno” de preguntas
    gs.question_limits[name] = max(0, gs.question_limits.get(name, 0) - 1)

    # Si es veraz y hay payload y la intención es de pista -> registrar
    if meta.get("truthful") and meta.get("payload") and meta.get("intent") in CLUE_INTENTS:
        badge = _mark_clue(gs, name, meta["payload"])
        return f"{answer}{badge}"

    return answer
