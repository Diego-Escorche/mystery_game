class NarrativeTracker:
    """Reserva para reglas futuras de coherencia (contradicciones, tiempo, etc.)."""
    def __init__(self, state):
        self.state = state

    def is_fact_allowed(self, character: str, fact: str) -> bool:
        # Aquí podrías chequear si la pista ya fue revelada o si contradice el escenario.
        return True
