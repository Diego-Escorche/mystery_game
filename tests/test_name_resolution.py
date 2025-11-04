from mystery_game.src.engine.name_resolver import NameResolver

def test_resolve_aliases():
    aliases = {
        "Silvana Funambula": ["silvana", "funambula"],
        "Madame Seraphine": ["madame", "seraphine"],
        "Jack Domador": ["jack", "domador"],
        "Mefisto Bombita": ["mefisto", "bombita"],
        "Ñopin Desfijo": ["ñopin", "desfijo", "nopin"]
    }
    r = NameResolver(aliases)
    assert r.resolve("Silvana") == "Silvana Funambula"
    assert r.resolve("madame") == "Madame Seraphine"
    assert r.resolve("Jack") == "Jack Domador"
    assert r.resolve("Bombita") == "Mefisto Bombita"
    assert r.resolve("ñopin") == "Ñopin Desfijo"
