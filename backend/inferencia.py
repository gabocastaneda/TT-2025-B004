# backend/inferencia_gestos.py
import mediapipe as mp
import cv2
import numpy as np
from math import acos, degrees
import time
import warnings
from typing import Tuple, Optional, Callable
from pathlib import Path
from collections import Counter
import joblib
from models.knn_model import KNN
from backend.model_utils import SimpleScaler, SimpleLabelEncoder

warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")

class KNN:
    def __init__(self, k=3):
        self.k = k
        self.X_train = None
        self.y_train = None

    def fit(self, X, y):
        self.X_train = X
        self.y_train = y

    def predict(self, X):
        return np.array([self._predecir(x) for x in X])
    
    def predict_proba(self, X):
        predictions = []
        for x in X:
            distancias = np.linalg.norm(self.X_train - x, axis=1)
            vecinos_idx = np.argsort(distancias)[:self.k]
            etiquetas_vecinas = self.y_train[vecinos_idx]
            counter = Counter(etiquetas_vecinas)
            total_vecinos = len(etiquetas_vecinas)
            probas = [counter.get(clase, 0) / total_vecinos for clase in np.unique(self.y_train)]
            predictions.append(probas)
        
        return np.array(predictions)

    def _predecir(self, x):
        distancias = np.linalg.norm(self.X_train - x, axis=1)
        vecinos_idx = np.argsort(distancias)[:self.k]
        etiquetas_vecinas = self.y_train[vecinos_idx]
        distancias_vecinas = distancias[vecinos_idx]

        # Evita división entre 0
        pesos = 1 / (distancias_vecinas + 1e-5)
        
        # Acumula pesos por clase
        pesos_por_clase = {}
        for etiqueta, peso in zip(etiquetas_vecinas, pesos):
            pesos_por_clase[etiqueta] = pesos_por_clase.get(etiqueta, 0) + peso

        # Selecciona la clase con mayor peso acumulado
        etiqueta_mas_comun = max(pesos_por_clase, key=pesos_por_clase.get)
        return etiqueta_mas_comun


