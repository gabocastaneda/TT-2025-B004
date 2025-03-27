import cv2
import mediapipe as mp
import numpy as np

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Abre el video de entrada
input_video = 'D:/TT/video_entrada.mp4'
cap = cv2.VideoCapture(input_video)

# Verificar si se abrió correctamente el video
if not cap.isOpened():
    print("Error al abrir el video.")
    exit()

# Obtener las propiedades del video (tamaño de los frames y tasa de fotogramas)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

# Inicializar el escritor de video para guardar el resultado
output_video = 'D:/TT/video_salida.mp4'
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec para MP4
out = cv2.VideoWriter(output_video, fourcc, fps, (frame_width, frame_height))

trayectoria_derecha = []
trayectoria_izquierda = []

with mp_hands.Hands(
    static_image_mode=False,  # Para procesar video
    max_num_hands=2,  # Detectar hasta 2 manos
    min_detection_confidence=0.8,
    min_tracking_confidence=0.5) as hands:

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (600, 600))

        # Voltear el frame una vez para simular un efecto de espejo
        frame = cv2.flip(frame, 1)  # Voltear horizontalmente una sola vez

        height, width, _ = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convertir a RGB

        results = hands.process(frame_rgb)

        # HANDEDNESS
        print(results.multi_handedness)

        if results.multi_hand_landmarks and results.multi_handedness:
            for idx, hand_landmark in enumerate(results.multi_hand_landmarks):
                hand_label = results.multi_handedness[idx].classification[0].label  # 'Left' o 'Right'

                puntos = [(int(p.x * width), int(p.y * height), p.z) for p in hand_landmark.landmark]

                x_centro = int(sum(p[0] for p in puntos) / len(puntos))
                y_centro = int(sum(p[1] for p in puntos) / len(puntos))
                centro = (x_centro, y_centro)

                if hand_label == "Right":
                    trayectoria_derecha.append(centro)
                elif hand_label == "Left":
                    trayectoria_izquierda.append(centro)

                mp_drawing.draw_landmarks(frame, hand_landmark, mp_hands.HAND_CONNECTIONS)
                cv2.circle(frame, centro, 5, (0, 0, 255), -1)
                cv2.putText(frame, f'Centro {hand_label}', (x_centro + 10, y_centro),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Escribir el frame procesado en el archivo de salida
        out.write(frame)

        cv2.imshow("Capture", frame)

        if cv2.waitKey(1) & 0xFF == 27:  # Salir si presionas 'Esc'
            break

cap.release()
out.release()
cv2.destroyAllWindows()

# Función para crear el pizarrón de la trayectoria
def crear_pizarron(trayectoria, nombre):
    if trayectoria:
        xs = [p[0] for p in trayectoria]
        ys = [p[1] for p in trayectoria]

        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        ancho = x_max - x_min + 20
        alto = y_max - y_min + 20

        pizarron = 255 * np.ones((alto, ancho, 3), dtype=np.uint8)
        puntos_recentrados = [((x - x_min + 10), (y - y_min + 10)) for (x, y) in trayectoria]

        for i in range(1, len(puntos_recentrados)):
            pt1 = puntos_recentrados[i - 1]
            pt2 = puntos_recentrados[i]
            cv2.line(pizarron, pt1, pt2, (0, 0, 0), 2)

        pizarron = cv2.resize(pizarron, (600, 600)) 
        cv2.imshow(nombre, pizarron)
        print(f"{nombre}: {len(puntos_recentrados)} puntos dibujados.")
    else:
        pizarron = 255 * np.ones((300, 300, 3), dtype=np.uint8)
        pizarron = cv2.resize(pizarron, (600, 600))
        cv2.imshow(nombre, pizarron)
        print(f"{nombre}: sin trayectoria.")

    return pizarron

# Mostrar los pizarrones de las trayectorias
derecha = crear_pizarron(trayectoria_derecha, "Pizarron derecha")
izquierda = crear_pizarron(trayectoria_izquierda, "Pizarron izquierda")

cv2.waitKey(0)
cv2.destroyAllWindows()

print("Trayectoria mano derecha: ", trayectoria_derecha)
print("Trayectoria mano izquierda: ", trayectoria_izquierda)

def pizarron_arreglo(pizarron):
    imagen_arreglo = np.asarray(pizarron)
    return imagen_arreglo

print(f'Pizarron derecha ({len(pizarron_arreglo(derecha))}): ', pizarron_arreglo(derecha))
print(f'Pizarron izquierda ({len(pizarron_arreglo(izquierda))}): ', pizarron_arreglo(izquierda))