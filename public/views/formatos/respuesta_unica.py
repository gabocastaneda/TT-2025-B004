# -*- coding: utf-8 -*-
# public/views/formatos/respuesta_unica.py
import cv2
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QLabel, QFrame
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from public.views.hilo_video import HiloVideo

class VentanaReproductorVideo(QMainWindow):
    # DEFINICIÓN DE SEÑALES (Deben estar aquí, fuera del __init__)
    redimensionada = pyqtSignal()
    transicion_solicitada = pyqtSignal()

    def __init__(self, ruta_video):
        super().__init__()
        self.setWindowTitle("Respuesta Única")
        self.resize(1280, 720)
        self.ruta_video = ruta_video
        self.cap = None
        self.hilo = None

        # --- Rutas de archivos (Imágenes) ---
        self.dir_public = Path(__file__).resolve().parents[2]
        self.dir_images = self.dir_public / "images"
        
        # --- Configurar Fondo ---
        fondo_path = self.dir_images / "fondo.png"
        if fondo_path.exists():
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-image: url({str(fondo_path).replace(chr(92), '/')});
                    background-repeat: no-repeat;
                    background-position: center;
                    background-attachment: fixed;
                }}
            """)
        else:
            self.setStyleSheet("background-color: #2c3e50;")

        self._init_ui()

    def _init_ui(self):
        # 1. Barra Superior
        self.barra = QLabel(self)
        barra_path = self.dir_images / "barra.png"
        if barra_path.exists():
            self.barra.setStyleSheet(f"border-image: url({str(barra_path).replace(chr(92), '/')}) 0 0 0 0 stretch stretch; border: none;")
        else:
            self.barra.setStyleSheet("background: #8B1538;") # Color institucional alternativo
            
        self.titulo = QLabel("ATENCIÓN AL CLIENTE", self)
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("background: transparent; color: white; letter-spacing: 2px;")
        self.titulo.setFont(QFont("Arial", 20, QFont.Bold))

        # 2. Marco del Video
        self.recuadro = QFrame(self)
        self.recuadro.setStyleSheet("""
            QFrame {
                background: black;
                border: 5px solid #e7c14d; /* Dorado */
                border-radius: 15px;
            }
        """)
        
        self.view = QLabel(self.recuadro)
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setScaledContents(True)

        self._recolocar_elementos()
        
        # Iniciar video automáticamente
        QTimer.singleShot(100, self.iniciar)

    def resizeEvent(self, event):
        self._recolocar_elementos()
        self.redimensionada.emit()
        super().resizeEvent(event)

    def _recolocar_elementos(self):
        w = self.width()
        h = self.height()

        # Barra superior (10% alto)
        alto_barra = int(h * 0.1)
        self.barra.setGeometry(0, 0, w, alto_barra)
        self.titulo.setGeometry(0, 0, w, alto_barra)

        # Recuadro Video (Centrado)
        area_y = alto_barra + 20
        area_h = h - area_y - 40
        area_w = w - 80
        
        # Aspect Ratio 16:9
        target_h = area_h
        target_w = int(target_h * (16/9))
        
        if target_w > area_w:
            target_w = area_w
            target_h = int(target_w * (9/16))
            
        vid_w = target_w
        vid_h = target_h
        
        x_pos = (w - vid_w) // 2
        y_pos = alto_barra + (area_h - vid_h) // 2
        
        self.recuadro.setGeometry(x_pos, y_pos, vid_w, vid_h)
        
        # El label interno con un pequeño margen
        margen = 10
        self.view.setGeometry(margen, margen, vid_w - (margen*2), vid_h - (margen*2))

    def iniciar(self):
        if not self.ruta_video or not Path(self.ruta_video).is_file():
            self.view.setText("Sin video. Continuando...")
            QTimer.singleShot(2000, self.transicion_solicitada.emit)
            return
            
        self.cap = cv2.VideoCapture(self.ruta_video)
        if not self.cap.isOpened():
            self.view.setText("Error al abrir el video.")
            QTimer.singleShot(2000, self.transicion_solicitada.emit)
            return
            
        self.hilo = HiloVideo(self.cap, bucle=False, mirror=False)
        self.hilo.senal_cambio_pixmap.connect(self._pintar)
        self.hilo.terminado.connect(self.transicion_solicitada.emit)
        self.hilo.start()

    def _pintar(self, pix: QPixmap):
        if self.view.width() > 0 and self.view.height() > 0:
            self.view.setPixmap(pix.scaled(self.view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def closeEvent(self, event):
        if self.hilo:
            self.hilo.stop()
        if self.cap:
            self.cap.release()
        super().closeEvent(event)