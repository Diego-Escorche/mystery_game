import random
import yaml
from pathlib import Path
from engine.state import GameState, Phase, StatementEvent
from engine.names import NameResolver
from gameplay.evidence import seed_evidence, reveal_random_real
from gameplay.interrogations import interrogate, BOLD, RESET, YELLOW, CYAN
from gameplay.endings import resolve_accusation
from ai.model import AIModelAdapter  # o usa HFModelAdapter si preferís el modelo real
from ai.quote_parser import detect_quote
from ai.prompts import PERSONALITIES

# ======= CONFIGURACIÓN GENERAL =======
DATA_DIR = Path(__file__).resolve().parent / "data"
DEBUG_MODE = True          # ← ponlo en False para ocultar el asesino al inicio
DEBUG_SEED = None          # ← opcional: p.ej. 42 para reproducibilidad. None = aleatorio real

# Colores extra
RED = "\033[91m"
def _color(s: str) -> str:
    return s if (RED and BOLD and RESET) else s  # por si querés desactivar colores globalmente


# ======= Utilidades YAML =======
def load_yaml(filename: str):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_characters_and_resolver() -> tuple[dict, NameResolver]:
    personas = load_yaml("personas.yaml")
    knowledge = load_yaml("knowledge.yaml")

    resolver = NameResolver()
    characters = {}

    # Alias específicos solicitados:
    # - "Mefisto (Bombita)" → "Mefisto", "Bombita"
    # - "Ñopin Desfijo" → "Ñopin", "Nopin" (por si alguien escribe sin tilde)
    # - "Madame Seraphine" → "Madame", "Seraphine"
    # Otros personajes: alias = su propio nombre

    for key, data in personas.items():
        name = data.get("name", key)
        role = data.get("role", "")
        personality_key = data.get("personality_key")
        personality = PERSONALITIES.get(personality_key, "")
        relations = data.get("relations", {})
        kdata = knowledge.get(name, {}) if knowledge else {}

        # Define alias por personaje
        aliases = []
        if name.lower().startswith("mefisto"):
            aliases = ["Mefisto", "Bombita", "Mefisto (Bombita)"]
        elif name.lower().startswith("ñopin") or name.lower().startswith("ñopin"):
            aliases = ["Ñopin", "Nopin", "Ñopin Desfijo"]
        elif name.lower().startswith("madame seraphine"):
            aliases = ["Madame", "Seraphine", "Madame Seraphine"]
        else:
            aliases = [name]

        resolver.add(name, aliases)

        characters[name] = {
            "name": name,
            "role": role,
            "personality": personality,
            "relations": relations,
            "knowledge": kdata,
            "truthfulness": 0.85,
            "hostility": 0.0,
        }

    return characters, resolver


# ======= Clase auxiliar del caso =======
class MurderCase:
    def __init__(self, victim: str, suspects):
        self.victim = victim
        self.location = "Camarín del circo"
        self.suspects = suspects
        self.initial_summary = (
            f"{self.victim} fue hallado muerto en su camarín con la puerta cerrada. "
            "No hay marcas visibles de violencia; el espejo está roto y hay símbolos extraños pintados."
        )


# ======= Configuración del juego =======
def setup_game(seed: int | None = DEBUG_SEED):
    gs = GameState()
    rnd = random.Random(seed) if seed is not None else random.Random()  # None => aleatorio real

    characters, resolver = load_characters_and_resolver()
    gs.suspects = list(characters.keys())

    # Inicializa límites
    for s in gs.suspects:
        gs.question_limits[s] = gs.question_limit_per_phase

    # Asignación de asesino realmente aleatoria
    gs.killer = rnd.choice(gs.suspects)
    seed_evidence(gs, seed=seed)

    # Marca asesino en datos del personaje
    for c in characters.values():
        c["is_killer"] = (c["name"] == gs.killer)

    return gs, characters, resolver


