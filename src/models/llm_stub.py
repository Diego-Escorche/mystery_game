import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import textwrap

class SmolLMStub:
    """
    Implementación real del stub usando el modelo SmolLM3-3B local de Hugging Face.
    Usa el formato de chat del modelo para mantener el contexto narrativo.
    """

    def __init__(self, state):
        self.state = state
        self.model_name = "HuggingFaceTB/SmolLM3-3B"
        self.device = "cpu" if os.getenv("FORCE_CPU") else ("cuda" if torch.cuda.is_available() else "cpu")

        print(f"Cargando modelo {self.model_name} en {self.device}... puede tardar un poco.")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name).to(self.device)

    def _generate_text(self, messages: list[str]) -> str:
        """Genera texto usando el formato de chat nativo del modelo."""
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer([text], return_tensors="pt").to(self.device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=500,
                temperature=0.9,
                top_p=0.9,
            )

        # Tomamos solo el nuevo texto generado
        output_ids = generated_ids[0][len(inputs.input_ids[0]):]
        return self.tokenizer.decode(output_ids, skip_special_tokens=True).strip()

    def generate(self, prompt: str, character: str = None) -> str:
        """
        Envía el prompt completo al modelo SmolLM3-3B.
        Usa el formato de conversación para que el modelo adopte el rol del personaje.
        """
        user_message = {"role": "user", "content": prompt}
        messages = [
            {"role": "system", "content": "Responde como si fueras un personaje del Circo de la Medianoche. Sé coherente con tu personalidad y el escenario."},
            user_message,
        ]
        output = self._generate_text(messages)
        return textwrap.shorten(output, width=600, placeholder="…")

    def generate_ending(self, actual_killer: str, accused: str) -> str:
        """
        Genera un final narrativo dinámico según el escenario y si el jugador acierta o no.
        """
        good = (actual_killer == accused)
        scen = self.state.active_scenario

        # === cierres base por escenario ===
        scenario_endings = {
            "S1_SilvanaAsesina": {
                "good": (
                    "Silvana baja la mirada, la cuerda aún manchada de polvo entre sus manos. "
                    "Las luces del circo se apagan una a una mientras los artistas guardan silencio. "
                    "Por fin, el público invisible que todos temían se desvanece: la verdad está suspendida en el aire, como su último salto."
                ),
                "bad": (
                    "Silvana llora en silencio al verte marchar. Las sogas cuelgan, inertes, como testigos mudos. "
                    "El verdadero culpable se escapa entre sombras, y el circo retoma su función, ahora un poco más vacío."
                )
            },
            "S2_SeraphineAsesina": {
                "good": (
                    "Madame Seraphine se descompone; su mirada pierde el brillo místico. "
                    "Entre lágrimas murmura que solo quiso proteger a Silvana. "
                    "Las velas se apagan solas, y el incienso deja un aroma agrio: el precio de la compasión."
                ),
                "bad": (
                    "Madame Seraphine enciende un último incienso antes de que partas. "
                    "Dice una oración por Ñopin... y por ti. El humo cubre sus labios mientras su sonrisa permanece intacta. "
                    "El verdadero asesino sonríe detrás del velo."
                )
            },
            "S3_JackAsesino": {
                "good": (
                    "Jack no opone resistencia. Camina hacia las jaulas y deja que las fieras lo observen en silencio. "
                    "‘Al menos no mintieron mis bestias’, dice antes de entregarse. "
                    "El rugido final marca el cierre de la función más peligrosa de su vida."
                ),
                "bad": (
                    "Las fieras rugen cuando te marchas. Jack te despide con una sonrisa que no sabes si es alivio o burla. "
                    "Esa noche, otra copa se derrama en la arena y el veneno vuelve a correr."
                )
            },
            "S4_MefistoAsesino": {
                "good": (
                    "Mefisto ríe, incluso cuando lo detienen. ‘El show debe continuar’, susurra, mientras el maquillaje se le corre con el sudor. "
                    "El circo queda vacío, y por primera vez nadie aplaude. El payaso sin público ha contado su último chiste."
                ),
                "bad": (
                    "Mefisto te despide con un guiño. Las risas resuenan en las carpas vacías y el eco parece decir tu nombre. "
                    "Esa noche, el circo vuelve a abrir sus puertas. Pero tú ya sabes que la risa no siempre viene del escenario."
                )
            },
            "S5_NyopinSuicidio": {
                "good": (
                    "No hubo asesino. Solo un hombre cansado de su propio espectáculo. "
                    "Ñopin dejó su última carta en blanco, como si quisiera que tú escribieras el final. "
                    "El circo se disuelve con la primera luz del amanecer."
                ),
                "bad": (
                    "Has acusado a un inocente. Mientras el eco de tus pasos se pierde, el viento arrastra una carta sin firma. "
                    "Tal vez Ñopin quiso morir, o tal vez quiso probar tu juicio. Nadie lo sabrá jamás."
                )
            }
        }

        selected = scenario_endings.get(scen, {})
        ending_text = selected.get("good" if good else "bad", "")

        # agregamos toque narrativo del modelo para darle estilo final
        tone = "justiciero" if good else "melancólico"
        model_prompt = (
            f"Reescribe este cierre en tono {tone} y cinematográfico, "
            "añadiendo una última línea poética. "
            f"Cierre base: {ending_text}"
        )

        messages = [{"role": "user", "content": model_prompt}]
        return self._generate_text(messages)

