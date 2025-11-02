import os
import yaml
from typing import Dict
from engine.state import GameState, Phase, StatementEvent
from engine.rng import choose_killer
from engine import rules
from world.casefile import MurderCase
from gameplay.evidence import seed_evidence, reveal_next
from gameplay.interrogations import interrogate
from gameplay.endings import resolve_accusation

# Elegimos backend (HF por defecto). Si falta transformers/torch, caemos al stub.
USE_STUB = os.getenv("USE_STUB", "0") == "1"
AIModelAdapter = None
if not USE_STUB:
    try:
        from ai.hf_adapter import HFModelAdapter as AIModelAdapter
    except Exception as e:
        print("[Aviso] No se pudo cargar el adaptador HF, usando stub. Detalle:", e)
        from ai.model import AIModelAdapter as AIModelAdapter
else:
    from ai.model import AIModelAdapter as AIModelAdapter

from ai.prompts import PERSONALITIES

def load_characters() -> Dict[str, Dict]:
    with open("data/personas.yaml", "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    with open("data/knowledge.yaml", "r", encoding="utf-8") as fk:
        facts = yaml.safe_load(fk)
    chars = {}
    for key, cfg in raw.items():
        name = cfg["name"]
        chars[name] = {
            "name": name,
            "role": cfg["role"],
            "personality": PERSONALITIES[cfg["personality_key"]],
            "relations": cfg.get("relations", {}),
            "is_killer": False,
            "truthfulness": 0.85,
            "hostility": 0.0,
            "knowledge": facts.get(name, {}),
        }
    return chars

def setup_game(seed=None):
    gs = GameState()
    chars = load_characters()
    suspects = list(chars.keys())  # incluye a Canelitas
    gs.suspects = suspects
    gs.killer = choose_killer(suspects, seed=seed)
    chars[gs.killer]["is_killer"] = True
    for s in suspects:
        gs.question_limits[s] = rules.DEFAULT_QUESTION_LIMIT_PER_PHASE
    seed_evidence(gs, seed=seed)
    return gs, chars

def phase_inicio(gs, chars, model):
    case = MurderCase(victim=gs.victim, suspects=gs.suspects)
    print("\n=== FASE 1: INICIO ===")
    print(case.initial_summary)
    print(f"Sospechosos: {', '.join(gs.suspects)}")
    while True:
        print("\n¿A quién interrogar? (o escribe 'siguiente' para pasar de fase)")
        target = input("> ").strip()
        if target.lower() == "siguiente":
            break
        if target not in chars:
            print("No reconocido.")
            continue
        if gs.question_limits.get(target,0) <= 0:
            print("Sin preguntas restantes para esta fase con este personaje.")
            continue
        print("Tu pregunta:")
        q = input("> ").strip()
        quoted = None
        print("¿Citas lo que dijo otra persona? (si/no)")
        yn = input("> ").strip().lower()
        if yn == "si":
            print("¿Quién lo dijo?")
            spk = input("> ").strip()
            print("¿De quién hablaba? (target)")
            about = input("> ").strip()
            print("Es acusación? (si/no)")
            acc = input("> ").strip().lower() == "si"
            print("Es apoyo? (si/no)")
            sup = input("> ").strip().lower() == "si"
            print("Contenido breve de la cita:")
            content = input("> ").strip()
            quoted = StatementEvent(speaker=spk, target=about, content=content, is_accusation=acc, is_support=sup)
        ans = interrogate(gs, chars[target], q, model, quoted=quoted)
        print(ans)

def phase_desarrollo(gs, chars, model):
    print("\n=== FASE 2: DESARROLLO ===")
    hint = reveal_next(gs)
    if hint:
        print(f"[Nueva evidencia] {hint}")
    else:
        print("[Sin nueva evidencia disponible]")
    for s in gs.suspects:
        gs.question_limits[s] = rules.DEFAULT_QUESTION_LIMIT_PER_PHASE
    while True:
        print("\n¿A quién interrogar ahora? (o 'siguiente' para pasar a conclusión)")
        target = input("> ").strip()
        if target.lower() == "siguiente":
            break
        if target not in chars:
            print("No reconocido.")
            continue
        if gs.question_limits.get(target,0) <= 0:
            print("Sin preguntas restantes con este personaje.")
            continue
        print("Tu pregunta:")
        q = input("> ").strip()
        ans = interrogate(gs, chars[target], q, model, quoted=None)
        print(ans)

def phase_conclusion(gs, chars):
    print("\n=== FASE 3: CONCLUSIÓN ===")
    print("¿A quién acusas como responsable final?")
    accused = input("> ").strip()
    print(resolve_accusation(gs, accused))

def main():
    gs, chars = setup_game(seed=42)
    model = AIModelAdapter(seed=42)
    phase_inicio(gs, chars, model)
    gs.set_phase(Phase.DESARROLLO)
    phase_desarrollo(gs, chars, model)
    gs.set_phase(Phase.CONCLUSION)
    phase_conclusion(gs, chars)

if __name__ == "__main__":
    main()
