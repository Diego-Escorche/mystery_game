import argparse
import sys
from typing import Optional, Dict, Any
from engine.setup import bootstrap_game
from engine.state import Phase, GameState
from ai.model import AIModelAdapter
from gameplay.interrogations import interrogate, GREEN, BOLD, RESET, CYAN, YELLOW

try:
    from gameplay.evidence import seed_evidence, reveal_random_real
except Exception:
    def seed_evidence(gs: GameState):
        gs._tmp_real_ev_pool = [
            "huellas de pintura carmesí tras el vagón de utilería",
            "marca de cuerda reciente en el poste de la carpa principal",
            "gota de sangre seca junto al camerino de Mefisto",
            "trozo de pañuelo con olor a solvente en bastidores",
        ]
    def reveal_random_real(gs: GameState) -> Optional[str]:
        pool = getattr(gs, "_tmp_real_ev_pool", [])
        if not pool:
            return None
        import random
        ev = random.choice(pool)
        pool.remove(ev)
        if ev not in gs.evidence_revealed:
            gs.evidence_revealed.append(ev)
        return ev


def build_hf_backend(model_id: str):
    from ai.hf_backend import HFSmolLMBackend
    return HFSmolLMBackend(model_id=model_id)

# ---------------- CLI ----------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Mystery Game (CLI) — Circo",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--characters", "-c", default="data/characters.yaml",
                   help="Ruta al YAML de personajes")
    p.add_argument("--victim", "-v", default="Ñopin desfijo",
                   help="Nombre de la víctima")
    p.add_argument("--seed", type=int, default=None,
                   help="Semilla para pruebas reproducibles (None = aleatorio)")
    p.add_argument("--max-questions", type=int, default=3,
                   help="Cantidad de preguntas por personaje y por fase")

    # MODELOS
    p.add_argument("--model", choices=["hf", "none"], default="hf",
                   help="Backend de lenguaje: 'hf' usa HuggingFaceTB/SmolLM3-3B; 'none' usa fallback procedural")
    p.add_argument("--hf-model-id", default="HuggingFaceTB/SmolLM3-3B",
                   help="ID del modelo en Hugging Face (ej. 'HuggingFaceTB/SmolLM3-3B' o '...-Instruct')")

    p.add_argument("--debug", action="store_true",
                   help="Muestra información de depuración (asesino, etc.)")
    return p.parse_args()

def build_model(args) -> AIModelAdapter:
    """Crea el adaptador con backend HF real o sin backend (fallback procedural)."""
    if args.model == "hf":
        llm = build_hf_backend(args.hf_model_id)
    else:
        llm = None
    return AIModelAdapter(seed=None, llm_backend=llm)

# ---------------- UI helpers ----------------

def _pretty_name(name: str) -> str:
    # Reemplaza '_' por espacio y Capitaliza
    s = name.replace("_", " ").strip()
    # Ñopin y otros con tilde/ñ deben mantenerse como en YAML si ya están correctos.
    return " ".join(w.capitalize() if w.islower() else w for w in s.split())

def list_suspects(gs: GameState, characters: Dict[str, Any]):
    # Construir una línea tipo: Sospechosos: Silvana, Madame Seraphine, Grigori, Lysandra, Jack, Mefisto (Bombita), Ñopin Desfijo
    items = []
    for s in gs.suspects:
        pretty = _pretty_name(s)
        aliases = characters.get(s, {}).get("aliases") or []
        # si hay alias cortito (1 palabra), mostrar el primero entre paréntesis
        short_alias = None
        for a in aliases:
            if len(a.split()) <= 2:
                short_alias = a
                break
        if short_alias and pretty.lower() != short_alias.lower():
            items.append(f"{pretty} ({short_alias})")
        else:
            items.append(pretty)
    line = ", ".join(items)
    print(f"\nSospechosos: {line}")

def print_intro(gs: GameState, characters: Dict[str, Any]):
    print(f"\n\033[1mBienvenido al Circo de Medianoche\033[0m")
    print(f"La víctima es \033[33m{gs.victim}\033[0m. Ha aparecido muerta dentro del circo.")
    print("Tu objetivo es interrogar, seguir las pistas y acusar al responsable.")
    print("\nComandos:")
    print("- Escribe el nombre de un sospechoso para interrogarlo.")
    print("- Escribe siguiente para pasar de fase.")
    print("- Escribe salir para terminar la partida.\n")
    
