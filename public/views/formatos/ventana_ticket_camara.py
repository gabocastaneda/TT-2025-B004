# -*- coding: utf-8 -*-
# public/views/formatos/ventana_ticket_camara.py
import cv2
import time
import mediapipe as mp
from pathlib import Path

from PyQt5.QtWidgets import (QMainWindow, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
                             QWidget, QScrollArea, QGraphicsDropShadowEffect)
from PyQt5.QtGui import (QPixmap, QImage, QFont, QColor, QPainter, QPen, 
                         QBrush, QPainterPath)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRect

# ==============================================================================
# CLASE: WIDGET DE PRODUCTO (ESTILO TARJETA 3D)
# ==============================================================================
class ItemProducto(QFrame):
    def __init__(self, data_producto: dict, base_img_path: Path, altura_asignada: int):
        super().__init__()
        self.data = data_producto
        self.id_prod = data_producto.get("idProducto")
        self.seleccionado = False
        self.progreso = 0.0 
        self.setFixedHeight(altura_asignada)

        # ESTILO: Tarjeta con bordes curvos y ligero degradado para efecto 3D
        self.setStyleSheet(f"""
            ItemProducto {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f0f0f0);
                border: 1px solid #c0c0c0;
                border-radius: 15px;
                margin: 4px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)

        layout_main = QHBoxLayout(self)
        layout_main.setContentsMargins(10, 5, 15, 5); layout_main.setSpacing(10)

        img_size = int(altura_asignada * 0.75)
        if img_size > 70: img_size = 70
        
        self.lbl_img = QLabel(self)
        self.lbl_img.setFixedSize(img_size, img_size); self.lbl_img.setScaledContents(True)
        img_rel = data_producto.get("imagen", "")
        if img_rel:
            full_path = base_img_path / img_rel
            if not full_path.exists(): full_path = base_img_path / Path(img_rel).name
            if full_path.exists(): self.lbl_img.setPixmap(QPixmap(str(full_path)))
            else: self.lbl_img.setText("Sin Foto")
        layout_main.addWidget(self.lbl_img)

        layout_texto = QVBoxLayout()
        layout_texto.setSpacing(2); layout_texto.setAlignment(Qt.AlignVCenter)
        self.lbl_nombre = QLabel(data_producto.get("NombreProducto", "Producto"), self)
        fsize = 12 if altura_asignada > 70 else 10
        self.lbl_nombre.setFont(QFont("Segoe UI", fsize, QFont.Bold))
        self.lbl_nombre.setStyleSheet("color: #2c3e50;"); self.lbl_nombre.setWordWrap(True)
        layout_texto.addWidget(self.lbl_nombre)
        
        self.lbl_id = QLabel(f"ID: {self.id_prod}", self)
        self.lbl_id.setFont(QFont("Consolas", 9)); self.lbl_id.setStyleSheet("color: #7f8c8d;")
        layout_texto.addWidget(self.lbl_id)
        layout_main.addLayout(layout_texto, stretch=1)

        precio = data_producto.get('PrecioVenta', 0.0)
        self.lbl_precio = QLabel(f"${precio:,.2f}", self)
        fprice = 14 if altura_asignada > 70 else 12
        self.lbl_precio.setFont(QFont("Segoe UI", fprice, QFont.Bold))
        self.lbl_precio.setStyleSheet("color: #e74c3c;"); self.lbl_precio.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_precio.setMinimumWidth(80) 
        layout_main.addWidget(self.lbl_precio)

        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(10); sombra.setColor(QColor(0, 0, 0, 40)); sombra.setOffset(2, 2)
        self.setGraphicsEffect(sombra)

    def actualizar_progreso(self, valor): self.progreso = valor; self.update()

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath(); rect = self.rect()
        path.addRoundedRect(0, 0, rect.width(), rect.height(), 15, 15)
        painter.setClipPath(path)
        super().paintEvent(event)

        if self.progreso > 0:
            painter.setPen(Qt.NoPen); painter.setBrush(QBrush(QColor(255, 193, 7, 120)))
            painter.drawRect(0, 0, int(self.width() * self.progreso), self.height())
            if self.progreso >= 1.0:
                painter.setBrush(Qt.NoBrush); painter.setPen(QPen(QColor(255, 160, 0), 3))
                painter.drawPath(path)


# ==============================================================================
# VENTANA PRINCIPAL
# ==============================================================================
class VentanaTicketCamara(QMainWindow):
    producto_seleccionado = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consulta Interactiva")
        self.resize(1280, 720)
        
        self.cap = None
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        self.modo_seleccion = False
        self.items_productos = []
        self.producto_bajo_cursor = None
        self.tiempo_inicio_hover = 0
        self.TIEMPO_PARA_SELECCIONAR = 2.0 
        self.left_hand_prev_y = None
        self.left_hand_active_scroll = False
        
        self.segundos_restantes = 10
        self.timer_countdown = QTimer(self)
        self.timer_countdown.timeout.connect(self._on_tick_countdown)
        
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self._actualizar_frame)
        
        self.dir_images = Path(__file__).resolve().parents[2] / "images"
        self._init_ui(); self._recolocar()

    def _init_ui(self):
        fpath = self.dir_images / "fondo.png"
        bg = f"url({str(fpath).replace(chr(92), '/')})" if fpath.exists() else "#2c3e50"
        self.setStyleSheet(f"QMainWindow {{ background-image: {bg}; background-repeat: no-repeat; background-position: center; background-attachment: fixed; }} QScrollBar:vertical {{ width: 20px; background: #f0f0f0; }} QScrollBar::handle:vertical {{ background: #c0c0c0; border-radius: 10px; }}")

        self.barra = QLabel(self)
        self.titulo = QLabel("TT 225-B004", self)
        self.titulo.setAlignment(Qt.AlignCenter); self.titulo.setStyleSheet("color: white; letter-spacing: 3px;") 
        self.titulo.setFont(QFont("Arial Black", 24, QFont.Bold))

        self.recuadro = QFrame(self)
        self.recuadro.setStyleSheet("QFrame { background: black; border: 8px solid #e7c14d; border-radius: 20px; }")
        
        self.view_cam = QLabel(self.recuadro)
        self.view_cam.setAlignment(Qt.AlignCenter); self.view_cam.setScaledContents(True)
        self.view_cam.setStyleSheet("background: transparent; border: none; border-radius: 12px;")

        self.contenedor_flotante = QWidget(self.recuadro)
        self.contenedor_flotante.setStyleSheet("background: transparent;")
        
        # --- VISTA A: TICKET PRINCIPAL (Estilo 3D Unificado) ---
        self.lbl_ticket = QLabel(self.contenedor_flotante)
        self.lbl_ticket.setWordWrap(True)
        self.lbl_ticket.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_ticket.setStyleSheet("""
            QLabel {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f0f0f0);
                color: #000000;
                padding: 25px;
                border: 1px solid #c0c0c0;
                border-radius: 15px; 
                font-family: 'Consolas', monospace;
            }
        """)
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(30); sombra.setColor(QColor(0,0,0,150)); sombra.setOffset(10, 15)
        self.lbl_ticket.setGraphicsEffect(sombra)

        self.lbl_contador = QLabel(self.lbl_ticket)
        self.lbl_contador.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_contador.setStyleSheet("color: #e74c3c; background: transparent; border: none;")
        self.lbl_contador.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.lbl_contador.hide()
        
        # --- VISTA B: LISTA PRODUCTOS ---
        self.scroll_area = QScrollArea(self.contenedor_flotante)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.hide()

        self.widget_lista = QWidget()
        self.layout_lista = QVBoxLayout(self.widget_lista)
        self.layout_lista.setContentsMargins(10, 10, 25, 10); self.layout_lista.setSpacing(10)
        self.scroll_area.setWidget(self.widget_lista)
        
        self.cursor_virtual = QLabel(self.recuadro)
        self.cursor_virtual.setFixedSize(30, 30)
        self.cursor_virtual.setStyleSheet("background-color: rgba(231, 76, 60, 0.9); border: 2px solid white; border-radius: 15px;")
        self.cursor_virtual.hide()

    def iniciar_camara_segura(self):
        self.intentos_camara = 0; self._intentar_abrir_camara()

    def _intentar_abrir_camara(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened(): self.cap = cv2.VideoCapture(0)

        if self.cap.isOpened():
            print("[CAMARA] Iniciada.")
            self.timer_cam.start(30)
            self.segundos_restantes = 10
            self._actualizar_contador_visual()
            self.lbl_contador.show()
            self.timer_countdown.start(1000) 
        else:
            self.intentos_camara += 1
            if self.intentos_camara < 5: QTimer.singleShot(500, self._intentar_abrir_camara)

    def _on_tick_countdown(self):
        self.segundos_restantes -= 1
        self._actualizar_contador_visual()
        if self.segundos_restantes <= 0:
            self.timer_countdown.stop()
            self._activar_fase_seleccion()

    def _actualizar_contador_visual(self):
        self.lbl_contador.setText(f"[ INICIO EN: {self.segundos_restantes:02d} s ]")
        w_t = self.lbl_ticket.width(); h_t = self.lbl_ticket.height()
        self.lbl_contador.setGeometry(w_t - 240, h_t - 45, 220, 35)

    def configurar_datos(self, html_ticket, lista_productos):
        self.lbl_ticket.setText(html_ticket); self.lbl_ticket.show()
        for i in reversed(range(self.layout_lista.count())): 
            w = self.layout_lista.itemAt(i).widget(); 
            if w: w.setParent(None)
        
        self.items_productos = []
        h_disp = self.contenedor_flotante.height()
        n_visible = min(len(lista_productos), 6) # Max 6
        if n_visible > 0:
            h = int((h_disp - 40) / n_visible)
            h = max(min(h, 130), 85)
        else: h = 100

        for p in lista_productos:
            item = ItemProducto(p, self.dir_images, h)
            self.layout_lista.addWidget(item)
            self.items_productos.append(item)
        self.layout_lista.addStretch()

    def _activar_fase_seleccion(self):
        self.modo_seleccion = True; self.lbl_ticket.hide(); self.lbl_contador.hide()
        self.scroll_area.show(); self.cursor_virtual.show()

    def liberar_recursos(self):
        self.timer_cam.stop(); self.timer_countdown.stop()
        if self.cap: self.cap.release(); self.cap = None
        if self.hands: self.hands.close(); self.hands = None
        self.modo_seleccion = False

    def _is_palm_open(self, lm):
        return sum(1 for t, p in zip([8,12,16,20], [6,10,14,18]) if lm.landmark[t].y < lm.landmark[p].y) >= 3

    def _actualizar_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret: return
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            x_c, y_c = -1, -1
            
            if self.modo_seleccion and self.hands:
                res = self.hands.process(rgb)
                if res.multi_hand_landmarks and res.multi_handedness:
                    for i, lm in enumerate(res.multi_hand_landmarks):
                        lbl = res.multi_handedness[i].classification[0].label
                        if lbl == "Right": # Cursor
                            tip = lm.landmark[8]
                            cx, cy = int(tip.x * w), int(tip.y * h)
                            cv2.circle(rgb, (cx, cy), 10, (255, 50, 50), -1)
                            vr = self.view_cam.geometry()
                            x_c = vr.x() + int(cx * (vr.width()/w))
                            y_c = vr.y() + int(cy * (vr.height()/h))
                        elif lbl == "Left": # Scroll
                            wrist = lm.landmark[0]
                            cy_p = int(wrist.y * h)
                            if self._is_palm_open(lm):
                                cv2.circle(rgb, (int(wrist.x*w), cy_p), 25, (50, 255, 50), 3)
                                if self.left_hand_active_scroll:
                                    if self.left_hand_prev_y is not None:
                                        diff = cy_p - self.left_hand_prev_y
                                        if abs(diff) > 2:
                                            b = self.scroll_area.verticalScrollBar()
                                            b.setValue(b.value() + int(diff * 4.0))
                                    self.left_hand_prev_y = cy_p
                                else:
                                    self.left_hand_active_scroll = True; self.left_hand_prev_y = cy_p
                            else:
                                cv2.circle(rgb, (int(wrist.x*w), cy_p), 15, (50, 50, 255), -1)
                                self.left_hand_active_scroll = False

            qimg = QImage(rgb.data, w, h, w*3, QImage.Format_RGB888)
            self.view_cam.setPixmap(QPixmap.fromImage(qimg).scaled(self.view_cam.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            if x_c != -1:
                self.cursor_virtual.move(x_c - 15, y_c - 15); self.cursor_virtual.raise_()
                self._procesar_interaccion(x_c, y_c)

    def _procesar_interaccion(self, cx, cy):
        pos = self.recuadro.mapToGlobal(QPoint(cx, cy))
        hov = None
        for it in self.items_productos:
            if it.isVisible() and QRect(it.mapToGlobal(QPoint(0,0)), it.size()).contains(pos): hov = it; break
        
        if hov:
            if self.producto_bajo_cursor == hov:
                prog = min((time.time() - self.tiempo_inicio_hover) / self.TIEMPO_PARA_SELECCIONAR, 1.0)
                hov.actualizar_progreso(prog)
                if prog >= 1.0 and not hov.seleccionado: self._confirmar_seleccion(hov)
            else:
                if self.producto_bajo_cursor: self.producto_bajo_cursor.actualizar_progreso(0.0)
                self.producto_bajo_cursor = hov; self.tiempo_inicio_hover = time.time(); hov.actualizar_progreso(0.1)
        else:
            if self.producto_bajo_cursor: self.producto_bajo_cursor.actualizar_progreso(0.0)
            self.producto_bajo_cursor = None

    def _confirmar_seleccion(self, item):
        item.seleccionado = True
        item.setStyleSheet("ItemProducto { background-color: #d4edda; border: 2px solid #28a745; border-radius: 15px; }")
        self.liberar_recursos(); self.cursor_virtual.hide()
        self.producto_seleccionado.emit(int(item.id_prod))

    def resizeEvent(self, ev):
        self._recolocar()
        if not self.lbl_ticket.isHidden(): self._actualizar_contador_visual()
        super().resizeEvent(ev)

    def _recolocar(self):
        w, h = self.width(), self.height()
        self.barra.setGeometry(0, 0, w, int(h*0.1)); self.titulo.setGeometry(0, 0, w, int(h*0.1))
        tw = min(w-60, int((h-int(h*0.1)-50)*(4/3)))
        self.recuadro.setGeometry((w-tw)//2, int(h*0.1)+20, tw, h-int(h*0.1)-50)
        self.view_cam.setGeometry(8, 8, tw-16, self.recuadro.height()-16)
        fw, fh = int(tw*0.4), int(self.recuadro.height()*0.9)
        self.contenedor_flotante.setGeometry(tw-fw-20, (self.recuadro.height()-fh)//2, fw, fh)
        self.lbl_ticket.setGeometry(0,0,fw,fh); self.scroll_area.setGeometry(0,0,fw,fh); self.cursor_virtual.raise_()

    def closeEvent(self, ev): self.liberar_recursos(); super().closeEvent(ev)