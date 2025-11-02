from typing import Optional, Dict, Any
from .guardrails import classify_intent

SYSTEM_CORE = (
    "Eres un personaje dentro de un caso de misterio en un circo. "
    "Responde SIEMPRE en español, de forma breve (1–3 oraciones), "
    "manteniendo el foco en la muerte de Canelitas. "
    "No inventes hechos fuera del contexto conocido. "
    "Si la pregunta está fuera de tema, redirige: "
    "\"Concentrémonos en el caso…\""
)

def build_prompt(
    character: Dict[str, Any],
    question: str,
    game_state,
    quoted: Optional[Dict[str, Any]],
    payload_text: str,
    truthful: bool,
) -> str:
    """
    Construye un prompt de una sola pasada (modelo causal) que guía el estilo/persona
    y le da el contenido base a incluir (payload_text) según veracidad.
    """
    name = character["name"]
    role = character.get("role", "")
    persona = character.get("personality", "")
    phase = game_state.phase.name
    evidence = " | ".join(game_state.evidence_revealed) if game_state.evidence_revealed else "—"
    intent = classify_intent(question)

    cited = ""
    if quoted:
        src = quoted.get("source","")
        about = quoted.get("about","")
        qtype = "acusación" if quoted.get("is_accusation") else "apoyo" if quoted.get("is_support") else "cita"
        content = quoted.get("content","")
        cited = f"[CITA: {src} sobre {about} ({qtype}) → \"{content}\"]"

    veracity_rule = (
        "Regla: Sé veraz y usa el payload como hecho propio."
        if truthful else
        "Regla: Evita dar información incriminatoria; suaviza/evade el payload o contradícelo creíblemente sin inventar fuera del contexto."
    )

    # Etiquetas de depuración: mantenemos [Nombre] (INTENT) para compatibilidad con el CLI actual
    debug_tag = f"[{name}] ({intent})"

    return (
        f"{SYSTEM_CORE}\n\n"
        f"[PERSONA]\n"
        f"Nombre: {name}\nRol: {role}\nRasgos: {persona}\n\n"
        f"[FASE] {phase}\n"
        f"[EVIDENCIAS_REVELADAS] {evidence}\n"
        f"{cited}\n\n"
        f"[PREGUNTA]\n{question}\n\n"
        f"[PAYLOAD]\n{payload_text}\n\n"
        f"{veracity_rule}\n"
        f"Estilo: directo si veraz, evasivo si mientes; 1–3 oraciones máximo.\n"
        f"Prefijo la respuesta exactamente con: {debug_tag} "
        f"y NO añadas nada antes del prefijo.\n"
    )
