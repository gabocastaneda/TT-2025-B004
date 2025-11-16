# -*- coding: utf-8 -*-
# public/views/formatos/interaccion.py
import os, re, cv2, hashlib, requests
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QFrame, QLabel
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from public.views.hilo_video import HiloVideo
# Para mapear IDs->nombre y guardar con nombre canónico cuando venga de Drive
from public.views.config.mapa_interaccion import FILE_IDS

_DRIVE_RE = re.compile(r"https://www\.googleapis\.com/drive/v3/files/([^?]+)")

class VentanaInteraccion(QMainWindow):
    redimensionada = pyqtSignal()
    video_terminado = pyqtSignal()  # <- desbloquea consola

    def __init__(self, src_inicial=None):
        super().__init__()
        self.setWindowTitle("Ventana de Interacción")
        self.resize(1280, 720)

        # Paths
        self.dir_public = Path(__file__).resolve().parents[2]   # .../public
        self.dir_videos = self.dir_public / "videos"
        self.dir_videos.mkdir(parents=True, exist_ok=True)

        # Barra superior
        self.barra = QLabel(self); self.barra.setStyleSheet("background:#1577d2;")
        self.barra.setGeometry(0,0,self.width(),int(self.height()*0.1))
        self.titulo = QLabel("TT 2025-B004", self)
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("color:white;")
        self.titulo.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.titulo.setGeometry(0,0,self.width(),int(self.height()*0.1))

        # Recuadro cámara (izq)
        self.recuadro_cam = QFrame(self)
        self.recuadro_cam.setStyleSheet("background:transparent; border:12px solid #e7c14d; border-radius:16px;")
        self.recuadro_cam.setGeometry(70, 200, 540, 380)
        self.view_cam = QLabel(self.recuadro_cam)
        self.view_cam.setGeometry(10, 10, 520, 360)
        self.view_cam.setAlignment(Qt.AlignCenter)

        # Recuadro video (der)
        self.recuadro_vid = QFrame(self)
        self.recuadro_vid.setStyleSheet("background:transparent; border:12px solid #e7c14d; border-radius:16px;")
        self.recuadro_vid.setGeometry(670, 200, 540, 380)
        self.view_vid = QLabel(self.recuadro_vid)
        self.view_vid.setGeometry(10, 10, 520, 360)
        self.view_vid.setAlignment(Qt.AlignCenter)

        # Cámara
        self.cap_cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self._tick_cam)
        self.timer_cam.start(30)

        # Video RESP
        self.cap_resp = None
        self.hilo_resp = None

        if src_inicial:
            self.cambiar_video_unidad(src_inicial, nombre_resp="resp1")

    # ----- Cámara (espejo) -----
    def _tick_cam(self):
        if not self.cap_cam.isOpened():
            return
        ok, frame = self.cap_cam.read()
        if not ok:
            return
        frame = cv2.flip(frame, 1)  # espejo en cámara
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888)
        self.view_cam.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.view_cam.width(), self.view_cam.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))

    # ----- RESP (sin espejo) -----
    def cambiar_video_unidad(self, src: str, nombre_resp: str | None = None):
        """src: ruta o URL; descarga si es URL. Guarda como nombre_resp.mp4 si aplica."""
        # Limpia anterior
        try:
            if self.hilo_resp:
                self.hilo_resp.stop()
        except Exception:
            pass
        try:
            if self.cap_resp:
                self.cap_resp.release()
        except Exception:
            pass
        self.hilo_resp = None
        self.cap_resp = None

        ruta = self._asegurar_local(src, nombre_resp=nombre_resp)
        if not ruta:
            self.view_vid.setText("Error al descargar / abrir video.")
            QTimer.singleShot(10, self.video_terminado.emit)
            return

        self.cap_resp = cv2.VideoCapture(ruta)
        if not self.cap_resp.isOpened():
            self.view_vid.setText("Error al abrir video.")
            QTimer.singleShot(10, self.video_terminado.emit)
            return

        self.hilo_resp = HiloVideo(self.cap_resp, bucle=False, mirror=False)
        self.hilo_resp.senal_cambio_pixmap.connect(self._pintar_resp)
        self.hilo_resp.terminado.connect(self.video_terminado.emit)
        self.hilo_resp.start()

    def _pintar_resp(self, pix: QPixmap):
        self.view_vid.setPixmap(pix.scaled(
            self.view_vid.width(), self.view_vid.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _asegurar_local(self, src: str, nombre_resp: str | None) -> str | None:
        """Descarga si es URL; intenta guardar como respX.mp4 si reconoce el ID."""
        if not (src.startswith("http://") or src.startswith("https://")):
            return src if Path(src).is_file() else None

        # Si nos pasaron nombre canonico (respX) úsalo
        fname = None
        if nombre_resp and re.fullmatch(r"resp\d{1,2}", nombre_resp):
            fname = f"{nombre_resp}.mp4"
        else:
            # Intentar extraer file_id y mapear a FILE_IDS -> nombre
            m = _DRIVE_RE.match(src)
            if m:
                file_id = m.group(1)
                for name, fid in FILE_IDS.items():
                    if fid == file_id:
                        fname = f"{name}.mp4"
                        break

        # Si no se pudo, usar hash estable
        if not fname:
            h = hashlib.md5(src.encode("utf-8")).hexdigest()[:12]
            fname = f"drive_{h}.mp4"

        destino = self.dir_videos / fname
        if destino.is_file():
            return str(destino)

        try:
            with requests.get(src, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(destino, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        if chunk:
                            f.write(chunk)
            return str(destino)
        except Exception as e:
            print("Error descargando:", e)
            if destino.exists():
                destino.unlink(missing_ok=True)
            return None

    # ----- cierre -----
    def closeEvent(self, ev):
        try:
            if self.hilo_resp:
                self.hilo_resp.stop()
        except Exception:
            pass
        try:
            if self.cap_resp:
                self.cap_resp.release()
        except Exception:
            pass
        try:
            self.timer_cam.stop()
            if self.cap_cam:
                self.cap_cam.release()
        except Exception:
            pass
        ev.accept()
