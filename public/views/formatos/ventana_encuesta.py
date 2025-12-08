# -*- coding: utf-8 -*-
# public/views/formatos/ventana_encuesta.py
import cv2
import time
import mediapipe as mp
from pathlib import Path

from PyQt5.QtWidgets import (QMainWindow, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
                             QWidget, QGraphicsDropShadowEffect)
from PyQt5.QtGui import (QPixmap, QImage, QFont, QColor, QPainter, QPen, 
                         QBrush, QPainterPath)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRect

# ==============================================================================
# CLASE: WIDGET DE CALIFICACIÓN (TARJETA 3D COMPACTA)
# ==============================================================================
class ItemCalificacion(QFrame):
    def __init__(self, valor: int, color_base: str):
        super().__init__()
        self.valor = valor
        self.seleccionado = False
        self.progreso = 0.0 
        
        # Tamaño compacto
        self.setFixedSize(110, 130)

        # Estilo 3D similar a productos
        self.estilo_base = f"""
            ItemCalificacion {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f0f0f0);
                border: 2px solid {color_base};
                border-radius: 15px;
                margin: 2px;
            }}
        """
        self.setStyleSheet(self.estilo_base)

        # Layout Vertical
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(5, 10, 5, 10)

        # Etiqueta del Número
        lbl_num = QLabel(str(valor), self)
        lbl_num.setAlignment(Qt.AlignCenter)
        lbl_num.setFont(QFont("Arial Black", 32, QFont.Bold))
        lbl_num.setStyleSheet(f"color: {color_base}; background: transparent; border: none;")
        layout.addWidget(lbl_num)

        # Etiqueta descriptiva
        desc = ["", "Muy Malo", "Malo", "Regular", "Bueno", "Excelente"]
        if 1 <= valor <= 5:
            lbl_desc = QLabel(desc[valor], self)
            lbl_desc.setAlignment(Qt.AlignCenter)
            lbl_desc.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl_desc.setStyleSheet("color: #555; background: transparent; border: none;")
            layout.addWidget(lbl_desc)

        # Sombra
        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(10)
        sombra.setColor(QColor(0, 0, 0, 60))
        sombra.setOffset(3, 3)
        self.setGraphicsEffect(sombra)

    def actualizar_progreso(self, valor: float):
        self.progreso = valor
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Clip Path para bordes redondeados
        path = QPainterPath()
        rect = self.rect()
        path.addRoundedRect(0, 0, rect.width(), rect.height(), 15, 15)
        painter.setClipPath(path)
        
        super().paintEvent(event)

        # Animación de llenado (Progreso)
        if self.progreso > 0:
            painter.setPen(Qt.NoPen)
            fill_color = QColor(46, 204, 113, 150) 
            painter.setBrush(QBrush(fill_color))
            
            h_fill = int(self.height() * self.progreso)
            painter.drawRect(0, self.height() - h_fill, self.width(), h_fill)
            
            if self.progreso >= 1.0:
                painter.setBrush(Qt.NoBrush)
                pen = QPen(QColor(39, 174, 96), 4)
                painter.setPen(pen)
                painter.drawPath(path)

