from typing import Optional
import os
import re
import json

from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM


class HFSmolLMBackend:
    """
    Backend real usando HuggingFaceTB/SmolLM3-3B (o variante).
    Debe devolver SIEMPRE:
      <META>{...}</META>
      línea de diálogo
    Si el modelo no respeta el formato, se intenta reparar.
    """

    def __init__(
        self,
        model_id: str = "HuggingFaceTB/SmolLM3-3B",
        max_new_tokens: int = 96,
        temperature: float = 0.8,
        top_p: float = 0.95,
        repetition_penalty: float = 1.05,
        use_fast: bool = True,
        trust_remote_code: bool = True,
    ):
        self.model_id = os.environ.get("HF_MODEL_ID", model_id)

        # Carga con device_map="auto" (NO pasar device explícito si usás accelerate)
        # Para CPU puro también funciona, sólo será más lento.
        self.pipe = pipeline(
            "text-generation",
            model=self.model_id,
            tokenizer=self.model_id,
            device_map="auto",
            trust_remote_code=trust_remote_code,
        )
        self.gen_kwargs = {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "do_sample": True,
            # “stop” heurísticos para acortar donde toca:
            "eos_token_id": self.pipe.tokenizer.eos_token_id,
        }

    # ---------- Reparadores de salida ----------
    _meta_re = re.compile(r"<META>(.*?)</META>\s*(.*)$", re.DOTALL)

    def _ensure_meta_and_line(self, text: str) -> str:
        """
        Si no viene <META>..., lo crea con defaults y toma la última línea no vacía como diálogo.
        """
        m = self._meta_re.search(text.strip())
        if m:
            # ya está en formato
            return f"<META>{m.group(1).strip()}</META>\n{m.group(2).strip()}"

        # Fallback: generar un META mínimo y tomar el texto como línea
        line = text.strip().splitlines()[-1].strip() if text.strip() else "No tengo más que añadir."
        meta = {
            "intent": "GENERAL",
            "truthful": False,
            "payload": "",
            "evasive": True,
            "said_before": False,
        }
        return f"<META>{json.dumps(meta, ensure_ascii=False)}</META>\n{line}"

    # ---------- Interfaz esperada por AIModelAdapter ----------
    def generate(self, prompt: str) -> str:
        out = self.pipe(prompt, **self.gen_kwargs)[0]["generated_text"]

        # Recortar a lo generado tras el último marcador del prompt
        cut_markers = ["[OUTPUT FORMAT]", "[FORMAT]"]
        last_pos = -1
        for mk in cut_markers:
            p = out.rfind(mk)
            if p > last_pos:
                last_pos = p
        if last_pos != -1:
            out = out[last_pos:]

        # Asegurar META y 2 líneas máximo
        out = self._ensure_meta_and_line(out)

        # Forzar a UNA línea de diálogo (segunda línea) y sin llaves marcadoras
        meta_match = self._meta_re.search(out)
        if meta_match:
            meta = meta_match.group(1).strip()
            rest = meta_match.group(2).strip()
            # tomar solo la primera línea del resto
            first_line = rest.splitlines()[0].strip()
            # limpiar placeholders comunes
            first_line = re.sub(r"\{[^}]*\}", "", first_line).strip()
            # limitar longitud para evitar narraciones largas
            if len(first_line) > 280:
                first_line = first_line[:278].rstrip() + "…"
            return f"<META>{meta}</META>\n{first_line}"

        return out
