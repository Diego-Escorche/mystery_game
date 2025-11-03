from typing import Tuple, Dict, Any, Optional
import yaml
import random

from .state import GameState, Phase

def load_characters_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Se espera un mapping: nombre -> atributos
    return data

def bootstrap_game(path_yaml: str, victim_name: str = "Ñopin desfijo", seed: Optional[int] = None) -> Tuple[GameState, Dict[str, Any]]:
    rnd = random.Random(seed)
    characters = load_characters_yaml(path_yaml)

    # sospechosos = claves del YAML
    suspects = list(characters.keys())

    gs = GameState(suspects=suspects, victim=victim_name, killer=None, phase=Phase.INICIO)

    # construir alias antes de ingest_relations (para canonicalizar nombres en YAML)
    gs.build_alias_index(characters)

    # ingerir relaciones del YAML -> gs.relations
    # si querés simetría suave, usa symmetric=True
    gs.ingest_yaml_relations(characters, symmetric=False)

    # limites de preguntas (ejemplo por fase)
    for s in suspects:
        gs.question_limits[s] = 3

    # killer aleatorio
    if suspects:
        gs.killer = rnd.choice(suspects)

    return gs, characters
