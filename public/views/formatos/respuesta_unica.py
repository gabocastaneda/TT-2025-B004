# -*- coding: utf-8 -*-
# public/views/formatos/respuesta_unica.py
import cv2
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QLabel, QFrame
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from public.views.hilo_video import HiloVideo

class VentanaReproductorVideo(QMainWindow):
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
            self.setStyleSheet("QMainWindow { background: #2c3e50; }")

        # --- Barra superior (Imagen ajustable) ---
        self.barra = QLabel(self)
        barra_path = self.dir_images / "barra.png"
        if barra_path.exists():
            img_url = str(barra_path).replace("\\", "/")
            self.barra.setStyleSheet(f"border-image: url({img_url}) 0 0 0 0 stretch stretch; border: none;")
        else:
            self.barra.setStyleSheet("background: #8B1538;")

        self.titulo = QLabel("TT 225-B004", self)
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("background: transparent; color: white; letter-spacing: 3px;")
        self.titulo.setFont(QFont("Arial Black", 24, QFont.Bold))

        # --- Recuadro Video (Marco Dorado) ---
        self.recuadro = QFrame(self)
        self.recuadro.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 8px solid #e7c14d;
                border-radius: 20px;
            }
        """)

        # --- Vista del Video (Interior negro) ---
        self.view = QLabel(self.recuadro)
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("""
            QLabel {
                background: black;
                color: white;
                border: none;
                border-radius: 12px;
            }
        """)

        # Inicializar geometría y video
        self._recolocar()
        self.iniciar()

    def resizeEvent(self, event):
        self._recolocar()
        super().resizeEvent(event)

    def _recolocar(self):
        """Calcula dimensiones dinámicas para maximizar el video"""
        w = self.width()
        h = self.height()
        
        # Barra superior (10% de la altura)
        alto_barra = int(h * 0.1)
        self.barra.setGeometry(0, 0, w, alto_barra)
        self.titulo.setGeometry(0, 0, w, alto_barra)

        # Área disponible debajo de la barra
        area_h = h - alto_barra
        
        # El video ocupará el 80% del ancho total y el 85% de la altura disponible
        vid_w = int(w * 0.80)
        vid_h = int(area_h * 0.85)
        
        # Centrar el recuadro
        x_pos = (w - vid_w) // 2
        y_pos = alto_barra + (area_h - vid_h) // 2
        
        self.recuadro.setGeometry(x_pos, y_pos, vid_w, vid_h)
        
        # El label interno con un pequeño margen para que no choque con el borde curvo
        margen = 10
        self.view.setGeometry(margen, margen, vid_w - (margen*2), vid_h - (margen*2))

    def iniciar(self):
        if not self.ruta_video or not Path(self.ruta_video).is_file():
            self.view.setText("Sin video. Continuando…")
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
            self.view.setPixmap(pix.scaled(
                self.view.width(), self.view.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def closeEvent(self, ev):
        try:
            if self.hilo: self.hilo.stop()
            if self.cap: self.cap.release()
        finally:
            ev.accept()