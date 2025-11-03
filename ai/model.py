# ai/model.py
import random
import json
import re
from typing import Dict, Any, Optional, Tuple

from .guardrails import is_offtopic, enforce_focus, classify_intent


# =====================================================
# 🔧 Prompt Builder — genera el texto para el modelo HF
# =====================================================
class PromptBuilder:
    @staticmethod
    def build_dialog_prompt(
        character: Dict[str, Any],
        question: str,
        intent: str,
        policy: str,
        game_state,
        quoted: Optional[Dict[str, Any]] = None,
        clue_guidance: str = "",
    ) -> str:
        """
        Construye el prompt que se pasa al modelo de lenguaje.
        """
        name = character["name"]
        personality = character.get("personality", "Neutral")
        role = character.get("role", "")
        killer = character.get("is_killer", False)
        phase = game_state.phase.name
        relations = game_state.relations.get(name, {})

        rel_desc = []
        for other, score in relations.items():
            if score > 0.5:
                rel_desc.append(f"Confía en {other}.")
            elif score < -0.5:
                rel_desc.append(f"Desconfía profundamente de {other}.")
        rel_line = " ".join(rel_desc)

        clue_part = ""
        if clue_guidance:
            # Si hay una pista que el personaje debe incluir, la instrucción es natural y sin etiquetas
            clue_part = f"- Incluye en tu respuesta una referencia a {clue_guidance}, de forma natural."


        sheet = f"Nombre: {name}\nRol: {role}\nPersonalidad: {personality}"
        ctx = f"Situación: fase {phase}. Conversación sobre la muerte de {game_state.victim}."
        quoted_part = ""
        if quoted:
            src = quoted.get("source")
            about = quoted.get("about")
            if quoted.get("is_accusation"):
                quoted_part = f"{src} ha acusado a {about}."
            elif quoted.get("is_support"):
                quoted_part = f"{src} ha defendido a {about}."
            else:
                quoted_part = f"{src} mencionó algo sobre {about}."

        return f"""
[SYSTEM]
Responde SOLO como el personaje {name}. Sin narrador externo ni descripción del entorno.
Tu salida DEBE tener exactamente dos líneas:
Línea 1: <META>{{...}}</META>
Línea 2: una o dos oraciones de DIÁLOGO directo del personaje (sin corchetes ni llaves).

[CHARACTER SHEET]
{sheet}

[CONTEXT]
{ctx}
{quoted_part}

[RELATIONS]
{rel_line}

[QUESTION]
Jugador: "{question}"

[INTENT]
{intent}

[POLICY]
Decisión: {policy}
- TRUTH: decir la verdad con detalle.
- LIE: mentir de forma convincente.
- HEDGE: responder con cautela o evasivas.

[STYLE]
- Máximo 2 oraciones.
- Mantén el tono de personalidad y la situación.
- NO uses narrador, ni describas acciones físicas, solo habla.
[STYLE]
- Máximo 2 oraciones.
- Mantén el tono de personalidad y la situación.
- NO uses narrador, ni describas acciones físicas, solo habla.
- Si NO hay pista nueva, deja payload como cadena vacía "".
- Si HAY pista nueva, payload debe ser un texto factual corto (<=120 caracteres), sin llaves < > ni corchetes [].
{clue_part}


[OUTPUT FORMAT]
<META>{{"intent":"{intent}","truthful":{str(policy=='TRUTH').lower()},"payload":"<hecho/pista si aplica>","evasive":{str(policy!='TRUTH').lower()},"said_before":false}}</META>
{{diálogo conciso del personaje}}
"""


