from ..engine.state import GameState

def resolve_accusation(gs: GameState, accused: str) -> str:
    if accused == gs.killer:
        return (
            f"¡Caso resuelto! {accused} era el responsable. "
            "Las piezas encajan: el espejo roto, las huellas y los símbolos fueron parte del encubrimiento. "
            "Confrontado con las pruebas, confiesa entre lágrimas."
        )
    elif accused in gs.suspects:
        return (
            f"Final malo: Acusaste a {accused}, pero no era el culpable. "
            "El verdadero asesino escapa entre las sombras del desierto y el circo continúa su función macabra."
        )
    else:
        return (
            "Final malo: Tu acusación fue confusa y nadie es detenido. "
            "El caso se enfría y la verdad se entierra bajo la carpa."
        )
