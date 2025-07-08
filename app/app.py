# app.py
from flask import Flask, request, jsonify, render_template
import threading
import time
import json
from datetime import datetime

app = Flask(__name__)

# Datos posturales globales
posture_data = {
    "head": {"angle": 0, "status": "", "code": 0},
    "shoulders": {"angle": 0, "status": "", "code": 0},
    "arms": {"angle": 0, "status": "", "code": 0},
    "back": {"angle": 0, "status": "", "code": 0},
    "category": 0,
    "recommendation": "",
    "timestamp": ""
}

# Ruta para la interfaz gráfica
@app.route('/')
def dashboard():
    return render_template('dashboard.html', data=posture_data)

# API para recibir datos del script de análisis
@app.route('/api/posture', methods=['POST'])
def update_posture():
    global posture_data
    data = request.json
    
    # Actualizar datos
    posture_data = {
        "head": {
            "angle": data['head_angle'],
            "status": data['head_status'],
            "code": data['head_code']
        },
        "shoulders": {
            "angle": data['shoulders_angle'],
            "status": data['shoulders_status'],
            "code": data['shoulders_code']
        },
        "arms": {
            "angle": data['arms_angle'],
            "status": data['arms_status'],
            "code": data['arms_code']
        },
        "back": {
            "angle": data['back_angle'],
            "status": data['back_status'],
            "code": data['back_code']
        },
        "category": data['category'],
        "recommendation": data['recommendation'],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return jsonify({"status": "success"})

# Ejecutar el servidor Flask
def run_flask_app():
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    # Iniciar el servidor Flask en un hilo separado
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Servidor API y dashboard iniciado en http://localhost:5000")
    
    # Mantener el script en ejecución
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServidor detenido")
