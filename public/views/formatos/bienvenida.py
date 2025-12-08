import sys
import os
import cv2
import time
import mediapipe as mp
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFrame, QLabel, QDesktopWidget, QWidget,
    QVBoxLayout, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon
from PyQt5.QtCore import QSize, QTimer, Qt, pyqtSignal, QRect, QThread

# Asumiendo que hilo_video.py está en la misma carpeta o accesible
from hilo_video import HiloVideo 

class HiloDeteccionPersona(QThread):
    """Hilo para detectar personas con MediaPipe antes de iniciar el video"""
    persona_detectada = pyqtSignal()
    frame_actualizado = pyqtSignal(QImage)
    
    def __init__(self):
        super().__init__()
        self._running = True
        self.cap = None
        
        # Inicializar MediaPipe Pose
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,  # Modelo ligero para mayor velocidad
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
    def run(self):
        print("[DETECCIÓN] Intentando abrir cámara...")
        self.cap = cv2.VideoCapture(0)
        
        # Intentar con diferentes backends si el primero falla
        if not self.cap.isOpened():
            print("[DETECCIÓN] Intento 1 falló, probando backend DirectShow...")
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened():
            print("[ERROR] No se pudo abrir la cámara para detección")
            return
        
        # Configurar resolución para mejor rendimiento
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        print("[DETECCIÓN] ✓ Cámara abierta correctamente")
        print("[DETECCIÓN] Esperando detección de persona...")
        
        frames_consecutivos_con_persona = 0
        frames_requeridos = 5  # Requiere 5 frames consecutivos para confirmar
        frame_count = 0
        
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                print("[DETECCIÓN] Error al leer frame de la cámara")
                self.msleep(100)
                continue
            
            frame_count += 1
            if frame_count % 30 == 0:  # Log cada 30 frames
                print(f"[DETECCIÓN] Procesando frames... (sin persona detectada aún)")
            
            # Voltear horizontalmente para efecto espejo
            frame = cv2.flip(frame, 1)
            
            # Convertir a RGB para MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)
            
            # Dibujar esqueleto si se detecta persona
            if results.pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=2)
                )
                frames_consecutivos_con_persona += 1
                
                # Si detectamos persona en frames consecutivos, emitir señal
                if frames_consecutivos_con_persona >= frames_requeridos:
                    print(f"[DETECCIÓN] ✓✓✓ ¡Persona detectada! ({frames_requeridos} frames consecutivos)")
                    self.persona_detectada.emit()
                    break
            else:
                frames_consecutivos_con_persona = 0
            
            # Convertir frame para mostrar en Qt
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.frame_actualizado.emit(qt_image)
            
            self.msleep(33)  # ~30 FPS
        
        print("[DETECCIÓN] Finalizando hilo de detección...")
        self.liberar_recursos()
    
    def liberar_recursos(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        if hasattr(self, 'pose') and self.pose is not None:
            try:
                self.pose.close()
            except (ValueError, AttributeError):
                pass  # Ya estaba cerrado o no existe
            self.pose = None
        print("[DETECCIÓN] Recursos liberados")
    
    def stop(self):
        self._running = False
        self.wait()
        self.liberar_recursos()


class VentanaBienvenida(QMainWindow):
    redimensionada = pyqtSignal()
    video_terminado = pyqtSignal()

    def __init__(self, ruta_video):
        super().__init__()
        self.setWindowTitle("Ventana de Bienvenida")
        self.setWindowIcon(QIcon())
        
        self.ruta_video = ruta_video
        self.cap = None
        self.tiempo_inicio_reproduccion = None
        self.modo_deteccion = True  # Inicia en modo detección
        self.hilo_deteccion = None
        self.hilo_video = None
        
        # --- Configuración de Paths ---
        self.dir_base = Path(__file__).resolve().parent
        self.dir_public = None
        
        # Buscamos la carpeta 'public' subiendo niveles
        temp_path = self.dir_base
        for _ in range(4):
            if (temp_path / "public").exists():
                self.dir_public = temp_path / "public"
                break
            temp_path = temp_path.parent
            
        if not self.dir_public:
             self.dir_public = Path(__file__).resolve().parents[2] 

        self.dir_images = self.dir_public / "images"
        
        # --- Inicialización UI ---
        self.inicializar_ui()
        
        # Maximizar
        self.showMaximized()
        self.actualizar_disposicion()
        
        # IMPORTANTE: Iniciar detección automáticamente al crear la ventana
        print("[SISTEMA] Ventana de Bienvenida creada, iniciando detección...")
        # Usar QTimer para asegurar que la UI esté completamente renderizada
        QTimer.singleShot(500, self.iniciar_deteccion_persona)
    
    def inicializar_ui(self):
        # Mantenemos esto por seguridad, pero showMaximized lo anulará positivamente
        geometria_pantalla = QDesktopWidget().screenGeometry()
        self.ancho_pantalla = geometria_pantalla.width()
        self.alto_pantalla = geometria_pantalla.height()
        
        # --- Configurar imagen de fondo ---
        fondo_path = self.dir_images / "fondo.png"
        
        if fondo_path.exists():
            fondo_str = str(fondo_path).replace("\\", "/")
            self.setStyleSheet(f"""
                QMainWindow {{
                    border-image: url({fondo_str}) 0 0 0 0 stretch stretch;
                }}
            """)
        else:
            print(f"[WARNING] No se encontró fondo en: {fondo_path}")
            self.setStyleSheet("QMainWindow { background: #2c3e50; }")

        self.widget_central = QWidget(self)
        self.widget_central.setStyleSheet("background: transparent;")
        self.setCentralWidget(self.widget_central)
        
        # --- Barra Superior ---
        self.barra_superior = QLabel(self.widget_central)
        barra_path = self.dir_images / "barra.png"
        
        if barra_path.exists():
            barra_url = str(barra_path).replace("\\", "/")
            self.barra_superior.setStyleSheet(f"border-image: url({barra_url}) 0 0 0 0 stretch stretch; border: none;")
        else:
            self.barra_superior.setStyleSheet("background: #8B1538;")

        self.etiqueta_titulo = QLabel("TT 225-B004", self.barra_superior)
        self.etiqueta_titulo.setAlignment(Qt.AlignCenter)
        self.etiqueta_titulo.setStyleSheet("background: transparent; color: white; letter-spacing: 3px;")
        self.etiqueta_titulo.setFont(QFont("Arial Black", 24, QFont.Bold))
        
        # --- Recuadro Video ---
        self.recuadro_video = QFrame(self.widget_central)
        self.recuadro_video.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 8px solid #e7c14d;
                border-radius: 20px;
            }
        """)
        
        self.etiqueta_video = QLabel(self.recuadro_video)
        self.etiqueta_video.setAlignment(Qt.AlignCenter)
        self.etiqueta_video.setStyleSheet("""
            QLabel {
                background: black;
                color: white;
                border: none;
                border-radius: 12px;
            }
        """)
        # Texto inicial mientras se activa la cámara
        self.etiqueta_video.setText("Activando cámara...")

        # --- Textos de Bienvenida (MODO ESPERA) ---
        self.contenedor_texto = QWidget(self.widget_central)
        self.disposicion_texto = QVBoxLayout(self.contenedor_texto)
        self.disposicion_texto.setAlignment(Qt.AlignCenter)

        self.texto_titulo = QLabel("¡ESPERANDO USUARIO!", self.contenedor_texto)
        self.texto_titulo.setWordWrap(True)
        self.texto_titulo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.texto_hola = QLabel("POR FAVOR, COLÓCATE FRENTE A LA CÁMARA.", self.contenedor_texto)
        self.texto_hola.setWordWrap(True)
        self.texto_hola.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.texto_bienvenida = QLabel("EL SISTEMA INICIARÁ AUTOMÁTICAMENTE.", self.contenedor_texto)
        self.texto_bienvenida.setWordWrap(True)
        self.texto_bienvenida.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        for etiqueta in [self.texto_titulo, self.texto_hola, self.texto_bienvenida]:
            etiqueta.setStyleSheet("color: black; background: transparent;")
            etiqueta.setAlignment(Qt.AlignCenter)
            etiqueta.setFont(QFont("Segoe UI", 30, QFont.Bold))
            self.disposicion_texto.addWidget(etiqueta)

        self.contenedor_texto.setMinimumWidth(int(self.ancho_pantalla * 0.40))
        self.contenedor_texto.setMinimumHeight(int(self.alto_pantalla * 0.45))

        self.redimensionada.connect(self.actualizar_disposicion)
        self.actualizar_disposicion()

    def resizeEvent(self, evento):
        self.redimensionada.emit()
        super().resizeEvent(evento)
    
    def actualizar_disposicion(self):
        w = self.width()
        h = self.height()
        
        # 1. Barra Superior
        alto_barra = int(h * 0.1)
        self.barra_superior.setGeometry(0, 0, w, alto_barra)
        self.etiqueta_titulo.setGeometry(0, 0, w, alto_barra)
        
        # 2. Recuadro Video
        ancho_video = int(w * 0.3)
        alto_video = int(h * 0.7)
        x_video = int(w * 0.15)
        y_video = int(h * 0.20)
        
        self.recuadro_video.setGeometry(x_video, y_video, ancho_video, alto_video)
        
        margen = 8
        self.etiqueta_video.setGeometry(
            margen, 
            margen, 
            ancho_video - (margen * 2), 
            alto_video - (margen * 2)
        )

        # 3. Texto
        ancho_texto = int(w * 0.40)
        x_texto = int(w * 0.55)
        y_texto = y_video
        
        self.contenedor_texto.setGeometry(x_texto, y_texto, ancho_texto, int(h * 0.5))

    def iniciar_deteccion_persona(self):
        """Inicia la detección de persona con MediaPipe"""
        print("[SISTEMA] ═══════════════════════════════════════════")
        print("[SISTEMA] Iniciando detección de persona...")
        print("[SISTEMA] ═══════════════════════════════════════════")
        
        self.modo_deteccion = True
        
        # Limpiar hilo anterior si existe
        if self.hilo_deteccion:
            self.hilo_deteccion.stop()
            self.hilo_deteccion = None
        
        self.hilo_deteccion = HiloDeteccionPersona()
        self.hilo_deteccion.persona_detectada.connect(self.on_persona_detectada)
        self.hilo_deteccion.frame_actualizado.connect(self.actualizar_frame_deteccion)
        self.hilo_deteccion.start()
        
        print("[SISTEMA] Hilo de detección iniciado correctamente")
    
    def actualizar_frame_deteccion(self, qt_image):
        """Actualiza el frame de la cámara durante la detección"""
        if self.etiqueta_video.width() > 0 and self.etiqueta_video.height() > 0:
            pixmap = QPixmap.fromImage(qt_image)
            self.etiqueta_video.setPixmap(pixmap.scaled(
                self.etiqueta_video.width(), 
                self.etiqueta_video.height(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            ))
    
    def on_persona_detectada(self):
        """Callback cuando se detecta una persona"""
        print("[SISTEMA] ═══════════════════════════════════════════")
        print("[SISTEMA] ✓✓✓ PERSONA DETECTADA ✓✓✓")
        print("[SISTEMA] Iniciando video de bienvenida...")
        print("[SISTEMA] ═══════════════════════════════════════════")
        
        # Detener hilo de detección
        if self.hilo_deteccion:
            self.hilo_deteccion.stop()
            self.hilo_deteccion = None
        
        # Cambiar textos a modo bienvenida
        self.texto_titulo.setText("¡HOLA, BIENVENIDO!")
        self.texto_hola.setText("SOMOS UN SISTEMA DE APOYO PARA PERSONAS SORDAS.")
        self.texto_bienvenida.setText("POR FAVOR, COLÓCATE EN EL ÁREA DESIGNADA.")
        
        # Iniciar video de bienvenida
        self.modo_deteccion = False
        QTimer.singleShot(500, self.iniciar_video)

    def iniciar_video(self):
        if not self.ruta_video:
            self.etiqueta_video.setText("Error: Ruta de video no especificada.")
            self.video_terminado.emit()
            return
            
        self.cap = cv2.VideoCapture(self.ruta_video)
        
        if not self.cap.isOpened():
            self.etiqueta_video.setText("Error al abrir el video.")
            self.video_terminado.emit()
            return
        
        fps = self.cap.get(cv2.CAP_PROP_FPS)

        print("-" * 50)
        print("Video de Bienvenida - Reproducción iniciada")
        if fps > 0:
            print(f"FPS del video: {fps}")
        print("-" * 50)

        self.tiempo_inicio_reproduccion = time.time()
        self.hilo_video = HiloVideo(self.cap)
        self.hilo_video.senal_cambio_pixmap.connect(self.actualizar_imagen)
        self.hilo_video.terminado.connect(self.finalizar_reproduccion)
        self.hilo_video.start()

    def actualizar_imagen(self, imagen):
        if self.etiqueta_video.width() > 0 and self.etiqueta_video.height() > 0:
            self.etiqueta_video.setPixmap(imagen.scaled(
                self.etiqueta_video.width(), 
                self.etiqueta_video.height(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            ))

    def finalizar_reproduccion(self):
        if self.hilo_video:
            self.hilo_video.stop()
            self.hilo_video = None
        
        if self.tiempo_inicio_reproduccion:
            tiempo_total_reproduccion = time.time() - self.tiempo_inicio_reproduccion
            print(f"Tiempo de reproducción real: {tiempo_total_reproduccion:.2f} segundos.")
        
        print("[SISTEMA] Video de bienvenida finalizado")
        self.video_terminado.emit()
    
    def reiniciar_deteccion(self):
        """Reinicia la ventana al modo de detección de persona"""
        print("[SISTEMA] ═══════════════════════════════════════════")
        print("[SISTEMA] REINICIANDO MODO DETECCIÓN...")
        print("[SISTEMA] ═══════════════════════════════════════════")
        
        # Limpiar video si existe
        if self.hilo_video:
            self.hilo_video.stop()
            self.hilo_video = None
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Restaurar textos iniciales
        self.texto_titulo.setText("¡ESPERANDO USUARIO!")
        self.texto_hola.setText("POR FAVOR, COLÓCATE FRENTE A LA CÁMARA.")
        self.texto_bienvenida.setText("EL SISTEMA INICIARÁ AUTOMÁTICAMENTE.")
        
        # Limpiar imagen de video anterior
        self.etiqueta_video.clear()
        self.etiqueta_video.setText("Reactivando cámara...")
        
        # Reiniciar detección con un pequeño delay
        QTimer.singleShot(500, self.iniciar_deteccion_persona)

    def closeEvent(self, evento):
        print("[SISTEMA] Cerrando VentanaBienvenida...")
        
        # Limpiar recursos de detección
        if self.hilo_deteccion:
            self.hilo_deteccion.stop()
            self.hilo_deteccion = None
        
        # Limpiar recursos de video
        if self.hilo_video:
            self.hilo_video.stop()
            self.hilo_video = None
        if self.cap:
            self.cap.release()
            self.cap = None
        
        evento.accept()
        print("[SISTEMA] VentanaBienvenida cerrada correctamente")