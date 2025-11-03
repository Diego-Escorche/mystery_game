import random
from engine.state import GameState

REAL_EVIDENCE = [
    "Huella parcial en el espejo roto que no coincide con la víctima.",
    "Rastro de arena húmeda hacia los vagones de utilería.",
    "Restos de pintura roja en un pañuelo detrás del escenario.",
    "Cuerda de funambulista con fibras cortadas recientemente.",
]

AMBIGUOUS_EVIDENCE = [
    "Un billete arrugado de otra ciudad en el suelo de la carpa.",
    "Olor a solvente cerca de un vagón sin identificar.",
    "Marcas de botas que coinciden con varios pares del vestuario.",
    "Un pendiente pequeño sin dueña confirmada encontrado entre asientos.",
]

def seed_evidence(gs: GameState, seed=None) -> None:
    rnd = random.Random(seed)
    pool = []
    pool += rnd.sample(REAL_EVIDENCE, k=3 if len(REAL_EVIDENCE) >=3 else len(REAL_EVIDENCE))
    pool += rnd.sample(AMBIGUOUS_EVIDENCE, k=2 if len(AMBIGUOUS_EVIDENCE) >=2 else len(AMBIGUOUS_EVIDENCE))
    rnd.shuffle(pool)
    gs.knowledge_tracker.setdefault("_evidence_pool", {})
    gs.knowledge_tracker["_evidence_pool"]["items"] = pool

def reveal_next(gs: GameState) -> str:
    pool = gs.knowledge_tracker.get("_evidence_pool", {}).get("items", [])
    if not pool:
        return ""
    item = pool.pop(0)
    gs.evidence_revealed.append(item)
    return item
