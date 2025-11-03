FOCUS_KEYWORDS = [
    "víctima","victima","muerte","camarín","circo","símbolo","sangre","huella","alibi","coartada",
    "hora","arma","prueba","evidencia","sospechoso","acusación","culpable","testigo","escena",
    "vagón","carpa","telón","espejo","pintura","cuerda",
    "ñopin","ñopin desfijo"
]

INTENT_KEYWORDS = {
    "COARTADA": ["coartada","dónde estabas","donde estabas","alibi","hora","a qué hora","a que hora","tiempo","cuando"],
    "LUGAR": ["dónde","donde","lugar","escena","camarín","carpa","vagón","telón","pasillo"],
    "PRUEBAS": ["prueba","pruebas","evidencia","huella","sangre","pintura","espejo","cuerda","objeto","arma"],
    "RELACIONES": ["relación","relaciones","te llevas","odio","amistad","rival","enemigo","celos","deuda"],
    "MÓVIL": ["motivo","móvil","por qué","por que","dinero","venganza","secreto","secta"],
    "RUMOR": ["dijo","dice","cuentan","rumor","acusó","acuso","acusación","acusaciones"],
    "OBJETO": ["pañuelo","navaja","cuerda","pistola","trapo","prop","utilería","llave","llaves"],
}

def classify_intent(question: str) -> str:
    q = question.lower()
    for intent, kws in INTENT_KEYWORDS.items():
        if any(k in q for k in kws):
            return intent
    return "GENERAL"

def is_offtopic(question: str) -> bool:
    q = question.lower()
    return not any(k in q for k in FOCUS_KEYWORDS)

def enforce_focus() -> str:
    return (
        "Concentrémonos en el caso. Esta conversación es sobre la muerte de Canelitas y lo ocurrido en el circo. "
        "Si tienes una pregunta específica sobre coartadas, pruebas o testimonios, dila con claridad."
    )
