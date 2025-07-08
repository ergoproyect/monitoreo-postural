import freenect
import cv2
import mediapipe as mp
import numpy as np
import time
import csv
from datetime import datetime
import os

# === CONFIGURACIÓN ACTUALIZADA ===
INTERVALO_SEGUNDOS = 10
NUMERO_IMAGENES = 60
CARPETA_CAPTURAS = "capturas"
CSV_FILE = "posturas_oficina_corregido.csv"
CALIBRAR_ANGULOS = True

# Umbrales completamente revisados
UMBRALES_CABEZA = [10, 20]      # Inclinación lateral (grados)
UMBRALES_HOMBROS = [5, 15]      # Desnivel hombros (grados)
UMBRALES_ANTEBRAZOS = [70, 120] # Ángulo óptimo del codo (grados)
UMBRALES_ESPALDA = [10, 20]     # Inclinación espalda (grados)

# === MediaPipe ===
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# === FUNCIONES CORREGIDAS Y COMPLETAS ===
def capturar_kinect():
    """Captura frame del sensor Kinect"""
    frame, _ = freenect.sync_get_video()
    if frame is not None:
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return None

def punto_a_xy(landmark, shape):
    """Convierte landmarks de MediaPipe a coordenadas de imagen"""
    h, w = shape[0], shape[1]
    return np.array([landmark.x * w, landmark.y * h])

def calcular_angulo_cabeza_corregido(nariz, oreja_izq, oreja_der):
    """Calcula inclinación lateral de la cabeza respecto a la vertical"""
    # Vector entre orejas (eje horizontal de la cabeza)
    vector_cabeza = oreja_der - oreja_izq
    # Vector vertical perfecto
    vector_vertical = np.array([0, -1])
    # Calcular ángulo entre vector cabeza y vertical
    unit_vector_cabeza = vector_cabeza / np.linalg.norm(vector_cabeza)
    angulo = np.degrees(np.arccos(np.clip(np.dot(unit_vector_cabeza, vector_vertical), -1.0, 1.0)))
    return 90 - angulo  # Convertir a inclinación lateral

def calcular_angulo_hombros_corregido(hombro_izq, hombro_der):
    """Calcula desnivel entre hombros respecto a la horizontal"""
    # Diferencia vertical entre hombros
    diferencia_vertical = abs(hombro_der[1] - hombro_izq[1])
    # Distancia entre hombros
    distancia_hombros = np.linalg.norm(hombro_der - hombro_izq)
    # Calcular ángulo de desnivel
    return np.degrees(np.arcsin(diferencia_vertical / distancia_hombros))

def calcular_angulo_antebrazo_corregido(hombro, codo, muneca):
    """Calcula ángulo del codo (hombro-codo-muneca)"""
    # Vectores para cálculo del ángulo
    v1 = hombro - codo
    v2 = muneca - codo
    # Calcular ángulo
    cos_angulo = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    return np.degrees(np.arccos(np.clip(cos_angulo, -1.0, 1.0)))

def calcular_inclinacion_espalda_corregida(hombro, cadera):
    """Calcula inclinación de la espalda respecto a la vertical"""
    # Vector espalda (hombro a cadera)
    vector_espalda = cadera - hombro
    # Vector vertical perfecto
    vector_vertical = np.array([0, 1])
    # Calcular ángulo
    unit_espalda = vector_espalda / np.linalg.norm(vector_espalda)
    return np.degrees(np.arccos(np.clip(np.dot(unit_espalda, vector_vertical), -1.0, 1.0)))

def clasificar_segmento_corregido(angulo, umbrales, segmento):
    """Clasificación revisada con lógica específica por segmento"""
    if segmento == "cabeza":
        inclinacion = abs(angulo)
        if inclinacion < umbrales[0]:
            return 0, "Recta"
        elif inclinacion < umbrales[1]:
            return 1, "Leve"
        else:
            return 2, "Pronunciada"
    
    elif segmento == "hombros":
        desnivel = abs(angulo)
        if desnivel < umbrales[0]:
            return 0, "Nivelados"
        elif desnivel < umbrales[1]:
            return 1, "Leve"
        else:
            return 2, "Pronunciado"
    
    elif segmento == "antebrazos":
        if umbrales[0] <= angulo <= umbrales[1]:
            return 0, "Óptimo"
        elif 50 <= angulo < 70 or 120 < angulo <= 140:
            return 1, "Aceptable"
        else:
            return 2, "Forzado"
    
    elif segmento == "espalda":
        if angulo < umbrales[0]:
            return 0, "Recta"
        elif angulo < umbrales[1]:
            return 1, "Leve"
        else:
            return 2, "Inclinada"

