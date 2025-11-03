import re
from typing import Optional, Dict, List

# -----------------------------------------
# Utilidades de nombres
# -----------------------------------------
def _name_variants(name: str) -> List[str]:
    """
    Podrías expandir a variaciones (apodos, etc). Por ahora escapamos literal.
    """
    safe = re.escape(name)
    return [safe]

def _resolve_name(raw: str, known_names: List[str]) -> Optional[str]:
    raw_s = raw.strip()
    for n in known_names:
        if re.fullmatch(rf"{re.escape(n)}", raw_s, flags=re.IGNORECASE):
            return n
    for n in known_names:
        if raw_s.lower() in n.lower() or n.lower() in raw_s.lower():
            return n
    return None

def _find_about_name(text: str, known_names: List[str], exclude: Optional[str]) -> Optional[str]:
    """
    Intenta encontrar 'about' por patrón 'a <Nombre>' o 'sobre <Nombre>' o contención general,
    evitando el 'source'.
    """
    # 1) Patrones dirigidos
    for n in known_names:
        if exclude and n.lower() == str(exclude).lower():
            continue
        # a <Nombre>
        if re.search(rf"\ba\s+{re.escape(n)}\b", text, flags=re.IGNORECASE):
            return n
        # sobre <Nombre>
        if re.search(rf"\bsobre\s+{re.escape(n)}\b", text, flags=re.IGNORECASE):
            return n
    # 2) Contención general si lo anterior no funcionó
    for n in known_names:
        if exclude and n.lower() == str(exclude).lower():
            continue
        if re.search(rf"\b{re.escape(n)}\b", text, flags=re.IGNORECASE):
            return n
    return None

