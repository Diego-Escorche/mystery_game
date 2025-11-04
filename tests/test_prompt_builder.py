from mystery_game.src.engine.game_state import GameState
from mystery_game.src.models.prompt_builder import PromptBuilder

def minimal_state():
    return GameState(
        world={"circus_name": "Circo de la Medianoche"},
        characters={
            "characters": {
                "Silvana Funambula": {
                    "role": "Equilibrista",
                    "voice": "Suave",
                    "traits": ["perfeccionista"],
                    "tics": ["evita miradas"],
                    "base_emotion": "tensa"
                }
            }
        },
        scenarios={
            "S1": {
                "killer": "Silvana Funambula",
                "motive": "desesperación",
                "modus": "golpe",
                "precrime": {},
                "emotional_state": {"Silvana Funambula": "culpa"},
                "clues": ["mancha"]
            }
        },
        relations={"relations": {"allies": [], "tensions": [], "rules": {}}},
        active_scenario="S1"
    )

def test_prompt_contains_blocks():
    state = minimal_state()
    pb = PromptBuilder(state)
    p = pb.build_prompt("Silvana Funambula", "¿Dónde estabas?")
    assert "## SCENARIO CONTEXT" in p
    assert "## CHARACTER CARD" in p
    assert "## GUARDRAILS" in p
    assert "¿Dónde estabas?" in p
