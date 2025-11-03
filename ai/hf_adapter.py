from typing import Dict, Any, Optional, Tuple
import random
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

from .config import MODEL_ID, DEVICE_MAP, MAX_NEW_TOKENS, TEMPERATURE, TOP_P, TOP_K
from .guardrails import is_offtopic, enforce_focus, classify_intent

INTENT_LIE_WEIGHTS_KILLER = {
    "COARTADA": 0.25, "PRUEBAS": 0.2, "MÓVIL": 0.2, "RELACIONES": 0.1,
    "LUGAR": 0.15, "OBJETO": 0.15, "RUMOR": 0.1, "GENERAL": 0.1,
}
INTENT_LIE_WEIGHTS_INNOCENT = {
    "COARTADA": -0.05, "PRUEBAS": -0.05, "MÓVIL": -0.02, "RELACIONES": 0.0,
    "LUGAR": 0.0, "OBJETO": 0.0, "RUMOR": 0.0, "GENERAL": 0.0,
}

def _pick_factual(character: Dict[str, Any], intent: str) -> Optional[str]:
    kn = character.get("knowledge", {})
    bucket = kn.get(intent, None) or kn.get(intent.capitalize(), None)
    if isinstance(bucket, list) and bucket:
        return random.choice(bucket)
    return None

def _soften(text: str) -> str:
    hedges = ["Quizá", "Podría ser que", "No estoy totalmente seguro, pero", "Diría que"]
    if not text:
        return "No estoy totalmente seguro."
    t = text[0].lower() + text[1:] if text and text[0].isupper() else text
    return f"{random.choice(hedges)} {t}"

class HFModelAdapter:
    def __init__(self, seed: Optional[int] = None):
        self.rnd = random.Random(seed)
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            device_map=DEVICE_MAP,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if torch.cuda.is_available() and DEVICE_MAP!="cpu" else -1,
        )

    def _decide_truth(self, character: Dict[str, Any], question: str, game_state, quoted) -> Tuple[bool, str, float]:
        is_killer = character.get("is_killer", False)
        base_truth = character.get("truthfulness", 0.85)
        hostility = character.get("hostility", 0.0)
        name = character["name"]

        intent = classify_intent(question)
        pressure = 0.0
        if quoted and quoted.get("is_accusation"):
            pressure += 0.25
        if game_state.phase.name != "INICIO":
            pressure += 0.15
        pressure += max(0.0, hostility) * 0.3

        # Presión adicional por memoria: si lo acusaron varios → más evasivo/mentiroso
        mem = game_state.per_character_memory.get(name)
        if mem:
            pressure += min(0.3, 0.1 * len(mem.accused_by))  # hasta +0.3
            pressure -= min(0.2, 0.05 * len(mem.supported_by))  # apoyos bajan presión
            pressure += min(0.15, 0.03 * mem.evasion_count)     # si ya evadió, mantiene sesgo evasivo

        if is_killer:
            lie_bias = INTENT_LIE_WEIGHTS_KILLER.get(intent, 0.1)
            truth_chance = max(0.05, min(0.95, 0.5 - pressure*0.25 - lie_bias))
        else:
            lie_bias = INTENT_LIE_WEIGHTS_INNOCENT.get(intent, 0.0)
            truth_chance = max(0.3, min(0.98, base_truth - pressure*0.1 + (-lie_bias)))
        truthful = self.rnd.random() < truth_chance
        return truthful, intent, pressure

    def _payload(self, truthful: bool, character: Dict[str, Any], intent: str) -> Tuple[str, bool]:
        fact = _pick_factual(character, intent)
        evasive = False
        if truthful and fact:
            return fact, evasive
        if truthful and not fact:
            return "No tengo nada claro sobre eso, pero escuché pasos y tensión en el ambiente.", evasive
        if not truthful and fact:
            evasive = True
            if self.rnd.random() < 0.5:
                return _soften(fact), evasive
            else:
                return "No vi ni escuché nada que valga la pena sobre eso.", evasive
        evasive = True
        return "No recuerdo nada útil en ese punto.", evasive

    def generate(self, character: Dict[str, Any], question: str, game_state, quoted: Optional[Dict[str, Any]] = None, return_meta: bool=False):
        if is_offtopic(question):
            s = enforce_focus()
            return (s, {"intent":"GENERAL","truthful":True,"payload":s,"evasive":True}) if return_meta else s

        truthful, intent, _pressure = self._decide_truth(character, question, game_state, quoted)
        payload_text, evasive = self._payload(truthful, character, intent)

        # Prompt con memoria
        from .prompt_builder import build_prompt
        prompt = build_prompt(
            character=character,
            question=question,
            game_state=game_state,
            quoted=quoted,
            payload_text=payload_text,
            truthful=truthful,
        )

        out = self.pipe(
            prompt,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            top_k=TOP_K,
            repetition_penalty=1.05,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.eos_token_id,
        )[0]["generated_text"]

        name = character["name"]
        marker = f"[{name}] ({intent})"
        idx = out.rfind(marker)
        text = out[idx:].strip() if idx >= 0 else f"{marker} {payload_text}"

        meta = {"intent": intent, "truthful": truthful, "payload": payload_text, "evasive": evasive}
        return (text, meta) if return_meta else text
