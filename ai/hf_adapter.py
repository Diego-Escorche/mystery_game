from typing import Dict, Any, Optional
import random
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

from .config import MODEL_ID, DEVICE_MAP, MAX_NEW_TOKENS, TEMPERATURE, TOP_P, TOP_K
from .guardrails import is_offtopic, enforce_focus, classify_intent

# Reutilizamos la misma lógica de veracidad del stub para consistencia
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
    """
    Adaptador para SmolLM3-3B con guardrails e intents.
    - Selecciona veracidad/mentira con la misma heurística del stub.
    - Arma un prompt con persona + payload de contenido (hecho/mentira) y el LLM redacta natural.
    """
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

    def _decide_truth(self, character: Dict[str, Any], question: str, game_state, quoted):
        is_killer = character.get("is_killer", False)
        base_truth = character.get("truthfulness", 0.85)
        hostility = character.get("hostility", 0.0)

        intent = classify_intent(question)
        pressure = 0.0
        if quoted and quoted.get("is_accusation"):
            pressure += 0.25
        if game_state.phase.name != "INICIO":
            pressure += 0.15
        pressure += max(0.0, hostility) * 0.3

        if is_killer:
            lie_bias = INTENT_LIE_WEIGHTS_KILLER.get(intent, 0.1)
            truth_chance = max(0.05, min(0.95, 0.5 - pressure*0.25 - lie_bias))
        else:
            lie_bias = INTENT_LIE_WEIGHTS_INNOCENT.get(intent, 0.0)
            truth_chance = max(0.3, min(0.98, base_truth - pressure*0.1 + (-lie_bias)))
        truthful = self.rnd.random() < truth_chance
        return truthful, intent

    def _payload(self, truthful: bool, character: Dict[str, Any], intent: str) -> str:
        fact = _pick_factual(character, intent)
        if truthful and fact:
            return fact
        if truthful and not fact:
            return "No tengo nada claro sobre eso, pero escuché pasos y tensión en el ambiente."
        if not truthful and fact:
            return _soften(fact) if self.rnd.random() < 0.5 else "No vi ni escuché nada que valga la pena sobre eso."
        return "No recuerdo nada útil en ese punto."

    def generate(self, character: Dict[str, Any], question: str, game_state, quoted: Optional[Dict[str, Any]] = None) -> str:
        if is_offtopic(question):
            return enforce_focus()

        truthful, intent = self._decide_truth(character, question, game_state, quoted)
        payload_text = self._payload(truthful, character, intent)

        # Construimos prompt
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

        # El modelo genera el prompt + la respuesta; recortamos para quedarnos desde el prefijo de respuesta.
        # Buscamos la última ocurrencia del prefijo "[Nombre] (INTENT)"
        name = character["name"]
        marker = f"[{name}] ({intent})"
        idx = out.rfind(marker)
        if idx >= 0:
            return out[idx:].strip()
        # Fallback mínimo si no aparece (raro)
        return f"{marker} {payload_text}"
