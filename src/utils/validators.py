def ensure_keys(d: dict, keys: list[str], ctx: str = ""):
    for k in keys:
        if k not in d:
            raise ValueError(f"Falta clave '{k}' en {ctx or 'estructura'}")
