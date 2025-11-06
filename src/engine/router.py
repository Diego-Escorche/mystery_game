import os
import sys
import random
from colorama import Fore, Style, init as colorama_init
from src.io.loader import load_all_data
from src.engine.name_resolver import NameResolver
from src.engine.interrogations import InterrogationEngine
from src.engine.game_state import GameState, MAX_QUESTIONS_PER_CHARACTER
from src.io.printer import print_header, print_hint

colorama_init(autoreset=True)

FINAL_PROMPT = (
    Fore.MAGENTA
    + "\n== Etapa final ==\n"
    + "Decide quién es el culpable. Usa: 'acusar <nombre o alias>'\n"
    + "Personajes: Silvana, Madame, Jack, Mefisto, Ñopin\n"
)

def _choose_initial_scenario(data) -> str:
    """
    Elige un escenario:
    - Si hay override por ENV SCENARIO_OVERRIDE, usa ese (si existe).
    - Si no, elige aleatoriamente entre las keys de data['scenarios'].
    """
    scenarios = list(data["scenarios"].keys())
    override = os.getenv("SCENARIO_OVERRIDE", "").strip()
    if override and override in data["scenarios"]:
        return override
    return random.choice(scenarios)

def _print_suspects(characters: dict):
    suspects = list(characters["characters"].keys())
    print(Fore.CYAN + "Sospechosos:")
    for s in suspects:
        print(Fore.CYAN + f" - {s}")
    print(Fore.CYAN + "Alias reconocidos: Silvana, Madame, Jack, Mefisto, Ñopin\n")

