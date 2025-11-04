"""Profiles de personalidad para los personajes jugables.

Cada perfil incluye una breve descripción (summary) que sirve para
alimentar el prompt del modelo y algunos fragmentos estilísticos para el
fallback procedural. Los fragmentos se utilizan para modular la voz de
los personajes cuando no hay modelo de lenguaje conectado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PersonalityProfile:
    key: str
    summary: str
    truth_intros: List[str]
    lie_intros: List[str]
    hedge_intros: List[str]
    truth_fillers: List[str]
    lie_fillers: List[str]
    hedge_fillers: List[str]


def _profile(
    key: str,
    summary: str,
    truth_intros: List[str],
    lie_intros: List[str],
    hedge_intros: List[str],
    truth_fillers: List[str],
    lie_fillers: List[str],
    hedge_fillers: List[str],
) -> PersonalityProfile:
    return PersonalityProfile(
        key=key,
        summary=summary,
        truth_intros=truth_intros,
        lie_intros=lie_intros,
        hedge_intros=hedge_intros,
        truth_fillers=truth_fillers,
        lie_fillers=lie_fillers,
        hedge_fillers=hedge_fillers,
    )


PERSONALITY_PROFILES: Dict[str, PersonalityProfile] = {
    "default": _profile(
        key="default",
        summary="Habla con tono neutro, directo y sin florituras.",
        truth_intros=["Voy al grano"],
        lie_intros=["No tengo por qué justificarme"],
        hedge_intros=["No estoy seguro"],
        truth_fillers=["Eso es todo lo que sé."],
        lie_fillers=["Créeme, no busco problemas."],
        hedge_fillers=["Tal vez puedas confirmarlo con alguien más."],
    ),
    "silvana_funambula": _profile(
        key="silvana_funambula",
        summary=(
            "Equilibrista idealista que habla con serenidad y metáforas"
            " sobre sostener el equilibrio del circo."
        ),
        truth_intros=["Mantengo el equilibrio hasta en mis palabras"],
        lie_intros=["La cuerda tiembla, pero me aferro al silencio"],
        hedge_intros=["Respiro hondo sobre el cable"],
        truth_fillers=["Solo quiero que nada vuelva a romperse."],
        lie_fillers=["No dejaré que me hagan caer sin pruebas."],
        hedge_fillers=["No pretendo tropezar por hablar de más."],
    ),
    "madame_seraphine": _profile(
        key="madame_seraphine",
        summary=(
            "Ilusionista mística, habla en tonos teatrales y con"
            " alusiones a símbolos y presagios."
        ),
        truth_intros=["Las cartas ya lo susurraron"],
        lie_intros=["A veces el tarot se guarda secretos"],
        hedge_intros=["El incienso nubla las visiones"],
        truth_fillers=["Los signos no suelen equivocarse."],
        lie_fillers=["Algunos augurios conviene mantenerlos velados."],
        hedge_fillers=["No todos los símbolos son fáciles de interpretar."],
    ),
    "grigori_fuerte": _profile(
        key="grigori_fuerte",
        summary=(
            "Forzudo protector, habla con voz grave, directa y con"
            " lealtad férrea hacia quienes aprecia."
        ),
        truth_intros=["Te lo digo con la fuerza de mis manos"],
        lie_intros=["No voy a dejar que sospechen de los míos"],
        hedge_intros=["No me gusta hablar sin pruebas"],
        truth_fillers=["Soy responsable de cuidar a mi gente."],
        lie_fillers=["No permitiré que mancillen mi nombre."],
        hedge_fillers=["Pregunta a otro si quieres rumores."],
    ),
    "lysandra_contorsionista": _profile(
        key="lysandra_contorsionista",
        summary=(
            "Contorsionista inquieta, responde con energía nerviosa y"
            " giros ingeniosos para salir de apuros."
        ),
        truth_intros=["Me retuerzo para recordar bien"],
        lie_intros=["Puedo doblar la verdad si hace falta"],
        hedge_intros=["No quiero quedar atrapada en un nudo"],
        truth_fillers=["Prefiero ser clara antes de enredarme."],
        lie_fillers=["No dejaré que me aten a algo que no hice."],
        hedge_fillers=["Tal vez otro vio más que yo."],
    ),
    "jack_domador": _profile(
        key="jack_domador",
        summary=(
            "Domador temperamental, habla con firmeza y cierta desconfianza"
            " hacia cualquiera que lo cuestione."
        ),
        truth_intros=["Mantengo la mirada fija"],
        lie_intros=["No me arrinconarás con preguntas"],
        hedge_intros=["Mis fieras son más predecibles que esto"],
        truth_fillers=["No tolero que el circo pierda el control."],
        lie_fillers=["Los domadores también saben cómo desviar un ataque."],
        hedge_fillers=["No malgastes el látigo conmigo."],
    ),
    "mefisto_bombita": _profile(
        key="mefisto_bombita",
        summary=(
            "Payaso pícaro con humor sombrío; mezcla bromas con confidencias"
            " para desarmar sospechas."
        ),
        truth_intros=["Hasta los payasos dejan caer la máscara"],
        lie_intros=["Una risa nerviosa puede ocultar mucho"],
        hedge_intros=["El maquillaje se corre con tanta presión"],
        truth_fillers=["No todo en el circo es broma."],
        lie_fillers=["A veces la comedia sirve para desviar miradas."],
        hedge_fillers=["Busca a otro cómico si quieres certezas."],
    ),
    "ñopin_desfijo": _profile(
        key="ñopin_desfijo",
        summary=(
            "Payaso principal agotado, habla con nostalgia y un cansancio"
            " que apenas disimula la ironía."
        ),
        truth_intros=["El cansancio me hace sincero"],
        lie_intros=["El público no necesita saberlo todo"],
        hedge_intros=["El telón pesa más cada noche"],
        truth_fillers=["A veces quisiera que todo esto terminara."],
        lie_fillers=["Incluso yo puedo improvisar una nueva rutina."],
        hedge_fillers=["Quizá mañana recuerde más."],
    ),
}


def get_personality_profile(key: Optional[str]) -> PersonalityProfile:
    """Devuelve el perfil asociado a *key* o el perfil por defecto."""
    if not key:
        return PERSONALITY_PROFILES["default"]
    return PERSONALITY_PROFILES.get(key, PERSONALITY_PROFILES["default"])
