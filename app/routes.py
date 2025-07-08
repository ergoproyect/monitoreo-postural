from app import app
from flask import render_template
from datetime import datetime
import json

# Datos de ejemplo (serán reemplazados por tu lógica)
posture_data = {
    "head": {"angle": 0, "status": "", "code": 0},
    "shoulders": {"angle": 0, "status": "", "code": 0},
    "arms": {"angle": 0, "status": "", "code": 0},
    "back": {"angle": 0, "status": "", "code": 0},
    "category": 0,
    "recommendation": "",
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

@app.route('/')
def dashboard():
    return render_template('dashboard.html', data=posture_data)

@app.route('/api/posture', methods=['POST'])
def update_posture():
    global posture_data
    data = request.json
    
    posture_data = {
        "head": {
            "angle": data.get('head_angle', 0),
            "status": data.get('head_status', ''),
            "code": data.get('head_code', 0)
        },
        # ... (completa con los demás campos)
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return jsonify({"status": "success"})
