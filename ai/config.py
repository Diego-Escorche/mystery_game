import os

MODEL_ID = os.getenv("MODEL_ID", "HuggingFaceTB/SmolLM3-3B")
DEVICE_MAP = os.getenv("DEVICE_MAP", "auto")   # "auto" o "cpu"
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "140"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
TOP_K = int(os.getenv("TOP_K", "40"))
USE_STUB = os.getenv("USE_STUB", "0") == "1"    # Forzar stub si hace falta
