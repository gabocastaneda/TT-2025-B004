import sys
import os
import cv2
import time
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFrame, QLabel, QDesktopWidget, QWidget,
    QVBoxLayout, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon
from PyQt5.QtCore import QSize, QTimer, Qt, pyqtSignal, QRect, QThread

# Asumiendo que hilo_video.py está en la misma carpeta o accesible
from hilo_video import HiloVideo 

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
        
        # --- Configuración de Paths (igual que en interaccion.py) ---
        # Ajusta el nivel de .parents[...] según donde esté guardado este archivo
        # Si este archivo está en public/views/formatos/, usar parents[2] para llegar a public
        # Si está en la raíz junto a main, quizás necesites ajustar.
        # Aquí asumo la estructura: root/.../este_archivo.py -> public/images
        
        # Opción genérica buscando "public" hacia arriba:
        self.dir_base = Path(__file__).resolve().parent
        self.dir_public = None
        
        # Buscamos la carpeta 'public' subiendo niveles
        temp_path = self.dir_base
        for _ in range(4): # Intentar subir hasta 4 niveles
            if (temp_path / "public").exists():
                self.dir_public = temp_path / "public"
                break
            temp_path = temp_path.parent
            
        # Si no la encuentra, asume una ruta relativa estándar (ajustar si es necesario)
        if not self.dir_public:
             self.dir_public = Path(__file__).resolve().parents[2] 

        self.dir_images = self.dir_public / "images"
        
        # --- Inicialización UI ---
        self.inicializar_ui()
        self.iniciar_video()
    
    def inicializar_ui(self):
        geometria_pantalla = QDesktopWidget().screenGeometry()
        self.ancho_pantalla = geometria_pantalla.width()
        self.alto_pantalla = geometria_pantalla.height()
        self.setGeometry(0, 0, self.ancho_pantalla, self.alto_pantalla)
        
        # --- Configurar imagen de fondo (Estilo interaccion.py) ---
        fondo_path = self.dir_images / "fondo.png"
        
        if fondo_path.exists():
            # Reemplazo de backslash para CSS
            fondo_str = str(fondo_path).replace("\\", "/")
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-image: url({fondo_str});
                    background-repeat: no-repeat;
                    background-position: center;
                    background-attachment: fixed;
                }}
            """)
        else:
            print(f"[WARNING] No se encontró fondo en: {fondo_path}")
            self.setStyleSheet("QMainWindow { background: #2c3e50; }")

        self.widget_central = QWidget(self)
        # Hacemos transparente el widget central para ver el fondo del QMainWindow
        self.widget_central.setStyleSheet("background: transparent;")
        self.setCentralWidget(self.widget_central)
        
        # --- Barra Superior (Imagen ajustada) ---
        self.barra_superior = QLabel(self.widget_central)
        barra_path = self.dir_images / "barra.png"
        
        if barra_path.exists():
            barra_url = str(barra_path).replace("\\", "/")
            # border-image con 'stretch' para ajustar sin importar dimensiones
            self.barra_superior.setStyleSheet(f"border-image: url({barra_url}) 0 0 0 0 stretch stretch; border: none;")
        else:
            # Color sólido de respaldo (Guinda)
            self.barra_superior.setStyleSheet("background: #8B1538;")

        self.etiqueta_titulo = QLabel("TT 225-B004", self.barra_superior)
        self.etiqueta_titulo.setAlignment(Qt.AlignCenter)
        self.etiqueta_titulo.setStyleSheet("background: transparent; color: white; letter-spacing: 3px;")
        # Usando la misma fuente que interaccion.py para consistencia
        self.etiqueta_titulo.setFont(QFont("Arial Black", 24, QFont.Bold))
        
        # --- Recuadro Video (Marco Curvo y Limpio) ---
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

        # --- Textos de Bienvenida ---
        self.contenedor_texto = QWidget(self.widget_central)
        self.disposicion_texto = QVBoxLayout(self.contenedor_texto)
        self.disposicion_texto.setAlignment(Qt.AlignCenter)

        self.texto_titulo = QLabel("¡HOLA, BIENVENIDO!", self.contenedor_texto)
        self.texto_titulo.setWordWrap(True)
        self.texto_titulo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.texto_hola = QLabel("SOMOS UN SISTEMA DE APOYO PARA PERSONAS SORDAS.", self.contenedor_texto)
        self.texto_hola.setWordWrap(True)
        self.texto_hola.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.texto_bienvenida = QLabel("POR FAVOR, COLOCATE EN EL ÁREA DESIGNADA.", self.contenedor_texto)
        self.texto_bienvenida.setWordWrap(True)
        self.texto_bienvenida.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        for etiqueta in [self.texto_titulo, self.texto_hola, self.texto_bienvenida]:
            # Color negro para el texto (o ajusta a white si el fondo es muy oscuro)
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
        
        # 1. Barra Superior (10% de altura)
        alto_barra = int(h * 0.1)
        self.barra_superior.setGeometry(0, 0, w, alto_barra)
        self.etiqueta_titulo.setGeometry(0, 0, w, alto_barra)
        
        # 2. Recuadro Video
        # Mismas proporciones que tenías, pero ajustando el contenido interior
        ancho_video = int(w * 0.3)
        alto_video = int(h * 0.7)
        x_video = int(w * 0.15)
        y_video = int(h * 0.20)
        
        self.recuadro_video.setGeometry(x_video, y_video, ancho_video, alto_video)
        
        # Ajuste interno para crear el efecto de "doble borde" limpio
        # El video real (etiqueta) es un poco más pequeño que el recuadro (frame)
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
        fotogramas_totales = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)

        print("-" * 50)
        print("Ventana de Bienvenida")
        # Logs opcionales de debug
        if fps > 0:
            print(f"FPS detectados: {fps}")

        self.tiempo_inicio_reproduccion = time.time()
        self.hilo_video = HiloVideo(self.cap)
        self.hilo_video.senal_cambio_pixmap.connect(self.actualizar_imagen)
        self.hilo_video.terminado.connect(self.finalizar_reproduccion)
        self.hilo_video.start()

    def actualizar_imagen(self, imagen):
        # Escalar al tamaño de la etiqueta interna, no del frame contenedor
        if self.etiqueta_video.width() > 0 and self.etiqueta_video.height() > 0:
            self.etiqueta_video.setPixmap(imagen.scaled(
                self.etiqueta_video.width(), 
                self.etiqueta_video.height(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            ))

    def finalizar_reproduccion(self):
        if hasattr(self, 'hilo_video'):
            self.hilo_video.stop()
        
        if self.tiempo_inicio_reproduccion:
            tiempo_total_reproduccion = time.time() - self.tiempo_inicio_reproduccion
            print(f"Tiempo de reproducción real: {tiempo_total_reproduccion:.2f} segundos.")
        self.video_terminado.emit()

    def closeEvent(self, evento):
        if hasattr(self, 'hilo_video'):
            self.hilo_video.stop()
        if self.cap:
            self.cap.release()
        evento.accept()