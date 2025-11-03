import json
import random
import re
import unicodedata
from typing import Dict, Any, Optional, Tuple

from .guardrails import is_offtopic, enforce_focus, classify_intent

CLUE_INTENTS = {"PRUEBAS", "OBJETO", "LUGAR", "RUMOR"}

INTENT_LIE_WEIGHTS_KILLER = {
    "COARTADA": 0.28, "PRUEBAS": 0.22, "MÓVIL": 0.22, "RELACIONES": 0.12,
    "LUGAR": 0.18, "OBJETO": 0.18, "RUMOR": 0.18, "GENERAL": 0.08,
}
INTENT_LIE_WEIGHTS_INNOCENT = {
    "COARTADA": -0.05, "PRUEBAS": -0.05, "MÓVIL": -0.02, "RELACIONES": 0.0,
    "LUGAR": 0.0, "OBJETO": 0.0, "RUMOR": 0.0, "GENERAL": 0.0,
}

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _norm(s: str) -> str:
    return _strip_accents(s.lower().strip())

def _pick_factual(character: Dict[str, Any], intent: str) -> Optional[str]:
    kn = character.get("knowledge", {})
    bucket = kn.get(intent) or kn.get(intent.capitalize())
    if isinstance(bucket, list) and bucket:
        return random.choice(bucket)
    return None

def _relationship_pressure(game_state, name: str) -> float:
    mem = game_state.per_character_memory.get(name)
    pressure = 0.0
    if mem:
        pressure += min(0.30, 0.10 * len(mem.accused_by))
        pressure -= min(0.20, 0.05 * len(mem.supported_by))
        pressure += min(0.15, 0.03 * mem.evasion_count)
    return pressure

def _phase_pressure(game_state) -> float:
    return 0.15 if game_state.phase.name != "INICIO" else 0.0

def _quote_pressure(quoted) -> float:
    if quoted and quoted.get("is_accusation"):
        return 0.25
    return 0.0

def _said_before(game_state, name: str, intent: str, payload_text: str) -> bool:
    if not payload_text:
        return False
    mem = game_state.per_character_memory.get(name)
    if not mem:
        return False
    facts = mem.told_facts.get(intent, set())
    return payload_text in facts

def _rel_label(score: float) -> str:
    if score >= 0.35:
        return "defiende / confía"
    if score <= -0.35:
        return "desconfía / podría acusar"
    return "neutral / ambiguo"

def _detect_target_person(game_state, question: str) -> Optional[str]:
    q = _norm(question)
    for s in game_state.suspects:
        if _norm(s) in q:
            return s
    return None

