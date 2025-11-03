from engine.state import GameState

def resolve_accusation(gs: GameState, accused: str) -> str:
    """
    Devuelve el texto final según la acusación.
    En finales fallidos, revela el asesino real para verificación.
    """
    if accused == gs.killer:
        return (
            f"¡Caso resuelto! {accused} era el responsable. "
            "Las piezas encajan: la secuencia de actos, el espejo roto y los símbolos encubrían la verdad. "
            "Confrontado con las pruebas, confiesa entre lágrimas."
        )
    elif accused in gs.suspects:
        return (
            f"Final malo: Acusaste a {accused}, pero no era el culpable. "
            f"El asesino real era {gs.killer}. "
            "Se escabulle entre las sombras del desierto y la carpa vuelve a encender sus luces."
        )
    else:
        return (
            "Final malo: Tu acusación fue confusa y nadie es detenido. "
            f"El asesino real era {gs.killer}. "
            "El caso se enfría y la verdad se entierra bajo la arena."
        )
