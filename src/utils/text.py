import unicodedata
import re

def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def normalize(s: str) -> str:
    s = s.strip().lower()
    s = strip_accents(s)
    s = re.sub(r"\s+", " ", s)
    return s