# =====================================================
# 🎭 AIModelAdapter — lógica principal de interacción
# =====================================================
class AIModelAdapter:
    """
    Controlador de generación de respuestas usando un modelo HF o fallback local.
    """

    def __init__(self, seed: Optional[int] = None, llm_backend=None):
        self.rnd = random.Random(seed)
        self.llm = llm_backend  # backend (por ejemplo HFSmolLMBackend)

    # -----------------------------
    # Métodos auxiliares
    # -----------------------------
    def _fallback_spoken_for_intent(self, intent: str) -> str:
        intent = (intent or "GENERAL").upper()
        fillers = {
            "COARTADA": "Estaba en mi rutina cuando ocurrió; no oí nada fuera de lo normal.",
            "PRUEBAS": "Vi algo raro cerca de los camerinos, podría ayudar.",
            "MÓVIL": "No sé quién tendría razones claras.",
            "RELACIONES": "Las cosas estaban tensas, sí.",
            "LUGAR": "Todo pasó alrededor de la carpa principal.",
            "OBJETO": "Se hablaba de una cuerda y un pañuelo.",
            "GENERAL": "Puedo responder si concretas la pregunta.",
        }
        return fillers.get(intent, "Puedo responder si concretas la pregunta.")

    def _decide_policy(self, character: Dict[str, Any], intent: str) -> str:
        """Decide si el personaje mentirá, dirá la verdad o se mostrará evasivo."""
        killer = character.get("is_killer", False)
        base_truth = 0.85 if not killer else 0.45
        r = self.rnd.random()
        if r < base_truth:
            return "TRUTH"
        elif r < base_truth + 0.2:
            return "HEDGE"
        else:
            return "LIE"

    def _parse_meta(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Extrae el JSON de <META> y la línea de diálogo; limpia placeholders y asegura diálogo."""
        m = re.search(r"<META>(.*?)</META>\s*(.*)$", text.strip(), re.DOTALL)
        if not m:
            spoken = text.strip() or "Puedo responder si concretas la pregunta."
            return spoken, {
                "intent": "GENERAL",
                "truthful": False,
                "payload": "",
                "evasive": True,
                "said_before": False,
            }

        meta_raw = m.group(1).strip()
        spoken = (m.group(2) or "").strip()

        # Parseo robusto de meta
        try:
            meta = json.loads(meta_raw)
        except Exception:
            meta = {"intent": "GENERAL", "truthful": False, "payload": "", "evasive": True, "said_before": False}

        # Sanitizar payload (evitar placeholders / etiquetas)
        raw_payload = str(meta.get("payload") or "").strip()
        if (not raw_payload
            or re.search(r"[<>{}\[\]]", raw_payload)
            or "hecho/pista" in raw_payload.lower()
            or "pista si aplica" in raw_payload.lower()
            or raw_payload.lower() in {"n/a","na","none","sin pista","no aplica","no hay"}):
            meta["payload"] = ""

        # Limpiar placeholders/narración en spoken
        spoken = re.sub(r"[\{\[][^}\]]*[\}\]]", "", spoken).strip()

        # 🔒 Asegurar diálogo no vacío
        if not spoken:
            intent = str(meta.get("intent", "GENERAL"))
            spoken = self._fallback_spoken_for_intent(intent)

        if len(spoken) > 280:
            spoken = spoken[:278].rstrip() + "…"
        return spoken, meta


    # -----------------------------
    # API principal: generar diálogo
    # -----------------------------
    def generate(
        self,
        character: Dict[str, Any],
        question: str,
        game_state,
        quoted: Optional[Dict[str, Any]] = None,
        return_meta: bool = False,
    ):
        name = character["name"]

        if is_offtopic(question):
            response = f"{enforce_focus()}"
            meta = {
                "intent": "GENERAL",
                "truthful": True,
                "payload": "",
                "evasive": True,
                "said_before": False,
            }
            return (f"[{name}] (GENERAL) {response}", meta) if return_meta else f"[{name}] (GENERAL) {response}"

        intent = classify_intent(question)
        policy = self._decide_policy(character, intent)
        clue_guidance = ""

        prompt = PromptBuilder.build_dialog_prompt(
            character, question, intent, policy, game_state, quoted, clue_guidance
        )

        # ----------------------------
        # Si hay modelo HF conectado
        # ----------------------------
        if self.llm:
            try:
                raw = self.llm.generate(prompt)
                spoken, meta = self._parse_meta(raw)
                if not spoken.strip():
                    # cinturón y tirantes: jamás devolver vacío
                    spoken = self._fallback_spoken_for_intent(intent)
                line = f"[{name}] ({intent}) {spoken}"
                return (line, meta) if return_meta else line

            except Exception as e:
                # Fallback en caso de error del modelo
                fallback = f"No sé si eso importa ahora… ({str(e)[:40]})"
                meta = {"intent": intent, "truthful": False, "payload": "", "evasive": True, "said_before": False}
                return (f"[{name}] ({intent}) {fallback}", meta) if return_meta else f"[{name}] ({intent}) {fallback}"

        # ----------------------------
        # Fallback local (sin modelo)
        # ----------------------------
        sample_replies = {
            "COARTADA": "Estaba cerca del escenario, pero no vi nada extraño.",
            "PRUEBAS": "Había algo raro cerca de los camerinos, quizá te ayude.",
            "MÓVIL": "No entiendo quién querría dañar a Ñopin.",
            "RELACIONES": "Últimamente no nos hablábamos mucho, la tensión era evidente.",
            "GENERAL": "No estoy seguro de cómo responder eso.",
        }
        spoken = sample_replies.get(intent, "No sabría decirte.")
        meta = {"intent": intent, "truthful": True, "payload": spoken, "evasive": False, "said_before": False}
        return (f"[{name}] ({intent}) {spoken}", meta) if return_meta else f"[{name}] ({intent}) {spoken}"

    # ==================================================
    # 🔚 generate_ending: relato final del caso
    # ==================================================
    def generate_ending(self, game_state, accused: str, characters: Dict[str, Any]) -> str:
        rnd = self.rnd
        killer = game_state.killer
        suspects = game_state.suspects
        ev = list(dict.fromkeys(game_state.evidence_revealed))
        ev_sample = ev[:3] if ev else []

        def fmt_evs():
            if not ev_sample:
                return "sin pruebas claras"
            if len(ev_sample) == 1:
                return f"la clave fue '{ev_sample[0]}'"
            if len(ev_sample) == 2:
                return f"las pistas '{ev_sample[0]}' y '{ev_sample[1]}'"
            return f"las señales '{ev_sample[0]}', '{ev_sample[1]}' y '{ev_sample[2]}'"

        # Final correcto
        if accused == killer:
            frases = [
                "El telón cayó y la verdad salió a la luz.",
                "Nadie pudo negar lo evidente.",
                "La carpa entera contuvo el aliento cuando el culpable confesó.",
            ]
            return (
                f"{rnd.choice(frases)} {killer} no pudo sostener más su coartada. "
                f"{fmt_evs()} te condujeron hasta él. El circo volvió a respirar."
            )

        # Acusó a inocente
        if accused in suspects:
            frases = [
                "El silencio se apoderó del lugar.",
                "La tensión se deshizo en incredulidad.",
                "Por un momento, todos pensaron que el caso estaba cerrado.",
            ]
            return (
                f"{rnd.choice(frases)} Pero las piezas no encajaban. "
                f"{fmt_evs()} apuntaban a otro lado. "
                f"El asesino real era {killer}, que desapareció entre bastidores."
            )

        # Acusación inválida
        frases = [
            "El señalamiento fue confuso, como un truco mal ensayado.",
            "La carpa se llenó de murmullos, sin respuestas.",
        ]
        return (
            f"{rnd.choice(frases)} Nadie creyó esa versión. "
            f"{fmt_evs()} quedaron sin interpretar. "
            f"El asesino real era {killer}, y el misterio se desvaneció con el humo del espectáculo."
        )
