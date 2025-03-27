import cv2
import mediapipe as mp
import numpy as np


mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

cap = cv2.VideoCapture(0)

trayectoria_derecha = []
trayectoria_izquierda = []

with mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.80,
    min_tracking_confidence=0.5) as hands:

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        height, width, _ = frame.shape
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

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

        cv2.imshow("Capture", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()

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

        #for punto in puntos_recentrados:
          #  cv2.circle(pizarron, punto, 4, (0, 0, 255), -1)

        pizarron = cv2.resize(pizarron, (600,600)) 
        cv2.imshow(nombre, pizarron)
        print(f"{nombre}: {len(puntos_recentrados)} puntos dibujados.")
    else:
        # Pizarrón vacío si no hubo trayectoria
        pizarron = 255 * np.ones((300, 300, 3), dtype=np.uint8)
        pizarron = cv2.resize(pizarron, (600,600)) 
        # cv2.putText(pizarron, "Sin datos", (80, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (128, 128, 128), 2)
        cv2.imshow(nombre, pizarron)
        print(f"{nombre}: sin trayectoria.")

    return pizarron

# Mostrar pizarrones
derecha = crear_pizarron(trayectoria_derecha, "Pizarron derecha")
izquierda = crear_pizarron(trayectoria_izquierda, "Pizarron izquierda")
    
def pizarron_arreglo(pizarron):
    imagen_arreglo = np.asarray(pizarron)
    return imagen_arreglo

print(f'Pizarron derecha ({len(pizarron_arreglo(derecha))}): ', pizarron_arreglo(derecha))
print(f'Pizarron izquierda ({len(pizarron_arreglo(izquierda))}): ', pizarron_arreglo(izquierda))


cv2.waitKey(0)
cv2.destroyAllWindows()