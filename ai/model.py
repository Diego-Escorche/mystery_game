import random
from typing import Dict, Any, Optional, Tuple
from .guardrails import is_offtopic, enforce_focus, classify_intent

# =========================
# Utilidades de estilo NLG
# =========================

DIRECT_OPENERS = [
    "Seré directo:",
    "Hablando claro:",
    "Voy al punto:",
    "No daré rodeos:",
]

EVASIVE_OPENERS = [
    "No veo cómo eso ayuda…",
    "No estoy seguro de que sea relevante ahora…",
    "Preferiría no entrar en eso…",
    "No creo que sea el momento para hablar de eso…",
]

HEDGE_PREFIXES = [
    "Quizá",
    "Podría ser que",
    "Diría que",
    "No estoy totalmente seguro, pero",
]

ACCUSATION_REACTIONS = [
    "Si {src} me señala, {counter}.",
    "Y si {src} insiste en culparme, {counter}.",
    "Si {src} anda diciendo eso, {counter}.",
]
COUNTERS = [
    "tal vez es porque {src_pron} esconde algo peor",
    "que explique qué hacía cuando nadie miraba",
    "que cuente por qué mintió antes",
    "yo también tengo preguntas para {src_pron}",
]

SUPPORT_REACTIONS = [
    "Supongo que {src} aún conserva algo de justicia.",
    "Agradezco que {src} diga eso.",
    "Tal vez {src} no esté tan equivocado esta vez.",
]

OFFTOPIC_REFOCUS = [
    "Concentrémonos en el caso.",
    "Volvamos a la muerte de la víctima.",
    "No perdamos el foco: el asesinato.",
]

# Qué intents se consideran “pista” si el contenido es veraz (lo usa gameplay/interrogations)
CLUE_INTENTS = {"PRUEBAS", "OBJETO", "LUGAR"}

# Viés de mentira por intención (asesino vs inocente)
INTENT_LIE_WEIGHTS_KILLER = {
    "COARTADA": 0.28, "PRUEBAS": 0.22, "MÓVIL": 0.22, "RELACIONES": 0.12,
    "LUGAR": 0.18, "OBJETO": 0.18, "RUMOR": 0.10, "GENERAL": 0.08,
}
INTENT_LIE_WEIGHTS_INNOCENT = {
    "COARTADA": -0.05, "PRUEBAS": -0.05, "MÓVIL": -0.02, "RELACIONES": 0.0,
    "LUGAR": 0.0, "OBJETO": 0.0, "RUMOR": 0.0, "GENERAL": 0.0,
}


# =========================
# Ayudas de selección factual
# =========================

def _pick_factual(character: Dict[str, Any], intent: str) -> Optional[str]:
    """
    Toma un hecho del conocimiento del personaje para el intent dado.
    """
    kn = character.get("knowledge", {})
    # soporta claves en distintos casos
    bucket = kn.get(intent) or kn.get(intent.capitalize())
    if isinstance(bucket, list) and bucket:
        return random.choice(bucket)
    return None

def _soften(text: str) -> str:
    """
    Suaviza/hedgea una afirmación para que suene menos comprometida.
    """
    if not text:
        return "No estoy totalmente seguro."
    t = text[0].lower() + text[1:] if text and text[0].isupper() else text
    return f"{random.choice(HEDGE_PREFIXES)} {t}"


# =========================
# Lógica principal del stub
# =========================

