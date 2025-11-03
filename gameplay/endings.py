# gameplay/endings.py
from engine.state import GameState

def resolve_accusation(gs: GameState, accused: str, model, characters) -> str:
    """
    Ahora el final lo genera dinámicamente el modelo (stub).
    """
    return model.generate_ending(gs, accused, characters)
