# -*- coding: utf-8 -*-
# public/views/formatos/ventana_ticket_camara.py
import cv2
import time
import mediapipe as mp
import math
from pathlib import Path

from PyQt5.QtWidgets import (QMainWindow, QLabel, QFrame, QVBoxLayout, 
                             QWidget, QScrollArea, QGraphicsDropShadowEffect)
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor, QPainter, QPen, QBrush
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRect

# ==============================================================================
# CLASE: WIDGET DE PRODUCTO (ESTILO RECIBO/TICKET)
# ==============================================================================
class ItemProducto(QFrame):
    def __init__(self, data_producto: dict, base_img_path: Path, altura_asignada: int):
        super().__init__()
        self.data = data_producto
        self.id_prod = data_producto.get("idProducto")
        self.seleccionado = False
        self.progreso = 0.0 
        
        # Guardamos la altura calculada
        self.setFixedHeight(altura_asignada)

        # ESTILO: Papel de recibo (Fondo blanco, borde inferior punteado)
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: none;
                border-bottom: 2px dashed #555555; /* Línea de corte de ticket */
                border-radius: 0px; /* Cuadrado como papel */
            }
        """)

        # --- CÁLCULO DE TAMAÑOS RELATIVOS ---
        # Calculamos tamaños basados en la altura asignada para que se vea bien
        # si es muy pequeño o muy grande.
        margen = 10
        img_size = int(altura_asignada * 0.8) # La imagen ocupa el 80% del alto
        if img_size > 80: img_size = 80 # Tope máximo de imagen
        
        # 1. Imagen (Izquierda)
        self.lbl_img = QLabel(self)
        self.lbl_img.setGeometry(margen, (altura_asignada - img_size)//2, img_size, img_size)
        self.lbl_img.setScaledContents(True)
        self.lbl_img.setStyleSheet("border: none; background: transparent;")
        
        img_rel = data_producto.get("imagen", "")
        if img_rel:
            full_path = base_img_path / img_rel
            if not full_path.exists():
                full_path = base_img_path / Path(img_rel).name
            
            if full_path.exists():
                self.lbl_img.setPixmap(QPixmap(str(full_path)))
            else:
                self.lbl_img.setText("Sin Foto")

        # Coordenada X donde empieza el texto
        x_text = margen + img_size + 15
        ancho_disp = 400 - x_text # Asumiendo un ancho base del contenedor flotante

        # 2. Nombre del Producto (Arriba)
        self.lbl_nombre = QLabel(self)
        self.lbl_nombre.setText(data_producto.get("NombreProducto", "Producto"))
        # Fuente estilo Ticket
        font_size_name = 12 if altura_asignada > 70 else 10
        self.lbl_nombre.setFont(QFont("Consolas", font_size_name, QFont.Bold))
        self.lbl_nombre.setStyleSheet("color: #000; border: none; background: transparent;")
        self.lbl_nombre.setGeometry(x_text, 10, 200, 25)

        # 3. ID (Abajo del nombre)
        self.lbl_id = QLabel(f"ID: {self.id_prod}", self)
        self.lbl_id.setFont(QFont("Consolas", 9))
        self.lbl_id.setStyleSheet("color: #555; border: none; background: transparent;")
        self.lbl_id.setGeometry(x_text, 35, 100, 20)

        # 4. Precio (Derecha, grande)
        self.lbl_precio = QLabel(f"${data_producto.get('PrecioVenta', 0.0):,.2f}", self)
        font_size_price = 14 if altura_asignada > 70 else 11
        self.lbl_precio.setFont(QFont("Consolas", font_size_price, QFont.Bold))
        self.lbl_precio.setStyleSheet("color: #000; border: none; background: transparent;")
        self.lbl_precio.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Pegado a la derecha
        w_parent = int(400 * 0.9) # Aproximación del ancho del contenedor padre
        self.lbl_precio.setGeometry(w_parent - 110, (altura_asignada - 40)//2, 100, 40)

    def actualizar_progreso(self, valor: float):
        self.progreso = valor
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Efecto de selección (Resaltador amarillo/naranja sobre el papel)
        if self.progreso > 0:
            # Relleno sutil que va creciendo
            painter.setPen(Qt.NoPen)
            fill_color = QColor(255, 200, 0, 100) # Amarillo ticket
            painter.setBrush(QBrush(fill_color))
            
            w_fill = int(self.width() * self.progreso)
            rect_fill = self.rect()
            rect_fill.setWidth(w_fill)
            painter.drawRect(rect_fill) # Rectángulo simple, sin bordes redondeados
            
            # Borde negro sólido al seleccionarse
            if self.progreso > 0.1:
                pen = QPen(QColor(0,0,0))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(self.rect().adjusted(1,1,-1,-1))


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
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        self.texto_ticket_cache = ""
        self.modo_seleccion = False
        self.items_productos = []
        self.producto_bajo_cursor = None
        self.tiempo_inicio_hover = 0
        self.TIEMPO_PARA_SELECCIONAR = 2.0 
        
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self._actualizar_frame)
        
        self.timer_fases = QTimer(self)
        self.timer_fases.setSingleShot(True)
        self.timer_fases.timeout.connect(self._activar_fase_seleccion)

        self.dir_public = Path(__file__).resolve().parents[2]
        self.dir_images = self.dir_public / "images"
        
        self._init_ui()
        self._recolocar()

    def _init_ui(self):
        fondo_path = self.dir_images / "fondo.png"
        estilo_fondo = f"background-image: url({str(fondo_path).replace(chr(92), '/')});" if fondo_path.exists() else "background: #2c3e50;"
        self.setStyleSheet(f"QMainWindow {{ {estilo_fondo} background-repeat: no-repeat; background-position: center; background-attachment: fixed; }} QScrollBar:vertical {{ width: 0px; }}")

        self.barra = QLabel(self)
        self.titulo = QLabel("TT 225-B004", self)
        self.titulo.setAlignment(Qt.AlignCenter); self.titulo.setStyleSheet("background: transparent; color: white; letter-spacing: 3px;"); self.titulo.setFont(QFont("Arial Black", 24, QFont.Bold))

        self.recuadro = QFrame(self)
        self.recuadro.setStyleSheet("QFrame { background: black; border: 8px solid #e7c14d; border-radius: 20px; }")
        self.view_cam = QLabel(self.recuadro)
        self.view_cam.setAlignment(Qt.AlignCenter); self.view_cam.setScaledContents(True); self.view_cam.setStyleSheet("background: transparent; border: none;")

        self.contenedor_flotante = QWidget(self.recuadro); self.contenedor_flotante.setStyleSheet("background: transparent;")
        
        # --- VISTA A: TICKET PRINCIPAL ---
        # Diseño mejorado: Sombra fuerte y bordes definidos
        self.lbl_ticket = QLabel(self.contenedor_flotante)
        self.lbl_ticket.setWordWrap(True)
        self.lbl_ticket.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_ticket.setStyleSheet("""
            QLabel {
                background-color: #ffffff; 
                color: #000000;
                padding: 20px;
                border: 1px solid #dcdcdc;
                font-family: 'Consolas', monospace; /* Fuente monoespaciada */
            }
        """)
        # Sombra pronunciada
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(25)
        sombra.setColor(QColor(0,0,0,180))
        sombra.setOffset(8, 8)
        self.lbl_ticket.setGraphicsEffect(sombra)
        
        # --- VISTA B: LISTA PRODUCTOS ---
        self.scroll_area = QScrollArea(self.contenedor_flotante)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.hide()

        self.widget_lista = QWidget()
        self.layout_lista = QVBoxLayout(self.widget_lista)
        self.layout_lista.setSpacing(0) # Sin espacio, pegados como ticket continuo
        self.layout_lista.setContentsMargins(0, 0, 0, 0)
        self.layout_lista.addStretch()
        self.scroll_area.setWidget(self.widget_lista)
        
        self.cursor_virtual = QLabel(self.recuadro); self.cursor_virtual.setFixedSize(30, 30); self.cursor_virtual.setStyleSheet("background-color: rgba(231, 76, 60, 0.8); border: 2px solid white; border-radius: 15px;"); self.cursor_virtual.hide()

    def iniciar_camara_segura(self):
        self.intentos_camara = 0
        self._intentar_abrir_camara()

    def _intentar_abrir_camara(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened(): self.cap = cv2.VideoCapture(0)

        if self.cap.isOpened():
            print("[CAMARA] Iniciada correctamente en Ticket.")
            self.timer_cam.start(30)
            # --- CAMBIO: 10 SEGUNDOS ---
            self.timer_fases.start(10000) 
        else:
            self.intentos_camara += 1
            if self.intentos_camara < 5: QTimer.singleShot(500, self._intentar_abrir_camara)

    def configurar_datos(self, html_ticket: str, lista_productos: list):
        self.lbl_ticket.setText(html_ticket)
        self.lbl_ticket.show()
        
        # Limpiar lista anterior
        for i in reversed(range(self.layout_lista.count())): 
            w = self.layout_lista.itemAt(i).widget()
            if w: w.setParent(None)
        
        self.items_productos = []
        
        # --- CÁLCULO DE ALTURA DINÁMICA ---
        # Queremos que quepan todos (max ~6) en el espacio disponible.
        # Altura del contenedor flotante
        h_disponible = self.contenedor_flotante.height()
        n_prods = len(lista_productos)
        
        if n_prods > 0:
            # Dividir espacio equitativamente
            altura_calc = int(h_disponible / n_prods)
            
            # Aplicar restricciones (ni muy chico, ni muy grande)
            altura_calc = min(altura_calc, 150) # Max 150px por item
            altura_calc = max(altura_calc, 70)  # Min 70px por item
        else:
            altura_calc = 100

        # Crear items con la altura calculada
        for prod in lista_productos:
            item = ItemProducto(prod, self.dir_images, altura_calc)
            self.layout_lista.addWidget(item) # Usamos addWidget normal
            self.items_productos.append(item)
            
        self.layout_lista.addStretch() # Relleno al final si sobra espacio

    def _activar_fase_seleccion(self):
        print("[SISTEMA] Activando selección touchless...")
        self.modo_seleccion = True
        self.lbl_ticket.hide()
        self.scroll_area.show()
        self.cursor_virtual.show()

    def liberar_recursos(self):
        print("[SISTEMA] Liberando recursos de VentanaTicketCamara...")
        self.timer_cam.stop()
        self.timer_fases.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release(); self.cap = None
        if self.hands:
            self.hands.close(); self.hands = None
        self.modo_seleccion = False

    def _actualizar_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret: return

            frame = cv2.flip(frame, 1)
            h_cam, w_cam, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            x_cursor_pantalla = -1
            y_cursor_pantalla = -1
            
            if self.modo_seleccion and self.hands:
                results = self.hands.process(rgb)
                if results.multi_hand_landmarks:
                    lm = results.multi_hand_landmarks[0].landmark[8]
                    cx, cy = int(lm.x * w_cam), int(lm.y * h_cam)
                    cv2.circle(rgb, (cx, cy), 10, (255, 0, 0), -1)
                    
                    view_rect = self.view_cam.geometry()
                    scale_x = view_rect.width() / w_cam
                    scale_y = view_rect.height() / h_cam
                    x_cursor_pantalla = view_rect.x() + int(cx * scale_x)
                    y_cursor_pantalla = view_rect.y() + int(cy * scale_y)
                    
                    self.cursor_virtual.move(x_cursor_pantalla - 15, y_cursor_pantalla - 15)
                    self.cursor_virtual.raise_()

            qimg = QImage(rgb.data, w_cam, h_cam, w_cam*3, QImage.Format_RGB888)
            self.view_cam.setPixmap(QPixmap.fromImage(qimg).scaled(self.view_cam.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

            if x_cursor_pantalla != -1: self._procesar_interaccion(x_cursor_pantalla, y_cursor_pantalla)

    def _procesar_interaccion(self, cursor_x, cursor_y):
        pos_global_cursor = self.recuadro.mapToGlobal(QPoint(cursor_x, cursor_y))
        item_hovered = None
        for item in self.items_productos:
            rect_global_item = QRect(item.mapToGlobal(QPoint(0,0)), item.size())
            if rect_global_item.contains(pos_global_cursor):
                item_hovered = item; break
        
        if item_hovered:
            if self.producto_bajo_cursor == item_hovered:
                progreso = min((time.time() - self.tiempo_inicio_hover) / self.TIEMPO_PARA_SELECCIONAR, 1.0)
                item_hovered.actualizar_progreso(progreso)
                if progreso >= 1.0 and not item_hovered.seleccionado: self._confirmar_seleccion(item_hovered)
            else:
                self._reset_progreso(); self.producto_bajo_cursor = item_hovered; self.tiempo_inicio_hover = time.time(); item_hovered.actualizar_progreso(0.1)
        else:
            self._reset_progreso(); self.producto_bajo_cursor = None

    def _reset_progreso(self):
        if self.producto_bajo_cursor: self.producto_bajo_cursor.actualizar_progreso(0.0)

    def _confirmar_seleccion(self, item):
        item.seleccionado = True
        print(f"[SELECCION] Producto seleccionado ID: {item.id_prod}")
        # Color verde semitransparente al seleccionar
        item.setStyleSheet("QFrame { background-color: #d4edda; border: none; border-bottom: 2px dashed #28a745; }")
        self.liberar_recursos()
        self.cursor_virtual.hide()
        self.producto_seleccionado.emit(int(item.id_prod))

    def resizeEvent(self, event):
        self._recolocar(); super().resizeEvent(event)

    def _recolocar(self):
        w, h = self.width(), self.height()
        alto_barra = int(h * 0.1)
        self.barra.setGeometry(0, 0, w, alto_barra); self.titulo.setGeometry(0, 0, w, alto_barra)
        
        area_h = h - alto_barra - 50; area_w = w - 60
        target_h = area_h; target_w = int(target_h * (4/3))
        if target_w > area_w: target_w = area_w
        
        x = (w - target_w) // 2; y = alto_barra + 20
        self.recuadro.setGeometry(x, y, target_w, target_h)
        self.view_cam.setGeometry(8, 8, target_w - 16, target_h - 16)
        
        fw = int(target_w * 0.35); fh = int(target_h * 0.90)
        fx = target_w - fw - 20; fy = (target_h - fh) // 2
        
        self.contenedor_flotante.setGeometry(fx, fy, fw, fh)
        self.lbl_ticket.setGeometry(0, 0, fw, fh); self.scroll_area.setGeometry(0, 0, fw, fh)
        self.cursor_virtual.raise_()

    def closeEvent(self, ev):
        self.liberar_recursos()
        super().closeEvent(ev)