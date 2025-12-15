# -*- coding: utf-8 -*-
# public/views/gestor_app.py — flujo con consola + UI segura en hilo principal
import sys, requests, traceback, json
from pathlib import Path
from typing import List, Optional
import time

from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject, QEvent
from PyQt5.QtWidgets import QApplication

# Importaciones de vistas
from public.views.formatos.bienvenida import VentanaBienvenida
from public.views.formatos.respuesta_unica import VentanaReproductorVideo
from public.views.formatos.interaccion import VentanaInteraccion
from public.views.formatos.ventana_ticket_camara import VentanaTicketCamara
from public.views.formatos.ventana_encuesta import VentanaEncuesta

TG_TOKEN = "8567289049:AAF1lFThXzqpu2ptbHUcAkS3-b6CKEUmaEI"
TG_CHAT_ID = "1794777471"

# Importaciones de configuración
try:
    from public.views.config.mapa_interaccion import build_mapa_videos_interaccion, FILE_IDS
    from public.views.config.drive_config import drive_api_url
except ImportError:
    def build_mapa_videos_interaccion(dir): return {}
    FILE_IDS = {}
    def drive_api_url(file_id): return f"https://mock.drive.api/{file_id}"


# ==============================================================================
# LOCAL REPOSITORY (LÓGICA DE DATOS)
# ==============================================================================
class LocalRepo:
    def __init__(self):
        self.base_data = Path(__file__).resolve().parents[1] / "data"
        self.paths = {
            "tickets": self.base_data / "tickets.json",
            "detalles": self.base_data / "ticket_detalle.json",
            "productos": self.base_data / "productos.json",
            "descuentos": self.base_data / "descuentos.json",
            "clientes": self.base_data / "clientes.json"
        }
        
    def _load_json(self, key: str):
        path = self.paths[key]
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def fetch_ticket_bundle(self, ticket_num: int) -> Optional[dict]:
        tickets = self._load_json("tickets")
        detalles = self._load_json("detalles")
        productos_cat = self._load_json("productos")
        descuentos_cat = self._load_json("descuentos")
        clientes_cat = self._load_json("clientes")

        ticket_header = tickets.get(str(ticket_num))
        if not ticket_header:
            return None

        items = [det for det in detalles.values() if det.get("NumTicket") == ticket_num]
        productos_finales = []
        total_calculado = 0.0

        for item in items:
            p_id_str = str(item.get("idProducto"))
            prod_info = productos_cat.get(p_id_str, {})
            
            if prod_info:
                precio_venta = item.get("PrecioVenta", prod_info.get("PrecioProducto", 0.0))
                cant = item.get("Cantidad", 1)
                subtotal = precio_venta * cant
                total_calculado += subtotal

                p_data = {
                    "id": int(p_id_str),
                    "idProducto": p_id_str, 
                    "NombreProducto": prod_info.get("NombreProducto", "Desconocido"),
                    "Descripcion": prod_info.get("Descripcion", ""),
                    "PrecioProducto": prod_info.get("PrecioProducto", 0.0), 
                    "PrecioVenta": precio_venta, 
                    "cantidad": cant,
                    "imagen": prod_info.get("ImagenURL", ""), 
                    "descuento": descuentos_cat.get(str(prod_info.get("idDescuento")))
                }
                productos_finales.append(p_data)

        cliente_id = str(ticket_header.get('idCliente'))
        cliente_info = clientes_cat.get(cliente_id, {})
        
        return {
            "ticket_num": ticket_header.get("NumTicket"),
            "fecha": ticket_header.get("FechaCompra", "N/A"),
            "total": total_calculado,
            "cliente": {"RFCCliente": cliente_info.get("RFCCliente"), "Nombre": cliente_info.get("NombreCliente", "N/A")},
            "productos": productos_finales
        }