def dibujar_angulo(frame, p1, p2, p3, angulo, color):
    """Dibuja ángulo en la imagen para visualización"""
    cv2.line(frame, tuple(p1.astype(int)), tuple(p2.astype(int)), color, 2)
    cv2.line(frame, tuple(p3.astype(int)), tuple(p2.astype(int)), color, 2)
    cv2.putText(frame, f"{angulo}°", tuple(p2.astype(int)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

# === BUCLE PRINCIPAL ACTUALIZADO ===
print("🔄 Iniciando sistema de análisis postural corregido...")

# Crear carpeta para capturas si no existe
if not os.path.exists(CARPETA_CAPTURAS):
    os.makedirs(CARPETA_CAPTURAS)

# Crear archivo CSV con cabeceras si no existe
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Fecha", "Hora", 
            "Angulo Cabeza", "Codigo Cabeza", 
            "Angulo Hombros", "Codigo Hombros", 
            "Angulo Antebrazos", "Codigo Antebrazos", 
            "Angulo Espalda", "Codigo Espalda", 
            "Categoria", "Recomendacion"
        ])

contador = 0

while True:
    try:
        frame = capturar_kinect()
        if frame is None:
            print("⚠️ No se pudo capturar imagen del Kinect")
            time.sleep(INTERVALO_SEGUNDOS)
            continue
            
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            shape = frame.shape
            lm = results.pose_landmarks.landmark

            puntos = {
                'nariz': punto_a_xy(lm[mp_pose.PoseLandmark.NOSE], shape),
                'oreja_izq': punto_a_xy(lm[mp_pose.PoseLandmark.LEFT_EAR], shape),
                'oreja_der': punto_a_xy(lm[mp_pose.PoseLandmark.RIGHT_EAR], shape),
                'hombro_izq': punto_a_xy(lm[mp_pose.PoseLandmark.LEFT_SHOULDER], shape),
                'hombro_der': punto_a_xy(lm[mp_pose.PoseLandmark.RIGHT_SHOULDER], shape),
                'codo_izq': punto_a_xy(lm[mp_pose.PoseLandmark.LEFT_ELBOW], shape),
                'muneca_izq': punto_a_xy(lm[mp_pose.PoseLandmark.LEFT_WRIST], shape),
                'cadera_izq': punto_a_xy(lm[mp_pose.PoseLandmark.LEFT_HIP], shape)
            }

            # Cálculos corregidos
            angulo_cabeza = calcular_angulo_cabeza_corregido(puntos['nariz'], puntos['oreja_izq'], puntos['oreja_der'])
            angulo_hombros = calcular_angulo_hombros_corregido(puntos['hombro_izq'], puntos['hombro_der'])
            angulo_antebrazos = calcular_angulo_antebrazo_corregido(puntos['hombro_izq'], puntos['codo_izq'], puntos['muneca_izq'])
            angulo_espalda = calcular_inclinacion_espalda_corregida(puntos['hombro_izq'], puntos['cadera_izq'])

            # Clasificación corregida
            cabeza_cod, cabeza_txt = clasificar_segmento_corregido(angulo_cabeza, UMBRALES_CABEZA, "cabeza")
            hombros_cod, hombros_txt = clasificar_segmento_corregido(angulo_hombros, UMBRALES_HOMBROS, "hombros")
            antebrazos_cod, antebrazos_txt = clasificar_segmento_corregido(angulo_antebrazos, UMBRALES_ANTEBRAZOS, "antebrazos")
            espalda_cod, espalda_txt = clasificar_segmento_corregido(angulo_espalda, UMBRALES_ESPALDA, "espalda")

            # Sistema de puntuación mejorado
            puntuacion = cabeza_cod + hombros_cod + antebrazos_cod + espalda_cod
            
            # Categorización flexible
            if puntuacion <= 1:
                categoria = 1
                recomendacion = "Postura excelente"
            elif puntuacion <= 3:
                categoria = 2
                recomendacion = "Postura aceptable"
            elif puntuacion <= 5:
                categoria = 3
                recomendacion = "Postura mejorable"
            else:
                categoria = 4
                recomendacion = "Postura incorrecta"

            # Visualización
            cv2.putText(frame, f"ANALISIS POSTURAL", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
            
            y_pos = 60
            for nombre, angulo, cod, txt in [
                ("Cabeza", angulo_cabeza, cabeza_cod, cabeza_txt),
                ("Hombros", angulo_hombros, hombros_cod, hombros_txt),
                ("Antebrazos", angulo_antebrazos, antebrazos_cod, antebrazos_txt),
                ("Espalda", angulo_espalda, espalda_cod, espalda_txt)
            ]:
                color = (0, 255, 0) if cod == 0 else (0, 255, 255) if cod == 1 else (0, 0, 255)
                cv2.putText(frame, f"{nombre}: {angulo}° ({txt})", (10, y_pos), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                y_pos += 25

            color_categoria = (0, 255, 0) if categoria == 1 else (0, 200, 255) if categoria == 2 else (0, 100, 255) if categoria == 3 else (0, 0, 255)
            cv2.putText(frame, f"RIESGO: Categoría {categoria}", (10, y_pos+10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_categoria, 2)
            cv2.putText(frame, recomendacion, (10, y_pos+40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_categoria, 1)

            # Dibujar ángulos
            dibujar_angulo(frame, puntos['nariz'], puntos['oreja_izq'], 
                          puntos['oreja_der'], angulo_cabeza, (0, 255, 255))
            dibujar_angulo(frame, puntos['hombro_izq'], puntos['hombro_der'], 
                          puntos['hombro_der'] + [100, 0], angulo_hombros, (255, 0, 255))
            dibujar_angulo(frame, puntos['hombro_izq'], puntos['codo_izq'], 
                          puntos['muneca_izq'], angulo_antebrazos, (255, 255, 0))
            dibujar_angulo(frame, puntos['hombro_izq'], puntos['cadera_izq'], 
                          puntos['cadera_izq'] + [0, 100], angulo_espalda, (0, 255, 0))

            # Guardar resultados
            nombre = f"captura_{contador:02d}.jpg"
            cv2.imwrite(os.path.join(CARPETA_CAPTURAS, nombre), frame)
            
            ahora = datetime.now()
            with open(CSV_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"),
                    angulo_cabeza, cabeza_cod,
                    angulo_hombros, hombros_cod,
                    angulo_antebrazos, antebrazos_cod,
                    angulo_espalda, espalda_cod,
                    categoria, recomendacion
                ])

            print(f"📊 {nombre} | Cabeza: {angulo_cabeza}°({cabeza_cod}) | Hombros: {angulo_hombros}°({hombros_cod}) | Antebrazos: {angulo_antebrazos}°({antebrazos_cod}) | Espalda: {angulo_espalda}°({espalda_cod}) | Cat: {categoria}")

        else:
            print("⚠️ Persona no detectada. Verifique posición frente al Kinect")

        contador = (contador + 1) % NUMERO_IMAGENES
        # Enviar datos a la API
        try:
            import requests
            api_url = "http://localhost:5000/api/posture"
            payload = {
                "head_angle": angulo_cabeza,
                "head_status": cabeza_txt,
                "head_code": cabeza_cod,
                "shoulders_angle": angulo_hombros,
                "shoulders_status": hombros_txt,
                "shoulders_code": hombros_cod,
                "arms_angle": angulo_antebrazos,
                "arms_status": antebrazos_txt,
                "arms_code": antebrazos_cod,
                "back_angle": angulo_espalda,
                "back_status": espalda_txt,
                "back_code": espalda_cod,
                "category": categoria,
                "recommendation": recomendacion
            }
            headers = {'Content-Type': 'application/json'}
            response = requests.post(api_url, json=payload, headers=headers)
        except Exception as e:
            print(f"⚠️ Error al enviar datos a la API: {e}")
        
        time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        print("\n🛑 Monitoreo detenido.")
        break
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        time.sleep(INTERVALO_SEGUNDOS)
