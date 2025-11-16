# -*- coding: utf-8 -*-
# public/views/hilo_video.py
import cv2, time
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

class HiloVideo(QThread):
    senal_cambio_pixmap = pyqtSignal(QPixmap)
    terminado = pyqtSignal()

    def __init__(self, cap, bucle=False, mirror=False, target_fps=None):
        super().__init__()
        self._run = True
        self.cap = cap
        self.bucle = bool(bucle)
        self.mirror = bool(mirror)  # True sólo para cámara
        fps = (self.cap.get(cv2.CAP_PROP_FPS) if self.cap.isOpened() else 0) or 30
        self.fps = target_fps or fps

    def run(self):
        while self._run:
            t0 = time.time()
            ok, frame = self.cap.read()
            if not ok:
                if self.bucle:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break
            if self.mirror:
                frame = cv2.flip(frame, 1)  # espejo (sólo cámara)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.senal_cambio_pixmap.emit(QPixmap.fromImage(qimg))

            dt = time.time() - t0
            wait = max(0.0, (1.0 / self.fps) - dt)
            if wait > 0:
                time.sleep(wait)

        self.terminado.emit()

    def stop(self):
        self._run = False
        self.wait()
