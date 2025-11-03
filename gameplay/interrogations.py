# gameplay/interrogations.py
from typing import Optional, Dict, Any
from engine.state import GameState
import re

# Colores / estilos CLI
RESET = "\033[0m"
BOLD = "\033[1m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
CYAN = "\033[36m"

def interrogate(
    gs: GameState,
    character: Dict[str, Any],
    question: str,
    model,  # AIModelAdapter
    quoted: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Ejecuta un turno de interrogatorio:
      - Genera respuesta con el modelo (y obtiene META).
      - Si META.payload tiene contenido, lo registra como pista.
      - Devuelve la línea a mostrar (y, si hay pista, añade la notificación en nueva línea).
    """

    # Generar respuesta con meta
    line, meta = model.generate(
        character=character,
        question=question,
        game_state=gs,
        quoted=quoted,
        return_meta=True,
    )

    # Registrar memoria básica (opcional)
    name = character["name"]

    # Detectar y registrar pista basada en payload válido (no vacío, sin placeholders)
    clue_badge = ""
    payload_clean = (meta.get("payload") or "").strip()
    if payload_clean:
        # Ignorar si parece placeholder o contiene delimitadores
        looks_placeholder = False
        if re.search(r"[<>{}\[\]]", payload_clean):
            looks_placeholder = True
        low = payload_clean.lower()
        if "hecho/pista" in low or "pista si aplica" in low or low in {"n/a","na","none","sin pista","no aplica","no hay"}:
            looks_placeholder = True

        if not looks_placeholder:
            if payload_clean not in gs.evidence_revealed:
                gs.evidence_revealed.append(payload_clean)
                gs.evidence_sources[payload_clean] = name
                clue_badge = f"\n{GREEN}{BOLD}Pista encontrada:{RESET} {payload_clean} {CYAN}(aportada por {name}){RESET}"

    # Decrementar cupo de preguntas del personaje en esta fase
    if gs.question_limits.get(name, 0) > 0:
        gs.question_limits[name] -= 1

    # Devolver línea formateada (+ badge de pista si aplica)
    return f"{line}{clue_badge}"