repo = LocalRepo()
# ==============================================================================
# RENDERIZADO HTML (DISEÑO TICKET REAL - FIT TO SCREEN)
# ==============================================================================
def render_ticket_html(bundle: dict) -> str:
    """Genera un ticket en formato HTML estilizado, ajustando tamaños según la cantidad de items."""
    num = bundle.get('ticket_num', 'N/A')
    fecha = bundle.get('fecha', 'N/A')
    total = bundle.get('total', 0.0)
    productos = bundle.get("productos", [])
    count = len(productos)

    if count <= 4:
        f_size_header, f_size_body, padding_td, margin_bottom, total_size, max_char = "22px", "16px", "10px", "15px", "26px", 20
    elif count <= 8:
        f_size_header, f_size_body, padding_td, margin_bottom, total_size, max_char = "20px", "14px", "6px", "10px", "22px", 18
    else:
        f_size_header, f_size_body, padding_td, margin_bottom, total_size, max_char = "18px", "11px", "2px", "5px", "18px", 15

    html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: 'Consolas', monospace; color: #000000; margin: 0; padding: 0; }}
        h1 {{ text-align: center; margin: 0 0 5px 0; font-size: {f_size_header}; color: #000; font-weight: 900; }}
        .fecha {{ text-align: center; font-size: 12px; color: #333; margin-bottom: {margin_bottom}; border-bottom: 1px dashed #000; padding-bottom: 5px; }}
        .tabla {{ width: 100%; border-collapse: collapse; margin-top: 5px; }}
        th {{ text-align: left; font-size: {f_size_body}; color: #000; text-transform: uppercase; border-bottom: 2px solid #000; }}
        .th-right {{ text-align: right; }}
        td {{ padding: {padding_td} 0; font-size: {f_size_body}; border-bottom: 1px dashed #777; }}
        .td-right {{ text-align: right; font-weight: bold; }}
        .total-container {{ margin-top: 10px; padding-top: 5px; border-top: 2px solid #000; }}
        .total {{ font-size: {total_size}; font-weight: bold; text-align: right; color: #000; }}
        .footer {{ text-align: center; font-size: 10px; color: #555; margin-top: 15px; font-style: italic; }}
    </style>
    </head>
    <body>
        <h1>TICKET #{num}</h1>
        <div class="fecha">{fecha}</div>
        <table class="tabla">
            <tr><th width="65%">PROD</th><th width="35%" class="th-right">$$$</th></tr>
    """
    for p in productos:
        nombre = p.get("NombreProducto", "Producto")
        if len(nombre) > max_char: nombre = nombre[:max_char-2] + ".."
        precio = p.get("PrecioVenta", 0.0)
        html += f"<tr><td>{nombre}</td><td class='td-right'>${precio:,.2f}</td></tr>"
        
    html += f"""
        </table>
        <div class="total-container"><div class="total">TOTAL: ${total:,.2f}</div></div>
        <div class="footer">*** GRACIAS POR SU COMPRA ***</div>
    </body>
    </html>
    """
    return html


# ==============================================================================
# CONSTANTES Y FLUJO DE ESTADOS
# ==============================================================================
RESP_INTERACCION = {"resp1","resp3","resp5","resp7","resp9","resp10","resp11","resp12"}
RESP_UNICA       = {"resp2","resp4","resp6","resp8","resp13","resp14","resp15","resp16"}

RESP_TEXTO = {
    "resp1":  "Resp1- Contamos con cinco ramas de atención, captura la palabra que corresponda a tu solicitud:\n\tFacturacion / Aclaracion / Devolucion / Dudas / Ninguna",
    "resp2":  "Resp2- Lamentamos no poder ayudarte, continuaremos trabajando para proporcionarte un mejor servicio",
    "resp3":  "Resp3- ¿Hay algo más en lo que te pueda ayudar?  ",
    "resp4":  "Resp4- Gracias por utilizar nuestro sistema",
    "resp5":  "Resp5- Por favor, ayúdanos contestando una encuesta de satisfacción",
    "resp6":  "Resp6- Lo lamentamos pero para poder darle el apoyo debe contar con su ticket para poder escanearlo",
    "resp7":  "Resp7- ¿Hay algún otro producto que desee seleccionar? Por favor capture Si o No",
    "resp8":  "Resp8- Hemos notificado al asociado correspondiente. Se acercará para apoyarte con el proceso. Comparte tu ticket y producto(s) capturado(s).",
    "resp9":  "Resp9- ¿Cuenta con su ticket? Por favor capture Si o No",
    "resp10": "Resp10- Con ayuda del escaner, escane el código de barras que se encuentra en su ticket",
    "resp11": "Resp11- Captura la palabra (producto) para confirmar que desea hacer una devolución, de lo contrario capture la palabra (ninguno)",
    "resp12": "Resp12- Especifique el motivo de devolución del producto. Capture la opción que corresponda al motivo de su devolución (dañado / defecto / equivocación) en caso de que no aplique ninguna opción, capture (ninguno)",
    "resp13": "Resp13- ¡Hola! Somos un sistema de apoyo de atención al cliente de personas sordas-señantes",
    "resp14": "Resp14- Para poder interectarua con el sistema deberás capturar únicamente las palabras indicadas en los siguientes videos.",
    "resp15": "Resp15- Sin tocar la pantalla mueva su dedo índice para que el cursor se coloque y mantenga durante 3 segundos sobre la calificación que desee otorgar al Sistema. ",
    "resp16": "Resp16- Sin tocar la pantalla, mueva su dedo índice para que el cursor se coloque durante 3 segundos sobre el botón de mostrár productos, Despues mueva el cursor sobre el producto que le gustaría devolver y mantenga durante 3 segundos. Mueva su mano izquierda hacia arriba o hacia abajo para visualizar más productos.\n Para detener el scroll de productos, cierre el puño de su mano izquierda, para reanudarlo vuelva a extender la mano."
}

def _norm(s: str) -> str: return s.strip().lower()
def _yes(s: str) -> bool: return _norm(s) in {"si","sí","yes","y","s"}
def _no(s: str) -> bool: return _norm(s) in {"no","n"}

class ST:
    MAIN="MAIN"; DEV_MENU="DEV_MENU"; DEV_REASON="DEV_REASON"; ASK_TICKET_YN="ASK_TICKET_YN"
    WAIT_TICKET="WAIT_TICKET"; WAIT_PRODUCT="WAIT_PRODUCT"; MORE_PRODUCT="MORE_PRODUCT"
    RESP3_MAIN="RESP3_MAIN"; RESP3_NINGUNO="RESP3_NINGUNO"; RESP3_NO_TICKET="RESP3_NO_TICKET"; SURVEY="SURVEY"

class HiloEntrada(QThread):
    senal_txt = pyqtSignal(str)
    senal_salir = pyqtSignal()
    
    def __init__(self): super().__init__(); self._ena=True; self._alive=True
    def set_habilitado(self, on: bool): self._ena = bool(on)
    def detener(self): self._alive = False
    
    def run(self):
        print("------------------------------------------------------------")
        print("FLUJO POR CONSOLA (entrada bloqueada mientras haya video)")
        print("------------------------------------------------------------")
        while self._alive:
            if not self._ena: self.msleep(50); continue
            try: s = input("> ").strip()
            except EOFError: self.senal_salir.emit(); break
            if not s: continue
            self.senal_txt.emit(s)

class GestorAplicacion(QObject):
    FILE_ID_BIENVENIDA = FILE_IDS.get("bienvenida")

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.ventana_actual = None
        self.playing = False
        self.modo_gestos_activo = False
        self.dir_public = Path(__file__).resolve().parents[1]
        self.dir_videos = self.dir_public / "videos"
        self.dir_videos.mkdir(parents=True, exist_ok=True)

        self.mapa = build_mapa_videos_interaccion(self.dir_videos)
        
        self.notificacion_counter = 0
        self.modo_gestos_activo = False
        self.state = ST.MAIN
        self.consecutive_errors = 0
            
        self.context = {"branch": None, "razon": None, "ticket_num": None, "ticket_bundle": None, "productos": [], "survey": None}
        self.queue = []; self.next_state_after_queue = None; self.processing_video_end = False
        
        self.buffer_teclado = ""
        self.captura_activa = False
        self.app.installEventFilter(self)
        
        # Timer para inactividad de gestos
        self.timer_inactividad_gestos = QTimer()
        self.timer_inactividad_gestos.timeout.connect(self._on_inactividad_gestos)
        self.timer_inactividad_gestos.setInterval(10000)  # 10 segundos

        self.hilo = HiloEntrada()
        self.hilo.senal_txt.connect(lambda s: QTimer.singleShot(0, lambda: self._on_txt_ui_guarded(s)))
        self.hilo.senal_salir.connect(self.app.quit)
        self.hilo.start()
        self.app.aboutToQuit.connect(self._on_quit)
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and self.captura_activa:
            key_text = event.text()
            key_code = event.key()

            if key_text.isdigit():
                self.buffer_teclado += key_text
                return True

            if key_code in (16777220, 16777221):
                if self.buffer_teclado.isdigit():
                    val = int(self.buffer_teclado)
                    self.buffer_teclado = ""
                    self._handle_ticket_number(val)
                    return True

                self.buffer_teclado = ""
                return True

        return False

    def _bloquear(self, on: bool):
        self.playing = bool(on)
        self.hilo.set_habilitado(not on)
        
        # Si se está bloqueando (reproduciendo video), detener timer de inactividad
        if on and self.timer_inactividad_gestos.isActive():
            self.timer_inactividad_gestos.stop()
            print("[GESTOR] Timer de inactividad pausado (reproduciendo video)")
        
        if isinstance(self.ventana_actual, VentanaInteraccion):
            if on:
                self.ventana_actual.bloquear_terminal()
            else:
                self.ventana_actual.desbloquear_terminal()

    def _on_quit(self):
        # Detener timer de inactividad
        if hasattr(self, 'timer_inactividad_gestos'):
            self.timer_inactividad_gestos.stop()
        
        try:
            self.hilo.detener()
        except:
            pass

    def _safe_disconnect_all(self, win):
        try:
            if isinstance(win, VentanaInteraccion):
                try: win.video_terminado.disconnect()
                except: pass
                try: win.gesto_detectado.disconnect()
                except: pass
                try: win.alerta_ayuda_terminada.disconnect()
                except: pass
            elif isinstance(win, VentanaReproductorVideo):
                try: win.transicion_solicitada.disconnect()
                except: pass 
            elif isinstance(win, VentanaBienvenida):
                try: win.video_terminado.disconnect()
                except: pass
        except Exception: pass

    def _ensure_local_resp(self, resp_name: str) -> Optional[str]:
        p = self.dir_videos / f"{resp_name}.mp4"
        if p.is_file(): return str(p)
        file_id = FILE_IDS.get(resp_name)
        if not file_id: return None
        try:
            with requests.get(drive_api_url(file_id), stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(p, "wb") as f:
                    for ch in r.iter_content(1<<20): f.write(ch)
            return str(p)
        except Exception: return None

    def _activar_modo_gestos(self, activar: bool = True):
        """Activa/desactiva modo gestos y su timer de inactividad"""
        
        # NO activar gestos si no estamos en VentanaInteraccion
        if activar and not isinstance(self.ventana_actual, VentanaInteraccion):
            print(f"[DEBUG] No activar gestos: ventana actual es {type(self.ventana_actual).__name__}")
            return
        
        self.modo_gestos_activo = activar
        
        if activar:
            print(f"[TIMER] Timer de inactividad INICIADO (ventana: {type(self.ventana_actual).__name__})")
            self.timer_inactividad_gestos.start()
        else:
            if self.timer_inactividad_gestos.isActive():
                print("[TIMER] Timer de inactividad DETENIDO")
                self.timer_inactividad_gestos.stop()
        
        if isinstance(self.ventana_actual, VentanaInteraccion):
            self.ventana_actual.set_modo_gestos(activar)
            if activar:
                try:
                    self.ventana_actual.gesto_detectado.disconnect()
                except:
                    pass
                self.ventana_actual.gesto_detectado.connect(self._on_gesto_detectado_con_reset)
                
    def _on_gesto_detectado_con_reset(self, gesto: str):
        """Callback cuando se detecta un gesto - resetea timer y procesa entrada"""
        # Resetear el timer de inactividad
        if self.modo_gestos_activo:
            self.timer_inactividad_gestos.stop()
            self.timer_inactividad_gestos.start()
            print("[GESTOR] Timer de inactividad reseteado por detección de gesto")
        
        # Procesar el gesto normalmente
        self._on_txt_ui_guarded(gesto)
        
    def _on_inactividad_gestos(self):
        """Se ejecuta cuando pasan 10 segundos sin detectar gestos"""
        print("[GESTOR] ⚠️ INACTIVIDAD DETECTADA - 10 segundos sin gestos")
        print("[GESTOR] Volviendo a pantalla de bienvenida...")
        
        self.timer_inactividad_gestos.stop()
        
        # Resetear contexto
        self.consecutive_errors = 0
        self.context = {
            "branch": None,
            "razon": None,
            "ticket_num": None,
            "ticket_bundle": None,
            "productos": [],
            "survey": None
        }
        
        # Volver a bienvenida
        self.mostrar_bienvenida()

    def _mostrar_error_entrada(self):
        if isinstance(self.ventana_actual, VentanaInteraccion): self.ventana_actual.mostrar_error_captura()

    def _handle_input_error(self):
        self.consecutive_errors += 1
        print(f"[DEBUG] Error input #{self.consecutive_errors}")
        if self.consecutive_errors >= 3: self._trigger_usability_alert()
        else: self._mostrar_error_entrada(); self._print_prompt()

    def _reset_error_count(self): self.consecutive_errors = 0
        
    def _get_descripcion_estado_actual(self) -> str:
        descripciones = {
            ST.MAIN: "Menú Principal (Facturación/Devolución/Dudas)",
            ST.DEV_MENU: "Selección de tipo Devolución (Producto vs Ninguno)",
            ST.DEV_REASON: "Selección de Razón de Devolución",
            ST.ASK_TICKET_YN: "Pregunta: ¿Cuenta con Ticket?",
            ST.WAIT_TICKET: "Esperando captura de Número de Ticket",
            ST.WAIT_PRODUCT: "Esperando captura de ID Producto",
            ST.MORE_PRODUCT: "Pregunta: ¿Más productos?",
            ST.RESP3_MAIN: "Pregunta: ¿Ayuda en algo más? (General)",
            ST.RESP3_NINGUNO: "Pregunta: ¿Ayuda en algo más? (Post-Ninguno)",
            ST.RESP3_NO_TICKET: "Pregunta: ¿Ir a encuesta? (Sin ticket)",
            ST.SURVEY: "Encuesta de Satisfacción (Visual)"
        }
        return descripciones.get(self.state, f"Estado desconocido ({self.state})")

    def _trigger_usability_alert(self):
        print("\n!!! ALERTA DE USABILIDAD - 3 ERRORES CONSECUTIVOS !!!")
        self.notificacion_counter += 1
        paso_detenido = self._get_descripcion_estado_actual()
        resumen_texto = self._generar_texto_resumen_string()
        msg_telegram = (f"🚨 APOYO EN CAPTURA DE SISTEMA 🚨\n📦 SEGUIMIENTO: #{self.notificacion_counter:04d}\n"
                        f"📍 DETENIDO EN: {paso_detenido}\n⚠️ El usuario ha fallado 3 veces consecutivas en este paso.\n"
                        f"--- RESUMEN HASTA EL MOMENTO ---\n{resumen_texto}")
        self._enviar_telegram(msg_telegram)
        
        if isinstance(self.ventana_actual, VentanaInteraccion):
            try: self.ventana_actual.gesto_detectado.disconnect()
            except: pass
            try: self.ventana_actual.alerta_ayuda_terminada.disconnect()
            except: pass
            self.ventana_actual.alerta_ayuda_terminada.connect(self._reiniciar_app_completo)
            self.ventana_actual.mostrar_alerta_ayuda_asociado()
        else:
            QTimer.singleShot(6000, self._reiniciar_app_completo)

    def _reiniciar_app_completo(self):
        print("[SISTEMA] Reiniciando aplicación por alerta de usabilidad...")
        self.consecutive_errors = 0
        self.context = {"branch": None, "razon": None, "ticket_num": None, "ticket_bundle": None, "productos": [], "survey": None}
        self.mostrar_bienvenida()

    def _hook_interaccion(self, win: VentanaInteraccion):
        try: win.video_terminado.disconnect()
        except: pass
        try: win.gesto_detectado.disconnect()
        except: pass
        win.video_terminado.connect(self._on_video_finished)
        win.bloquear_terminal() if self.playing else win.desbloquear_terminal()

    def _hook_unica(self, win: VentanaReproductorVideo):
        win.transicion_solicitada.connect(self._on_video_finished)
        self._activar_modo_gestos(False)

    def _play_resp(self, resp_name: str):
        self._bloquear(True)
        if resp_name in RESP_TEXTO: print("\n" + RESP_TEXTO[resp_name] + "\n")

        if resp_name in RESP_INTERACCION:
            src = self.mapa.get(resp_name)
            if not isinstance(self.ventana_actual, VentanaInteraccion):
                win = VentanaInteraccion(src)
                win.set_modo_reproduccion(True)
                self._safe_disconnect_all(win)
                self._hook_interaccion(win)
                self._swap(win)
            else:
                self._safe_disconnect_all(self.ventana_actual)
                self._hook_interaccion(self.ventana_actual)
                self.ventana_actual.set_modo_reproduccion(True)
                self.ventana_actual.cambiar_video_unidad(src, nombre_resp=resp_name)
        else:
            ruta = self._ensure_local_resp(resp_name)
            win = VentanaReproductorVideo(ruta if ruta else None)
            self._safe_disconnect_all(win)
            self._hook_unica(win)
            self._swap(win)

    def _enqueue_and_play(self, resp_list: List[str], next_state: str):
        self.queue = list(resp_list)
        self.next_state_after_queue = next_state
        self.processing_video_end = False
        if next_state == ST.WAIT_TICKET: self.hilo.set_habilitado(True)
        self._play_next_in_queue()

    def _play_next_in_queue(self):
        if not self.queue:
            self._bloquear(False)
            if self.next_state_after_queue:
                self._set_state(self.next_state_after_queue)
                self.next_state_after_queue = None
            return
        self._play_resp(self.queue.pop(0))

    def _on_video_finished(self):
        if isinstance(self.ventana_actual, VentanaInteraccion):
            try:
                self.ventana_actual.set_modo_reproduccion(False)
                self.ventana_actual.desbloquear_terminal()
                self._activar_modo_gestos(True)
            except Exception: pass

        if self.processing_video_end: return
        self.processing_video_end = True

        if self.queue:
            self.processing_video_end = False
            self._play_next_in_queue()
            return

        self._bloquear(False)
        if self.next_state_after_queue:
            self._set_state(self.next_state_after_queue)
            self.next_state_after_queue = None
        else:
            self._print_prompt()
        self.processing_video_end = False

    def _swap(self, nueva):
        nueva.show()
        if self.ventana_actual:
            vieja = self.ventana_actual
            self.ventana_actual = nueva
            QTimer.singleShot(100, vieja.close)
        else: self.ventana_actual = nueva
        
        if isinstance(nueva, VentanaInteraccion):
            if self.playing: self._activar_modo_gestos(False)
            else: self._activar_modo_gestos(True)
        else: self._activar_modo_gestos(False)

    def _set_state(self, st: str):
        self.state = st
        if self.state == ST.WAIT_TICKET: self.captura_activa = True; self.buffer_teclado = ""; self._activar_modo_gestos(False)
        elif self.state == ST.SURVEY:
            self._lanzar_ventana_encuesta()
            return
        else: self.captura_activa = False; self.buffer_teclado = ""
        self._print_prompt()

    def _print_prompt(self):
        prompts = {
            ST.MAIN: "> Opciones: facturacion | devolucion | dudas | otros",
            ST.DEV_MENU: "> Opciones devolucion: producto | ninguno",
            ST.DEV_REASON: "> Razones: danado | defecto | equivocacion",
            ST.ASK_TICKET_YN: "> ¿Tiene ticket? (si/no)",
            ST.WAIT_TICKET: "> Captura el número de ticket:",
            ST.WAIT_PRODUCT: "> CAPTURE EL NUMERO DEL PRODUCTO:",
            ST.MORE_PRODUCT: "> ¿Hay otro producto? (si/no)",
            ST.RESP3_MAIN: "> ¿Ayuda en algo más? (si/no)",
            ST.RESP3_NINGUNO: "> ¿Ayuda en algo más? (si/no)",
            ST.RESP3_NO_TICKET: "> Escribe 'no' para ir a encuesta.",
        }
        msg = prompts.get(self.state, "> Esperando entrada...")
        print(msg)

    def _on_txt_ui_guarded(self, s: str):
        try: self._on_txt_ui(s)
        except Exception:
            traceback.print_exc()
            self._bloquear(False)
            self._print_prompt()

    def _on_txt_ui(self, s: str):
        if self.playing: return
        v = _norm(s)

        if v.isdigit():
            val = int(v)
            if self.state == ST.WAIT_TICKET: self._handle_ticket_number(val); return
            if self.state == ST.WAIT_PRODUCT: self._handle_product_number(val); return
            if self.state == ST.SURVEY:
                if 1 <= val <= 5: self._handle_encuesta_result(val)
                else: self._handle_input_error()
                return
            
        if self.state in {ST.WAIT_TICKET, ST.WAIT_PRODUCT}:
            if isinstance(self.ventana_actual, VentanaInteraccion): self.ventana_actual.mostrar_error_captura()
            self._handle_input_error(); return

        if self.state == ST.MAIN:
            if v in {"devolucion","devolución"}:
                self._reset_error_count()
                self.context = {k:None for k in self.context}
                self.context["productos"] = []
                self.context["branch"] = "devolucion"
                self._enqueue_and_play(["resp11"], ST.DEV_MENU)
            else: self._handle_input_error()

        elif self.state == ST.DEV_MENU:
            if v == "producto":
                self._reset_error_count(); self._enqueue_and_play(["resp12"], ST.DEV_REASON)
            elif v == "ninguno":
                self._reset_error_count(); self._enqueue_and_play(["resp2","resp3"], ST.RESP3_NINGUNO)
            else: self._handle_input_error()

        elif self.state == ST.DEV_REASON:
            if v in {"danado","dañado","defecto","equivocacion","equivocación"}:
                self._reset_error_count(); self.context["razon"] = v
                self._enqueue_and_play(["resp9"], ST.ASK_TICKET_YN)
            else: self._handle_input_error()

        elif self.state == ST.ASK_TICKET_YN:
            if _yes(v): self._reset_error_count(); self._enqueue_and_play(["resp10"], ST.WAIT_TICKET)
            elif _no(v): self._reset_error_count(); self._enqueue_and_play(["resp6","resp3"], ST.RESP3_NO_TICKET)
            else: self._handle_input_error()

        elif self.state == ST.MORE_PRODUCT:
            if _yes(v):
                self._reset_error_count()
                self._lanzar_ventana_ticket()
            elif _no(v):
                self._reset_error_count()
                self._enqueue_and_play(["resp4","resp8","resp3"], ST.RESP3_MAIN)
            else: self._handle_input_error()

        elif self.state in {ST.RESP3_MAIN, ST.RESP3_NINGUNO}:
            if _yes(v): self._reset_error_count(); self._enqueue_and_play(["resp1"], ST.MAIN)
            elif _no(v):
                self._reset_error_count()
                self._enqueue_and_play(["resp5", "resp15"], ST.SURVEY)
            else: self._handle_input_error()
        
        elif self.state == ST.RESP3_NO_TICKET:
             if _no(v):
                self._reset_error_count()
                self._enqueue_and_play(["resp4","resp5", "resp15"], ST.SURVEY)
             else: self._handle_input_error()
        else: self._set_state(ST.MAIN)

    # ==============================================================================
    # INTEGRACIÓN TICKET CAMARA & ENCUESTA
    # ==============================================================================
    def _handle_ticket_number(self, num: int):
        print(f"[DATA] Buscando ticket {num} en archivos locales...")
        bundle = repo.fetch_ticket_bundle(num)
        if not bundle:
            print(f"[ERROR] No existe el ticket {num} en archivos locales.")
            self._handle_input_error(); return

        self._reset_error_count()
        self.context["ticket_num"] = num
        self.context["ticket_bundle"] = bundle

        print("[FLUJO] Reproduciendo Resp16 antes de mostrar cámara...")
        ruta = self._ensure_local_resp("resp16")
        win = VentanaReproductorVideo(ruta if ruta else None)
        self._safe_disconnect_all(win)
        win.transicion_solicitada.connect(self._lanzar_ventana_ticket)
        self._swap(win); self._bloquear(True)

    def _lanzar_ventana_ticket(self):
        print("[SISTEMA] Lanzando VentanaTicketCamara...")

        # ============================
        # 🔥 1. APAGAR GESTOS COMPLETAMENTE
        # ============================
        try:
            print("[GESTOS] Desactivando gestos y timer para captura de producto...")
            self._activar_modo_gestos(False)          # apaga detector + timer
            if self.timer_inactividad_gestos.isActive():
                self.timer_inactividad_gestos.stop()
                print("[GESTOR] Timer de inactividad DETENIDO (modo ticket)")
        except Exception as e:
            print("[GESTOS] Error al desactivar gestos:", e)

        # ============================
        # 🔥 2. LIBERAR RECURSOS DE VENTANA ANTERIOR
        # ============================
        if isinstance(self.ventana_actual, VentanaInteraccion):
            self._safe_disconnect_all(self.ventana_actual)
            try:
                self.ventana_actual.close()
            except:
                pass

        # ============================
        # 🔥 3. LIBERAR MODELO DE GESTOS / MEDIAPIPE
        # ============================
        try:
            if hasattr(self, "gestor_gestos"):
                print("[GESTOS] Liberando recursos MediaPipe antes de abrir cámara...")
                self.gestor_gestos.liberar_recursos()
        except Exception as e:
            print("[GESTOS] Error liberando recursos:", e)

        # ============================
        # 🔥 4. VALIDAR BUNDLE
        # ============================
        bundle = self.context.get("ticket_bundle")
        if not bundle:
            print("[ERROR] Intento de abrir cámara sin bundle de ticket.")
            self._set_state(ST.MAIN)
            return

        # ============================
        # 🔥 5. CREAR NUEVA VENTANA CAMERA
        # ============================
        win = VentanaTicketCamara()
        texto_ticket_html = render_ticket_html(bundle)
        lista_productos = bundle.get("productos", [])

        win.configurar_datos(texto_ticket_html, lista_productos)
        win.producto_seleccionado.connect(self._handle_product_number)

        self.ventana_actual = win
        win.show()

        # ============================
        # 🔥 6. INICIAR CÁMARA
        # ============================
        win.iniciar_camara_segura()

        # ============================
        # 🔥 7. SIN GESTOS — SIN TIMER — SOLO TECLADO
        # ============================
        self._bloquear(False)
        self.state = ST.WAIT_PRODUCT
        self._print_prompt()

        print("[SISTEMA] Cámara iniciada (gestos desactivados correctamente)")


    def _handle_product_number(self, prod_id: int):
        print(f"[GESTOR] Producto seleccionado recibido: {prod_id}")
        if isinstance(self.ventana_actual, VentanaTicketCamara): self.ventana_actual.liberar_recursos()

        bundle = self.context.get("ticket_bundle")
        if not bundle:
            print("[ERROR] No hay bundle de ticket en contexto."); self._handle_input_error(); return
        
        prods_ticket = bundle.get("productos", [])
        found = next((p for p in prods_ticket if p.get("id") == prod_id), None)
        if not found:
            print(f"[ERROR] ID {prod_id} no encontrado en el ticket actual."); self._handle_input_error(); return
        
        self._reset_error_count()
        if prod_id not in self.context["productos"]: self.context["productos"].append(prod_id)
        
        print("[GESTOR] Transición a siguiente paso (MORE_PRODUCT)...")
        QTimer.singleShot(200, lambda: self._enqueue_and_play(["resp7"], ST.MORE_PRODUCT))

    # --- NUEVOS MÉTODOS PARA ENCUESTA ---
    def _lanzar_ventana_encuesta(self):
        print("[SISTEMA] Lanzando VentanaEncuesta...")
        if isinstance(self.ventana_actual, VentanaInteraccion):
            self._safe_disconnect_all(self.ventana_actual)
            self.ventana_actual.close()
        
        win = VentanaEncuesta()
        win.calificacion_seleccionada.connect(self._handle_encuesta_result)
        
        self.ventana_actual = win
        win.show(); win.iniciar_camara()
        self._bloquear(False)

    def _handle_encuesta_result(self, val: int):
        print(f"[ENCUESTA] Valor recibido: {val}")
        self._reset_error_count()
        self.context["survey"] = val
        self._mostrar_resumen_y_finalizar()

    # ==============================================================================
    # RESUMEN Y FINALIZACIÓN
    # ==============================================================================
    def _generar_texto_resumen_string(self) -> str:
        ctx = self.context
        bundle = ctx.get("ticket_bundle")
        ids_seleccionados = ctx.get("productos", [])

        lineas = []
        lineas.append(f" 📌 OPERACIÓN:      {str(ctx.get('branch', 'General')).upper()}")
        lineas.append(f" 📌 MOTIVO/RAZÓN:   {str(ctx.get('razon', 'N/A')).upper()}")
        lineas.append(f" ⭐ CALIFICACIÓN:   {ctx.get('survey', 'N/A')}/5")
        
        if bundle:
            lineas.append("-" * 40)
            lineas.append(f" 🧾 TICKET #{bundle.get('ticket_num')} | {bundle.get('fecha')}")
            nom_cliente = bundle.get('cliente', {}).get('Nombre', 'N/A')
            lineas.append(f" 👤 CLIENTE: {nom_cliente[:30]}")
            lineas.append("-" * 40)
            lineas.append(f" {'ID':<6} | {'PRODUCTO':<20} | ESTADO")
            for prod in bundle.get("productos", []):
                p_id = prod.get('id')
                nombre = prod.get('NombreProducto', 'Sin nombre')[:20]
                es_seleccionado = p_id in ids_seleccionados
                m_der = " <-- [OBJETO]" if es_seleccionado else ""
                lineas.append(f" {str(p_id):<6} | {nombre:<20} |{m_der}")
            lineas.append("-" * 40)
            lineas.append(f" TOTAL: ${bundle.get('total', 0.0):.2f}")
        else:
            lineas.append(" [!] Sin información de ticket asociada.")
        return "\n".join(lineas)

    def _mostrar_resumen_y_finalizar(self):
        
        """Después de la encuesta: generar resumen, limpiar contexto y reiniciar TODO el flujo."""
        
        # 1. Generar y enviar resumen
        self.notificacion_counter += 1
        cuerpo_resumen = self._generar_texto_resumen_string()
        
        lineas = []
        lineas.append("✅ RESUMEN FINAL DE LA INTERACCIÓN")
        lineas.append(f"📦 SEGUIMIENTO: # DEV{self.notificacion_counter:04d}")
        lineas.append("╔" + "═" * 58 + "╗")
        lineas.append(cuerpo_resumen)
        lineas.append("╚" + "═" * 58 + "╝")
        
        mensaje_completo = "\n".join(lineas)
        print("\n" + mensaje_completo + "\n")
        self._enviar_telegram(mensaje_completo)

        # 2. Apagar modo gestos + timers
        self._activar_modo_gestos(False)
        if self.timer_inactividad_gestos.isActive():
            self.timer_inactividad_gestos.stop()

        # 3. Cerrar ventana activa
        if self.ventana_actual:
            try:
                self._safe_disconnect_all(self.ventana_actual)
                self.ventana_actual.close()
            except:
                pass

        # 4. Resetear contexto completamente
        self.consecutive_errors = 0
        self.context = {
            "branch": None,
            "razon": None,
            "ticket_num": None,
            "ticket_bundle": None,
            "productos": [],
            "survey": None
        }

        # 5. Reiniciar todo el flujo → bienvenida real
        print("[SISTEMA] Reiniciando ciclo completo después de encuesta...")
        time.sleep(1.5)
        self.mostrar_bienvenida()

    def mostrar_bienvenida(self):
        """Reinicia la bienvenida con detección completa desde cero."""
        dest = self.dir_videos / "bienvenida.mp4"

        print("[SISTEMA] Mostrando pantalla de bienvenida...")

        # Forzar bloqueo (video reproducción) y desactivar gestos
        self._bloquear(True)
        self._activar_modo_gestos(False)

        # Crear ventana nueva SIEMPRE (no reutilizar)
        win = VentanaBienvenida(str(dest) if dest.is_file() else None)
        self._safe_disconnect_all(win)
        win.video_terminado.connect(self._after_bienvenida)

        self._swap(win)



    def _after_bienvenida(self):
        print("[FLUJO] Inicio -> Resp14 (Instrucciones de captura)...")
        ruta = self._ensure_local_resp("resp14")
        win = VentanaReproductorVideo(ruta if ruta else None)
        self._safe_disconnect_all(win)
        win.transicion_solicitada.connect(self._iniciar_menu_principal)
        self._swap(win)

    def _iniciar_menu_principal(self):
        print("[FLUJO] Instrucciones terminadas -> Menú Principal (Resp1)...")
        src = self.mapa.get("resp1")
        win = VentanaInteraccion(src)
        self._safe_disconnect_all(win)
        self._hook_interaccion(win)
        self._swap(win)
        self._bloquear(True)
        print("\n" + RESP_TEXTO["resp1"] + "\n")
        def _after_first():
            self._safe_disconnect_all(win)
            self._hook_interaccion(win)
            self._activar_modo_gestos(True)
            self._bloquear(False)
            self._set_state(ST.MAIN)
        win.video_terminado.connect(_after_first)

    def run(self):
        self.mostrar_bienvenida()
        sys.exit(self.app.exec_())
    
    def _enviar_telegram(self, mensaje_texto):
        if not TG_TOKEN or not TG_CHAT_ID:
            print("[Telegram] No se ha configurado Token o Chat ID.")
            return
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        texto_formateado = f"```text\n{mensaje_texto}\n```"
        payload = {"chat_id": TG_CHAT_ID, "text": texto_formateado, "parse_mode": "MarkdownV2"}
        try:
            requests.post(url, json=payload, timeout=3)
            print(f"[Telegram] Reporte #{self.notificacion_counter} enviado correctamente.")
        except Exception as e:
            print(f"[Telegram] Error al enviar reporte: {e}")