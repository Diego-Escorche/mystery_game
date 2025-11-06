from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import random
import yaml
import os

# Usamos la configuración estándar: templates/ para HTML y static/ para CSS/JS
app = Flask(__name__)
CORS(app)

# --- Cargar datos de YAML ---
def load_suspect_data():
    try:
        # Asume que datos.yaml está en la misma carpeta que app.py
        with open('datos.yaml', 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            suspects = {}
            # Convertimos la lista de YAML a un diccionario indexado por ID
            for item in data.get('suspects', []):
                suspects[item['id']] = item
            return suspects
    except FileNotFoundError:
        print("Error: datos.yaml no encontrado.")
        return {}
    except yaml.YAMLError as e:
        print(f"Error al parsear datos.yaml: {e}")
        return {}

suspects_data = load_suspect_data()

# 🚨 DEFINICIÓN DEL ASESINO REAL
# Basado en la historia del circo, estableceremos al ID 6 (La Pitonisa) como el culpable
# Si tu YAML tiene otro ID, ajústalo.
TRUE_KILLER_ID = 6 

# --- RUTAS DE LA API ---

@app.route('/')
def index():
    """Sirve el archivo HTML principal (index.html) desde la carpeta 'templates'."""
    # Nota: El HTML debe estar en una carpeta 'templates'
    return render_template('index.html')

@app.route('/api/question', methods=['POST'])
def handle_question():
    """Endpoint para manejar preguntas al sospechoso."""
    data = request.json
    suspect_id_str = data.get('suspect_id')
    question = data.get('question', '').lower()
    
    try:
        suspect_id = int(suspect_id_str)
    except (ValueError, TypeError):
        return jsonify({"error": "ID de sospechoso inválido"}), 400

    if suspect_id not in suspects_data:
        return jsonify({"error": "Sospechoso no encontrado"}), 404
    
    suspect = suspects_data[suspect_id]
    
    # Lógica de respuesta (mejorada para el nuevo formato YAML)
    responses = suspect.get('responses', {})
    
    for keyword, response_text in responses.get('keywords', {}).items():
        if keyword.lower() in question:
            return jsonify({
                "suspect_id": suspect_id,
                "suspect_name": suspect['name'],
                "response": response_text
            })
    
    # Respuesta por defecto aleatoria
    default_list = responses.get('default', [])
    default_response = random.choice(default_list) if default_list else "..."
    
    return jsonify({
        "suspect_id": suspect_id,
        "suspect_name": suspect['name'],
        "response": default_response
    })

@app.route('/api/suspects', methods=['GET'])
def get_suspects():
    """Endpoint para obtener lista de sospechosos (sin el secreto de 'isKiller')."""
    suspects_list = []
    for suspect_id, suspect in suspects_data.items():
        suspects_list.append({
            "id": suspect_id,
            "name": suspect['name'],
            "role": suspect['role'],
            "personality": suspect['personality']
            # No enviamos 'isKiller' real al frontend
        })
    return jsonify(suspects_list)

@app.route('/api/accuse', methods=['POST'])
def handle_accusation():
    """Endpoint para manejar la acusación final."""
    data = request.json
    accused_id_str = data.get('accused_id')

    try:
        accused_id = int(accused_id_str)
    except (ValueError, TypeError):
        return jsonify({"error": "ID de acusado inválido"}), 400

    if accused_id not in suspects_data:
        return jsonify({"error": "Sospechoso no encontrado"}), 404

    accused = suspects_data[accused_id]
    
    is_correct = accused_id == TRUE_KILLER_ID
    
    # Mensajes de resolución del caso
    resolution_message = ""
    if is_correct:
        resolution_message = f"¡Correcto! {accused['name']} es el asesino. Se derrumba bajo la presión del interrogatorio y confiesa."
    else:
        killer_name = suspects_data[TRUE_KILLER_ID]['name']
        resolution_message = f"¡Error! {accused['name']} es inocente. Mientras tú lo acusabas, el verdadero culpable, {killer_name}, escapó en la oscuridad."


    return jsonify({
        "accused_name": accused['name'],
        "is_correct": is_correct,
        "resolution": resolution_message,
        "true_killer_name": suspects_data[TRUE_KILLER_ID]['name']
    })

if __name__ == '__main__':
    # Usamos host='0.0.0.0' para que sea accesible en el entorno del contenedor
    app.run(host='0.0.0.0', port=5000, debug=True)