# ==============================================================================
# VENTANA DE ENCUESTA (CÁMARA AJUSTADA)
# ==============================================================================
class VentanaEncuesta(QMainWindow):
    calificacion_seleccionada = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Encuesta de Satisfacción")
        # Quitamos resize fijo y usamos showMaximized al final
        
        self.cap = None
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        self.opciones = []
        self.opcion_bajo_cursor = None
        self.tiempo_inicio_hover = 0
        self.TIEMPO_PARA_SELECCIONAR = 3.0 
        
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self._actualizar_frame)
        
        self.dir_images = Path(__file__).resolve().parents[2] / "images"
        
        self._init_ui()
        
        # Maximizar ventana al inicio
        self.showMaximized()
        
        # Llamamos a recolocar después de mostrar para asegurar geometrías correctas
        QTimer.singleShot(100, self._recolocar)

    def _init_ui(self):
        # Fondo
        fpath = self.dir_images / "fondo.png"
        if fpath.exists():
            bg_url = str(fpath).replace(chr(92), '/')
            self.setStyleSheet(f"""
                QMainWindow {{
                    border-image: url({bg_url}) 0 0 0 0 stretch stretch;
                }}
            """)
        else:
            self.setStyleSheet("QMainWindow { background-color: #2c3e50; }")

        # Títulos
        self.titulo = QLabel("TT-2025 B004", self) # TÍTULO SOLICITADO
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("background: transparent; color: white; letter-spacing: 2px;") 
        self.titulo.setFont(QFont("Arial Black", 24, QFont.Bold))
        
        self.subtitulo = QLabel("Por favor, califique su experiencia manteniendo su dedo índice sobre una opción.", self)
        self.subtitulo.setAlignment(Qt.AlignCenter)
        self.subtitulo.setStyleSheet("background: transparent; color: #f0f0f0;") 
        self.subtitulo.setFont(QFont("Segoe UI", 16))

        # Recuadro Principal (Cámara)
        self.recuadro = QFrame(self)
        self.recuadro.setStyleSheet("QFrame { background: black; border: 6px solid #e7c14d; border-radius: 20px; }")
        
        self.view_cam = QLabel(self.recuadro)
        self.view_cam.setAlignment(Qt.AlignCenter)
        self.view_cam.setScaledContents(True)
        self.view_cam.setStyleSheet("background: transparent; border: none; border-radius: 14px;")

        # Contenedor de Opciones
        self.contenedor_opciones = QWidget(self.recuadro)
        self.contenedor_opciones.setStyleSheet("background: transparent; border: none;")
        
        self.layout_opciones = QHBoxLayout(self.contenedor_opciones)
        self.layout_opciones.setSpacing(10) 
        self.layout_opciones.setAlignment(Qt.AlignCenter)

        # Generar las 5 tarjetas
        colores = ["#e74c3c", "#e67e22", "#f1c40f", "#3498db", "#2ecc71"]
        for i in range(1, 6):
            item = ItemCalificacion(i, colores[i-1])
            self.layout_opciones.addWidget(item)
            self.opciones.append(item)
        
        # Cursor Virtual
        self.cursor_virtual = QLabel(self.recuadro)
        self.cursor_virtual.setFixedSize(30, 30)
        self.cursor_virtual.setStyleSheet("background-color: rgba(46, 204, 113, 0.9); border: 2px solid white; border-radius: 15px;")
        self.cursor_virtual.hide()

    def iniciar_camara(self):
        self.intentos_camara = 0
        self._intentar_abrir_camara()

    def _intentar_abrir_camara(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened(): self.cap = cv2.VideoCapture(0)

        if self.cap.isOpened():
            print("[CAMARA ENCUESTA] Iniciada.")
            self.timer_cam.start(30)
            self.cursor_virtual.show()
        else:
            self.intentos_camara += 1
            if self.intentos_camara < 5: QTimer.singleShot(500, self._intentar_abrir_camara)

    def liberar_recursos(self):
        self.timer_cam.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release(); self.cap = None
        if self.hands:
            self.hands.close(); self.hands = None

    def _actualizar_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret: return

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            x_cur, y_cur = -1, -1
            
            results = self.hands.process(rgb)
            if results.multi_hand_landmarks:
                lm = results.multi_hand_landmarks[0].landmark[8] 
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(rgb, (cx, cy), 12, (0, 255, 0), -1)
                
                view_rect = self.view_cam.geometry()
                x_cur = view_rect.x() + int(cx * (view_rect.width() / w))
                y_cur = view_rect.y() + int(cy * (view_rect.height() / h))

            qimg = QImage(rgb.data, w, h, w*3, QImage.Format_RGB888)
            self.view_cam.setPixmap(QPixmap.fromImage(qimg).scaled(self.view_cam.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

            if x_cur != -1:
                self.cursor_virtual.move(x_cur - 15, y_cur - 15)
                self.cursor_virtual.raise_()
                self._procesar_interaccion(x_cur, y_cur)

    def _procesar_interaccion(self, cx, cy):
        pos_global = self.recuadro.mapToGlobal(QPoint(cx, cy))
        hovered = None
        for item in self.opciones:
            rect_global = QRect(item.mapToGlobal(QPoint(0,0)), item.size())
            if rect_global.contains(pos_global):
                hovered = item; break
        
        if hovered:
            if self.opcion_bajo_cursor == hovered:
                tiempo_transcurrido = time.time() - self.tiempo_inicio_hover
                progreso = min(tiempo_transcurrido / self.TIEMPO_PARA_SELECCIONAR, 1.0)
                hovered.actualizar_progreso(progreso)
                if progreso >= 1.0 and not hovered.seleccionado:
                    self._confirmar_seleccion(hovered)
            else:
                self._reset_progreso()
                self.opcion_bajo_cursor = hovered
                self.tiempo_inicio_hover = time.time()
                hovered.actualizar_progreso(0.05)
        else:
            self._reset_progreso()
            self.opcion_bajo_cursor = None

    def _reset_progreso(self):
        if self.opcion_bajo_cursor:
            self.opcion_bajo_cursor.actualizar_progreso(0.0)

    def _confirmar_seleccion(self, item):
        item.seleccionado = True
        print(f"[ENCUESTA] Calificación seleccionada: {item.valor}")
        self.liberar_recursos()
        self.cursor_virtual.hide()
        self.calificacion_seleccionada.emit(item.valor)

    def resizeEvent(self, ev):
        self._recolocar()
        super().resizeEvent(ev)

    def _recolocar(self):
        w, h = self.width(), self.height()
        
        # 1. Barra Superior (10% de la pantalla)
        alto_barra = int(h * 0.1)
        self.barra.setGeometry(0, 0, w, alto_barra)
        self.titulo.setGeometry(0, 0, w, alto_barra)
        
        # 2. Subtítulo (Debajo de la barra)
        self.subtitulo.setGeometry(0, alto_barra + 10, w, 30)
        
        # --- AJUSTE DE ASPECT RATIO (CORRECCIÓN DISTORSIÓN) ---
        # Espacio disponible debajo del subtítulo
        y_inicio_recuadro = alto_barra + 50
        h_disponible = h - y_inicio_recuadro - 20 # 20px margen inferior
        
        # Altura objetivo (Maximizando el espacio vertical disponible)
        target_h = int(h_disponible)
        # Ancho objetivo (4:3)
        target_w = int(target_h * (4/3))
        
        # Si el ancho calculado es mayor al ancho de la ventana, ajustamos por ancho
        if target_w > w - 40: # 40px margen lateral
            target_w = w - 40
            target_h = int(target_w * (3/4))

        x = (w - target_w) // 2
        y = y_inicio_recuadro + (h_disponible - target_h) // 2
        
        self.recuadro.setGeometry(x, y, target_w, target_h)
        self.view_cam.setGeometry(6, 6, target_w - 12, target_h - 12)
        
        # Opciones en la parte superior del recuadro
        self.contenedor_opciones.setGeometry(0, 20, target_w, 150)
        self.cursor_virtual.raise_()

    def closeEvent(self, ev):
        self.liberar_recursos()
        super().closeEvent(ev)