def run_cli():
    data = load_all_data()
    resolver = NameResolver(data["aliases"])

    # === Elegir escenario inicial (ahora aleatorio, con ENV opcional) ===
    active = _choose_initial_scenario(data)

    state = GameState(
        world=data["world"],
        characters=data["characters"],
        scenarios=data["scenarios"],
        relations=data["relations"],
        active_scenario=active
    )
    engine = InterrogationEngine(state=state, resolver=resolver)

    print_header(state.world["circus_name"])
    scenario_id = state.active_scenario

    openings = {
        "S1_SilvanaAsesina": (
            "El aire del amanecer huele a cuerda quemada y maquillaje seco. "
            "Ñopin Desfijo fue hallado con el cuello marcado por una soga de acrobacia, "
            "una de esas que Silvana Funambula usaba en sus números aéreos. "
            "Nadie vio nada, pero todos juran haber oído un grito breve, ahogado entre los aplausos finales."
        ),
        "S2_SeraphineAsesina": (
            "Una fragancia de incienso y cera derretida aún flota en el camarote de Ñopin Desfijo. "
            "El cuerpo yace rígido sobre la mesa de lectura, los ojos abiertos como si esperaran una respuesta. "
            "Madame Seraphine fue la última en hablar con él, pero asegura que solo quiso 'ayudar'."
        ),
        "S3_JackAsesino": (
            "El rugido de las fieras se mezcló con el último aliento de Ñopin Desfijo. "
            "Una copa de vino caída, restos de veneno usado en el entrenamiento de serpientes... "
            "Jack Domador afirma no saber nada, aunque su silencio suena demasiado ensayado."
        ),
        "S4_MefistoAsesino": (
            "La escena parece un truco mal hecho: la sonrisa de Ñopin pintada con tiza blanca en su rostro muerto. "
            "Nadie entiende cómo Mefisto Bombita apareció con manchas de pintura en las manos, riendo sin razón. "
            "En el circo, la línea entre comedia y tragedia siempre fue delgada."
        ),
        "S5_NyopinSuicidio": (
            "El camarote está cerrado por dentro. Ñopin Desfijo descansa sobre la mesa de su despacho, "
            "una copa medio vacía y una carta sin destinatario frente a él. "
            "Algunos dicen que fue un acto de desesperación; otros, que quiso culpar a alguien más antes de morir."
        ),
    }

    # texto común para todas las variantes
    common_context = (
        "\n\nEl Circo de la Medianoche despierta atrapado en un círculo de sospechas. "
        "Nadie puede abandonar el recinto hasta que se esclarezca lo ocurrido. "
        "Tú eres el detective asignado para descubrir la verdad antes de que llegue la policía. "
        "Interroga a los artistas, analiza sus palabras y sigue el rastro de las pistas. "
        "Cuando creas tener suficientes pruebas, escribe 'siguiente' para pasar a la acusación final."
    )

    intro_text = openings.get(scenario_id, "Algo terrible ha ocurrido en el circo esta noche...") + common_context
    print(f"\n{Fore.LIGHTWHITE_EX}{intro_text}\n")

    _print_suspects(state.characters)
    print_hint("Comandos: 'interrogar <nombre o alias>' | 'escenario' | 'siguiente' | 'salir'")

    # === DEBUG: mostrar asesino si MODO_DEBUG ===
    modo_debug = os.getenv("MODO_DEBUG", "false").lower() in ("1", "true", "yes", "y")
    if modo_debug:
        killer = state.get_scenario().get("killer", "¿?")
        print(Fore.RED + f"[DEBUG] Escenario activo: {state.active_scenario} — Asesino: {killer}")

    current_target = None

    def maybe_enter_final_stage():
        if state.in_final_stage:
            return
        if state.all_clues_found() or state.all_characters_exhausted():
            state.in_final_stage = True
            print(FINAL_PROMPT)

    while True:
        try:
            raw = input(Fore.CYAN + "> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n" + Fore.YELLOW + "Hasta luego.")
            sys.exit(0)

        if not raw:
            continue

        cmd_lower = raw.lower()

        # salida global
        if cmd_lower in ("salir", "exit", "quit"):
            print(Fore.YELLOW + "Hasta luego.")
            break

        # mostrar escenario (ver explicación abajo)
        if cmd_lower == "escenario":
            scen = state.get_scenario()
            print(Fore.MAGENTA + f"Escenario activo: {state.active_scenario}")
            # En modo normal mostramos sólo el título; en debug, un poco más de contexto.
            if modo_debug:
                print(Fore.MAGENTA + f" (killer esperado: {scen.get('killer')})")
                print(Fore.MAGENTA + f" pistas previstas: {len(scen.get('clues', []))}")
            continue

        # forzar etapa final manualmente
        if cmd_lower in ("siguiente", "final"):
            state.in_final_stage = True
            print(FINAL_PROMPT)
            # Mostrar recopilación de pistas antes del final
            found = state.revealed_clues.get(state.active_scenario, [])
            if found:
                print(Fore.CYAN + "\nPistas recopiladas durante la investigación:")
                for c in found:
                    print(Fore.CYAN + f" - {c}")
            else:
                print(Fore.CYAN + "\nNo encontraste ninguna pista clara...")
            continue

        # si estamos en etapa final, sólo aceptamos acusaciones
        if state.in_final_stage and not cmd_lower.startswith("acusar"):
            print(Fore.MAGENTA + "\nCuando estés listo, acusa a alguien con: 'acusar <nombre>'.")
            continue

        if state.in_final_stage:
            if cmd_lower.startswith("acusar"):
                target_text = raw[len("acusar"):].strip()
                accused = resolver.resolve(target_text)
                if not accused:
                    print(Fore.RED + "No reconozco ese nombre. Intenta: Silvana, Madame, Jack, Mefisto, Ñopin.")
                    continue
                actual_killer = state.get_scenario().get("killer")

                ending = engine.model.generate_ending(actual_killer, accused)
                print("\n" + Style.BRIGHT + ending)
                print(Fore.YELLOW + "\nFin de la partida.")
                break

            else:
                print(Fore.YELLOW + "Estás en la etapa final. Usa: 'acusar <nombre>'.")
            continue

        # selección de objetivo a interrogar
        if cmd_lower.startswith("interrogar"):
            target_text = raw[len("interrogar"):].strip()
            if not target_text:
                print(Fore.RED + "Debes indicar a quién interrogar.")
                continue
            canonical = resolver.resolve(target_text)
            if not canonical:
                print(Fore.RED + "No reconozco ese nombre. Intenta: Silvana, Madame, Jack, Mefisto, Ñopin.")
                continue

            # chequear límite de preguntas de ese personaje
            if state.is_char_exhausted(canonical):
                print(Fore.YELLOW + f"{canonical} ya no responderá más. (Límite {MAX_QUESTIONS_PER_CHARACTER})")
                maybe_enter_final_stage()
                continue

            current_target = canonical
            rem = state.remaining_questions(canonical)
            print(Fore.GREEN + f"Interrogas a {current_target}. Te quedan {rem} preguntas para esta persona.")
            print(Fore.GREEN + "Escribe tu pregunta.")
            continue

        # si hay objetivo, tratamos el input como pregunta
        if current_target:
            if state.is_char_exhausted(current_target):
                print(Fore.YELLOW + f"{current_target} ya no responderá más. (Límite {MAX_QUESTIONS_PER_CHARACTER})")
                current_target = None
                maybe_enter_final_stage()
                continue

            answer, clues = engine.ask(current_target, raw)
            rem = state.remaining_questions(current_target)
            print(Style.BRIGHT + answer)

            # Mostrar solo pistas nuevas
            new_clues = []
            for c in clues:
                if c not in state.revealed_clues[state.active_scenario]:
                    state.add_clue(c)
                    new_clues.append(c)
            if new_clues:
                for c in new_clues:
                    print(Fore.BLUE + f"[PISTA NUEVA] {c}")

            print(Fore.CYAN + f"(Preguntas restantes con {current_target}: {rem})")
            
            if state.is_char_exhausted(current_target):
                print(Fore.YELLOW + f"{current_target} guarda silencio ahora.")
                current_target = None

            maybe_enter_final_stage()
        else:
            print(Fore.YELLOW + "Primero elige a quién interrogar: 'interrogar Silvana', por ejemplo.")
