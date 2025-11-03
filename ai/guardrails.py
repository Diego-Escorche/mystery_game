import re
import unicodedata
from typing import Optional

# =====================================================
# Normalización de texto
# =====================================================

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _norm(s: str) -> str:
    s = s.strip().lower()
    s = _strip_accents(s)
    # espacios simples
    s = re.sub(r"\s+", " ", s)
    return s

# =====================================================
# Palabras del dominio (caso de asesinato en el circo)
# =====================================================

DOMAIN_HINTS = [
    # núcleo del caso
    r"\b(caso|asesin|muerte|victima|culpable|homicidio|crimen|asesino)\b",
    r"\b(circo|carpa|camarin|escenario|bastidores|vagon(?:es)?)\b",
    r"\b(prueba(?:s)?|evidenc(?:ia|ias)|huella(?:s)?|sangre|pintura|cuerda|espejo|panuelo|arma|objeto)\b",
    r"\b(testimoni(?:o|os)|coartada|alibi|alibi)\b",
    r"\b(hora|cuando|donde|quien|como|por que|porque)\b",
]

# Temas claramente fuera del caso (si NO aparecen hints del dominio)
OFFTOPIC_BLACKLIST = [
    r"\b(clima|tiempo hace|llueve|temperatura|pronostico)\b",
    r"\b(comida|cena|almuerzo|desayuno|receta|restaurante|delivery)\b",
    r"\b(futbol|partido|nba|tenis|mundial|champions|gol|seleccion)\b",
    r"\b(politic|eleccion(?:es)?|presidente|senador|diputado|partido politico)\b",
    r"\b(tiktok|instagram|facebook|twitter|x\.com|youtube|red(?:es)? sociales)\b",
    r"\b(cripto|bitcoin|precio|dolar|acciones|inversiones?)\b",
    r"\b(viaje|turismo|hotel|airbnb|playa|montana)\b",
    r"\b(musica|cancion|pelicula|serie|netflix|spotify)\b",
    r"\b(chiste|broma|adivinanza)\b",
]

# =====================================================
# Clasificación de intención
# =====================================================
# Intenciones: COARTADA, PRUEBAS, MOVIL, RELACIONES, LUGAR, OBJETO, RUMOR, GENERAL

# Heurísticas (todas insensibles a mayúsculas/acentos)
PATTERNS = {
    "COARTADA": [
        r"\b(que|q) estabas? haciendo\b",
        r"\b(donde|en que lugar) estabas?\b",
        r"\b(a que hora|cuando) estabas?\b",
        r"\b(cual es|tienes?) tu coartada\b",
        r"\bque hacias?\b",
        r"\bcon quien estabas?\b",
    ],
    "PRUEBAS": [
        r"\b(prueba(?:s)?|evidenc(?:ia|ias)|huellas?|sangre|espejo roto|cuerda|pintura|panuelo)\b",
        r"\b(encontraste|viste|oiste|escuchaste)\b.*\b(prueba|evidenc|huella|sangre|objeto)\b",
        r"\b(muestrame|dime) (una )?pista\b",
    ],
    "OBJETO": [
        r"\b(arma|objeto|herramienta|cuerda|navaja|panuelo|espejo)\b",
        r"\b(de quien es|a quien pertenece)\b.*\b(objeto|arma|cuerda|panuelo|espejo)\b",
    ],
    "LUGAR": [
        r"\b(donde|en que lugar|hacia donde|a donde)\b",
        r"\b(vagon|carpa|camarin|escenario|bastidores|detras del escenario)\b",
        r"\b(rastro|huella|camino)\b",
    ],
    "MOVIL": [
        r"\b(por que|porque|motivo|razon|celos|dinero|venganza|envidia)\b",
        r"\b(que te llevo|que los llevo|que podria llevar)\b.*\b(hacerlo|matar|lastimar)\b",
    ],
    "RELACIONES": [
        r"\b(relacion|trato|pelea|discutiste|enemistad|amistad|problema)\b",
        r"\b(que opinas de|como te llevas con|que piensas de)\b",
        r"\b(acusaste?|acus[oó]|defendiste?|apoyaste?)\b",
    ],
    "RUMOR": [
        r"\b(quien crees? que lo (hizo|mato)|tus sospechas|rumores?)\b",
        r"\b(si tuvieras que acusar a alguien|a quien acusarias?)\b",
    ],
}

def _match_any(text: str, patterns) -> bool:
    return any(re.search(p, text) for p in patterns)

def classify_intent(question: str) -> str:
    """
    Clasifica la intención sin exigir palabras “clave” explícitas.
    Orden de chequeo pensado para preguntas cortas como:
    - "¿Qué estabas haciendo?" → COARTADA
    - "¿Quién crees que lo hizo?" → RUMOR
    - "¿Dónde estabas?" → COARTADA (o LUGAR si aplica)
    - "¿Viste algo?" → PRUEBAS
    """
    q = _norm(question)

    # Heurísticas fuertes por orden práctico
    if _match_any(q, PATTERNS["COARTADA"]):
        return "COARTADA"
    if _match_any(q, PATTERNS["PRUEBAS"]):
        return "PRUEBAS"
    if _match_any(q, PATTERNS["OBJETO"]):
        return "OBJETO"
    if _match_any(q, PATTERNS["LUGAR"]):
        return "LUGAR"
    if _match_any(q, PATTERNS["MOVIL"]):
        return "MÓVIL"
    if _match_any(q, PATTERNS["RELACIONES"]):
        return "RELACIONES"
    if _match_any(q, PATTERNS["RUMOR"]):
        return "RUMOR"

    # Preguntas genéricas cortas que solemos usar en interrogatorio y deben ser válidas
    # asúmelas como COARTADA/PRUEBAS por defecto si contienen verbos de ver/estar/oír/hacer
    if re.search(r"\b(que hacias?|que estabas? haciendo|donde estabas?|a que hora)\b", q):
        return "COARTADA"
    if re.search(r"\b(que viste|viste algo|oiste algo|escuchaste algo)\b", q):
        return "PRUEBAS"

    return "GENERAL"

def is_offtopic(question: str) -> bool:
    """
    Devuelve True sólo si la pregunta es claramente ajena al caso.
    Primero intenta clasificar una intención válida; si la hay, NO es offtopic.
    """
    q = _norm(question)

    # Si se detecta una intención útil → no es offtopic
    intent = classify_intent(question)
    if intent != "GENERAL":
        return False

    # Si incluye palabras del dominio, aunque sea GENERAL → no es offtopic
    if any(re.search(p, q) for p in DOMAIN_HINTS):
        return False

    # Si cae en temas “prohibidos” y no hay dominio → sí es offtopic
    if any(re.search(p, q) for p in OFFTOPIC_BLACKLIST):
        return True

    # Por defecto, preguntas muy cortas y neutras no se consideran offtopic
    # (permitimos que el personaje pida precisión de forma breve, pero no corta)
    return False

def enforce_focus() -> str:
    """
    Mensaje breve de recentrado. El stub/modelo lo usa cuando is_offtopic=True.
    """
    return "volvamos a la investigación y a lo ocurrido con la víctima."