def choose_person(gs: GameState, raw: str) -> Optional[str]:
    name = raw.strip()
    if not name:
        return None
    canon = gs.canonicalize_name(name)
    return canon

def advance_phase(gs: GameState):
    if gs.phase == Phase.INICIO:
        gs.set_phase(Phase.DESARROLLO)
        print(f"\n{BOLD}Fase 2: Desarrollo{RESET}")
        new_ev = reveal_random_real(gs)
        if new_ev:
            src = "(escena del crimen)"
            gs.evidence_sources[new_ev] = src
            print(f"{GREEN}{BOLD}Pista encontrada:{RESET} {new_ev} {CYAN}(aportada por {src}){RESET}")
        else:
            print(f"{YELLOW}No se encontró evidencia nueva inmediata...{RESET}")
    elif gs.phase == Phase.DESARROLLO:
        gs.set_phase(Phase.CONCLUSION)
        print(f"\n{BOLD}Fase 3: Conclusión{RESET}")

def accusation_phase(gs: GameState, model: AIModelAdapter, characters: Dict[str, Any]):
    print("\nEs momento de acusar. ¿Quién es el asesino?")
    list_suspects(gs, characters)
    while True:
        raw = input("> ").strip()
        if not raw:
            continue
        if raw.lower() in ("salir", "exit", "quit"):
            print("Partida terminada.")
            sys.exit(0)
        accused = choose_person(gs, raw)
        if not accused:
            print("Nombre no reconocido. Intenta con un sospechoso de la lista o su alias.")
            continue
        break

    print("\n" + BOLD + "Resolución del caso" + RESET)
    ending = model.generate_ending(gs, accused, characters)
    print(ending)

    if accused != gs.killer:
        print(f"\n{YELLOW}Fallaste. El asesino real era: {BOLD}{gs.killer}{RESET}{YELLOW}.{RESET}")

    if gs.evidence_revealed:
        print("\nPistas registradas:")
        for ev in gs.evidence_revealed:
            src = gs.evidence_sources.get(ev, "desconocido")
            print(f" - {ev} {CYAN}(aportada por {src}){RESET}")

# ---------------- Main loop ----------------
def main():
    args = parse_args()

    gs, characters = bootstrap_game(args.characters, victim_name=args.victim, seed=args.seed)

    for s in gs.suspects:
        gs.question_limits[s] = args.max_questions

    for name in characters.keys():
        characters[name]["is_killer"] = (name == gs.killer)

    if args.debug:
        print(f"{YELLOW}[DEBUG] Asesino seleccionado: {gs.killer}{RESET}")

    seed_evidence(gs)

    model = build_model(args)

    print_intro(gs, characters)

    while True:
        if gs.phase == Phase.CONCLUSION:
            accusation_phase(gs, model, characters)
            break

        available = [s for s in gs.suspects if gs.question_limits.get(s, 0) > 0]
        if not available:
            print(f"{YELLOW}No quedan preguntas disponibles en esta fase.{RESET}")
            advance_phase(gs)
            if gs.phase != Phase.CONCLUSION:
                for s in gs.suspects:
                    gs.question_limits[s] = args.max_questions
            continue
        
        list_suspects(gs, characters)
        print("\n¿A quién interrogar? (o escribe 'siguiente' para pasar de fase)")
        target_raw = input("> ").strip()
        if not target_raw:
            continue

        low = target_raw.lower()
        if low in ("siguiente", "next", "continuar"):
            advance_phase(gs)
            if gs.phase != Phase.CONCLUSION:
                for s in gs.suspects:
                    gs.question_limits[s] = args.max_questions
            continue
        if low in ("salir", "exit", "quit"):
            print("Partida terminada.")
            sys.exit(0)

        target = choose_person(gs, target_raw)
        if not target:
            print("No reconozco ese nombre. Prueba con un sospechoso de la lista (alias aceptados).")
            list_suspects(gs, characters)
            continue

        if gs.question_limits.get(target, 0) <= 0:
            print(f"{YELLOW}Ya no puedes hacer más preguntas a {target} en esta fase.{RESET}")
            continue

        print("Tu pregunta:")
        q = input("> ").strip()
        if not q:
            print("Necesito una pregunta.")
            continue

        answer_line = interrogate(gs, characters[target], q, model, quoted=None)
        print(answer_line)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
