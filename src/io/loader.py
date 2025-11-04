import json
import yaml
from pathlib import Path

def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def load_all_data():
    base = Path(__file__).resolve().parents[2] / "data"
    aliases = load_json(base / "aliases.json")
    characters = load_yaml(base / "characters.yaml")
    scenarios = load_yaml(base / "scenarios.yaml")["scenarios"]
    relations = load_yaml(base / "relationships.yaml")
    world = load_yaml(base / "world.yaml")["world"]
    return {
        "aliases": aliases,
        "characters": characters,
        "scenarios": scenarios,
        "relations": relations,
        "world": world
    }
