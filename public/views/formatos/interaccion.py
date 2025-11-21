# -*- coding: utf-8 -*-
# public/views/formatos/interaccion.py
import re, cv2, hashlib, requests
from pathlib import Path
from typing import Optional, Callable

from PyQt5.QtWidgets import QMainWindow, QFrame, QLabel
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect

from public.views.hilo_video import HiloVideo
from public.views.config.mapa_interaccion import FILE_IDS

# Coincide con las URLs de la Drive API: https://www.googleapis.com/drive/v3/files/<ID>?alt=media&key=...
_DRIVE_RE = re.compile(r"https://www\.googleapis\.com/drive/v3/files/([^?]+)")

class VentanaInteraccion(QMainWindow):
    redimensionada = pyqtSignal()
    video_terminado = pyqtSignal()  # desbloquea consola tras RESP

    def __init__(self, src_inicial: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Interacción")
        self.resize(1280, 720)

        # Paths
        self.dir_public = Path(__file__).resolve().parents[2]   # .../public
        self.dir_videos = self.dir_public / "videos"
        self.dir_videos.mkdir(parents=True, exist_ok=True)

        # --- Barra superior ---
        self.barra = QLabel(self)
        self.barra.setStyleSheet("background:#1577d2;")
        self.titulo = QLabel("TT 2025-B004", self)
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("color:white;")
        self.titulo.setFont(QFont("Segoe UI", 22, QFont.Bold))

        # --- Recuadro cámara (izq) ---
        self.recuadro_cam = QFrame(self)
        self.recuadro_cam.setStyleSheet(
            "background:transparent; border:12px solid #e7c14d; border-radius:16px;"
        )
        self.view_cam = QLabel(self.recuadro_cam)
        self.view_cam.setAlignment(Qt.AlignCenter)

        # --- Recuadro video RESP (der) ---
        self.recuadro_vid = QFrame(self)
        self.recuadro_vid.setStyleSheet(
            "background:transparent; border:12px solid #e7c14d; border-radius:16px;"
        )
        self.view_vid = QLabel(self.recuadro_vid)
        self.view_vid.setAlignment(Qt.AlignCenter)

        # --- Banner rojo bajo el área de video (solo durante reproducción) ---
        self.banner = QFrame(self)
        self.banner.setStyleSheet("background:#c0392b; border-radius:10px;")
        self.banner_lbl = QLabel("POR FAVOR, ESPERE PARA CAPTURAR SU RESPUESTA", self.banner)
        self.banner_lbl.setAlignment(Qt.AlignCenter)
        self.banner_lbl.setStyleSheet("color:#ffffff; font-size:22px; font-weight:800; text-transform:uppercase;")
        self.banner.hide()

        # --- Overlay para mostrar texto (ticket, etc.) sobre el área del video ---
        self.overlay = QFrame(self.recuadro_vid)
        self.overlay.setStyleSheet(
            "background: rgba(255,255,255,235); border: 2px solid #e7c14d; border-radius:12px;"
        )
        self.overlay.hide()
        self.lbl_overlay = QLabel(self.overlay)
        self.lbl_overlay.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_overlay.setWordWrap(True)
        self.lbl_overlay.setStyleSheet("color:#2c3e50; padding:12px;")
        self.lbl_overlay.setFont(QFont("Segoe UI", 11))
        self._overlay_timer = QTimer(self)
        self._overlay_timer.setSingleShot(True)
        self._overlay_cb: Optional[Callable[[], None]] = None
        self._overlay_timer.timeout.connect(self._cerrar_overlay)

        # --- Cámara ---
        self.cap_cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self._tick_cam)
        self.timer_cam.start(30)

        # --- Video RESP (OpenCV + hilo) ---
        self.cap_resp = None
        self.hilo_resp: Optional[HiloVideo] = None

        # Estado de layout
        self._modo_reproduccion = False  # True => cámara pequeña + banner rojo ON

        # Layout inicial
        self._recolocar()
        self.redimensionada.connect(self._recolocar)

        if src_inicial:
            # Iniciar con RESP1 ya respetando modo reproducción
            self.set_modo_reproduccion(True)
            self.cambiar_video_unidad(src_inicial, nombre_resp="resp1")

    # =================== Cámara (espejo SOLO la cámara) ===================
    def _tick_cam(self):
        if not self.cap_cam or not self.cap_cam.isOpened():
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

    # =================== RESP (sin espejo) ===================
    def cambiar_video_unidad(self, src: Optional[str], nombre_resp: Optional[str] = None):
        """Abre/descarga el video; si es URL lo guarda con nombre canónico si aplica."""
        # Oculta overlay si estuviera activo
        self._overlay_timer.stop()
        self.overlay.hide()

        # Limpia vídeo anterior
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

        if not src:
            QTimer.singleShot(0, self._emitir_terminado)
            return

        ruta = self._asegurar_local(src, nombre_resp=nombre_resp)
        if not ruta:
            self.view_vid.setText("Error al descargar / abrir video.")
            QTimer.singleShot(10, self._emitir_terminado)
            return

        self.cap_resp = cv2.VideoCapture(ruta)
        if not self.cap_resp.isOpened():
            self.view_vid.setText("Error al abrir video.")
            QTimer.singleShot(10, self._emitir_terminado)
            return

        # Ya que vamos a reproducir, aseguramos modo reproducción
        self.set_modo_reproduccion(True)

        self.hilo_resp = HiloVideo(self.cap_resp, bucle=False, mirror=False)
        self.hilo_resp.senal_cambio_pixmap.connect(self._pintar_resp)
        self.hilo_resp.terminado.connect(self._on_video_end)
        self.hilo_resp.start()

    def _pintar_resp(self, pix: QPixmap):
        self.view_vid.setPixmap(pix.scaled(
            self.view_vid.width(), self.view_vid.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_video_end(self):
        # Apagamos modo reproducción y emitimos terminado
        self.set_modo_reproduccion(False)
        self._emitir_terminado()

    def _emitir_terminado(self):
        try:
            self.video_terminado.emit()
        except Exception:
            pass

    # =================== Overlay: texto de ticket ===================
    def mostrar_overlay_texto(self, texto: str, ms: int = 10_000, on_done: Optional[Callable[[], None]] = None):
        """
        Muestra 'texto' sobre el recuadro de video durante 'ms' ms.
        Llama on_done() al finalizar. No bloquea la UI.
        (Se muestra en modo NORMAL, no en reproducción de video)
        """
        try:
            self.lbl_overlay.setText(texto)
            self._recolocar_overlay()
            self.overlay.show()
            self._overlay_cb = on_done
            self._overlay_timer.start(max(1, int(ms)))
        except Exception as e:
            print("[Overlay] Error al mostrar:", e)
            self.overlay.hide()
            if callable(on_done):
                on_done()

    def _cerrar_overlay(self):
        self.overlay.hide()
        cb = self._overlay_cb
        self._overlay_cb = None
        if callable(cb):
            try:
                cb()
            except Exception as e:
                print("[Overlay] callback error:", e)

    # =================== Descarga local ===================
    def _asegurar_local(self, src: str, nombre_resp: Optional[str]) -> Optional[str]:
        """Descarga si es URL; intenta guardar como respX.mp4 si reconoce el ID."""
        if not (src.startswith("http://") or src.startswith("https://")):
            return str(Path(src)) if Path(src).is_file() else None

        # nombre canónico si viene (respX)
        fname = None
        if nombre_resp and re.fullmatch(r"resp\d{1,2}", nombre_resp):
            fname = f"{nombre_resp}.mp4"
        else:
            # mapear file_id -> respX
            m = _DRIVE_RE.match(src)
            if m:
                file_id = m.group(1)
                for name, fid in FILE_IDS.items():
                    if fid == file_id:
                        fname = f"{name}.mp4"
                        break
        if not fname:
            h = hashlib.md5(src.encode("utf-8")).hexdigest()[:12]
            fname = f"drive_{h}.mp4"

        destino = self.dir_videos / fname
        if destino.is_file():
            return str(destino)

        try:
            with requests.get(src, stream=True, timeout=45) as r:
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

    # =================== Layout / Redimensionamiento ===================
    def set_modo_reproduccion(self, on: bool):
        """
        True  => reduce cámara y muestra banner rojo (espera).
        False => cámara grande normal y oculta banner.
        """
        self._modo_reproduccion = bool(on)
        # Banner rojo visible solo mientras se reproduce video
        self.banner.setVisible(self._modo_reproduccion)
        self._recolocar()  # reacomoda tamaños

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.redimensionada.emit()

    def _recolocar(self):
        W, H = self.width(), self.height()
        barra_h = int(H * 0.1)
        self.barra.setGeometry(0, 0, W, barra_h)
        self.titulo.setGeometry(0, 0, W, barra_h)

        margen_lateral = 60
        gap = 40
        alto_panel = int(H * 0.55)

        # Distribución dinámica:
        # - Normal: 50% cámara / 50% video
        # - Reproducción: cámara 35% / video 65%
        if self._modo_reproduccion:
            frac_cam = 0.35
            frac_vid = 0.65
        else:
            frac_cam = 0.50
            frac_vid = 0.50

        ancho_total = W - 2 * margen_lateral - gap
        ancho_cam = int(ancho_total * frac_cam)
        ancho_vid = int(ancho_total * frac_vid)

        # Cámara (izquierda)
        x_cam = margen_lateral
        y_pan = barra_h + 60
        self.recuadro_cam.setGeometry(x_cam, y_pan, ancho_cam, alto_panel)
        self.view_cam.setGeometry(10, 10, ancho_cam - 20, alto_panel - 20)

        # Video (derecha)
        x_vid = x_cam + ancho_cam + gap
        self.recuadro_vid.setGeometry(x_vid, y_pan, ancho_vid, alto_panel)
        self.view_vid.setGeometry(10, 10, ancho_vid - 20, alto_panel - 20)

        # Banner rojo (debajo del video, mismo ancho)
        banner_h = 42
        self.banner.setGeometry(x_vid, y_pan + alto_panel + 16, ancho_vid, banner_h)
        self.banner_lbl.setGeometry(0, 0, ancho_vid, banner_h)

        # Recoloca overlay para que siga al recuadro de video
        self._recolocar_overlay()

    def _recolocar_overlay(self):
        # Overlay ocupa ~90% del recuadro de video
        w = self.recuadro_vid.width() - 20
        h = self.recuadro_vid.height() - 20
        self.overlay.setGeometry(10, 10, w, h)
        self.lbl_overlay.setGeometry(12, 12, w - 24, h - 24)

    # =================== Cierre ===================
    def closeEvent(self, ev):
        try:
            self._overlay_timer.stop()
            self.overlay.hide()
        except Exception:
            pass
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
