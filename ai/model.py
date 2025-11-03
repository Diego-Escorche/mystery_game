import random
from typing import Dict, Any, Optional, Tuple
from .guardrails import is_offtopic, enforce_focus, classify_intent

INTENT_LIE_WEIGHTS_KILLER = {
    "COARTADA": 0.25,
    "PRUEBAS": 0.2,
    "MÓVIL": 0.2,
    "RELACIONES": 0.1,
    "LUGAR": 0.15,
    "OBJETO": 0.15,
    "RUMOR": 0.1,
    "GENERAL": 0.1,
}
INTENT_LIE_WEIGHTS_INNOCENT = {
    "COARTADA": -0.05,
    "PRUEBAS": -0.05,
    "MÓVIL": -0.02,
    "RELACIONES": 0.0,
    "LUGAR": 0.0,
    "OBJETO": 0.0,
    "RUMOR": 0.0,
    "GENERAL": 0.0,
}

def pick_factual(character: Dict[str, Any], intent: str) -> Optional[str]:
    kn = character.get("knowledge", {})
    bucket = kn.get(intent, None) or kn.get(intent.capitalize(), None)
    if isinstance(bucket, list) and bucket:
        return random.choice(bucket)
    return None

def soften(text: str) -> str:
    hedges = ["Quizá", "Podría ser que", "No estoy totalmente seguro, pero", "Diría que"]
    return f"{random.choice(hedges)} {text[0].lower() + text[1:] if text and text[0].isupper() else text}"

class AIModelAdapter:
    def __init__(self, seed: Optional[int]=None):
        self.rnd = random.Random(seed)

    def _said_before(self, game_state, name: str, intent: str, payload_text: str) -> bool:
        if not payload_text:
            return False
        mem = game_state.per_character_memory.get(name)
        if not mem:
            return False
        facts = mem.told_facts.get(intent, set())
        return payload_text in facts

    def generate(self, character: Dict[str, Any], question: str, game_state, quoted: Optional[Dict[str, Any]]=None, return_meta: bool=False):
        name = character["name"]
        is_killer = character.get("is_killer", False)
        base_truth = character.get("truthfulness", 0.85)
        hostility = character.get("hostility", 0.0)

        if is_offtopic(question):
            s = enforce_focus()
            meta = {"intent":"GENERAL","truthful":True,"payload":s,"evasive":True,"said_before":False}
            return (s, meta) if return_meta else s

        intent = classify_intent(question)

        pressure = 0.0
        if quoted and quoted.get("is_accusation"):
            pressure += 0.25
        if game_state.phase.name != "INICIO":
            pressure += 0.15
        pressure += max(0.0, hostility) * 0.3

        mem = game_state.per_character_memory.get(name)
        if mem:
            pressure += min(0.3, 0.1 * len(mem.accused_by))
            pressure -= min(0.2, 0.05 * len(mem.supported_by))
            pressure += min(0.15, 0.03 * mem.evasion_count)

        if is_killer:
            lie_bias = INTENT_LIE_WEIGHTS_KILLER.get(intent, 0.1)
            truth_chance = max(0.05, min(0.95, 0.5 - pressure*0.25 - lie_bias))
        else:
            lie_bias = INTENT_LIE_WEIGHTS_INNOCENT.get(intent, 0.0)
            truth_chance = max(0.3, min(0.98, base_truth - pressure*0.1 + (-lie_bias)))

        truthful = self.rnd.random() < truth_chance
        fact = pick_factual(character, intent)

        evasive = False
        if truthful and fact:
            payload = fact
        elif truthful and not fact:
            payload = "No tengo nada claro sobre eso, pero escuché pasos y tensión en el ambiente."
        elif not truthful and fact:
            evasive = True
            if self.rnd.random() < 0.5:
                payload = soften(fact)
            else:
                payload = "No vi ni escuché nada que valga la pena sobre eso."
        else:
            evasive = True
            payload = "No recuerdo nada útil en ese punto."

        said_before = self._said_before(game_state, name, intent, payload)

        opener = "Seré directo:" if truthful else "No veo cómo eso ayuda…"
        prefix = f"[{name}] ({intent}) "
        if said_before and truthful:
            text = f"{prefix}Ya lo comenté: {payload}"
        else:
            text = f"{prefix}{opener} {payload}"

        if quoted:
            src = quoted.get("source")
            about = quoted.get("about")
            if quoted.get("is_accusation") and (about == name or self.rnd.random() < 0.3):
                text += f" Y si {src} me señala, diré que tiene sus propios fantasmas que esconder."
            elif quoted.get("is_support") and about == name:
                text += f" Supongo que {src} aún conserva algo de justicia en su mirada."

        if return_meta:
            return text, {"intent": intent, "truthful": truthful, "payload": payload, "evasive": evasive, "said_before": said_before}
        return text
