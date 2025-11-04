from dotenv import load_dotenv
from src.engine.router import run_cli

if __name__ == "__main__":
    load_dotenv()  # carga .env (MODO_DEBUG, MODEL_NAME, etc.)
    run_cli()
