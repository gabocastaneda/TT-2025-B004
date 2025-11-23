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
    gesto_detectado = pyqtSignal(str)  # NUEVA señal para gestos detectados

    def __init__(self, src_inicial: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Interacción")
        self.resize(1280, 720)

        # Paths
        self.dir_public = Path(__file__).resolve().parents[2]   # .../public
        self.dir_videos = self.dir_public / "videos"
        self.dir_videos.mkdir(parents=True, exist_ok=True)
        
        # Configurar imagen de fondo
        self.dir_images = self.dir_public / "images"
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
            print(f"[WARNING] No se encontró la imagen de fondo en: {fondo_path}")
            self.setStyleSheet("QMainWindow { background: #2c3e50; }")

        # --- Barra superior con IMAGEN (barra.png) ---
        self.barra = QLabel(self)
        self.barra.setObjectName("barraSuperior")
        self.barra.setScaledContents(False)  # usamos 'cover' manual, no auto-escalado completo
        self.barra_pix_original: Optional[QPixmap] = None

        barra_path = self.dir_images / "barra.png"
        if barra_path.exists():
            try:
                # Cargamos la imagen base de la barra
                self.barra_pix_original = QPixmap(str(barra_path).replace("\\", "/"))
            except Exception as e:
                print(f"[UI] Error cargando barra.png: {e}")
                self.barra_pix_original = None

        if not self.barra_pix_original or self.barra_pix_original.isNull():
            # Fallback: color sólido guinda si no hay imagen
            self.barra.setStyleSheet("background: #8B1538; border-radius: 0px;")
        else:
            # Fondo transparente: solo se verá la imagen
            self.barra.setStyleSheet("background: transparent;")

        self.titulo = QLabel("TT 2025-B004", self)
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("color: white; letter-spacing: 3px;")
        self.titulo.setFont(QFont("Arial Black", 24, QFont.Bold))

        # --- Recuadro cámara (izq) - MARCOS LIMPIOS ---
        self.recuadro_cam = QFrame(self)
        self.recuadro_cam.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 8px solid #e7c14d;
                border-radius: 20px;
            }
        """)
        self.view_cam = QLabel(self.recuadro_cam)
        self.view_cam.setAlignment(Qt.AlignCenter)
        self.view_cam.setStyleSheet("""
            QLabel {
                background: black;
                color: white;
                border: none;
                border-radius: 12px;
            }
        """)

        # --- Recuadro video RESP (der) - MARCOS LIMPIOS ---
        self.recuadro_vid = QFrame(self)
        self.recuadro_vid.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 8px solid #e7c14d;
                border-radius: 20px;
            }
        """)
        self.view_vid = QLabel(self.recuadro_vid)
        self.view_vid.setAlignment(Qt.AlignCenter)
        self.view_vid.setStyleSheet("""
            QLabel {
                background: black;
                color: white;
                border: none;
                border-radius: 12px;
            }
        """)

        # --- Banner ROJO bajo el área de video (solo durante reproducción) ---
        self.banner_rojo = QFrame(self)
        self.banner_rojo.setStyleSheet("background: #c0392b; border-radius: 12px; border: none;")
        self.banner_rojo_lbl = QLabel("⚠️  POR FAVOR, ESPERE PARA CAPTURAR SU RESPUESTA  ⚠️", self.banner_rojo)
        self.banner_rojo_lbl.setAlignment(Qt.AlignCenter)
        self.banner_rojo_lbl.setStyleSheet(
            "color: #ffffff; font-size: 22px; font-weight: 800; text-transform: uppercase; border: none;"
        )
        self.banner_rojo.hide()

        # --- Banner VERDE bajo el área de video (cuando puede capturar respuesta) ---
        self.banner_verde = QFrame(self)
        self.banner_verde.setStyleSheet("background: #27ae60; border-radius: 12px; border: none;")
        self.banner_verde_lbl = QLabel("✓  CAPTURE SU RESPUESTA  ✓", self.banner_verde)
        self.banner_verde_lbl.setAlignment(Qt.AlignCenter)
        self.banner_verde_lbl.setStyleSheet(
            "color: #ffffff; font-size: 22px; font-weight: 800; text-transform: uppercase; border: none;"
        )
        self.banner_verde.hide()

        # --- NUEVA: Ventana flotante para respuesta no capturada ---
        self.ventana_error = QFrame(self)
        self.ventana_error.setStyleSheet("""
            QFrame {
                background: rgba(231, 76, 60, 240);
                border: 3px solid #c0392b;
                border-radius: 15px;
            }
        """)
        self.ventana_error.hide()
        
        self.lbl_error = QLabel("⚠️RESPUESTA NO CAPTURADA\nPOR FAVOR, CAPTURE NUEVAMENTE⚠️", self.ventana_error)
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 20px;
                border: none;
            }
        """)
        self.lbl_error.setWordWrap(True)
        
        self._error_timer = QTimer(self)
        self._error_timer.setSingleShot(True)
        self._error_timer.timeout.connect(self._cerrar_ventana_error)

        # --- Overlay para mostrar texto (ticket, etc.) sobre el área del video ---
        self.overlay = QFrame(self.recuadro_vid)
        self.overlay.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 235);
                border: 3px solid #e7c14d;
                border-radius: 15px;
            }
        """)
        self.overlay.hide()
        self.lbl_overlay = QLabel(self.overlay)
        self.lbl_overlay.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_overlay.setWordWrap(True)
        self.lbl_overlay.setStyleSheet("color: #2c3e50; padding: 12px; border: none;")
        self.lbl_overlay.setFont(QFont("Segoe UI", 11))
        self._overlay_timer = QTimer(self)
        self._overlay_timer.setSingleShot(True)
        self._overlay_cb: Optional[Callable[[], None]] = None
        self._overlay_timer.timeout.connect(self._cerrar_overlay)

        # --- Cámara ---
        self.cap_cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap_cam.isOpened():
            # Intentar sin DSHOW
            self.cap_cam = cv2.VideoCapture(0)
            
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self._tick_cam)
        self.timer_cam.start(30)

        # --- Video RESP (OpenCV + hilo) ---
        self.cap_resp = None
        self.hilo_resp: Optional[HiloVideo] = None

        # --- Inferencia de gestos ---
        self.inferencia = None
        self.modo_gestos = False  # Controla si estamos en modo detección de gestos
        
        # Label para mostrar estado de gestos
        self.label_estado_gestos = QLabel(self.recuadro_cam)
        self.label_estado_gestos.setAlignment(Qt.AlignCenter)
        self.label_estado_gestos.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px;
                border-radius: 10px;
                font-size: 14px;
                border: none;
            }
        """)
        self.label_estado_gestos.hide()
        
        # Inicializar inferencia de gestos
        self._inicializar_inferencia_gestos()

        # Estado de layout
        self._modo_reproduccion = False  # True => cámara pequeña + banner rojo ON

        # Layout inicial
        self._recolocar()
        self.redimensionada.connect(self._recolocar)

        if src_inicial:
            # Iniciar con RESP1 ya respetando modo reproducción
            self.set_modo_reproduccion(True)
            self.cambiar_video_unidad(src_inicial, nombre_resp="resp1")

    def mostrar_error_captura(self):
        """Muestra la ventana flotante de error por 5 segundos"""
        try:
            self._recolocar_ventana_error()
            self.ventana_error.show()
            self.ventana_error.raise_()  # Traer al frente
            self._error_timer.start(5000)  # 5 segundos
            print("[UI] Mostrando mensaje de error de captura")
        except Exception as e:
            print(f"[UI] Error al mostrar ventana de error: {e}")

    def _cerrar_ventana_error(self):
        """Cierra la ventana flotante de error"""
        self.ventana_error.hide()
        print("[UI] Ventana de error cerrada")

    def _recolocar_ventana_error(self):
        """Recoloca la ventana de error en el centro de la pantalla"""
        error_width = 450
        error_height = 150
        x = (self.width() - error_width) // 2
        y = (self.height() - error_height) // 2
        self.ventana_error.setGeometry(x, y, error_width, error_height)
        self.lbl_error.setGeometry(0, 0, error_width, error_height)

    def set_modo_gestos(self, activar: bool):
        """Activa/desactiva el modo de detección de gestos"""
        self.modo_gestos = activar
        if activar:
            print("[GESTOS] Modo gestos activado")
            self.label_estado_gestos.show()
            self._actualizar_estado_gestos("🟢 LISTO - Mostrando manos", "#27ae60")
        else:
            print("[GESTOS] Modo gestos desactivado")
            self.label_estado_gestos.hide()
    
    def _inicializar_inferencia_gestos(self):
        """Inicializa el módulo de inferencia desde el backend"""
        try:
            # Nueva ruta del modelo en backend
            modelo_path = Path(__file__).resolve().parents[3] / "backend" / "modelo.pkl"
            print(f"[GESTOS] Buscando modelo en: {modelo_path}")
            
            # Importar desde el backend
            from backend.inferencia import InferenciaGestos
            
            if modelo_path.exists():
                self.inferencia = InferenciaGestos(str(modelo_path))
                print("[GESTOS] Modelo cargado desde backend")
            else:
                print("[GESTOS] Modelo no encontrado en backend, usando modo simulación")
                self.inferencia = InferenciaGestos()
                    
            self.inferencia.inicializar_deteccion()
            self.inferencia.set_callback_prediccion(self._on_gesto_detectado)
            print("[GESTOS] Inferencia inicializada desde backend")
                    
        except Exception as e:
            print(f"[GESTOS] Error inicializando inferencia: {e}")
            # Fallback básico
            self.inferencia = type('InferenciaSimulada', (), {})()
            self.inferencia.procesar_frame = lambda frame: (cv2.flip(frame, 1), "Simulación", 0.0, "SIMULACION")
            self.inferencia.set_callback_prediccion = lambda cb: setattr(self.inferencia, 'callback_prediccion', cb)
            self.inferencia.liberar = lambda: None

    def _on_gesto_detectado(self, gesto: str):
        """Callback cuando se detecta un gesto"""
        print(f"[GESTOS] Gesto detectado: {gesto}")
        self.gesto_detectado.emit(gesto)

    def _actualizar_estado_gestos(self, mensaje: str, color: str = "#3498db"):
        """Actualiza el label de estado de gestos"""
        self.label_estado_gestos.setText(mensaje)
        self.label_estado_gestos.setStyleSheet(f"""
            QLabel {{
                background: rgba(0, 0, 0, 0.8);
                color: {color};
                padding: 8px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }}
        """)
        # Recolocar el label
        self._recolocar_estado_gestos()

    def _recolocar_estado_gestos(self):
        """Recoloca el label de estado de gestos en la esquina inferior"""
        if self.label_estado_gestos.isVisible():
            label_width = 300
            label_height = 40
            x = 15
            y = self.recuadro_cam.height() - label_height - 15
            self.label_estado_gestos.setGeometry(x, y, label_width, label_height)

    # =================== Cámara (con detección de gestos) ===================
    def _tick_cam(self):
        if not self.cap_cam or not self.cap_cam.isOpened():
            self.view_cam.setText("CÁMARA NO DISPONIBLE\n\nVerifique que:\n• La cámara esté conectada\n• No esté en uso por otra aplicación\n• Los drivers estén instalados")
            return
            
        ok, frame = self.cap_cam.read()
        if not ok:
            self.view_cam.setText("ERROR LEYENDO CÁMARA\n\nReinicie la aplicación")
            return
            
        # Procesar frame para detección de gestos si está activo el modo
        frame_procesado = frame
        if self.modo_gestos and self.inferencia:
            try:
                frame_procesado, pred, conf, estado = self.inferencia.procesar_frame(frame)
                
                # Actualizar estado visual
                if estado == "GRABANDO":
                    self._actualizar_estado_gestos("GRABANDO gesto...", "#e67e22")
                elif estado == "RECONOCIDO":
                    self._actualizar_estado_gestos(f"Reconocido: {pred}", "#27ae60")
                elif estado == "LISTO":
                    self._actualizar_estado_gestos("Mueve la mano", "#3498db")
                elif estado == "ESPERANDO":
                    self._actualizar_estado_gestos("Acerca tu mano", "#95a5a6")
                elif estado == "MANO_DETECTADA":
                    self._actualizar_estado_gestos("Mano detectada", "#9b59b6")
                elif estado == "SIMULACION":
                    self._actualizar_estado_gestos("Modo simulación", "#e67e22")
                elif estado == "ERROR":
                    self._actualizar_estado_gestos("Error detección", "#e74c3c")
                else:
                    self._actualizar_estado_gestos(f"{estado}", "#f39c12")
                    
            except Exception as e:
                print(f"[GESTOS] Error procesando frame: {e}")
                frame_procesado = cv2.flip(frame, 1)  # fallback a espejo normal
                self._actualizar_estado_gestos("Error procesando", "#e74c3c")
        else:
            frame_procesado = cv2.flip(frame, 1)  # espejo en cámara normal
            if self.modo_gestos:
                self._actualizar_estado_gestos("Gestos pausados", "#7f8c8d")

        # Convertir y mostrar el frame
        try:
            rgb = cv2.cvtColor(frame_procesado, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Escalar manteniendo aspect ratio
            if self.view_cam.width() > 0 and self.view_cam.height() > 0:
                pixmap = QPixmap.fromImage(qimg)
                scaled_pixmap = pixmap.scaled(
                    self.view_cam.width(), self.view_cam.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.view_cam.setPixmap(scaled_pixmap)
            else:
                self.view_cam.setPixmap(QPixmap.fromImage(qimg))
                
        except Exception as e:
            print(f"[CAMARA] Error mostrando frame: {e}")
            self.view_cam.setText("Error mostrando video")

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
        if self.view_vid.width() > 0 and self.view_vid.height() > 0:
            self.view_vid.setPixmap(pix.scaled(
                self.view_vid.width(), self.view_vid.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.view_vid.setPixmap(pix)

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
        True  => reduce cámara, muestra banner ROJO (espera) y oculta banner VERDE.
        False => cámara grande normal, oculta banner ROJO y muestra banner VERDE.
        """
        self._modo_reproduccion = bool(on)
        # Banner rojo visible solo mientras se reproduce video
        self.banner_rojo.setVisible(self._modo_reproduccion)
        # Banner verde visible cuando NO se reproduce video (puede capturar)
        self.banner_verde.setVisible(not self._modo_reproduccion)
        self._recolocar()  # reacomoda tamaños

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.redimensionada.emit()

    def _recolocar(self):
        W, H = self.width(), self.height()
        barra_h = int(H * 0.1)
        self.barra.setGeometry(0, 0, W, barra_h)
        self.titulo.setGeometry(0, 0, W, barra_h)

        # Actualizar imagen de la barra para que cubra toda el área
        self._actualizar_barra_pixmap()

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
        # El view_cam con margen interno para crear el efecto limpio
        self.view_cam.setGeometry(8, 8, ancho_cam - 16, alto_panel - 16)

        # Video (derecha)
        x_vid = x_cam + ancho_cam + gap
        self.recuadro_vid.setGeometry(x_vid, y_pan, ancho_vid, alto_panel)
        # El view_vid con margen interno para crear el efecto limpio
        self.view_vid.setGeometry(8, 8, ancho_vid - 16, alto_panel - 16)

        # Banners (debajo del video, mismo ancho)
        banner_h = 42
        banner_y = y_pan + alto_panel + 16
        
        # Banner ROJO (espera)
        self.banner_rojo.setGeometry(x_vid, banner_y, ancho_vid, banner_h)
        self.banner_rojo_lbl.setGeometry(0, 0, ancho_vid, banner_h)
        
        # Banner VERDE (capture respuesta)
        self.banner_verde.setGeometry(x_vid, banner_y, ancho_vid, banner_h)
        self.banner_verde_lbl.setGeometry(0, 0, ancho_vid, banner_h)

        # Recoloca overlay para que siga al recuadro de video
        self._recolocar_overlay()
        
        # Recolocar estado de gestos
        self._recolocar_estado_gestos()
        
        # Recolocar ventana de error
        if self.ventana_error.isVisible():
            self._recolocar_ventana_error()

    def _actualizar_barra_pixmap(self):
        """
        Escala la imagen de la barra para que cubra todo el área
        (comportamiento tipo 'background-size: cover').
        """
        if not self.barra_pix_original or self.barra_pix_original.isNull():
            return

        w = self.barra.width()
        h = self.barra.height()
        if w <= 0 or h <= 0:
            return

        # KeepAspectRatioByExpanding => cubre todo el área, recortando si es necesario
        scaled = self.barra_pix_original.scaled(
            w, h,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        self.barra.setPixmap(scaled)

    def _recolocar_overlay(self):
        # Overlay ocupa ~90% del recuadro de video
        w = self.recuadro_vid.width() - 40
        h = self.recuadro_vid.height() - 40
        self.overlay.setGeometry(20, 20, w, h)
        self.lbl_overlay.setGeometry(12, 12, w - 24, h - 24)

    # =================== Cierre ===================
    def closeEvent(self, ev):
        try:
            self._overlay_timer.stop()
            self.overlay.hide()
        except Exception:
            pass
        try:
            self._error_timer.stop()
            self.ventana_error.hide()
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
        try:
            if self.inferencia:
                self.inferencia.liberar()
        except Exception:
            pass
        ev.accept()
