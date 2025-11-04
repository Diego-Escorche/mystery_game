from typing import Tuple, Dict, Any, Optional
import os
import unicodedata
import yaml
import random

from gameplay.personalities import get_personality_profile
from .state import GameState, Phase


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def _norm_key(text: str) -> str:
    return _strip_accents(text or "").strip().lower()

def load_characters_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Se espera un mapping: nombre -> atributos
    return data

def load_knowledge_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def _attach_personality_and_knowledge(
    characters: Dict[str, Any],
    knowledge: Dict[str, Any],
):
    norm_knowledge = {_norm_key(k): v for k, v in knowledge.items()}

    for canonical, data in characters.items():
        if not isinstance(data, dict):
            continue

        profile = get_personality_profile(data.get("personality_key"))
        if profile.summary:
            data.setdefault("personality", profile.summary)
        # Guardamos el perfil completo para el fallback procedural
        data.setdefault("personality_profile", profile)

        display_name = data.get("name") or canonical
        matched = norm_knowledge.get(_norm_key(display_name))
        if not matched:
            matched = norm_knowledge.get(_norm_key(canonical))
        if matched:
            data.setdefault("knowledge", matched)


def bootstrap_game(
    path_yaml: str,
    victim_name: str = "Ñopin desfijo",
    seed: Optional[int] = None,
    knowledge_path: Optional[str] = None,
) -> Tuple[GameState, Dict[str, Any]]:
    rnd = random.Random(seed)
    characters = load_characters_yaml(path_yaml)

    if knowledge_path is None:
        base_dir = os.path.dirname(path_yaml)
        knowledge_path = os.path.join(base_dir, "knowledge.yaml")
    knowledge = load_knowledge_yaml(knowledge_path)
    _attach_personality_and_knowledge(characters, knowledge)

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
