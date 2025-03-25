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
        #print("Handedness: ", results.multi_handedness)
    
        if results.multi_hand_landmarks is not None:
            # Dibujo de las conexiones 
            for hand_landmark in results.multi_hand_landmarks:
                print(hand_landmark)
                mp_drawing.draw_landmarks(frame, hand_landmark, mp_hands.HAND_CONNECTIONS) 

        cv2.imshow("Capture", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break;

cap.release()
cv2.destroyAllWindows()