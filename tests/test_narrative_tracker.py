from mystery_game.src.engine.narrative_tracker import NarrativeTracker
from mystery_game.src.engine.game_state import GameState

def test_tracker_allows_fact():
    state = GameState(world={}, characters={}, scenarios={"S": {}}, relations={}, active_scenario="S")
    nt = NarrativeTracker(state)
    assert nt.is_fact_allowed("Silvana Funambula", "algo")