class PromptBuilder:
    @staticmethod
    def brief_character(character: Dict[str, Any]) -> str:
        return (
            f"Nombre: {character.get('name')}\n"
            f"Rol: {character.get('role','')}\n"
            f"Personalidad: {character.get('personality','')}\n"
        )

    @staticmethod
    def brief_context(game_state, quoted: Optional[Dict[str, Any]]) -> str:
        evs = game_state.evidence_revealed[-5:] if game_state.evidence_revealed else []
        ev_text = ("- " + "\n- ".join(evs)) if evs else "(sin evidencias registradas)"
        quoted_text = ""
        if quoted:
            src = quoted.get("source")
            about = quoted.get("about")
            content = quoted.get("content","")
            acc = "acusación" if quoted.get("is_accusation") else ("apoyo" if quoted.get("is_support") else "cita")
            quoted_text = f"\nÚltima cita: {acc} de {src} sobre {about}: “{content}”."
        return (
            f"Fase: {game_state.phase.name}\n"
            f"Víctima: {game_state.victim}\n"
            f"Evidencias recientes:\n{ev_text}{quoted_text}"
        )

    @staticmethod
    def brief_relations(game_state, name: str, target_person: Optional[str]) -> str:
        parts = []
        for other in game_state.suspects:
            if other == name:
                continue
            v = game_state.get_relationship(name, other)
            if abs(v) >= 0.2 or (target_person and other == target_person):
                tag = _rel_label(v)
                parts.append(f"{other}: {tag} ({v:+.2f})")
        return "Relaciones relevantes: " + (", ".join(parts) if parts else "(neutras)")

    @staticmethod
    def build_dialog_prompt(
        character: Dict[str, Any],
        question: str,
        intent: str,
        policy: str,
        must_include_clue: bool,
        selected_payload: Optional[str],
        game_state,
        quoted: Optional[Dict[str, Any]],
        target_person: Optional[str]
    ) -> str:
        sheet = PromptBuilder.brief_character(character)
        ctx = PromptBuilder.brief_context(game_state, quoted)
        rels = PromptBuilder.brief_relations(game_state, character["name"], target_person)

        rel_line = ""
        if target_person:
            score = game_state.get_relationship(character["name"], target_person)
            rel_line = f"\n[TARGET_PERSON]\nPersona objetivo mencionada por el jugador: {target_person}\nRelación hacia {target_person}: {_rel_label(score)} ({score:+.2f})\n- Si la relación es negativa, puedes insinuar sospecha.\n- Si es positiva, tiende a defender o matizar a favor.\n"

        clue_guidance = ""
        if must_include_clue and selected_payload:
            clue_guidance = (
                "\n- Debes INCLUIR esta pista de forma natural y verificable para el jugador: "
                f"«{selected_payload}». No la inventes; exprésala con tus palabras."
            )

        return f"""\
[SYSTEM]
Responde SOLO como el personaje. Sin narrador externo, sin etiquetas adicionales.
No inventes hechos fuera del mundo del circo ni contradigas evidencias registradas.
Mantén foco en el caso; si la pregunta es ajena, recentra brevemente y vuelve al caso.

[CHARACTER SHEET]
{sheet}

[CONTEXT]
{ctx}

{rels}{rel_line}
[QUESTION]
Jugador: "{question}"

[INTENT]
{intent}

[POLICY]
Decisión: {policy}
- TRUTH: responder verazmente con detalles concretos del mundo (evita vaguedades).
- LIE: engaños plausibles y consistentes con personalidad/relaciones; no contradigas pruebas obvias.
- HEDGE: ambiguo/parsimonioso sin negar todo; puedes usar cautela.

[STYLE]
- 1–3 oraciones. Tono acorde a la personalidad. Reacciona a acusación/apoyo si aplica.
{clue_guidance}

[OUTPUT FORMAT]
<META>{{"intent":"{intent}","truthful":{str(policy=='TRUTH').lower()},"payload":"<hecho/pista base si corresponde>","evasive":{str(policy!='TRUTH').lower()},"said_before":false}}</META>
{{LÍNEA DE DIÁLOGO DEL PERSONAJE}}\
"""

    @staticmethod
    def build_ending_prompt(game_state, accused: str, characters: Dict[str, Any]) -> str:
        killer = game_state.killer
        ev = list(dict.fromkeys(game_state.evidence_revealed))[:3]
        ev_text = ", ".join(ev) if ev else "casi sin pruebas claras"
        killer_role = (characters.get(killer, {}).get("role") or "").lower()
        role_hint = ""
        if "ilusionista" in killer_role:
            role_hint = "juegos de manos y desvíos de atención"
        elif "funámbul" in killer_role:
            role_hint = "destreza con cuerdas y equilibrio"
        elif "payaso" in killer_role:
            role_hint = "maquillaje y utilería"
        elif "domador" in killer_role:
            role_hint = "disciplina férrea"
        elif "hombre fuerte" in killer_role:
            role_hint = "fuerza bruta detrás de una sonrisa"
        elif "contorsion" in killer_role:
            role_hint = "flexibilidad imposible"

        outcome = ("ACIERTO" if accused == killer else ("INOCENTE" if accused in game_state.suspects else "INVALIDA"))
        return f"""\
[SYSTEM] Eres un narrador sobrio. Cierre breve (4–6 oraciones) en tono noir.

[DATA]
Acusado por el jugador: {accused}
Asesino real: {killer}
Evidencias clave: {ev_text}
Rol del asesino: {killer_role} ({role_hint})

[OUTCOME]
{outcome}

[FORMAT]
Devuelve SOLO el relato final.\
"""