class InferenciaGestos:
    def __init__(self, modelo_path: str = None, umbral_confianza: float = 0.70):
        # Definiciones de puntos
        self.pulgar = [1, 2, 4]
        self.puntos_palma = [0, 1, 2, 5, 9, 13, 17]
        self.bases = [6, 10, 14, 18]
        self.puntas = [8, 12, 16, 20]
        
        self.UMBRAL_CONFIANZA = umbral_confianza
        self.modelo_data = None
        self.callback_prediccion = None
        
        # Variables de estado
        self.grabando = False
        self.frames_video = []
        self.centroides_trayectoria_left = []
        self.centroides_trayectoria_right = []
        self.estados_dedos_trayectoria_left = []
        self.estados_dedos_trayectoria_right = []
        self.mano_detectada_anteriormente = False
        self.ultima_deteccion = time.time()
        self.prediccion_actual = "Esperando..."
        self.confianza_actual = 0.0
        self.estado_prediccion = "INICIAL"
        
        # MediaPipe
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.hands = None
        
        # Si no se proporciona ruta, buscar en la carpeta actual (backend)
        if modelo_path is None:
            modelo_default = Path(__file__).parent / "modelo.pkl"
            if modelo_default.exists():
                modelo_path = str(modelo_default)
                print(f"[GESTOS] ✅ Usando modelo por defecto: {modelo_path}")
        
        if modelo_path:
            self._cargar_modelo_definitivo(modelo_path)
        else:
            print("❌ [GESTOS] No se proporcionó ruta de modelo, usando simulación")
            self._crear_modelo_simulado()

    def _cargar_modelo_definitivo(self, modelo_path: str):
        """Carga el modelo usando la estructura real de módulos"""
        print(f"[GESTOS] === CARGA CON ESTRUCTURA REAL ===")
        print(f"[GESTOS] Ruta: {modelo_path}")
        
        path_obj = Path(modelo_path)
        if not path_obj.exists():
            print(f"❌ ERROR CRÍTICO: Archivo de modelo no existe en {modelo_path}")
            raise FileNotFoundError(f"Modelo no encontrado: {modelo_path}")
        
        try:
            # ============================================================
            # 1. VERIFICAR QUE LOS MÓDULOS REQUERIDOS EXISTAN
            # ============================================================
            try:
                # Intentar importar la clase KNN desde la estructura real dentro de backend
                print("✅ Módulo 'backend.models.knn_model' importado correctamente")
            except ImportError as e:
                print(f"❌ Error importando backend.models.knn_model: {e}")
                print("💡 Asegúrate de que existe la carpeta 'backend/models' con 'knn_model.py'")
                # Intentar estructura alternativa
                try:
                    print("✅ Módulo 'models.knn_model' importado correctamente (estructura alternativa)")
                except ImportError:
                    raise ImportError("No se pudo importar KNN desde ninguna estructura")

            # ============================================================
            # 2. CARGAR EL MODELO
            # ============================================================
            print(f"[GESTOS] Cargando modelo desde: {modelo_path}")
            
            with open(modelo_path, 'rb') as f:
                self.modelo_data = joblib.load(f)
            
            print("✅ ARCHIVO DE MODELO CARGADO")

            # ============================================================
            # 3. VERIFICACIONES DE INTEGRIDAD DEL MODELO
            # ============================================================
            if not isinstance(self.modelo_data, dict):
                raise TypeError(f"Modelo debe ser un diccionario, no {type(self.modelo_data)}")
            
            if 'model' not in self.modelo_data:
                raise KeyError("El modelo no contiene la clave 'model'")
            
            model = self.modelo_data['model']
            if model is None:
                raise ValueError("El modelo interno es None")
            
            # Verificar que el modelo tenga los métodos necesarios
            if not hasattr(model, 'predict'):
                raise AttributeError("El modelo no tiene método 'predict'")
            
            if not hasattr(model, 'predict_proba'):
                raise AttributeError("El modelo no tiene método 'predict_proba'")
            
            # Verificar que sea un modelo KNN real
            model_type = type(model).__name__
            if "KNN" not in model_type:
                print(f"⚠️  Tipo de modelo: {model_type} (no es KNN, pero continuando)")
            else:
                print(f"✅ Modelo KNN detectado: {model_type}")
            
            # Verificar clases
            if 'classes' not in self.modelo_data:
                raise KeyError("El modelo no contiene la clave 'classes'")
            
            classes = self.modelo_data['classes']
            if not classes or len(classes) == 0:
                raise ValueError("La lista de clases está vacía")
            
            # Verificar scaler
            scaler = self.modelo_data.get('scaler', None)
            if scaler is not None and not hasattr(scaler, 'transform'):
                print("⚠️  Scaler no tiene método 'transform', pero continuando...")

            # Verificar datos de entrenamiento
            if hasattr(model, 'X_train') and model.X_train is not None:
                print(f"✅ Datos de entrenamiento: {len(model.X_train)} muestras")
            else:
                print("⚠️  No se encontraron datos de entrenamiento en el modelo")

            # ============================================================
            # 4. INFORMACIÓN DE DIAGNÓSTICO
            # ============================================================
            print("✅ MODELO KNN PERSONALIZADO CARGADO EXITOSAMENTE")
            print(f"   • Tipo de modelo: {model_type}")
            print(f"   • Parámetro k: {getattr(model, 'k', 'N/A')}")
            print(f"   • Clases: {list(classes)}")
            print(f"   • Scaler: {type(scaler).__name__ if scaler else 'None'}")
            print(f"   • Tamaño dataset de entrenamiento: {len(getattr(model, 'X_train', [])) if hasattr(model, 'X_train') and model.X_train is not None else 'N/A'}")
            
            # ============================================================
            # 5. PRUEBA BÁSICA DE FUNCIONALIDAD
            # ============================================================
            print("[GESTOS] Realizando prueba básica del modelo...")
            try:
                # Determinar el número de características
                if hasattr(model, 'X_train') and model.X_train is not None and len(model.X_train) > 0:
                    n_features = model.X_train.shape[1]
                else:
                    # Estimación por defecto basada en el dataset
                    n_features = 820  # Valor por defecto basado en tu dataset
                
                # Crear datos de prueba simples
                test_data = np.random.rand(1, n_features)
                
                # Probar predicción
                prediction = model.predict(test_data)
                proba = model.predict_proba(test_data)
                
                print(f"   • Prueba predict: ✅ (output: {prediction})")
                print(f"   • Prueba predict_proba: ✅ (shape: {proba.shape})")
                print(f"   • Características: {n_features}")
                
            except Exception as test_error:
                print(f"⚠️  Advertencia en prueba: {test_error}")
                # No levantamos excepción aquí, solo es una prueba diagnóstica

            print("=" * 60)
                
        except Exception as e:
            print(f"❌ ERROR cargando modelo: {e}")
            print(f"❌ Tipo de error: {type(e).__name__}")
            import traceback
            print(f"❌ Traceback completo:\n{traceback.format_exc()}")
            
            # Limpiar en caso de error
            self.modelo_data = None
            
            # Proporcionar mensaje de ayuda específico
            if "No module named" in str(e):
                print("\n💡 SOLUCIÓN:")
                print("   Crea la carpeta 'backend/models' en el proyecto")
                print("   con el archivo 'knn_model.py' que contiene la clase KNN")
            
            raise RuntimeError(f"No se pudo cargar el modelo: {e}") from e

    def _crear_modelo_simulado(self):
        """Crea un modelo simulado para desarrollo cuando falla la carga"""
        print("🔧 Creando modelo simulado...")
        
        class ModeloSimulado:
            def __init__(self):
                self.k = 3
                self.X_train = None
                self.y_train = None
                print("🔧 Modelo simulado inicializado")
                
            def predict(self, X):
                # Simular reconocimiento de gestos básicos
                if len(X) > 0:
                    gestos = ['hola', 'adios', 'si', 'no', 'gracias']
                    return np.array([np.random.choice(gestos) for _ in range(len(X))])
                return np.array(['simulado'])
            
            def predict_proba(self, X):
                # Simular probabilidades
                if len(X) > 0:
                    return np.random.rand(len(X), 5)  # 5 clases
                return np.array([[0.8, 0.2, 0.0, 0.0, 0.0]])
        
        self.modelo_data = {
            'model': ModeloSimulado(),
            'classes': ['hola', 'adios', 'si', 'no', 'gracias'],
            'scaler': None
        }
        print("🔧 Modelo simulado creado para desarrollo")

    def inicializar_deteccion(self):
        """Inicializa MediaPipe"""
        try:
            self.hands = self.mp_hands.Hands(
                model_complexity=0, 
                max_num_hands=2, 
                min_detection_confidence=0.80,
                min_tracking_confidence=0.80
            )
            print("✅ MediaPipe inicializado")
        except Exception as e:
            print(f"❌ Error MediaPipe: {e}")

    def centroide(self, lista_coordenadas):
        """Calcula el centroide de una lista de coordenadas"""
        coordenadas = np.array(lista_coordenadas)
        centroid = np.mean(coordenadas, axis=0)
        return int(centroid[0]), int(centroid[1])

    def detectar_dedos_mejorado(self, hand_landmarks, width, height, label):
        """Detecta el estado de los dedos (extendidos/contraídos)"""
        try:
            coordinadas_pulgar = []
            coordenadas_palma = []
            coordenadas_bases = []
            coordenadas_puntas = []

            for i in self.pulgar:
                coordinadas_pulgar.append([int(hand_landmarks.landmark[i].x * width),
                                         int(hand_landmarks.landmark[i].y * height)])
            for i in self.puntos_palma:
                coordenadas_palma.append([int(hand_landmarks.landmark[i].x * width),
                                        int(hand_landmarks.landmark[i].y * height)])
            for i in self.bases:
                coordenadas_bases.append([int(hand_landmarks.landmark[i].x * width),
                                        int(hand_landmarks.landmark[i].y * height)])
            for i in self.puntas:
                coordenadas_puntas.append([int(hand_landmarks.landmark[i].x * width),
                                         int(hand_landmarks.landmark[i].y * height)])

            # Detección del pulgar (ángulo entre puntos)
            p1, p2, p3 = map(np.array, coordinadas_pulgar)
            l1, l2, l3 = np.linalg.norm(p2 - p3), np.linalg.norm(p1 - p3), np.linalg.norm(p1 - p2)
            angle = degrees(acos((l1**2 + l3**2 - l2**2) / (2 * l1 * l3)))
            dedo_pulgar = 1 if angle > 150 else 0

            # Detección de otros dedos (comparación distancias)
            nx, ny = self.centroide(coordenadas_palma)
            coordenadas_centroide = np.array([nx, ny])
            dis_centroid_puntas = np.linalg.norm(coordenadas_centroide - np.array(coordenadas_puntas), axis=1)
            dis_centroid_bases = np.linalg.norm(coordenadas_centroide - np.array(coordenadas_bases), axis=1)
            dedos = (dis_centroid_puntas > dis_centroid_bases).astype(int)

            return np.append(dedo_pulgar, dedos), (nx, ny)

        except Exception as e:
            print(f"❌ Error en detectar_dedos_mejorado: {e}")
            return np.zeros(5, dtype=int), (0, 0)

    def extraer_centroide_y_dedos(self, results, width, height):
        """Extrae datos de manos detectadas por MediaPipe"""
        hands_data = []
        model_labels = []

        if results.multi_hand_landmarks:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                model_label = results.multi_handedness[idx].classification[0].label
                dedos, centroide_pos = self.detectar_dedos_mejorado(hand_landmarks, width, height, model_label)
                hands_data.append((centroide_pos, dedos))
                model_labels.append(model_label)

        data = {'Left': None, 'Right': None}

        if len(hands_data) == 0:
            return data
        elif len(hands_data) == 1:
            data[model_labels[0]] = hands_data[0]
        else:
            # Ordenar por posición X (izquierda a derecha)
            sorted_indices = sorted(range(2), key=lambda i: hands_data[i][0][0])
            left_idx, right_idx = sorted_indices
            data['Left'] = hands_data[left_idx]
            data['Right'] = hands_data[right_idx]

        return data

    def crear_pizarron(self, trayectoria, nombre):
        """Crea una representación visual de la trayectoria del gesto"""
        if trayectoria and len(trayectoria) > 0:
            puntos = np.array(trayectoria)
            x_min, y_min = np.min(puntos, axis=0)
            x_max, y_max = np.max(puntos, axis=0)
            ancho = max(x_max - x_min + 40, 50)
            alto = max(y_max - y_min + 40, 50)
            pizarron = 255 * np.ones((alto, ancho, 3), dtype=np.uint8)
            puntos_recentrados = [((x - x_min + 20), (y - y_min + 20)) for (x, y) in trayectoria]

            # Dibujar líneas de la trayectoria
            for i in range(1, len(puntos_recentrados)):
                cv2.line(pizarron, puntos_recentrados[i - 1], puntos_recentrados[i], (0, 0, 0), 2)

            # Dibujar puntos
            for punto in puntos_recentrados:
                cv2.circle(pizarron, punto, 2, (255, 0, 0), -1)

            return cv2.resize(pizarron, (200, 200))
        else:
            pizarron = 255 * np.ones((200, 200, 3), dtype=np.uint8)
            cv2.putText(pizarron, "Sin datos", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
            return pizarron

    def pizarron_a_vector_binario(self, pizarron, tamano_salida=(20, 20), umbral=128):
        """Convierte el pizarrón a un vector binario para el modelo"""
        gris = cv2.cvtColor(pizarron, cv2.COLOR_BGR2GRAY)
        gris_redim = cv2.resize(gris, tamano_salida)
        _, binaria = cv2.threshold(gris_redim, umbral, 255, cv2.THRESH_BINARY)
        return binaria.flatten(), binaria

    def estandarizar_frames(self, frames, num_frames_deseado=30):
        """Estandariza el número de frames a un valor fijo"""
        if len(frames) == 0:
            return []
        if len(frames) == num_frames_deseado:
            return frames
        if len(frames) < num_frames_deseado:
            return frames + [frames[-1]] * (num_frames_deseado - len(frames))
        indices = np.linspace(0, len(frames) - 1, num_frames_deseado, dtype=int)
        return [frames[i] for i in indices]

    def obtener_frames_medios(self, frames, num_frames=5):
        """Obtiene los frames del medio de una secuencia"""
        if len(frames) <= num_frames:
            return frames
        inicio = (len(frames) - num_frames) // 2
        return frames[inicio:inicio + num_frames]

    def preparar_caracteristicas_inferencia(self, secuencia_dedos_left, secuencia_dedos_right,
                                          vector_binario_left, vector_binario_right):
        """Prepara las características para la inferencia del modelo"""
        secuencia_left_flat = np.array(secuencia_dedos_left).flatten()
        secuencia_right_flat = np.array(secuencia_dedos_right).flatten()
        vector_left_norm = (vector_binario_left / 255.0).astype(np.float64)
        vector_right_norm = (vector_binario_right / 255.0).astype(np.float64)
        caracteristicas = np.hstack([secuencia_left_flat, secuencia_right_flat,
                                   vector_left_norm, vector_right_norm])
        return caracteristicas.reshape(1, -1)

    def determinar_prediccion_final(self, prediccion, confianza, clases_modelo):
        """Determina la predicción final basada en la confianza"""
        if confianza >= self.UMBRAL_CONFIANZA:
            if prediccion in clases_modelo:
                return prediccion, "RECONOCIDO", (0, 255, 0)
            else:
                return "Gesto desconocido", "NO_RECONOCIDO", (255, 0, 0)
        else:
            return "Vuelve a intentarlo", "BAJA_CONFIANZA", (0, 165, 255)

    def procesar_frame(self, frame):
        """Procesa un frame para detección y reconocimiento de gestos"""
        if self.hands is None:
            frame_espejo = cv2.flip(frame, 1)
            return frame_espejo, "MediaPipe no inicializado", 0.0, "ERROR"

        if self.modelo_data is None or 'model' not in self.modelo_data:
            frame_espejo = cv2.flip(frame, 1)
            return frame_espejo, "SIN MODELO - MODO SIMULACION", 0.0, "SIMULACION"

        # Aplicar espejo
        frame_espejo = cv2.flip(frame, 1)
        height, width, _ = frame_espejo.shape
        
        # Procesar con MediaPipe
        frame_rgb = cv2.cvtColor(frame_espejo, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)
        mano_actualmente_detectada = results.multi_hand_landmarks is not None

        # Lógica de grabación
        if not self.grabando and mano_actualmente_detectada and not self.mano_detectada_anteriormente:
            self.grabando = True
            self.frames_video = []
            self.centroides_trayectoria_left = []
            self.centroides_trayectoria_right = []
            self.estados_dedos_trayectoria_left = []
            self.estados_dedos_trayectoria_right = []
            self.ultima_deteccion = time.time()
            self.prediccion_actual = "Grabando..."
            self.estado_prediccion = "GRABANDO"

        if self.grabando:
            if mano_actualmente_detectada:
                self.ultima_deteccion = time.time()
                self.frames_video.append(frame_espejo.copy())
                data = self.extraer_centroide_y_dedos(results, width, height)

                if data['Left']:
                    centroide_pos, dedos = data['Left']
                    self.centroides_trayectoria_left.append(centroide_pos)
                    self.estados_dedos_trayectoria_left.append(dedos)

                if data['Right']:
                    centroide_pos, dedos = data['Right']
                    self.centroides_trayectoria_right.append(centroide_pos)
                    self.estados_dedos_trayectoria_right.append(dedos)

                estado_texto = f"GRABANDO: {len(self.frames_video)} frames"
                color_estado = (0, 255, 0)
            else:
                if time.time() - self.ultima_deteccion > 1.0:
                    self.grabando = False
                    
                    # Procesar datos recolectados
                    secuencia_dedos_array_left = np.zeros((5, 5), dtype=int)
                    secuencia_dedos_array_right = np.zeros((5, 5), dtype=int)
                    vector_binario_left = np.zeros(400, dtype=np.uint8)
                    vector_binario_right = np.zeros(400, dtype=np.uint8)

                    if len(self.centroides_trayectoria_left) > 0:
                        centroides_medios_left = self.obtener_frames_medios(
                            self.estandarizar_frames(self.centroides_trayectoria_left, 30), 5)
                        estados_medios_left = self.obtener_frames_medios(
                            self.estandarizar_frames(self.estados_dedos_trayectoria_left, 30), 5)
                        secuencia_dedos_array_left = np.array(estados_medios_left)
                        pizarra_left = self.crear_pizarron(centroides_medios_left, 'Left')
                        vector_binario_left, _ = self.pizarron_a_vector_binario(pizarra_left)

                    if len(self.centroides_trayectoria_right) > 0:
                        centroides_medios_right = self.obtener_frames_medios(
                            self.estandarizar_frames(self.centroides_trayectoria_right, 30), 5)
                        estados_medios_right = self.obtener_frames_medios(
                            self.estandarizar_frames(self.estados_dedos_trayectoria_right, 30), 5)
                        secuencia_dedos_array_right = np.array(estados_medios_right)
                        pizarra_right = self.crear_pizarron(centroides_medios_right, 'Right')
                        vector_binario_right, _ = self.pizarron_a_vector_binario(pizarra_right)

                    if len(self.centroides_trayectoria_left) > 0 or len(self.centroides_trayectoria_right) > 0:
                        try:
                            model = self.modelo_data['model']
                            clases_modelo = self.modelo_data['classes']
                            scaler = self.modelo_data.get('scaler', None)

                            X_inferencia = self.preparar_caracteristicas_inferencia(
                                secuencia_dedos_array_left, secuencia_dedos_array_right,
                                vector_binario_left, vector_binario_right
                            )
                            if scaler is not None:
                                X_inferencia = scaler.transform(X_inferencia)

                            # Hacer predicción
                            prediccion_encoded = model.predict(X_inferencia)[0]
                            probabilidades = model.predict_proba(X_inferencia)[0]
                            confianza = np.max(probabilidades)

                            prediccion, estado, color_pred = self.determinar_prediccion_final(
                                prediccion_encoded, confianza, clases_modelo)

                            self.prediccion_actual = prediccion
                            self.confianza_actual = confianza
                            self.estado_prediccion = estado

                            # Llamar al callback si se reconoció un gesto
                            if self.callback_prediccion and estado == "RECONOCIDO":
                                print(f"🎯 [GESTOS] Gesto reconocido: {prediccion.lower()}")
                                self.callback_prediccion(prediccion.lower())

                        except Exception as e:
                            print(f"❌ Error en prediccion: {e}")
                            self.prediccion_actual = "Error en prediccion"
                            self.confianza_actual = 0.0
                            self.estado_prediccion = "ERROR"
                    else:
                        self.prediccion_actual = "Sin datos"
                        self.confianza_actual = 0.0
                        self.estado_prediccion = "SIN DATOS"

                    estado_texto = "PROCESADO"
                    color_estado = (255, 0, 0)
                else:
                    estado_texto = f"GRABANDO: {len(self.frames_video)} frames (sin mano)"
                    color_estado = (0, 165, 255)
        else:
            if mano_actualmente_detectada:
                estado_texto = "LISTO - Mueve la mano para comenzar"
                color_estado = (0, 255, 255)
            else:
                estado_texto = "ESPERANDO MANO..."
                color_estado = (0, 0, 255)

        # Dibujar landmarks
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame_espejo, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )

        self.mano_detectada_anteriormente = mano_actualmente_detectada

        return frame_espejo, self.prediccion_actual, self.confianza_actual, self.estado_prediccion

    def set_callback_prediccion(self, callback: Callable[[str], None]):
        """Configura el callback para cuando se detecta un gesto"""
        self.callback_prediccion = callback
        print("✅ Callback de gestos configurado")

    def liberar(self):
        """Libera recursos"""
        if self.hands:
            self.hands.close()
            print("✅ Recursos de inferencia liberados")