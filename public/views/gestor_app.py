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
# LOCAL REPOSITORY (LÓGICA DE DATOS BASADA EN TUS JSONS SUBIDOS)
# ==============================================================================
class LocalRepo:
    """Clase para manejar la lectura de los JSONs locales e inyectar el mock data."""
    
    def __init__(self):
        # Paths y estructura base (asumiendo public/data/)
        self.base_data = Path(__file__).resolve().parents[1] / "data"
        self.paths = {
            "tickets": self.base_data / "tickets.json",
            "detalles": self.base_data / "ticket_detalle.json",
            "productos": self.base_data / "productos.json",
            "descuentos": self.base_data / "descuentos.json",
            "clientes": self.base_data / "clientes.json"
        }
        
        # Mocks de datos inyectados de los archivos subidos por el usuario
        self._mock_data = {
            "tickets": json.loads('{"1001": {"NumTicket": 1001, "FechaCompra": "2025-10-20 13:45:10", "idCliente": 1}, "1002": {"NumTicket": 1002, "FechaCompra": "2025-10-20 15:10:25", "idCliente": 2}}'),
            "detalles": json.loads('{"1": {"idTicketDetalle": 1, "NumTicket": 1001, "idProducto": 101, "Cantidad": 1, "PrecioVenta": 8450.0}, "2": {"idTicketDetalle": 2, "NumTicket": 1001, "idProducto": 201, "Cantidad": 2, "PrecioVenta": 637.5}, "3": {"idTicketDetalle": 3, "NumTicket": 1002, "idProducto": 102, "Cantidad": 1, "PrecioVenta": 22000.0}, "4": {"idTicketDetalle": 4, "NumTicket": 1002, "idProducto": 201, "Cantidad": 1, "PrecioVenta": 637.5}, "5": {"idTicketDetalle": 5, "NumTicket": 1002, "idProducto": 202, "Cantidad": 1, "PrecioVenta": 1020.0}}'),
            "productos": json.loads('{"101": {"idProducto": 101, "NombreProducto": "Televisión LED 50\\"", "PrecioProducto": 8500.0, "Descripcion": "Smart TV 4K UHD", "Disponibilidad": true, "CodigoArea": 10, "idDescuento": 2, "ImagenURL": "productos/tv_led_50.png"}, "102": {"idProducto": 102, "NombreProducto": "Laptop Gamer", "PrecioProducto": 22000.0, "Descripcion": "Laptop con tarjeta gráfica dedicada", "Disponibilidad": true, "CodigoArea": 10, "idDescuento": null, "ImagenURL": "productos/laptop_gamer.png"}, "103": {"idProducto": 103, "NombreProducto": "Audífonos Bluetooth", "PrecioProducto": 1800.0, "Descripcion": "Cancelación de ruido activa, 20hrs de batería", "Disponibilidad": true, "CodigoArea": 10, "idDescuento": 1, "ImagenURL": "productos/audifonos_bt.png"}, "201": {"idProducto": 201, "NombreProducto": "Camisa de Lino", "PrecioProducto": 750.0, "Descripcion": "Camisa casual manga larga", "Disponibilidad": true, "CodigoArea": 20, "idDescuento": 1, "ImagenURL": "productos/camisa_lino.png"}, "202": {"idProducto": 202, "NombreProducto": "Zapatos de Piel", "PrecioProducto": 1200.0, "Descripcion": "Zapatos formales color negro", "Disponibilidad": true, "CodigoArea": 20, "idDescuento": 1, "ImagenURL": "productos/zapatos_piel.jpg"}}'),
            "descuentos": json.loads('{"1": {"idDescuento": 1, "Valor": 15.0, "Tipo": "Porcentaje", "FechaInicio": "2025-10-01", "FechaFin": "2025-10-31", "Estado": "Activo"}, "2": {"idDescuento": 2, "Valor": 50.0, "Tipo": "MontoFijo", "FechaInicio": "2025-10-15", "FechaFin": "2025-10-25", "Estado": "Activo"}}'),
            "clientes": json.loads('{"1": {"idCliente": 1, "RFCCliente": "GOPJ850101AA1", "NombreCliente": "Juan Pérez"}, "2": {"idCliente": 2, "RFCCliente": "GAML880202BB2", "NombreCliente": "Ana García"}}')
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
                    "idProducto": p_id_str, # Usamos ambos para compatibilidad de mocks
                    "NombreProducto": prod_info.get("NombreProducto", "Desconocido"),
                    "Descripcion": prod_info.get("Descripcion", ""),
                    "PrecioProducto": prod_info.get("PrecioProducto", 0.0), # Precio base
                    "PrecioVenta": precio_venta, # Precio final pagado (incl. descuento si aplica)
                    "cantidad": cant,
                    "imagen": prod_info.get("ImagenURL", ""), # RUTA CLAVE PARA EL UI
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

# Instancia del repositorio de datos
repo = LocalRepo()


# ==============================================================================
# FUNCIONES DE RENDERIZADO PARA TEXTO
# ==============================================================================
def render_ticket_text_formato_ticket(bundle: dict) -> str:
    """Renderiza el ticket completo en formato de ticket de compra"""
    lineas = []
    lineas.append("=" * 16 + f" TICKET #{bundle.get('ticket_num', 'N/A')} " + "=" * 16)
    lineas.append(f"Fecha: {bundle.get('fecha', 'N/A')}")
    lineas.append("-" * 50)
    lineas.append(f"{'ID':<5} | {'Producto':<25} | {'Precio':>8}")
    
    for p in bundle.get("productos", []):
        prod_id = p.get("id", "N/A")
        nombre = p.get("NombreProducto", "Producto")[:25]
        precio = p.get("PrecioVenta", 0.0)
        lineas.append(f"{prod_id:<5} | {nombre:<25} | ${precio:>7.2f}")
    
    lineas.append("-" * 50)
    lineas.append(f"TOTAL: ${bundle.get('total', 0.0):.2f}")
    lineas.append("=" * 50)
    
    return "\n".join(lineas)

def render_producto_individual(producto: dict, ticket_num: int) -> str:
    """Renderiza un producto individual en formato de texto para el overlay."""
    return (
        f"📦 ID: {producto.get('id', 'N/A')} | Nombre: {producto.get('NombreProducto', 'Producto')}\n"
        f"----------------------------------------\n"
        f"Precio: ${producto.get('PrecioVenta', 0.0):.2f}"
    )


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

        self.state = ST.MAIN
        self.context = {
            "branch": None,
            "razon": None,
            "ticket_num": None,
            "ticket_bundle": None,
            "productos": [], # IDs de productos seleccionados
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

    def _on_quit(self):
        try:
            self.hilo.detener()
        except:
            pass

    def _safe_disconnect_all(self, win):
        try:
            if isinstance(win, VentanaInteraccion):
                win.video_terminado.disconnect()
                win.gesto_detectado.disconnect()
            elif isinstance(win, VentanaReproductorVideo):
                win.transicion_solicitada.disconnect()
            elif isinstance(win, VentanaBienvenida):
                win.video_terminado.disconnect()
        except TypeError:
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
                self.ventana_actual.gesto_detectado.connect(self._on_gesto_detectado)

    def _on_gesto_detectado(self, gesto: str):
        if not self.modo_gestos_activo or self.playing:
            return
        self._on_txt_ui_guarded(gesto)

    def _mostrar_error_entrada(self):
        if isinstance(self.ventana_actual, VentanaInteraccion):
            self.ventana_actual.mostrar_error_captura()

    def _hook_interaccion(self, win: VentanaInteraccion):
        win.video_terminado.connect(self._on_video_finished)
        self._activar_modo_gestos(True)

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
                    self.context["survey"] = val
                    self._mostrar_resumen_y_finalizar()
                else:
                    self._mostrar_error_entrada()
                    self._print_prompt()
                return

        # Lógica de estados de texto
        if self.state == ST.MAIN:
            if v in {"devolucion","devolución"}:
                self.context = {k:None for k in self.context}
                self.context["productos"] = []
                self.context["branch"] = "devolucion"
                self._enqueue_and_play(["resp11"], ST.DEV_MENU)
            else:
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.DEV_MENU:
            if v == "producto":
                self._enqueue_and_play(["resp12"], ST.DEV_REASON)
            elif v == "ninguno":
                self._enqueue_and_play(["resp2","resp3"], ST.RESP3_NINGUNO)
            else:
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.DEV_REASON:
            if v in {"danado","dañado","defecto","equivocacion","equivocación"}:
                self.context["razon"] = v
                self._enqueue_and_play(["resp9"], ST.ASK_TICKET_YN)
            else:
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.ASK_TICKET_YN:
            if _yes(v):
                self._enqueue_and_play(["resp10"], ST.WAIT_TICKET)
            elif _no(v):
                self._enqueue_and_play(["resp6","resp3"], ST.RESP3_NO_TICKET)
            else:
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.MORE_PRODUCT:
            if _yes(v):
                bundle = self.context.get("ticket_bundle")
                if bundle and isinstance(self.ventana_actual, VentanaInteraccion):
                    self._mostrar_secuencia_ticket_productos(bundle, ST.WAIT_PRODUCT)
                else:
                    self._set_state(ST.WAIT_PRODUCT)
            elif _no(v):
                self._enqueue_and_play(["resp4","resp8","resp3"], ST.RESP3_MAIN)
            else:
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state in {ST.RESP3_MAIN, ST.RESP3_NINGUNO}:
            if _yes(v):
                self._enqueue_and_play(["resp1"], ST.MAIN)
            elif _no(v):
                self._enqueue_and_play(["resp5"], ST.SURVEY)
            else:
                self._mostrar_error_entrada()
                self._print_prompt()
        
        elif self.state == ST.RESP3_NO_TICKET:
             if _no(v):
                self._enqueue_and_play(["resp4","resp5"], ST.SURVEY)
             else:
                self._mostrar_error_entrada()
                self._print_prompt()
        else:
            self._set_state(ST.MAIN)

    def _mostrar_secuencia_ticket_productos(self, bundle: dict, next_state: str):
        """
        Muestra la secuencia completa: 1. Ticket (5s), 2. Cada producto (3s), 3. Ticket final (5s)
        """
        if not isinstance(self.ventana_actual, VentanaInteraccion) or not bundle:
            self._set_state(next_state)
            return
        
        self._bloquear(True)
        # --- ACTIVAR MODO REPRODUCCION: Oculta banner verde, muestra rojo ---
        self.ventana_actual.set_modo_reproduccion(True)
        
        productos = bundle.get("productos", [])
        indice_actual = [0]
        
        def ejecutar_paso():
            idx = indice_actual[0]
            
            # Definir la secuencia de pasos con los tiempos:
            pasos = [
                {"type": "ticket", "tiempo": 10000, "data": None},
            ]
            for p in productos:
                pasos.append({"type": "producto", "tiempo": 6000, "data": p}) 
            pasos.append({"type": "ticket", "tiempo": 10000, "data": None})

            if idx >= len(pasos):
                self._bloquear(False)
                # --- DESACTIVAR MODO REPRODUCCION: Muestra banner verde para captura ---
                self.ventana_actual.set_modo_reproduccion(False)
                self._set_state(next_state)
                return
            
            step = pasos[idx]
            
            if step["type"] == "ticket":
                texto = render_ticket_text_formato_ticket(bundle)
                
                self.ventana_actual.mostrar_overlay_texto(
                    texto=texto, 
                    ms=step["tiempo"], 
                    producto_data=None, # Para ticket completo, no pasamos data
                    on_done=lambda: (indice_actual.__setitem__(0, idx + 1), ejecutar_paso())
                )
            
            elif step["type"] == "producto":
                producto = step["data"]
                texto = render_producto_individual(producto, bundle.get('ticket_num', 'N/A'))
                
                self.ventana_actual.mostrar_overlay_texto(
                    texto=texto, 
                    ms=step["tiempo"], 
                    producto_data=producto, # <-- FIX CLAVE: PASAR DATA PARA LA IMAGEN
                    on_done=lambda: (indice_actual.__setitem__(0, idx + 1), ejecutar_paso())
                )
        
        ejecutar_paso()

    def _handle_ticket_number(self, num: int):
        print(f"[DATA] Buscando ticket {num} en archivos locales...")
        bundle = repo.fetch_ticket_bundle(num)

        if not bundle:
            print(f"[ERROR] No existe el ticket {num} en archivos locales.")
            self._mostrar_error_entrada()
            self._print_prompt()
            return

        self.context["ticket_num"] = num
        self.context["ticket_bundle"] = bundle

        if not isinstance(self.ventana_actual, VentanaInteraccion):
            src = self.mapa.get("resp10")
            win = VentanaInteraccion(src)
            self._safe_disconnect_all(win)
            self._hook_interaccion(win)
            self._swap(win)
            try:
                win.set_modo_reproduccion(False)
            except:
                pass

        self._mostrar_secuencia_ticket_productos(bundle, ST.WAIT_PRODUCT)

    def _handle_product_number(self, prod_id: int):
        bundle = self.context.get("ticket_bundle")
        if not bundle:
            self._mostrar_error_entrada()
            return
        
        prods_ticket = bundle.get("productos", [])
        found = next((p for p in prods_ticket if p.get("id") == prod_id), None)
        
        if not found:
            ids_validos = [p.get("id") for p in prods_ticket]
            self._mostrar_error_entrada()
            self._print_prompt()
            return
        
        self.context["productos"].append(prod_id)
        self._enqueue_and_play(["resp7"], ST.MORE_PRODUCT)

    def _mostrar_resumen_y_finalizar(self):
        ctx = self.context
        bundle = ctx.get("ticket_bundle")
        ids_seleccionados = ctx.get("productos", [])

        print("\n" + "═" * 70)
        print(f"{'RESUMEN FINAL DE LA INTERACCIÓN':^70}")
        print("═" * 70)
        
        # 1. Opciones seleccionadas por el usuario y Encuesta
        print(f" 📌 OPERACIÓN:      {str(ctx.get('branch', 'General')).upper()}")
        print(f" 📌 MOTIVO/RAZÓN:   {str(ctx.get('razon', 'N/A')).upper()}")
        print(f" ⭐ CALIFICACIÓN:   {ctx.get('survey', 'N/A')}/5")
        
        # 2. Información completa del ticket con resaltado
        if bundle:
            print("-" * 70)
            print(f" 🧾 TICKET #{bundle.get('ticket_num')} | 📅 {bundle.get('fecha')}")
            print(f" 👤 CLIENTE: {bundle.get('cliente', {}).get('Nombre', 'Desconocido')}")
            print("-" * 70)
            
            # Encabezados de tabla
            print(f" {'ID':<6} | {'PRODUCTO':<32} | {'PRECIO':>10} | {'ESTADO'}")
            print("-" * 70)

            for prod in bundle.get("productos", []):
                p_id = prod.get('id')
                nombre = prod.get('NombreProducto', 'Sin nombre')[:30] # Truncar si es muy largo
                precio = prod.get('PrecioVenta', 0.0)
                
                # Lógica de resaltado
                es_seleccionado = p_id in ids_seleccionados
                
                marcador_izq = ">>" if es_seleccionado else "  "
                marcador_der = " <-- [OBJETO DEL TRÁMITE]" if es_seleccionado else ""
                
                # Renderizado de la fila
                print(f" {marcador_izq:<2} {str(p_id):<6} | {nombre:<32} | ${precio:>9.2f} |{marcador_der}")

            print("-" * 70)
            print(f" TOTAL TICKET: ${bundle.get('total', 0.0):.2f}")
        else:
            print(" [!] No se cargó información detallada del ticket en esta sesión.")
            
        print("═" * 70 + "\n")
        
        # Reinicio del contexto para la siguiente interacción
        self.context = {
            "branch": None,
            "razon": None,
            "ticket_num": None,
            "ticket_bundle": None,
            "productos": [],
            "survey": None
        }
        # Regresar al video de 'Bienvenida' o Menú Principal
        self._enqueue_and_play(["resp1"], ST.MAIN)
        print("\n╔════════════════════════════════════════════════════════╗")
        print("║          RESUMEN DE INTERACCIÓN                        ║")
        print("╚════════════════════════════════════════════════════════╝")
        print(f"  Ticket:    {self.context.get('ticket_num')}")
        print(f"  Prod. IDs: {self.context.get('productos')}")
        print(f"  Encuesta:  {self.context.get('survey')}/5")
        print("╚════════════════════════════════════════════════════════╝\n")
        
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
            # Lógica de descarga simplificada
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
        self._swap(win)
        self._bloquear(True)
        print("\n" + RESP_TEXTO["resp1"] + "\n")

        def _after_first():
            self._bloquear(False)
            self._safe_disconnect_all(win)
            self._hook_interaccion(win)
            self._set_state(ST.MAIN)
        win.video_terminado.connect(_after_first)

    def run(self):
        self.mostrar_bienvenida()
        sys.exit(self.app.exec_())
    
    # --------------------------------------------------------------------------
    # NUEVO MÉTODO AUXILIAR: Enviar a Telegram
    # --------------------------------------------------------------------------
    def _enviar_telegram(self, mensaje_texto):
        """Envía el texto formateado al bot de Telegram configurado."""
        if not TG_TOKEN or not TG_CHAT_ID:
            print("[Telegram] No se ha configurado Token o Chat ID.")
            return

        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        
        # Envolvemos el mensaje en etiquetas de código (```) para que Telegram
        # respete el formato de tabla y la fuente monoespaciada.
        texto_formateado = f"```text\n{mensaje_texto}\n```"

        payload = {
            "chat_id": TG_CHAT_ID,
            "text": texto_formateado,
            "parse_mode": "MarkdownV2" # Importante para que se vea como bloque de código
        }
        
        try:
            # Enviamos en un hilo o con timeout corto para no congelar la UI si falla internet
            requests.post(url, json=payload, timeout=3)
            print("[Telegram] Reporte enviado correctamente.")
        except Exception as e:
            print(f"[Telegram] Error al enviar reporte: {e}")

    # --------------------------------------------------------------------------
    # MÉTODO ACTUALIZADO: Construye string, imprime y envía
    # --------------------------------------------------------------------------
    def _mostrar_resumen_y_finalizar(self):
        ctx = self.context
        bundle = ctx.get("ticket_bundle")
        ids_seleccionados = ctx.get("productos", [])

        # Construimos el mensaje línea por línea en una lista para manejarlo limpio
        lineas = []
        lineas.append("═" * 60)
        lineas.append(f"{'RESUMEN FINAL DE LA INTERACCIÓN':^60}")
        lineas.append("═" * 60)
        
        # 1. Datos Generales
        lineas.append(f" 📌 OPERACIÓN:      {str(ctx.get('branch', 'General')).upper()}")
        lineas.append(f" 📌 MOTIVO/RAZÓN:   {str(ctx.get('razon', 'N/A')).upper()}")
        lineas.append(f" ⭐ CALIFICACIÓN:   {ctx.get('survey', 'N/A')}/5")
        
        # 2. Información del Ticket
        if bundle:
            lineas.append("-" * 60)
            lineas.append(f" 🧾 TICKET #{bundle.get('ticket_num')} | 📅 {bundle.get('fecha')}")
            nom_cliente = bundle.get('cliente', {}).get('Nombre', 'N/A')
            # Si el nombre es muy largo, lo cortamos para que no rompa la tabla
            lineas.append(f" 👤 CLIENTE: {nom_cliente[:40]}")
            lineas.append("-" * 60)
            
            # Encabezados
            lineas.append(f" {'ID':<6} | {'PRODUCTO':<23} | {'PRECIO':>9} | ESTADO")
            lineas.append("-" * 60)

            for prod in bundle.get("productos", []):
                p_id = prod.get('id')
                nombre = prod.get('NombreProducto', 'Sin nombre')[:23]
                precio = prod.get('PrecioVenta', 0.0)
                
                es_seleccionado = p_id in ids_seleccionados
                
                # Definición de marcadores visuales
                m_izq = ">>" if es_seleccionado else "  "
                m_der = " <-- [OBJETO]" if es_seleccionado else ""
                
                lineas.append(f" {m_izq:<2} {str(p_id):<6} | {nombre:<23} | ${precio:>8.2f} |{m_der}")

            lineas.append("-" * 60)
            lineas.append(f" TOTAL TICKET: ${bundle.get('total', 0.0):.2f}")
        else:
            lineas.append(" [!] Sin información de ticket asociada.")
            
        lineas.append("═" * 60)
        
        # Unimos todo en un solo string
        mensaje_completo = "\n".join(lineas)

        # 1. Imprimir en consola local (como antes)
        print("\n" + mensaje_completo + "\n")

        # 2. Enviar a Telegram
        self._enviar_telegram(mensaje_completo)
        
        # --- Limpieza y Reinicio ---
        self.context = {
            "branch": None,
            "razon": None,
            "ticket_num": None,
            "ticket_bundle": None,
            "productos": [],
            "survey": None
        }
        self._enqueue_and_play(["resp1"], ST.MAIN)