# -*- coding: utf-8 -*-
# public/views/formatos/interaccion.py
import re, cv2, hashlib, requests
from pathlib import Path
from typing import Optional, Callable

from PyQt5.QtWidgets import QMainWindow, QFrame, QLabel, QGraphicsDropShadowEffect, QMessageBox
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect

from public.views.hilo_video import HiloVideo
from public.views.config.mapa_interaccion import FILE_IDS
try:
    from public.views.config.drive_config import drive_api_url
except ImportError:
    def drive_api_url(file_id): return f"https://mock.drive.api/{file_id}"


# Coincide con las URLs de la Drive API
_DRIVE_RE = re.compile(r"https://www\.googleapis\.com/drive/v3/files/([^?]+)")

class VentanaInteraccion(QMainWindow):
    redimensionada = pyqtSignal()
    video_terminado = pyqtSignal()
    gesto_detectado = pyqtSignal(str)
    
    # NUEVA SEÑAL: Se emite cuando termina el tiempo de la alerta de ayuda (6s)
    alerta_ayuda_terminada = pyqtSignal()
    
    

    def __init__(self, src_inicial: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Interacción")
        # Resize removido
        
        # Control de estado para el bloqueo
        self.terminal_bloqueada = True
        
        # Paths
        self.dir_root = Path(__file__).resolve().parents[3]
        self.dir_public = self.dir_root / "public"
        self.dir_backend = self.dir_root / "backend" 
        
        self.dir_videos = self.dir_public / "videos"
        self.dir_videos.mkdir(parents=True, exist_ok=True)
        
        self.dir_images = self.dir_public / "images" 
        self.dir_images.mkdir(parents=True, exist_ok=True)
        
        # --- DEBUG AL INICIAR ---
        print(f"[INIT] Raíz del proyecto: {self.dir_root}")
        
        # Verificar si el modelo existe
        modelo_path = self.dir_backend / "modelo.pkl"
        
        fondo_path = self.dir_images / "fondo.png"
        
        # Configurar imagen de fondo
        if fondo_path.exists():
            self.setStyleSheet(f"""
                QMainWindow {{
                    border-image: url({str(fondo_path).replace(chr(92), '/')}) 0 0 0 0 stretch stretch;
                }}
            """)
        else:
            self.setStyleSheet("QMainWindow { background: #2c3e50; }")

        # --- Barra superior ---
        self.barra = QLabel(self)
        self.barra.setObjectName("barraSuperior")
        self.barra.setScaledContents(False)
        self.barra_pix_original: Optional[QPixmap] = None

        barra_path = self.dir_images / "barra.png"
        if barra_path.exists():
            try:
                self.barra_pix_original = QPixmap(str(barra_path).replace("\\", "/"))
            except Exception as e:
                self.barra_pix_original = None

        if not self.barra_pix_original or self.barra_pix_original.isNull():
            self.barra.setStyleSheet("background: #8B1538; border-radius: 0px;")
        else:
            self.barra.setStyleSheet("background: transparent;")

        self.titulo = QLabel("TT 225-B004", self)
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("color: white; letter-spacing: 3px;")
        self.titulo.setFont(QFont("Arial Black", 24, QFont.Bold))

        # --- Recuadro cámara (izq) ---
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
        self.view_cam.setText("Cámara activa")

        # --- Recuadro video RESP (der) ---
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
        self.view_vid.setText("Video")

        # --- Banner ROJO (Tipografía Arial, Mixed Case) ---
        self.banner_rojo = QFrame(self)
        self.banner_rojo.setStyleSheet("background: #c0392b; border-radius: 12px; border: none;")
        self.banner_rojo_lbl = QLabel("⚠️ Por favor, espere para capturar su respuesta ⚠️", self.banner_rojo)
        self.banner_rojo_lbl.setAlignment(Qt.AlignCenter)
        self.banner_rojo_lbl.setStyleSheet(
            "color: #ffffff; font-family: 'Arial'; font-size: 22px; font-weight: bold; border: none;"
        )
        self.banner_rojo.hide()

        # --- Banner VERDE (Tipografía Arial, Mixed Case) ---
        self.banner_verde = QFrame(self)
        self.banner_verde.setStyleSheet("background: #27ae60; border-radius: 12px; border: none;")
        self.banner_verde_lbl = QLabel("✓ Capture su respuesta ✓", self.banner_verde)
        self.banner_verde_lbl.setAlignment(Qt.AlignCenter)
        self.banner_verde_lbl.setStyleSheet(
            "color: #ffffff; font-family: 'Arial'; font-size: 22px; font-weight: bold; border: none;"
        )
        self.banner_verde.hide()

        # --- Ventana flotante de error ---
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

        # --- Overlay MEJORADO ---
        self.overlay = QFrame(self.recuadro_vid)
        self.overlay.setStyleSheet("""
            QFrame {
                background: rgba(15, 15, 15, 255); 
                border: 2px solid #e7c14d;
                border-radius: 15px;
            }
        """)
        self.overlay.hide()
        
        # Cronómetro
        self.lbl_cronometro = QLabel("5s", self.overlay)
        self.lbl_cronometro.setAlignment(Qt.AlignCenter)
        self.lbl_cronometro.setStyleSheet("""
            QLabel {
                background-color: #f1c40f; 
                color: #2c3e50;
                font-family: 'Arial';
                font-size: 18px;
                font-weight: 900;
                border-radius: 20px; 
                padding: 5px 15px;
                border: 2px solid #f39c12;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.lbl_cronometro.setGraphicsEffect(shadow)
        
        # Imagen del producto
        self.lbl_producto_img = QLabel(self.overlay)
        self.lbl_producto_img.setAlignment(Qt.AlignCenter)
        self.lbl_producto_img.setScaledContents(True) 
        self.lbl_producto_img.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: white;
                font-size: 14px;
            }
        """)
        self.lbl_producto_img.setText("IMAGEN NO CARGADA")
        self.lbl_producto_img.hide()
        
        # Texto del ticket
        self.lbl_overlay = QLabel(self.overlay)
        self.lbl_overlay.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_overlay.setWordWrap(True)
        self.lbl_overlay.setStyleSheet(self._get_overlay_style(font_size=15))
        
        self._overlay_timer = QTimer(self)
        self._overlay_timer.setSingleShot(True)
        self._overlay_cb: Optional[Callable[[], None]] = None
        self._overlay_timer.timeout.connect(self._cerrar_overlay)
        
        self._cronometro_timer = QTimer(self)
        self._cronometro_timer.timeout.connect(self._actualizar_cronometro)
        self._tiempo_restante = 0

        # --- Cámara ---
        self.cap_cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap_cam.isOpened():
            self.cap_cam = cv2.VideoCapture(0)
            
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self._tick_cam)
        self.timer_cam.start(30)

        self.cap_resp = None
        self.hilo_resp: Optional[HiloVideo] = None

        # --- Inferencia ---
        self.inferencia = None
        self.modo_gestos = False
        
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
        
        self._verificar_dependencias()
        self._inicializar_inferencia_gestos_estricta()

        self._modo_reproduccion = False
        
        # Maximizar y recolocar
        self.showMaximized()
        self._recolocar()
        self.redimensionada.connect(self._recolocar)

        if src_inicial:
            self.set_modo_reproduccion(True)
            self.cambiar_video_unidad(src_inicial, nombre_resp="resp1")

    def _verificar_dependencias(self):
        print("\n" + "="*50)
        print("🔍 VERIFICACIÓN DE DEPENDENCIAS")
        print("="*50)
        
        try:
            import mediapipe as mp
            print("✅ MediaPipe: OK")
        except Exception as e:
            print(f"❌ MediaPipe: ERROR - {e}")
            
        try:
            import google.protobuf
            print(f"✅ Protobuf: OK (v{google.protobuf.__version__})")
        except Exception as e:
            print(f"❌ Protobuf: ERROR - {e}")
            
        modelo_path = self.dir_backend / "modelo.pkl"
        print(f"📁 Modelo: {'✅ EXISTE' if modelo_path.exists() else '❌ NO EXISTE'}")
        print("="*50)

    def bloquear_terminal(self):
        self.terminal_bloqueada = True
        self.set_modo_gestos(False)
        
    def desbloquear_terminal(self):
        self.terminal_bloqueada = False
        self.set_modo_gestos(True)
        
    def cambiar_estado_terminal(self, bloqueada: bool):
        if bloqueada:
            self.bloquear_terminal()
        else:
            self.desbloquear_terminal()

    def _inicializar_inferencia_gestos_estricta(self):
        try:
            modelo_path = self.dir_backend / "modelo.pkl"
            
            if not modelo_path.exists():
                print(f"❌ [GESTOS] ERROR CRÍTICO: Modelo no encontrado en {modelo_path}")
                raise FileNotFoundError(f"Modelo no encontrado: {modelo_path}")
            
            try:
                import mediapipe as mp
                from backend.inferencia import InferenciaGestos
                
                print("[GESTOS] ✅ Cargando modelo real...")
                self.inferencia = InferenciaGestos(str(modelo_path))
                        
                self.inferencia.inicializar_deteccion()
                self.inferencia.set_callback_prediccion(self._on_gesto_detectado)
                
                if hasattr(self.inferencia, 'modelo_data') and self.inferencia.modelo_data:
                    model = self.inferencia.modelo_data.get('model', None)
                    if model:
                        model_type = type(model).__name__
                        if "Simulado" in model_type:
                            raise RuntimeError("Modelo simulado detectado cuando se esperaba modelo real")
                        else:
                            print("✅ [GESTOS] Modelo real cargado correctamente")
                else:
                    raise RuntimeError("No se pudo cargar el modelo_data en la inferencia")
                
            except Exception as e:
                print(f"❌ Error inicializando componentes: {e}")
                raise
                    
        except Exception as e:
            print(f"❌ ERROR CRÍTICO inicializando inferencia: {e}")
            self.inferencia = None
            self._mostrar_error_modelo_faltante(str(e))
            raise RuntimeError(f"No se pudo inicializar el sistema de gestos: {e}") from e

    def _mostrar_error_modelo_faltante(self, mensaje: str):
        error_msg = f"""
        ❌ ERROR CRÍTICO: Modelo no disponible
        Detalles: {mensaje}
        Verifique que 'modelo.pkl' exista.
        """
        QMessageBox.critical(self, "Error de Modelo", error_msg)

    def _get_overlay_style(self, font_size=15):
        return f"""
            QLabel {{
                color: #ecf0f1;
                padding: 10px;
                border: none;
                font-family: 'Consolas', monospace;
                font-size: {font_size}px;
                font-weight: bold;
                background: transparent;
            }}
        """
        
    def mostrar_indicador_concatenacion(self, mensaje: str):
        """Muestra indicador de concatenación de dígitos"""
        self.label_estado_gestos.show()
        self._actualizar_estado_gestos(mensaje, "#3498db")

    def actualizar_indicador_concatenacion(self, mensaje: str):
        """Actualiza el indicador de concatenación"""
        self._actualizar_estado_gestos(mensaje, "#3498db")

    def ocultar_indicador_concatenacion(self):
        """Oculta el indicador de concatenación"""
        self.label_estado_gestos.hide()

    def mostrar_error_digito_invalido(self):
        """Muestra error cuando se detecta un gesto no numérico en estado numérico"""
        # Mostrar error temporal
        self._actualizar_estado_gestos("❌ Solo se aceptan dígitos (0-9)", "#e74c3c")
        
        # Programar para volver al estado normal después de 2 segundos
        QTimer.singleShot(2000, lambda: self._actualizar_estado_gestos(
            "Esperando dígitos...", "#3498db"
        ))

    def mostrar_error_captura(self):
        """Muestra el error estándar de captura"""
        try:
            self.lbl_error.setText("⚠️RESPUESTA NO CAPTURADA\nPOR FAVOR, CAPTURE NUEVAMENTE⚠️")
            self._recolocar_ventana_error()
            self.ventana_error.show()
            self.ventana_error.raise_()
            self._error_timer.start(5000)
        except Exception as e:
            pass

    def mostrar_alerta_ayuda_asociado(self):
        """
        Muestra la alerta crítica cuando se alcanza el límite de errores.
        Dura 6 segundos y emite señal al finalizar.
        """
        try:
            texto = "⚠️ Notamos que no puedes realizar correctamente tu captura, un asociado vendrá a apoyarte ⚠️"
            self.lbl_error.setText(texto)
            self._recolocar_ventana_error()
            self.ventana_error.show()
            self.ventana_error.raise_()
            
            # Detenemos cualquier timer anterior
            self._error_timer.stop()
            try:
                self._error_timer.timeout.disconnect()
            except: pass
            
            # Definimos la función de finalización
            def _on_finish():
                self._cerrar_ventana_error()
                self.alerta_ayuda_terminada.emit()
                # Restaurar comportamiento normal del timer
                try: self._error_timer.timeout.disconnect()
                except: pass
                self._error_timer.timeout.connect(self._cerrar_ventana_error)

            self._error_timer.timeout.connect(_on_finish)
            self._error_timer.start(6000) # 6 segundos exactos
            
        except Exception as e:
            print(f"Error mostrando alerta ayuda: {e}")
            # Si falla, emitimos la señal para no bloquear el flujo
            self.alerta_ayuda_terminada.emit()

    def _cerrar_ventana_error(self):
        self.ventana_error.hide()

    def _recolocar_ventana_error(self):
        error_width = 450
        error_height = 150
        x = (self.width() - error_width) // 2
        y = (self.height() - error_height) >> 1
        self.ventana_error.setGeometry(x, y, error_width, error_height)
        self.lbl_error.setGeometry(0, 0, error_width, error_height)

    def _actualizar_cronometro(self):
        if self._tiempo_restante > 0:
            self._tiempo_restante -= 1
            self.lbl_cronometro.setText(f"⏱ {self._tiempo_restante}s")
        else:
            self._cronometro_timer.stop()

    def set_modo_gestos(self, activar: bool):
        if self.inferencia is None:
            return
            
        if self.terminal_bloqueada:
            activar = False
            
        self.modo_gestos = activar
        if activar:
            self.label_estado_gestos.show()
        else:
            self.label_estado_gestos.hide()

    def _on_gesto_detectado(self, gesto: str):
        self.gesto_detectado.emit(gesto)

    def _actualizar_estado_gestos(self, mensaje: str, color: str = "#3498db"):
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
        
        # Ajustar tamaño según contenido
        fm = self.label_estado_gestos.fontMetrics()
        text_width = fm.width(mensaje) + 20
        self.label_estado_gestos.setFixedWidth(min(text_width, 400))
        
        self._recolocar_estado_gestos()

    def _recolocar_estado_gestos(self):
        if self.label_estado_gestos.isVisible():
            label_width = 300
            label_height = 40
            x = 15
            y = self.recuadro_cam.height() - label_height - 15
            self.label_estado_gestos.setGeometry(x, y, label_width, label_height)

    def _tick_cam(self):
        if not self.cap_cam or not self.cap_cam.isOpened():
            self.view_cam.setText("CÁMARA NO DISPONIBLE")
            return
            
        try:
            ok, frame = self.cap_cam.read()
            if not ok: return
                
            frame_procesado = frame
            estado_mensaje = "Cámara activa"
            color_estado = "#3498db"
            
            if self.terminal_bloqueada:
                estado_mensaje = "🔒 Terminal bloqueada"
                self.label_estado_gestos.hide()
                
            elif self.modo_gestos and self.inferencia:
                try:
                    frame_procesado, pred, conf, estado = self.inferencia.procesar_frame(frame)
                    
                    estados_config = {
                        "SIMULACION": ("🔧 MODO SIMULACIÓN", "#f39c12"),
                        "RECONOCIDO": (f"✅ {pred} ({conf*100:.1f}%)", "#27ae60"),
                        "GRABANDO": (f"📹 {pred}", "#e67e22"),
                        "ESPERANDO": ("🔄 Esperando gesto...", "#95a5a6"),
                        "MANO": ("✋ Mano detectada", "#9b59b6"),
                        "ERROR": ("❌ Error detección", "#e74c3c"),
                        "PROCESANDO": ("⏳ Procesando...", "#3498db")
                    }
                    
                    for key, (mensaje, color) in estados_config.items():
                        if key in estado.upper():
                            estado_mensaje = mensaje
                            color_estado = color
                            break
                    else:
                        estado_mensaje = f"{estado}: {pred}"
                        color_estado = "#f39c12"
                        
                except Exception as e:
                    frame_procesado = cv2.flip(frame, 1)
                    estado_mensaje = "❌ Error en gestos"
                    color_estado = "#e74c3c"
            else:
                frame_procesado = cv2.flip(frame, 1)
                if not self.modo_gestos:
                    self.label_estado_gestos.hide()
                    estado_mensaje = ""
                    color_estado = ""

            self._actualizar_estado_gestos(estado_mensaje, color_estado)

            rgb_image = cv2.cvtColor(frame_procesado, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            if self.view_cam.width() > 0 and self.view_cam.height() > 0:
                pixmap = QPixmap.fromImage(qimg)
                scaled_pixmap = pixmap.scaled(
                    self.view_cam.width(), self.view_cam.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.view_cam.setPixmap(scaled_pixmap)
            else:
                self.view_cam.setPixmap(QPixmap.fromImage(qimg))
                
        except Exception:
            pass

    def cambiar_video_unidad(self, src: Optional[str], nombre_resp: Optional[str] = None):
        self._cerrar_overlay() 

        try:
            if self.hilo_resp: self.hilo_resp.stop()
        except: pass
        try:
            if self.cap_resp: self.cap_resp.release()
        except: pass
        
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
        self.set_modo_reproduccion(False)
        self._emitir_terminado()

    def _emitir_terminado(self):
        try: self.video_terminado.emit()
        except: pass

    def mostrar_overlay_texto(self, texto: str, ms: int = 10_000, on_done: Optional[Callable[[], None]] = None, producto_data: Optional[dict] = None):
        try:
            self.lbl_overlay.setText(texto)
            is_product_mode = producto_data is not None and 'imagen' in producto_data and producto_data['imagen']
            
            if is_product_mode:
                raw_path = str(producto_data['imagen'])
                fname = Path(raw_path).name
                final_path = None
                
                # Búsqueda recursiva
                try:
                    encontrados = list(self.dir_backend.rglob(fname))
                    if encontrados: final_path = encontrados[0]
                except: pass
                
                if not final_path:
                    try:
                        encontrados = list(self.dir_public.rglob(fname))
                        if encontrados: final_path = encontrados[0]
                    except: pass
                
                if final_path:
                    pix = QPixmap(str(final_path))
                    if not pix.isNull():
                        self.lbl_producto_img.setPixmap(pix)
                        self.lbl_producto_img.setText("") 
                        self.lbl_producto_img.show()
                    else:
                        self.lbl_producto_img.setText(f"ERROR: Archivo dañado")
                        self.lbl_producto_img.show()
                else:
                    self.lbl_producto_img.setText(f"NO ENCONTRADO:\n{fname}")
                    self.lbl_producto_img.show()
            else:
                self.lbl_producto_img.hide()
                self.lbl_producto_img.setText("IMAGEN NO CARGADA")

            font_size = 24 if is_product_mode else 15
            self.lbl_overlay.setStyleSheet(self._get_overlay_style(font_size=font_size))

            self._recolocar_overlay(is_product_mode=is_product_mode)
            
            self._tiempo_restante = ms // 1000
            self.lbl_cronometro.setText(f"⏱ {self._tiempo_restante}s")
            self._cronometro_timer.start(1000)
            
            self.overlay.show()
            self.lbl_cronometro.show()
            self.overlay.raise_()
            
            self._overlay_cb = on_done
            self._overlay_timer.start(max(1, int(ms)))
        except Exception as e:
            print(f"Error mostrando overlay: {e}")
            self.overlay.hide()
            if callable(on_done):
                on_done()

    def _cerrar_overlay(self):
        self._cronometro_timer.stop()
        self.overlay.hide()
        self.lbl_producto_img.hide()
        cb = self._overlay_cb
        self._overlay_cb = None
        if callable(cb):
            try: cb()
            except: pass

    def _asegurar_local(self, src: str, nombre_resp: Optional[str]) -> Optional[str]:
        if not (src.startswith("http://") or src.startswith("https://")):
            return str(Path(src)) if Path(src).is_file() else None

        fname = None
        if nombre_resp and re.fullmatch(r"resp\d{1,2}", nombre_resp):
            fname = f"{nombre_resp}.mp4"
        else:
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
        except Exception:
            if destino.exists(): destino.unlink(missing_ok=True)
            return None

    def set_modo_reproduccion(self, on: bool):
        self._modo_reproduccion = bool(on)
        # bloquear siempre modo gestos
        if on:
            self.set_modo_gestos(False)
            
        self.banner_rojo.setVisible(self._modo_reproduccion)
        self.banner_verde.setVisible(not self._modo_reproduccion)
        self.set_modo_gestos(True)
        self._recolocar()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.redimensionada.emit()

    def _recolocar(self):
        W, H = self.width(), self.height()
        barra_h = int(H * 0.1)
        self.barra.setGeometry(0, 0, W, barra_h)
        self.titulo.setGeometry(0, 0, W, barra_h)

        self._actualizar_barra_pixmap()

        margen_lateral = 60
        gap = 40
        alto_panel = int(H * 0.55)

        if self._modo_reproduccion:
            frac_cam = 0.35
            frac_vid = 0.65
        else:
            frac_cam = 0.50
            frac_vid = 0.50

        ancho_total = W - 2 * margen_lateral - gap
        ancho_cam = int(ancho_total * frac_cam)
        ancho_vid = int(ancho_total * frac_vid)

        x_cam = margen_lateral
        y_pan = barra_h + 60
        self.recuadro_cam.setGeometry(x_cam, y_pan, ancho_cam, alto_panel)
        self.view_cam.setGeometry(8, 8, ancho_cam - 16, alto_panel - 16)

        x_vid = x_cam + ancho_cam + gap
        self.recuadro_vid.setGeometry(x_vid, y_pan, ancho_vid, alto_panel)
        self.view_vid.setGeometry(8, 8, ancho_vid - 16, alto_panel - 16)

        banner_h = 42
        banner_y = y_pan + alto_panel + 16
        
        self.banner_rojo.setGeometry(x_vid, banner_y, ancho_vid, banner_h)
        self.banner_rojo_lbl.setGeometry(0, 0, ancho_vid, banner_h)
        
        self.banner_verde.setGeometry(x_vid, banner_y, ancho_vid, banner_h)
        self.banner_verde_lbl.setGeometry(0, 0, ancho_vid, banner_h)

        has_pixmap = (self.lbl_producto_img.pixmap() is not None and not self.lbl_producto_img.pixmap().isNull())
        has_error_txt = "NO ENCONTRADO" in self.lbl_producto_img.text() or "IMAGEN NO" in self.lbl_producto_img.text() or "ERROR" in self.lbl_producto_img.text()
        
        is_prod_mode = self.lbl_producto_img.isVisible() and (has_pixmap or has_error_txt)
        
        self._recolocar_overlay(is_product_mode=is_prod_mode)
        self._recolocar_estado_gestos()
        
        if self.ventana_error.isVisible():
            self._recolocar_ventana_error()

    def _actualizar_barra_pixmap(self):
        if not self.barra_pix_original or self.barra_pix_original.isNull():
            return
        w = self.barra.width()
        h = self.barra.height()
        if w <= 0 or h <= 0: return
        scaled = self.barra_pix_original.scaled(
            w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        self.barra.setPixmap(scaled)

    def _recolocar_overlay(self, is_product_mode: bool = False):
        w_overlay = self.recuadro_vid.width() - 40
        h_overlay = self.recuadro_vid.height() - 40
        
        self.overlay.setGeometry(20, 20, w_overlay, h_overlay)
        
        badge_w, badge_h = 80, 40
        self.lbl_cronometro.setGeometry(w_overlay - badge_w - 20, 20, badge_w, badge_h)
        
        if is_product_mode:
            text_margin = 20
            text_height = 140 
            text_y = 60 
            
            self.lbl_overlay.setGeometry(text_margin, text_y, w_overlay - (text_margin*2), text_height)
            self.lbl_overlay.setAlignment(Qt.AlignTop | Qt.AlignHCenter) 
            
            img_y = text_y + text_height + 10
            img_h = h_overlay - img_y - 20
            img_w = w_overlay - 40
            
            if img_h > 50:
                self.lbl_producto_img.setGeometry(20, img_y, img_w, img_h)
                curr_pix = self.lbl_producto_img.pixmap()
                if curr_pix and not curr_pix.isNull():
                    scaled = curr_pix.scaled(
                        self.lbl_producto_img.size(), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.lbl_producto_img.setPixmap(scaled)
            else:
                self.lbl_producto_img.hide()
        else:
            self.lbl_overlay.setGeometry(20, 70, w_overlay - 40, h_overlay - 90)
            self.lbl_overlay.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.lbl_producto_img.setGeometry(0, 0, 0, 0)
            self.lbl_producto_img.hide()

    def closeEvent(self, ev):
        try: self._overlay_timer.stop(); self._cronometro_timer.stop(); self.overlay.hide()
        except: pass
        try: self._error_timer.stop(); self.ventana_error.hide()
        except: pass
        try:
            if self.hilo_resp: self.hilo_resp.stop()
        except: pass
        try:
            if self.cap_resp: self.cap_resp.release()
        except: pass
        try: self.timer_cam.stop();
        except: pass
        try:
            if self.cap_cam: self.cap_cam.release()
        except: pass
        try:
            if self.inferencia: self.inferencia.liberar()
        except: pass
        ev.accept()