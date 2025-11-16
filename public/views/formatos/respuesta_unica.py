# -*- coding: utf-8 -*-
# public/views/formatos/respuesta_unica.py
import cv2
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QLabel, QFrame
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, pyqtSignal

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

        self.barra = QLabel(self); self.barra.setStyleSheet("background:#1577d2;")
        self.barra.setGeometry(0,0,self.width(),int(self.height()*0.1))
        self.titulo = QLabel("TT 2025-B004", self)
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("color:white;")
        self.titulo.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.titulo.setGeometry(0,0,self.width(),int(self.height()*0.1))

        self.recuadro = QFrame(self)
        self.recuadro.setStyleSheet("background:transparent; border:12px solid #e7c14d; border-radius:16px;")
        self.recuadro.setGeometry(360, 220, 560, 360)

        self.view = QLabel(self.recuadro); self.view.setGeometry(10,10,540,340)
        self.view.setAlignment(Qt.AlignCenter)

        self.iniciar()

    def iniciar(self):
        if not self.ruta_video or not Path(self.ruta_video).is_file():
            self.view.setText("Sin video. Continuando…")
            self.transicion_solicitada.emit()
            return
        self.cap = cv2.VideoCapture(self.ruta_video)
        if not self.cap.isOpened():
            self.view.setText("Error al abrir el video.")
            self.transicion_solicitada.emit()
            return
        self.hilo = HiloVideo(self.cap, bucle=False, mirror=False)  # SIN espejo
        self.hilo.senal_cambio_pixmap.connect(self._pintar)
        self.hilo.terminado.connect(self.transicion_solicitada.emit)
        self.hilo.start()

    def _pintar(self, pix: QPixmap):
        self.view.setPixmap(pix.scaled(
            self.view.width(), self.view.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def closeEvent(self, ev):
        try:
            if self.hilo: self.hilo.stop()
            if self.cap: self.cap.release()
        finally:
            ev.accept()