# -----------------------------------------
# Detección de citas
# -----------------------------------------
def detect_quote(question: str, known_names: List[str]) -> Optional[Dict]:
    """
    Devuelve un dict estilo StatementEvent serializable:
    {
      "source": <quien lo dijo>,
      "about": <de quien hablaba> | None,
      "is_accusation": bool,
      "is_support": bool,
      "content": <frase citada (si logramos extraerla) o resumen corto>
    }
    o None si no se detecta cita.
    """
    q = question.strip()
    if not q:
        return None

    # Prepara mapa rápido de nombres para presencia
    present_sources = []
    for n in known_names:
        if re.search(rf"\b{re.escape(n)}\b", q, flags=re.IGNORECASE):
            present_sources.append(n)

    # Verbos y marcadores de cita ampliados
    SAY_SYNS = r"(?:dijo|dice|coment[oó]|comentó|mencion[oó]|mencionó|asegur[oó]|aseguró|afirm[oó]|afirmó|cont[oó]|contó|declar[oó]|declaró|sostuvo|señal[oó]|señaló|explic[oó]|explicó|apunt[oó]|apuntó|indic[oó]|indicó)"
    INTRO_MARKERS = r"(?:seg[uú]n|de acuerdo con|a decir de|conforme a|de conformidad con|tal como dijo|tal y como dijo)"
    ACCUSE_SYNS = r"(?:acus[aoó]|acusó|acusaba|acusa)"
    SUPPORT_SYNS = r"(?:defiende|apoya|respalda|abala|avala)"

    # 1) Patrones acusación explícita: "X acusa a Y de Z"
    m_accuse = re.search(
        rf"\b([A-ZÁÉÍÓÚÑ][\w() áéíóúñ]+?)\s+{ACCUSE_SYNS}\s+a\s+([A-ZÁÉÍÓÚÑ][\w() áéíóúñ]+)\s*(?:de\s+(.*))?$",
        q,
        flags=re.IGNORECASE,
    )
    if m_accuse:
        raw_src, raw_tgt, content = m_accuse.groups()
        src = _resolve_name(raw_src, known_names) or raw_src.strip()
        tgt = _resolve_name(raw_tgt, known_names)
        content = (content or "algo serio").strip()
        return {
            "source": src,
            "about": tgt,
            "is_accusation": True,
            "is_support": False,
            "content": content[:240] + ("…" if len(content) > 240 else ""),
        }

    # 2) Patrones apoyo explícito: "X defiende/apoya/respalda a Y"
    m_support = re.search(
        rf"\b([A-ZÁÉÍÓÚÑ][\w() áéíóúñ]+?)\s+{SUPPORT_SYNS}\s+a\s+([A-ZÁÉÍÓÚÑ][\w() áéíóúñ]+)\b(.*)$",
        q,
        flags=re.IGNORECASE,
    )
    if m_support:
        raw_src, raw_tgt, tail = m_support.groups()
        src = _resolve_name(raw_src, known_names) or raw_src.strip()
        tgt = _resolve_name(raw_tgt, known_names)
        content = tail.strip() or f"{src} apoya a {tgt}"
        return {
            "source": src,
            "about": tgt,
            "is_accusation": False,
            "is_support": True,
            "content": content[:240] + ("…" if len(content) > 240 else ""),
        }

    # 3) "Según X ..." / "De acuerdo con X ..." (cita genérica)
    m_intro = re.search(
        rf"(?:{INTRO_MARKERS})\s+([A-ZÁÉÍÓÚÑ][\w() áéíóúñ]+)\s+(.*)$",
        q,
        flags=re.IGNORECASE,
    )
    if m_intro:
        raw_src, tail = m_intro.groups()
        src = _resolve_name(raw_src, known_names) or raw_src.strip()
        about = _find_about_name(q, known_names, exclude=src)
        content = tail.strip() or "lo indicó de esa manera"
        return {
            "source": src,
            "about": about,
            "is_accusation": bool(re.search(ACCUSE_SYNS, tail, flags=re.IGNORECASE)),
            "is_support": bool(re.search(SUPPORT_SYNS, tail, flags=re.IGNORECASE)),
            "content": content[:240] + ("…" if len(content) > 240 else ""),
        }

    # 4) "X dijo/aseguró/comentó que ..." (cita con 'que')
    m_say_that = re.search(
        rf"\b([A-ZÁÉÍÓÚÑ][\w() áéíóúñ]+?)\s+{SAY_SYNS}\s+que\s+(.*)$",
        q,
        flags=re.IGNORECASE,
    )
    if m_say_that:
        raw_src, content = m_say_that.groups()
        src = _resolve_name(raw_src, known_names) or raw_src.strip()
        about = _find_about_name(q, known_names, exclude=src)
        content = (content or "").strip()
        return {
            "source": src,
            "about": about,
            "is_accusation": bool(re.search(ACCUSE_SYNS, content, flags=re.IGNORECASE)),
            "is_support": bool(re.search(SUPPORT_SYNS, content, flags=re.IGNORECASE)),
            "content": content[:240] + ("…" if len(content) > 240 else "") if content else "lo mencionó en términos generales",
        }

    # 5) "X dice ..." (sin 'que')
    m_say = re.search(
        rf"\b([A-ZÁÉÍÓÚÑ][\w() áéíóúñ]+?)\s+{SAY_SYNS}\b(.*)$",
        q,
        flags=re.IGNORECASE,
    )
    if m_say:
        raw_src, tail = m_say.groups()
        src = _resolve_name(raw_src, known_names) or raw_src.strip()
        about = _find_about_name(q, known_names, exclude=src)
        tail = (tail or "").strip()
        return {
            "source": src,
            "about": about,
            "is_accusation": bool(re.search(ACCUSE_SYNS, tail, flags=re.IGNORECASE)),
            "is_support": bool(re.search(SUPPORT_SYNS, tail, flags=re.IGNORECASE)),
            "content": tail[:240] + ("…" if len(tail) > 240 else "") if tail else "hizo un comentario",
        }

    # 6) Si aparece un nombre y “acusó/defendió/apoyó/respalda” en la misma frase sin patrón claro
    if present_sources and re.search(rf"{ACCUSE_SYNS}|{SUPPORT_SYNS}", q, flags=re.IGNORECASE):
        src = present_sources[0]
        about = _find_about_name(q, known_names, exclude=src)
        return {
            "source": src,
            "about": about,
            "is_accusation": bool(re.search(ACCUSE_SYNS, q, flags=re.IGNORECASE)),
            "is_support": bool(re.search(SUPPORT_SYNS, q, flags=re.IGNORECASE)),
            "content": "lo señaló en esa línea",
        }

    return None
