from typing import Optional, Dict, Any
from .guardrails import classify_intent

SYSTEM_CORE = (
    "Eres un personaje dentro de un caso de misterio en un circo. "
    "Responde SIEMPRE en español, de forma breve (1–3 oraciones), "
    "manteniendo el foco en la muerte de la víctima. "
    "No inventes hechos fuera del contexto conocido. "
    "Si la pregunta está fuera de tema, redirige: "
    "\"Concentrémonos en el caso…\""
)

def _summarize_memory(character_name: str, game_state) -> str:
    m = game_state.per_character_memory.get(character_name)
    if not m:
        return "—"
    parts = []
    if m.told_facts:
        facts_count = sum(len(v) for v in m.told_facts.values())
        parts.append(f"hechos_contados={facts_count}")
    if m.accused_by:
        parts.append(f"acusado_por={','.join(sorted(m.accused_by))}")
    if m.supported_by:
        parts.append(f"apoyado_por={','.join(sorted(m.supported_by))}")
    if m.evasion_count:
        parts.append(f"evasivas={m.evasion_count}")
    if not parts:
        return "—"
    return "; ".join(parts)

def build_prompt(
    character: Dict[str, Any],
    question: str,
    game_state,
    quoted: Optional[Dict[str, Any]],
    payload_text: str,
    truthful: bool,
    said_before: bool = False,
) -> str:
    name = character["name"]
    role = character.get("role", "")
    persona = character.get("personality", "")
    phase = game_state.phase.name
    victim = getattr(game_state, "victim", "la víctima")
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

    memory_line = _summarize_memory(name, game_state)
    debug_tag = f"[{name}] ({intent})"

    ya_lo_comente_rule = (
        "Si este hecho ya lo dijiste antes, COMIENZA la respuesta con: 'Ya lo comenté:' y resume en 1 oración."
        if said_before else
        "No incluyas 'Ya lo comenté' a menos que realmente ya lo hayas dicho antes."
    )

    return (
        f"{SYSTEM_CORE}\n\n"
        f"[PERSONA]\n"
        f"Nombre: {name}\nRol: {role}\nRasgos: {persona}\n\n"
        f"[FASE] {phase}\n"
        f"[VÍCTIMA] {victim}\n"
        f"[EVIDENCIAS_REVELADAS] {evidence}\n"
        f"[MEMORIA_PERSONAJE] {memory_line}\n"
        f"{cited}\n\n"
        f"[PREGUNTA]\n{question}\n\n"
        f"[PAYLOAD]\n{payload_text}\n\n"
        f"{veracity_rule}\n"
        f"{ya_lo_comente_rule}\n"
        f"Estilo: directo si veraz, evasivo si mientes; 1–3 oraciones máximo.\n"
        f"Prefijo la respuesta exactamente con: {debug_tag} "
        f"y NO añadas nada antes del prefijo.\n"
    )
