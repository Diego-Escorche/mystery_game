# Mystery Game — Circo en el Desierto (CLI)

Un juego de misterio en **3 fases** (Inicio → Desarrollo → Conclusión) ambientado en un circo en medio del desierto.
Incluye **sospechoso aleatorio** (incluso Canelitas), **interrogatorios con memoria social**, **evidencias reales y ambiguas**,
y un **modelo de diálogo** con guardrails para evitar desvíos del caso.

### 🧠 Memoria por personaje

Cada sospechoso conserva:

- Q/A recientes (para coherencia tipo “ya lo dije…”),
- hechos declarados por intent,
- quién lo acusó/apoyó (y a quién acusó/apoyó),
- conteo de evasivas.

Esto modula la presión y la probabilidad de mentir/decir verdad, y se incluye en el prompt del LLM.

## ⚙️ Instalación rápida (con SmolLM3-3B)

1. Python 3.10+ y (opcional) venv
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Cómo ejecutar

1. Asegúrate de tener Python 3.10+.
2. (Opcional) Crea un entorno virtual.
3. Ejecuta desde la carpeta del proyecto:
   ```bash
   python main.py
   ```