# ======= Fase 1 =======
def phase_inicio(gs: GameState, chars, resolver: NameResolver, model):
    case = MurderCase(victim=gs.victim, suspects=gs.suspects)
    print("\n=== FASE 1: INICIO ===")
    print(case.initial_summary)
    print(f"Sospechosos: {', '.join(gs.suspects)}")

    # DEBUG: mostrar asesino al inicio si está activado
    if DEBUG_MODE:
        print(f"\n{RED}{BOLD}[DEBUG] El asesino real es: {gs.killer}{RESET}")

    while True:
        print("\n¿A quién interrogar? (o escribe 'siguiente' para pasar de fase)")
        raw_target = input("> ").strip()
        if raw_target.lower() == "siguiente":
            break

        target = resolver.canonicalize(raw_target)
        if not target or target not in chars:
            print("No reconocido.")
            continue

        if gs.question_limits.get(target, 0) <= 0:
            print("Sin preguntas restantes para esta fase con este personaje.")
            continue

        print("Tu pregunta:")
        q = input("> ").strip()

        # Detección de citas con soporte de alias:
        # Pasamos una lista rica de nombres (canónicos y/o variantes).
        qp = detect_quote(q, list(resolver.alias_to_canonical.values()) + list(resolver.canonical_names))
        quoted = None
        if qp:
            # Canonicalizamos ‘source’ y ‘about’ por si vienen como alias
            src = resolver.canonicalize(qp.get("source", "")) or qp.get("source")
            about = resolver.canonicalize(qp.get("about", "")) if qp.get("about") else None
            quoted = StatementEvent(
                speaker=src,
                target=about,
                content=qp.get("content", ""),
                is_accusation=qp.get("is_accusation", False),
                is_support=qp.get("is_support", False),
            )

        ans = interrogate(gs, chars[target], q, model, quoted=quoted)
        print(ans)


# ======= Fase 2 =======
def phase_desarrollo(gs: GameState, chars, resolver: NameResolver, model):
    print("\n=== FASE 2: DESARROLLO ===")
    hint = reveal_random_real(gs)
    if hint:
        print(f"{YELLOW}{BOLD}[Nueva evidencia REAL]{RESET} {hint}")
    else:
        print(f"{YELLOW}[Sin nueva evidencia real disponible]{RESET}")

    # Reset de límites
    for s in gs.suspects:
        gs.question_limits[s] = gs.question_limit_per_phase

    while True:
        print("\n¿A quién interrogar ahora? (o 'siguiente' para pasar a conclusión)")
        raw_target = input("> ").strip()
        if raw_target.lower() == "siguiente":
            break

        target = resolver.canonicalize(raw_target)
        if not target or target not in chars:
            print("No reconocido.")
            continue

        if gs.question_limits.get(target, 0) <= 0:
            print("Sin preguntas restantes con este personaje.")
            continue

        print("Tu pregunta:")
        q = input("> ").strip()

        qp = detect_quote(q, list(resolver.alias_to_canonical.values()) + list(resolver.canonical_names))
        quoted = None
        if qp:
            src = resolver.canonicalize(qp.get("source", "")) or qp.get("source")
            about = resolver.canonicalize(qp.get("about", "")) if qp.get("about") else None
            quoted = StatementEvent(
                speaker=src,
                target=about,
                content=qp.get("content", ""),
                is_accusation=qp.get("is_accusation", False),
                is_support=qp.get("is_support", False),
            )

        ans = interrogate(gs, chars[target], q, model, quoted=quoted)
        print(ans)


# ======= Fase 3 =======
def phase_conclusion(gs: GameState):
    print("\n=== FASE 3: CONCLUSIÓN ===")
    print("Evidencias encontradas:")
    if gs.evidence_revealed:
        for ev in gs.evidence_revealed:
            who = gs.evidence_sources.get(ev)
            suffix = f" {CYAN}(aportada por {who}){RESET}" if who else ""
            print(f" - {ev}{suffix}")
    else:
        print(" (ninguna)")

    print("\n¿A quién acusas como responsable final?")
    accused = input("> ").strip()
    print("")
    print(resolve_accusation(gs, accused))


# ======= Ejecución general =======
def main():
    gs, chars, resolver = setup_game(seed=DEBUG_SEED)  # None => aleatorio real

    # Modelo (stub o HF)
    model = AIModelAdapter(seed=DEBUG_SEED)
    # from ai.hf_adapter import HFModelAdapter
    # model = HFModelAdapter(seed=DEBUG_SEED)

    phase_inicio(gs, chars, resolver, model)
    gs.set_phase(Phase.DESARROLLO)
    phase_desarrollo(gs, chars, resolver, model)
    gs.set_phase(Phase.CONCLUSION)
    phase_conclusion(gs)


if __name__ == "__main__":
    main()