class AIModelAdapter:
    def __init__(self, seed: Optional[int] = None, llm_backend: Optional[Any] = None):
        self.rnd = random.Random(seed)
        self.llm = llm_backend

    def _decide_truth(self, character: Dict[str, Any], intent: str, game_state, quoted) -> Tuple[str, float]:
        is_killer = character.get("is_killer", False)
        base_truth = character.get("truthfulness", 0.85)
        hostility = character.get("hostility", 0.0)

        pressure = _phase_pressure(game_state)
        pressure += _relationship_pressure(game_state, character["name"])
        pressure += _quote_pressure(quoted)
        pressure += max(0.0, hostility) * 0.30

        if is_killer:
            lie_bias = INTENT_LIE_WEIGHTS_KILLER.get(intent, 0.10)
            truth_chance = max(0.05, min(0.85, 0.50 - pressure*0.25 - lie_bias))
            if intent in CLUE_INTENTS:
                phase = game_state.phase.name
                phase_floor = 0.12 if phase == "INICIO" else (0.20 if phase == "DESARROLLO" else 0.28)
                truth_chance = max(truth_chance, phase_floor)
        else:
            lie_bias = INTENT_LIE_WEIGHTS_INNOCENT.get(intent, 0.0)
            truth_chance = max(0.30, min(0.98, base_truth - pressure*0.10 + (-lie_bias)))

        r = self.rnd.random()
        policy = "TRUTH" if r < truth_chance else ("LIE" if self.rnd.random() < 0.5 else "HEDGE")
        return policy, pressure

    def _publish_memory_flags(self, game_state, name: str, intent: str, payload: str, truthful: bool, evasive: bool):
        game_state.remember_qa(name, intent, payload or "")
        if truthful and payload:
            game_state.remember_fact(name, intent, payload)
        if evasive:
            game_state.increment_evasion(name)

    def _llm_generate(self, prompt: str) -> str:
        if self.llm is None:
            return ""
        try:
            return self.llm.generate(prompt)
        except Exception:
            return ""

    def _fallback_line(self, *, name: str, intent: str, policy: str, payload: Optional[str],
                       target_person: Optional[str], rel_score: Optional[float]) -> Tuple[str, Dict[str, Any]]:
        truthful = (policy == "TRUTH")
        evasive = (policy != "TRUTH")
        said_before_flag = False

        # Redacción mínima sin frases enlatadas:
        pieces = []

        if target_person:
            # opinión basada en relación
            if rel_score is not None:
                if rel_score >= 0.35:
                    pieces.append(f"{target_person} no se me hace sospechosa; la he visto actuar con calma.")
                elif rel_score <= -0.35:
                    pieces.append(f"{target_person} me inquieta; hubo gestos y tensión poco normales.")
                else:
                    pieces.append(f"De {target_person} no tengo postura firme; hubo actitudes ambiguas.")
        # payload si hay
        if truthful and payload:
            pieces.append(payload)
        elif policy == "LIE":
            pieces.append("No tengo nada útil que aportar en ese punto.")
        else:  # HEDGE
            pieces.append("No podría afirmarlo con seguridad.")

        line = " ".join(pieces).strip()
        meta = {
            "intent": intent,
            "truthful": truthful,
            "payload": payload or "",
            "evasive": evasive,
            "said_before": said_before_flag
        }
        meta_str = f'<META>{json.dumps(meta, ensure_ascii=False)}</META>'
        return f"{meta_str}\n{line}", meta

    def _parse_meta(self, text: str) -> Tuple[str, Dict[str, Any]]:
        m = re.search(r"<META>(.*?)</META>\s*(.*)$", text.strip(), re.DOTALL)
        if not m:
            return text.strip(), {"intent":"GENERAL","truthful":False,"payload":"","evasive":True,"said_before":False}
        meta_raw = m.group(1).strip()
        spoken = m.group(2).strip()
        try:
            meta = json.loads(meta_raw)
        except Exception:
            meta = {"intent":"GENERAL","truthful":False,"payload":"","evasive":True,"said_before":False}
        return spoken, meta

    def generate(self, character: Dict[str, Any], question: str, game_state, quoted: Optional[Dict[str, Any]] = None, return_meta: bool=False):
        name = character["name"]

        if is_offtopic(question):
            s = f"Concentrémonos en el caso; {enforce_focus()}"
            meta = {"intent":"GENERAL","truthful":True,"payload":s,"evasive":True,"said_before":False}
            line = f"{s}"
            return (f"[{name}] (GENERAL) {line}", meta) if return_meta else f"[{name}] (GENERAL) {line}"

        # Intento base
        intent = classify_intent(question)

        # Si el jugador menciona a un sospechoso concreto, pasa TARGET_PERSON y refuerza RELACIONES/RUMOR
        target_person = _detect_target_person(game_state, question)
        if target_person:
            if intent == "GENERAL":
                # si formula “qué me dices de X”, cae en RELACIONES por guardrails; si no, forzamos RELACIONES
                intent = "RELACIONES"

        policy, _ = self._decide_truth(character, intent, game_state, quoted)
        payload = _pick_factual(character, intent)
        must_include_clue = (policy == "TRUTH") and bool(payload) and (intent in CLUE_INTENTS)

        # Rel score hacia target (si lo hay)
        rel_score = game_state.get_relationship(name, target_person) if target_person else None

        prompt = PromptBuilder.build_dialog_prompt(
            character=character,
            question=question,
            intent=intent,
            policy=policy,
            must_include_clue=must_include_clue,
            selected_payload=payload,
            game_state=game_state,
            quoted=quoted,
            target_person=target_person
        )

        raw = self._llm_generate(prompt)
        if not raw:
            raw, meta = self._fallback_line(
                name=name, intent=intent, policy=policy, payload=payload,
                target_person=target_person, rel_score=rel_score
            )
            spoken = raw.split("\n", 1)[-1] if "\n" in raw else raw
        else:
            spoken, meta = self._parse_meta(raw)

        self._publish_memory_flags(game_state, name, intent, meta.get("payload",""), bool(meta.get("truthful")), bool(meta.get("evasive")))

        final = f"[{name}] ({intent}) {spoken}"
        return (final, meta) if return_meta else final

    def generate_ending(self, game_state, accused: str, characters: Dict[str, Any]) -> str:
        prompt = PromptBuilder.build_ending_prompt(game_state, accused, characters)
        raw = self._llm_generate(prompt)
        if raw:
            return raw.strip()
        killer = game_state.killer
        ev = list(dict.fromkeys(game_state.evidence_revealed))[:3]
        ev_txt = ", ".join(ev) if ev else "casi sin pruebas claras"
        if accused == killer:
            return f"Cuando bajaron las luces, las piezas encajaron. {ev_txt} marcó el camino. {killer} dejó caer su máscara, y la carpa exhaló."
        elif accused in game_state.suspects:
            return f"El nombre pronunciado no era el correcto; {killer} se escurrió entre sombras. Quedó el rastro de {ev_txt} y la certeza tardía."
        else:
            return f"La acusación se diluyó en ruido. El verdadero asesino, {killer}, siguió su rutina. {ev_txt} no alcanzó para cerrar."
