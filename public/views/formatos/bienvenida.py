import sys
import os
import cv2
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFrame, QLabel, QDesktopWidget, QWidget,
    QVBoxLayout, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon
from PyQt5.QtCore import QSize, QTimer, Qt, pyqtSignal, QRect, QThread
import time

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
        
        self.inicializar_ui()
        self.iniciar_video()
    
    def inicializar_ui(self):
        geometria_pantalla = QDesktopWidget().screenGeometry()
        self.ancho_pantalla = geometria_pantalla.width()
        self.alto_pantalla = geometria_pantalla.height()
        self.alto_barra = int(self.alto_pantalla * 0.1)
        self.setGeometry(0, 0, self.ancho_pantalla, self.alto_pantalla)
        self.widget_central = QWidget(self)
        self.setCentralWidget(self.widget_central)
        
        self.barra_superior = QFrame(self.widget_central)
        self.barra_superior.setStyleSheet("background-color: #1881d7;")
        self.etiqueta_titulo = QLabel("TT 2025-B004", self.barra_superior)
        self.etiqueta_titulo.setAlignment(Qt.AlignCenter)
        self.etiqueta_titulo.setStyleSheet("color: white;")
        fuente = QFont("Arial", 20, QFont.Bold, italic=True)
        self.etiqueta_titulo.setFont(fuente)
        
        self.etiqueta_fondo = QLabel(self.widget_central)
        self.etiqueta_fondo.setScaledContents(True)
        self.etiqueta_fondo.lower()
        
        self.recuadro_video = QFrame(self.widget_central)
        self.recuadro_video.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 10px solid #F3D05C;
                border-radius: 20px;
            }
        """)
        self.etiqueta_video = QLabel(self.recuadro_video)
        self.etiqueta_video.setAlignment(Qt.AlignCenter)

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
            etiqueta.setStyleSheet("color: black;")
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
        alto_barra = int(h * 0.1)
        
        self.barra_superior.setGeometry(0, 0, w, alto_barra)
        self.etiqueta_titulo.setGeometry(0, 0, w, alto_barra)
        
        dir_base = Path(__file__).parent if '__file__' in globals() else Path.cwd()
        ruta_imagen = dir_base.parent.parent.parent / 'public' / 'images' / 'fondo2.png'
        try:
            imagen_fondo_original = QPixmap(str(ruta_imagen))
            if not imagen_fondo_original.isNull():
                imagen_fondo_escalada = imagen_fondo_original.scaled(w, h - alto_barra, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.etiqueta_fondo.setPixmap(imagen_fondo_escalada)
                self.etiqueta_fondo.setGeometry(0, alto_barra, w, h - alto_barra)
                self.etiqueta_fondo.lower()
        except Exception as e:
            print(f"Error cargando imagen de fondo: {e}")
        
        ancho_video = int(w * 0.3)
        alto_video = int(h * 0.7)
        x_video = int(w * 0.15)
        y_video = int(h * 0.20)
        self.recuadro_video.setGeometry(x_video, y_video, ancho_video, alto_video)
        self.etiqueta_video.setGeometry(10, 10, ancho_video - 20, alto_video - 20)

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
        ancho = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fotogramas_totales = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)

        print("-" * 50)
        print("Ventana de Bienvenida")
        if fps > 0 and fotogramas_totales > 0:
            duracion_seg = fotogramas_totales / fps
            minutos = int(duracion_seg // 60)
            segundos = int(duracion_seg % 60)
            print(f"   Duración Nominal: {minutos:02d}:{segundos:02d} ({duracion_seg:.2f} seg)")
            print(f"   FPS: {fps:.2f}")
            print(f"   Calidad: {ancho}x{alto}")
        else:
            print("   Propiedades: No disponibles")

        self.tiempo_inicio_reproduccion = time.time()
        self.hilo_video = HiloVideo(self.cap)
        self.hilo_video.senal_cambio_pixmap.connect(self.actualizar_imagen)
        self.hilo_video.terminado.connect(self.finalizar_reproduccion)
        self.hilo_video.start()

    def actualizar_imagen(self, imagen):
        self.etiqueta_video.setPixmap(imagen.scaled(self.etiqueta_video.width(), self.etiqueta_video.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

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