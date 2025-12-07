# -*- coding: utf-8 -*-
# public/views/gestor_app.py — flujo con consola + UI segura en hilo principal
import sys, requests, traceback, json
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtWidgets import QApplication

# Importaciones de vistas
from public.views.formatos.bienvenida import VentanaBienvenida
from public.views.formatos.respuesta_unica import VentanaReproductorVideo
from public.views.formatos.interaccion import VentanaInteraccion
# IMPORTACIÓN CLAVE: Ventana de ticket con cámara integrada
from public.views.formatos.ventana_ticket_camara import VentanaTicketCamara

TG_TOKEN = "8567289049:AAF1lFThXzqpu2ptbHUcAkS3-b6CKEUmaEI"
TG_CHAT_ID = "1794777471"

# Importaciones de configuración
try:
    from public.views.config.mapa_interaccion import build_mapa_videos_interaccion, FILE_IDS
    from public.views.config.drive_config import drive_api_url
except ImportError:
    # Mocks si las configuraciones no están disponibles
    def build_mapa_videos_interaccion(dir): return {}
    FILE_IDS = {}
    def drive_api_url(file_id): return f"https://mock.drive.api/{file_id}"


# ==============================================================================
# LOCAL REPOSITORY (LÓGICA DE DATOS)
# ==============================================================================
class LocalRepo:
    """Clase para manejar la lectura de los JSONs locales e inyectar el mock data."""
    
    def __init__(self):
        # Paths y estructura base
        self.base_data = Path(__file__).resolve().parents[1] / "data"
        self.paths = {
            "tickets": self.base_data / "tickets.json",
            "detalles": self.base_data / "ticket_detalle.json",
            "productos": self.base_data / "productos.json",
            "descuentos": self.base_data / "descuentos.json",
            "clientes": self.base_data / "clientes.json"
        }
        
        # Mocks de datos inyectados
        self._mock_data = {
            "tickets": json.loads('{"1001": {"NumTicket": 1001, "FechaCompra": "225-10-20 13:45:10", "idCliente": 1}, "112": {"NumTicket": 112, "FechaCompra": "225-10-20 15:10:25", "idCliente": 2}}'),
            "detalles": json.loads('{"1": {"idTicketDetalle": 1, "NumTicket": 1001, "idProducto": 101, "Cantidad": 1, "PrecioVenta": 8450.0}, "2": {"idTicketDetalle": 2, "NumTicket": 1001, "idProducto": 21, "Cantidad": 2, "PrecioVenta": 637.5}, "3": {"idTicketDetalle": 3, "NumTicket": 112, "idProducto": 12, "Cantidad": 1, "PrecioVenta": 22000.0}, "4": {"idTicketDetalle": 4, "NumTicket": 112, "idProducto": 21, "Cantidad": 1, "PrecioVenta": 637.5}, "5": {"idTicketDetalle": 5, "NumTicket": 112, "idProducto": 22, "Cantidad": 1, "PrecioVenta": 120.0}}'),
            "productos": json.loads('{"101": {"idProducto": 101, "NombreProducto": "Televisión LED 50\\"", "PrecioProducto": 8500.0, "Descripcion": "Smart TV 4K UHD", "Disponibilidad": true, "CodigoArea": 10, "idDescuento": 2, "ImagenURL": "productos/tv_led_50.png"}, "12": {"idProducto": 12, "NombreProducto": "Laptop Gamer", "PrecioProducto": 22000.0, "Descripcion": "Laptop con tarjeta gráfica dedicada", "Disponibilidad": true, "CodigoArea": 10, "idDescuento": null, "ImagenURL": "productos/laptop_gamer.png"}, "103": {"idProducto": 103, "NombreProducto": "Audífonos Bluetooth", "PrecioProducto": 1800.0, "Descripcion": "Cancelación de ruido activa, 20hrs de batería", "Disponibilidad": true, "CodigoArea": 10, "idDescuento": 1, "ImagenURL": "productos/audifonos_bt.png"}, "21": {"idProducto": 21, "NombreProducto": "Camisa de Lino", "PrecioProducto": 750.0, "Descripcion": "Camisa casual manga larga", "Disponibilidad": true, "CodigoArea": 20, "idDescuento": 1, "ImagenURL": "productos/camisa_lino.png"}, "22": {"idProducto": 22, "NombreProducto": "Zapatos de Piel", "PrecioProducto": 1200.0, "Descripcion": "Zapatos formales color negro", "Disponibilidad": true, "CodigoArea": 20, "idDescuento": 1, "ImagenURL": "productos/zapatos_piel.jpg"}}'),
            "descuentos": json.loads('{"1": {"idDescuento": 1, "Valor": 15.0, "Tipo": "Porcentaje", "FechaInicio": "225-10-01", "FechaFin": "225-10-31", "Estado": "Activo"}, "2": {"idDescuento": 2, "Valor": 50.0, "Tipo": "MontoFijo", "FechaInicio": "225-10-15", "FechaFin": "225-10-25", "Estado": "Activo"}}'),
            "clientes": json.loads('{"1": {"idCliente": 1, "RFCCliente": "GOPJ850101AA1", "NombreCliente": "Juan Pérez"}, "2": {"idCliente": 2, "RFCCliente": "GAML88022BB2", "NombreCliente": "Ana García"}}')
        }

    def _load_json(self, key: str):
        path = self.paths[key]
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self._mock_data.get(key, {})
        return self._mock_data.get(key, {})

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
# RENDERIZADO HTML (DISEÑO TICKET REAL)
# ==============================================================================
def render_ticket_html(bundle: dict) -> str:
    """Genera un ticket en formato HTML estilizado como recibo real."""
    num = bundle.get('ticket_num', 'N/A')
    fecha = bundle.get('fecha', 'N/A')
    total = bundle.get('total', 0.0)
    
    # CSS Inline optimizado para PyQt Labels
    html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: 'Consolas', monospace; color: #000000; margin: 0; padding: 0; }}
        h1 {{ text-align: center; margin: 0 0 10px 0; font-size: 22px; color: #000; font-weight: 900; }}
        .fecha {{ text-align: center; font-size: 13px; color: #333; margin-bottom: 15px; border-bottom: 1px dashed #000; padding-bottom: 10px; }}
        .tabla {{ width: 100%; border-collapse: collapse; margin-top: 5px; }}
        th {{ text-align: left; font-size: 14px; color: #000; text-transform: uppercase; border-bottom: 2px solid #000; }}
        .th-right {{ text-align: right; }}
        td {{ padding: 8px 0; font-size: 16px; border-bottom: 1px dashed #777; }}
        .td-right {{ text-align: right; font-weight: bold; }}
        .total-container {{ margin-top: 20px; padding-top: 10px; border-top: 2px solid #000; }}
        .total {{ font-size: 26px; font-weight: bold; text-align: right; color: #000; }}
        .footer {{ text-align: center; font-size: 11px; color: #555; margin-top: 25px; font-style: italic; }}
    </style>
    </head>
    <body>
        <h1>TICKET #{num}</h1>
        <div class="fecha">{fecha}</div>
        
        <table class="tabla">
            <tr>
                <th width="65%">PROD</th>
                <th width="35%" class="th-right">$$$</th>
            </tr>
    """
    
    for p in bundle.get("productos", []):
        nombre = p.get("NombreProducto", "Producto")
        if len(nombre) > 20: nombre = nombre[:18] + ".."
        precio = p.get("PrecioVenta", 0.0)
        
        html += f"""
            <tr>
                <td>{nombre}</td>
                <td class="td-right">${precio:,.2f}</td>
            </tr>
        """
        
    html += f"""
        </table>
        
        <div class="total-container">
            <div class="total">TOTAL: ${total:,.2f}</div>
        </div>
        <div class="footer">
            *** GRACIAS POR SU COMPRA ***
        </div>
    </body>
    </html>
    """
    return html


# ==============================================================================
# CONSTANTES Y FLUJO DE ESTADOS
# ==============================================================================
RESP_INTERACCION = {"resp1","resp3","resp5","resp7","resp9","resp10","resp11","resp12"}
RESP_UNICA       = {"resp2","resp4","resp6","resp8"}

RESP_TEXTO = {
    "resp1":  "Resp1- Captura alguna de las siguientes opciones:\n\tFacturacion / Aclaracion / Devolucion / Dudas / Ninguna",
    "resp2":  "Resp2- Lamentamos no poder ayudarte, continuaremos trabajando para proporcionarte un mejor servicio",
    "resp3":  "Resp3- ¿Hay algo más en lo que te pueda ayudar? (si/no)",
    "resp4":  "Resp4- Gracias por utilizar nuestro sistema",
    "resp5":  "Resp5- Por favor, ayúdanos contestando una encuesta de satisfacción (1..5)",
    "resp6":  "Resp6- Lo lamentamos pero para poder darle el apoyo debe contar con su número de ticket.",
    "resp7":  "Resp7- ¿Hay algún otro producto? (si/no)",
    "resp8":  "Resp8- Un asociado se acercará para apoyarte con el proceso. Comparte tu ticket y producto(s) capturados.",
    "resp9":  "Resp9- ¿Cuenta con su ticket? (si/no)",
    "resp10": "Resp10- Capture su número de ticket",
    "resp11": "Resp11- Opciones para devolución (producto / ninguno)",
    "resp12": "Resp12- Opciones de devolución (dañado / defecto / equivocación)",
}

def _norm(s: str) -> str:
    return s.strip().lower()

def _yes(s: str) -> bool:
    return _norm(s) in {"si","sí","yes","y","s"}

def _no(s: str) -> bool:
    return _norm(s) in {"no","n"}

class ST:
    MAIN = "MAIN"
    DEV_MENU = "DEV_MENU"
    DEV_REASON = "DEV_REASON"
    ASK_TICKET_YN = "ASK_TICKET_YN"
    WAIT_TICKET = "WAIT_TICKET"
    WAIT_PRODUCT = "WAIT_PRODUCT"
    MORE_PRODUCT = "MORE_PRODUCT"
    RESP3_MAIN = "RESP3_MAIN"
    RESP3_NINGUNO = "RESP3_NINGUNO"
    RESP3_NO_TICKET = "RESP3_NO_TICKET"
    SURVEY = "SURVEY"

class HiloEntrada(QThread):
    senal_txt = pyqtSignal(str)
    senal_salir = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._ena = True
        self._alive = True
    
    def set_habilitado(self, on: bool):
        self._ena = bool(on)
    
    def detener(self):
        self._alive = False
    
    def run(self):
        print("------------------------------------------------------------")
        print("FLUJO POR CONSOLA (entrada bloqueada mientras haya video)")
        print("------------------------------------------------------------")
        while self._alive:
            if not self._ena:
                self.msleep(50)
                continue
            try:
                s = input("> ").strip()
            except EOFError:
                self.senal_salir.emit()
                break
            if not s:
                continue
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
        
        self.context = {
            "branch": None,
            "razon": None,
            "ticket_num": None,
            "ticket_bundle": None,
            "productos": [], 
            "survey": None
        }

        self.queue = []
        self.next_state_after_queue = None
        self.processing_video_end = False

        self.hilo = HiloEntrada()
        self.hilo.senal_txt.connect(lambda s: QTimer.singleShot(0, lambda: self._on_txt_ui_guarded(s)))
        self.hilo.senal_salir.connect(self.app.quit)
        self.hilo.start()
        self.app.aboutToQuit.connect(self._on_quit)

    def _bloquear(self, on: bool):
        self.playing = bool(on)
        self.hilo.set_habilitado(not on)
        
        if isinstance(self.ventana_actual, VentanaInteraccion):
            if on:
                self.ventana_actual.bloquear_terminal()
            else:
                self.ventana_actual.desbloquear_terminal()

    def _on_quit(self):
        try:
            self.hilo.detener()
        except:
            pass

    def _safe_disconnect_all(self, win):
        """Desconecta señales de manera segura, ignorando errores si no estaban conectadas."""
        try:
            if isinstance(win, VentanaInteraccion):
                try: win.video_terminado.disconnect()
                except: pass
                try: win.gesto_detectado.disconnect()
                except: pass
                try: win.alerta_ayuda_terminada.disconnect()
                except: pass
            
            elif isinstance(win, VentanaReproductorVideo):
                # PROTECCIÓN EXTRA AQUÍ
                try: win.transicion_solicitada.disconnect()
                except Exception: pass # Ignorar cualquier error de desconexión
            
            elif isinstance(win, VentanaBienvenida):
                try: win.video_terminado.disconnect()
                except: pass
        except Exception:
            pass
        """Desconecta señales de manera segura, ignorando errores si no estaban conectadas."""
        try:
            if isinstance(win, VentanaInteraccion):
                try: win.video_terminado.disconnect()
                except: pass
                try: win.gesto_detectado.disconnect()
                except: pass
                try: win.alerta_ayuda_terminada.disconnect()
                except: pass
            
            elif isinstance(win, VentanaReproductorVideo):
                # PROTECCIÓN EXTRA AQUÍ
                try: win.transicion_solicitada.disconnect()
                except Exception: pass # Ignorar cualquier error de desconexión
            
            elif isinstance(win, VentanaBienvenida):
                try: win.video_terminado.disconnect()
                except: pass
        except Exception:
            pass

    def _ensure_local_resp(self, resp_name: str) -> Optional[str]:
        p = self.dir_videos / f"{resp_name}.mp4"
        if p.is_file():
            return str(p)
        file_id = FILE_IDS.get(resp_name)
        if not file_id:
            return None
        try:
            with requests.get(drive_api_url(file_id), stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(p, "wb") as f:
                    for ch in r.iter_content(1<<20):
                        if ch:
                            f.write(ch)
            return str(p)
        except Exception as e:
            return None

    def _activar_modo_gestos(self, activar: bool = True):
        self.modo_gestos_activo = activar
        if isinstance(self.ventana_actual, VentanaInteraccion):
            self.ventana_actual.set_modo_gestos(activar)
            if activar:
                try:
                    self.ventana_actual.gesto_detectado.disconnect()
                except:
                    pass
                # Conexión directa a _on_txt_ui_guarded sin filtros de contexto
                self.ventana_actual.gesto_detectado.connect(lambda s: self._on_txt_ui_guarded(s))

    def _mostrar_error_entrada(self):
        if isinstance(self.ventana_actual, VentanaInteraccion):
            self.ventana_actual.mostrar_error_captura()

    def _handle_input_error(self):
        self.consecutive_errors += 1
        print(f"[DEBUG] Error input #{self.consecutive_errors}")

        if self.consecutive_errors >= 3:
            self._trigger_usability_alert()
        else:
            self._mostrar_error_entrada()
            self._print_prompt()

    def _reset_error_count(self):
        self.consecutive_errors = 0
        
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
            ST.SURVEY: "Encuesta de Satisfacción (1-5)"
        }
        return descripciones.get(self.state, f"Estado desconocido ({self.state})")

    def _trigger_usability_alert(self):
        print("\n!!! ALERTA DE USABILIDAD - 3 ERRORES CONSECUTIVOS !!!")
        self.notificacion_counter += 1
        paso_detenido = self._get_descripcion_estado_actual()
        resumen_texto = self._generar_texto_resumen_string()
        
        msg_telegram = (
            f"🚨 APOYO EN CAPTURA DE SISTEMA 🚨\n"
            f"📦 SEGUIMIENTO: #{self.notificacion_counter:04d}\n"
            f"📍 DETENIDO EN: {paso_detenido}\n\n"
            f"⚠️ El usuario ha fallado 3 veces consecutivas en este paso.\n\n"
            f"--- RESUMEN HASTA EL MOMENTO ---\n"
            f"{resumen_texto}"
        )
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
        self.context = {
            "branch": None,
            "razon": None,
            "ticket_num": None,
            "ticket_bundle": None,
            "productos": [],
            "survey": None
        }
        self.mostrar_bienvenida()

    def _hook_interaccion(self, win: VentanaInteraccion):
        try: win.video_terminado.disconnect()
        except: pass
        try: win.gesto_detectado.disconnect()
        except: pass
        win.video_terminado.connect(self._on_video_finished)
        if self.playing:
            win.bloquear_terminal()
        else:
            win.desbloquear_terminal()

    def _hook_unica(self, win: VentanaReproductorVideo):
        win.transicion_solicitada.connect(self._on_video_finished)
        self._activar_modo_gestos(False)

    def _play_resp(self, resp_name: str):
        self._bloquear(True)
        if resp_name in RESP_TEXTO:
            print("\n" + RESP_TEXTO[resp_name] + "\n")

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
            except Exception as e:
                pass

        if self.processing_video_end:
            return
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
        else:
            self.ventana_actual = nueva
        if isinstance(nueva, VentanaInteraccion):
            self._activar_modo_gestos(True)
        else:
            self._activar_modo_gestos(False)

    def _set_state(self, st: str):
        self.state = st
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
            ST.SURVEY: "> Califica del 1 al 5:"
        }
        msg = prompts.get(self.state, "> Esperando entrada...")
        print(msg)

    def _on_txt_ui_guarded(self, s: str):
        try:
            self._on_txt_ui(s)
        except Exception as e:
            traceback.print_exc()
            self._bloquear(False)
            self._print_prompt()

    def _on_txt_ui(self, s: str):
        if self.playing:
            return

        v = _norm(s)

        if v.isdigit():
            val = int(v)
            if self.state == ST.WAIT_TICKET:
                self._handle_ticket_number(val)
                return
            if self.state == ST.WAIT_PRODUCT:
                self._handle_product_number(val)
                return
            if self.state == ST.SURVEY:
                if 1 <= val <= 5:
                    self._reset_error_count() # Exito
                    self.context["survey"] = val
                    self._mostrar_resumen_y_finalizar()
                else:
                    self._handle_input_error() # Error
                return
            
        if self.state in {ST.WAIT_TICKET, ST.WAIT_PRODUCT, ST.SURVEY}:
            if isinstance(self.ventana_actual, VentanaInteraccion):
                self.ventana_actual.mostrar_error_captura()
                
            self._handle_input_error()
            return

        # Lógica de estados de texto
        if self.state == ST.MAIN:
            if v in {"devolucion","devolución"}:
                self._reset_error_count()
                self.context = {k:None for k in self.context}
                self.context["productos"] = []
                self.context["branch"] = "devolucion"
                self._enqueue_and_play(["resp11"], ST.DEV_MENU)
            else:
                self._handle_input_error()

        elif self.state == ST.DEV_MENU:
            if v == "producto":
                self._reset_error_count()
                self._enqueue_and_play(["resp12"], ST.DEV_REASON)
            elif v == "ninguno":
                self._reset_error_count()
                self._enqueue_and_play(["resp2","resp3"], ST.RESP3_NINGUNO)
            else:
                self._handle_input_error()

        elif self.state == ST.DEV_REASON:
            if v in {"danado","dañado","defecto","equivocacion","equivocación"}:
                self._reset_error_count()
                self.context["razon"] = v
                self._enqueue_and_play(["resp9"], ST.ASK_TICKET_YN)
            else:
                self._handle_input_error()

        elif self.state == ST.ASK_TICKET_YN:
            if _yes(v):
                self._reset_error_count()
                self._enqueue_and_play(["resp10"], ST.WAIT_TICKET)
            elif _no(v):
                self._reset_error_count()
                self._enqueue_and_play(["resp6","resp3"], ST.RESP3_NO_TICKET)
            else:
                self._handle_input_error()

        elif self.state == ST.MORE_PRODUCT:
            if _yes(v):
                self._reset_error_count()
                # Volvemos a pedir producto
                self._set_state(ST.WAIT_PRODUCT)
            elif _no(v):
                self._reset_error_count()
                self._enqueue_and_play(["resp4","resp8","resp3"], ST.RESP3_MAIN)
            else:
                self._handle_input_error()

        elif self.state in {ST.RESP3_MAIN, ST.RESP3_NINGUNO}:
            if _yes(v):
                self._reset_error_count()
                self._enqueue_and_play(["resp1"], ST.MAIN)
            elif _no(v):
                self._reset_error_count()
                self._enqueue_and_play(["resp5"], ST.SURVEY)
            else:
                self._handle_input_error()
        
        elif self.state == ST.RESP3_NO_TICKET:
             if _no(v):
                self._reset_error_count()
                self._enqueue_and_play(["resp4","resp5"], ST.SURVEY)
             else:
                self._handle_input_error()
        else:
            self._set_state(ST.MAIN)

    # ==============================================================================
    # INTEGRACIÓN TICKET CAMARA (COMPATIBLE CON VENTANA ACTUAL)
    # ==============================================================================
    def _handle_ticket_number(self, num: int):
        print(f"[DATA] Buscando ticket {num} en archivos locales...")
        bundle = repo.fetch_ticket_bundle(num)

        if not bundle:
            print(f"[ERROR] No existe el ticket {num} en archivos locales.")
            self._handle_input_error()
            return

        self._reset_error_count()
        self.context["ticket_num"] = num
        self.context["ticket_bundle"] = bundle

        # --- TRANSICIÓN SEGURA: CERRAR ANTERIOR ---
        if isinstance(self.ventana_actual, VentanaInteraccion):
            print("[SISTEMA] Cerrando VentanaInteraccion y liberando recursos...")
            try:
                if hasattr(self.ventana_actual, 'timer_cam'):
                    self.ventana_actual.timer_cam.stop()
                if hasattr(self.ventana_actual, 'cap_cam') and self.ventana_actual.cap_cam:
                    self.ventana_actual.cap_cam.release()
                if hasattr(self.ventana_actual, 'inferencia') and self.ventana_actual.inferencia:
                    self.ventana_actual.inferencia = None
            except Exception as e:
                print(f"[WARN] Error liberando recursos manual: {e}")

            self._safe_disconnect_all(self.ventana_actual)
            self.ventana_actual.close()
            self.ventana_actual = None
        
        # --- ABRIR NUEVA VENTANA TICKET ---
        win = VentanaTicketCamara()
        
        # Preparar datos HTML
        texto_ticket_html = render_ticket_html(bundle)
        lista_productos = bundle.get("productos", [])
        
        # CONFIGURACIÓN CORRECTA: Usando 'configurar_datos'
        win.configurar_datos(texto_ticket_html, lista_productos)
        
        # Conectar señal de selección por gestos/touchless
        win.producto_seleccionado.connect(self._handle_product_number)
        
        self.ventana_actual = win
        win.show()
        
        # Iniciar cámara de ticket
        win.iniciar_camara_segura()

        self._set_state(ST.WAIT_PRODUCT)

    def _handle_product_number(self, prod_id: int):
        print(f"[GESTOR] Producto seleccionado recibido: {prod_id}")
        
        # --- CORRECCIÓN ---
        # No cerramos manualmente la ventana aquí (self.ventana_actual.close()).
        # Permitimos que la ventana siga viva unos milisegundos más hasta que
        # _enqueue_and_play -> _play_resp -> _swap se encargue de reemplazarla.
        # Esto evita cortes en el flujo.

        bundle = self.context.get("ticket_bundle")
        if not bundle:
            print("[ERROR] No hay bundle de ticket en contexto.")
            self._handle_input_error()
            return
        
        prods_ticket = bundle.get("productos", [])
        found = next((p for p in prods_ticket if p.get("id") == prod_id), None)
        
        if not found:
            print(f"[ERROR] ID {prod_id} no encontrado en el ticket actual.")
            self._handle_input_error()
            return
        
        self._reset_error_count()
        self.context["productos"].append(prod_id)
        
        print("[GESTOR] Transición a siguiente paso (MORE_PRODUCT)...")
        # Llamada directa sin QTimer para asegurar ejecución inmediata, 
        # o con un tiempo muy corto.
        self._enqueue_and_play(["resp7"], ST.MORE_PRODUCT)
        print(f"[GESTOR] Producto seleccionado recibido: {prod_id}")
        
        # 1. Asegurarnos de que la ventana anterior liberó recursos
        if isinstance(self.ventana_actual, VentanaTicketCamara):
            self.ventana_actual.liberar_recursos()
            self.ventana_actual.close()
            self.ventana_actual = None

        bundle = self.context.get("ticket_bundle")
        if not bundle:
            self._handle_input_error()
            return
        
        prods_ticket = bundle.get("productos", [])
        found = next((p for p in prods_ticket if p.get("id") == prod_id), None)
        
        if not found:
            self._handle_input_error()
            return
        
        self._reset_error_count()
        self.context["productos"].append(prod_id)
        
        # Pequeño delay para transición suave a videos
        QTimer.singleShot(200, lambda: self._enqueue_and_play(["resp7"], ST.MORE_PRODUCT))

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
        self.notificacion_counter += 1
        cuerpo_resumen = self._generar_texto_resumen_string()
        
        lineas = []
        lineas.append("✅ RESUMEN FINAL DE LA INTERACCIÓN")
        lineas.append(f"📦 SEGUIMIENTO: #{self.notificacion_counter:04d}")
        lineas.append("═" * 60)
        lineas.append(cuerpo_resumen)
        lineas.append("═" * 60)
        
        mensaje_completo = "\n".join(lineas)
        print("\n" + mensaje_completo + "\n")
        self._enviar_telegram(mensaje_completo)
        
        self.consecutive_errors = 0
        self.context = {
            "branch": None,
            "razon": None,
            "ticket_num": None,
            "ticket_bundle": None,
            "productos": [],
            "survey": None
        }
        self._enqueue_and_play(["resp1"], ST.MAIN)

    def mostrar_bienvenida(self):
        dest = self.dir_videos / "bienvenida.mp4"
        if not dest.is_file():
            pass
            
        win = VentanaBienvenida(str(dest) if dest.is_file() else None)
        self._safe_disconnect_all(win)
        win.video_terminado.connect(self._after_bienvenida)
        self._bloquear(True)
        self._swap(win)

    def _after_bienvenida(self):
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
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": texto_formateado,
            "parse_mode": "MarkdownV2"
        }
        
        try:
            requests.post(url, json=payload, timeout=3)
            print(f"[Telegram] Reporte #{self.notificacion_counter} enviado correctamente.")
        except Exception as e:
            print(f"[Telegram] Error al enviar reporte: {e}")