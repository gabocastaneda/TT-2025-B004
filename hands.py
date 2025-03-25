import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

cap = cv2.VideoCapture(0)

with mp_hands.Hands(
    static_image_mode = False,
    max_num_hands = 2) as hands:

    while cap.isOpened():
        ret, frame = cap.read()
        if ret is False:
            break

        height, width, _ = frame.shape
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = hands.process(frame_rgb)

        # HANDEDNESS
        if results.multi_hand_landmarks and results.multi_handedness:
            for idx, hand_landmark in enumerate(results.multi_hand_landmarks):
                # Identificar la mano
                hand_label = results.multi_handedness[idx].classification[0].label  # 'Left' o 'Right'
    
        if results.multi_hand_landmarks is not None:

            # Guardar coordenadas
            puntos_mano = []
            for punto in hand_landmark.landmark:
                x = int(punto.x * width)
                y = int(punto.y * height)
                z = punto.z
                puntos_mano.append((x, y, z))
                
            # Imprimir coordenadas con etiqueta
            print(f"Mano {hand_label}:")
            for i, (x, y, z) in enumerate(puntos_mano):
                print(f"  Punto {i}: x={x}, y={y}, z={z:.4f}")
            
            # Dibujo de las conexiones 
            for hand_landmark in results.multi_hand_landmarks:
                # print(hand_landmark)
                mp_drawing.draw_landmarks(frame, hand_landmark, mp_hands.HAND_CONNECTIONS) 

        cv2.imshow("Capture", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break;

cap.release()
cv2.destroyAllWindows()