class AIModelAdapter:
    """
    Stub generativo: produce respuestas dinámicas en base a contexto, intención y memoria.
    No usa un LLM externo; sintetiza NLG con plantillas y varianza.
    """
    def __init__(self, seed: Optional[int] = None):
        self.rnd = random.Random(seed)

    # ---------- señales contextuales ----------
    def _relationship_pressure(self, game_state, name: str) -> float:
        mem = game_state.per_character_memory.get(name)
        pressure = 0.0
        if mem:
            pressure += min(0.30, 0.10 * len(mem.accused_by))
            pressure -= min(0.20, 0.05 * len(mem.supported_by))
            pressure += min(0.15, 0.03 * mem.evasion_count)
        return pressure

    def _phase_pressure(self, game_state) -> float:
        # mayor presión a partir de DESARROLLO
        return 0.15 if game_state.phase.name != "INICIO" else 0.0

    def _quote_pressure(self, quoted) -> float:
        if quoted and quoted.get("is_accusation"):
            return 0.25
        return 0.0

    def _is_said_before(self, game_state, name: str, intent: str, payload_text: str) -> bool:
        if not payload_text:
            return False
        mem = game_state.per_character_memory.get(name)
        if not mem:
            return False
        facts = mem.told_facts.get(intent, set())
        return payload_text in facts

    # ---------- decisión de veracidad ----------
    def _decide_truth(self, character: Dict[str, Any], intent: str, game_state, quoted) -> Tuple[bool, float]:
        is_killer = character.get("is_killer", False)
        base_truth = character.get("truthfulness", 0.85)
        hostility = character.get("hostility", 0.0)

        pressure = self._phase_pressure(game_state)
        pressure += self._relationship_pressure(game_state, character["name"])
        pressure += self._quote_pressure(quoted)
        pressure += max(0.0, hostility) * 0.30

        if is_killer:
            lie_bias = INTENT_LIE_WEIGHTS_KILLER.get(intent, 0.10)
            truth_chance = max(0.05, min(0.95, 0.50 - pressure*0.25 - lie_bias))
        else:
            lie_bias = INTENT_LIE_WEIGHTS_INNOCENT.get(intent, 0.0)
            truth_chance = max(0.30, min(0.98, base_truth - pressure*0.10 + (-lie_bias)))

        truthful = self.rnd.random() < truth_chance
        return truthful, pressure

    # ---------- construcción de payload ----------
    def _build_payload(self, truthful: bool, character: Dict[str, Any], intent: str) -> Tuple[str, bool]:
        fact = _pick_factual(character, intent)
        evasive = False
        if truthful and fact:
            return fact, evasive
        if truthful and not fact:
            # fallback contextual mínimo (no inventa fuera del mundo del circo)
            return "No tengo nada claro sobre eso, pero vi nervios y prisa tras bastidores.", evasive
        if not truthful and fact:
            evasive = True
            if self.rnd.random() < 0.5:
                return _soften(fact), evasive
            else:
                return "No vi ni escuché nada que valga la pena sobre eso.", evasive
        evasive = True
        return "No recuerdo nada útil en ese punto.", evasive

    # ---------- estilo según personalidad ----------
    def _style_tweak(self, text: str, character: Dict[str, Any], truthful: bool, pressure: float) -> str:
        persona = (character.get("personality") or "").lower()
        # modulaciones ligeras
        if "sarcástico" in persona or "sarcastico" in persona:
            if not truthful or pressure > 0.25:
                text += " (¿contento ahora?)"
        if "perfeccionista" in persona or "tensa" in persona:
            if truthful and self.rnd.random() < 0.3:
                text = text.replace("No daré rodeos:", "Voy al punto:") if "No daré rodeos:" in text else text
        if "críptica" in persona or "críptico" in persona:
            if truthful and self.rnd.random() < 0.35:
                text += " Mira más allá de lo obvio."
        if "directo" in persona or "pragmático" in persona or "pragmatico" in persona:
            if truthful and self.rnd.random() < 0.35:
                text = text.replace("Seré directo:", "Voy al grano:") if "Seré directo:" in text else f"Voy al grano: {text}"
        return text

    # ---------- reacción a citas ----------
    def _quote_tail(self, quoted: Optional[Dict[str, Any]], name: str) -> str:
        if not quoted:
            return ""
        src = quoted.get("source")
        about = quoted.get("about")
        if quoted.get("is_accusation") and (about == name or self.rnd.random() < 0.30):
            counter = random.choice(COUNTERS).format(src_pron=src)
            react = random.choice(ACCUSATION_REACTIONS).format(src=src, counter=counter)
            return f" {react}"
        if quoted.get("is_support") and about == name:
            react = random.choice(SUPPORT_REACTIONS).format(src=src)
            return f" {react}"
        return ""

    # ---------- publíca memoria & meta ----------
    def _publish_memory_flags(self, game_state, name: str, intent: str, payload: str, truthful: bool, evasive: bool):
        game_state.remember_qa(name, intent, payload)
        if truthful and payload:
            game_state.remember_fact(name, intent, payload)
        if evasive:
            game_state.increment_evasion(name)

    # ---------- API principal ----------
    def generate(self, character: Dict[str, Any], question: str, game_state, quoted: Optional[Dict[str, Any]] = None, return_meta: bool=False):
        name = character["name"]

        # 1) fuera de tema
        if is_offtopic(question):
            s = f"{random.choice(OFFTOPIC_REFOCUS)} {enforce_focus()}"
            meta = {"intent":"GENERAL","truthful":True,"payload":s,"evasive":True,"said_before":False}
            return (f"[{name}] (GENERAL) {s}", meta) if return_meta else f"[{name}] (GENERAL) {s}"

        # 2) intención
        intent = classify_intent(question)

        # 3) decidir veracidad
        truthful, pressure = self._decide_truth(character, intent, game_state, quoted)

        # 4) construir payload factual/evitativo
        payload_text, evasive = self._build_payload(truthful, character, intent)

        # 5) ¿ya lo había dicho?
        said_before = self._is_said_before(game_state, name, intent, payload_text)

        # 6) prefijos variados
        opener = ""
        if said_before and truthful:
            opener = "Ya lo comenté:"
        elif truthful:
            opener = random.choice(DIRECT_OPENERS)
        else:
            opener = random.choice(EVASIVE_OPENERS)

        # 7) arma respuesta base
        prefix = f"[{name}] ({intent}) "
        response = f"{prefix}{opener} {payload_text}".strip()

        # 8) reacciones a citas (acusación/apoyo)
        response += self._quote_tail(quoted, name)

        # 9) estilizar por personalidad
        response = self._style_tweak(response, character, truthful, pressure)

        # 10) publicar memoria y meta
        self._publish_memory_flags(game_state, name, intent, payload_text, truthful, evasive)
        meta = {"intent": intent, "truthful": truthful, "payload": payload_text, "evasive": evasive, "said_before": said_before}

        return (response, meta) if return_meta else response