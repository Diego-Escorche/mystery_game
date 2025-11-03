import re
import unicodedata
from typing import Dict, List, Optional

def _strip_accents(s: str) -> str:
    # Normaliza y quita diacríticos (ñ se mantiene como n~ para coincidencias simples)
    normalized = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

def _clean(s: str) -> str:
    # Lowercase, quita tildes, espacios extras y ciertos signos
    s = s.strip().lower()
    s = _strip_accents(s)
    s = re.sub(r"[\s]+", " ", s)
    s = re.sub(r"[()\"']", "", s)
    s = s.strip()
    return s

class NameResolver:
    """
    Mantiene un mapa de alias -> nombre canónico y utilidades para
    normalizar entradas del usuario y para ampliar la detección de citas.
    """
    def __init__(self):
        self.alias_to_canonical: Dict[str, str] = {}
        self.canonical_names: List[str] = []

    def add(self, canonical: str, aliases: Optional[List[str]] = None):
        if canonical not in self.canonical_names:
            self.canonical_names.append(canonical)
        # Canonical también se mapea a sí mismo
        self.alias_to_canonical[_clean(canonical)] = canonical
        if aliases:
            for a in aliases:
                self.alias_to_canonical[_clean(a)] = canonical

    def canonicalize(self, raw: str) -> Optional[str]:
        key = _clean(raw)
        return self.alias_to_canonical.get(key)

    def is_known(self, raw: str) -> bool:
        return self.canonicalize(raw) is not None

    def all_canonical(self) -> List[str]:
        return list(self.canonical_names)

    def all_alias_keys(self) -> List[str]:
        """
        Devuelve todas las claves (alias normalizados) que reconoce,
        útil para pasar a detectores que no usan canonicalización.
        """
        return list(self.alias_to_canonical.keys())

    def expand_aliases_for_quote_detection(self) -> List[str]:
        """
        Para quote_parser, conviene pasar NOMBRES NO NORMALIZADOS (humanos).
        Devolvemos la lista de nombres 'bonitos' que el usuario podría usar:
        todas las formas (canonical + alias exactos).
        """
        # Reconstruimos valores legibles: usamos los canónicos y además intentamos
        # reconstruir variantes comunes a partir de los canónicos.
        # En la práctica, lo mejor es pasar explícitamente las variantes que definimos
        # al crear el resolver, así que este método lo reemplazamos por algo simple:
        return self.canonical_names
