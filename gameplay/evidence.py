import random
from typing import Optional
from engine.state import GameState

# --- Pools de evidencia ---
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

def seed_evidence(gs: GameState, seed: Optional[int] = None) -> None:
    """
    Deja un pool mixto para usos generales (si hiciera falta).
    La Fase 2 usa reveal_random_real() para mostrar evidencia REAL aleatoria.
    """
    rnd = random.Random(seed)
    pool = []
    if REAL_EVIDENCE:
        k_real = min(3, len(REAL_EVIDENCE))
        pool += rnd.sample(REAL_EVIDENCE, k=k_real)
    if AMBIGUOUS_EVIDENCE:
        k_amb = min(2, len(AMBIGUOUS_EVIDENCE))
        pool += rnd.sample(AMBIGUOUS_EVIDENCE, k=k_amb)
    rnd.shuffle(pool)
    gs.knowledge_tracker.setdefault("_evidence_pool", {})
    gs.knowledge_tracker["_evidence_pool"]["items"] = pool

def reveal_next(gs: GameState) -> str:
    """
    Compatibilidad: revela el siguiente del pool mixto (real o ambiguo).
    """
    pool = gs.knowledge_tracker.get("_evidence_pool", {}).get("items", [])
    if not pool:
        return ""
    item = pool.pop(0)
    gs.evidence_revealed.append(item)
    return item

def reveal_random_real(gs: GameState, seed: Optional[int] = None) -> str:
    """
    Revela UNA evidencia REAL aleatoria que aún no haya sido revelada.
    """
    rnd = random.Random(seed)
    remaining = [e for e in REAL_EVIDENCE if e not in gs.evidence_revealed]
    if not remaining:
        return ""
    item = rnd.choice(remaining)
    gs.evidence_revealed.append(item)
    return item
