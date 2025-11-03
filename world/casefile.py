from dataclasses import dataclass
from typing import List

@dataclass
class MurderCase:
    victim: str
    location: str = "Camarín del circo"
    initial_summary: str = (
        "Ñopin desfijo fue hallado muerto en su camarín con la puerta cerrada. "
        "No hay marcas visibles de violencia; el espejo está roto y hay símbolos extraños pintados."
    )
    suspects: List[str] = None
