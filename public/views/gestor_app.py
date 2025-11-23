# -*- coding: utf-8 -*-
# public/views/gestor_app.py — flujo con consola + UI segura en hilo principal
import sys, requests, traceback
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

from public.views.formatos.bienvenida import VentanaBienvenida
from public.views.formatos.respuesta_unica import VentanaReproductorVideo
from public.views.formatos.interaccion import VentanaInteraccion

from public.views.config.mapa_interaccion import build_mapa_videos_interaccion, FILE_IDS
from public.views.config.drive_config import drive_api_url

# BD (ticket)
from backend.repo_tickets import fetch_ticket_bundle, render_ticket_text

# RESP que van en Interacción y en Respuesta Única
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
        print("Escribe palabras del flujo (p.ej. devolucion, producto, danado, si/no)")
        print("Cuando se solicite, escribe números para ticket/producto/encuesta.")
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

class GestorAplicacion:
    FILE_ID_BIENVENIDA = "1D_Mzl0UdVYyTKY2a1jeOVW-2cKmZ30lj"

    def __init__(self, app: QApplication):
        self.app = app
        self.ventana_actual = None
        self.playing = False
        self.modo_gestos_activo = False

        self.dir_public = Path(__file__).resolve().parents[1]
        self.dir_videos = self.dir_public / "videos"
        self.dir_videos.mkdir(parents=True, exist_ok=True)
        print("VIDEO_DIR =", self.dir_videos)

        self.mapa = build_mapa_videos_interaccion(self.dir_videos)

        self.state = ST.MAIN
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
            print(f"[DESCARGA] {resp_name}.mp4 …")
            with requests.get(drive_api_url(file_id), stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(p, "wb") as f:
                    for ch in r.iter_content(1<<20):
                        if ch:
                            f.write(ch)
            print("[OK]", p)
            return str(p)
        except Exception as e:
            print("[ERR] Descargando", resp_name, ":", e)
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
                print("[GESTOS]Modo gestos activado")
            else:
                print("[GESTOS]Modo gestos desactivado")

    def _on_gesto_detectado(self, gesto: str):
        if not self.modo_gestos_activo or self.playing:
            return
        print(f"[GESTOS]Gesto detectado: '{gesto}'")
        self._on_txt_ui_guarded(gesto)

    def _mostrar_error_entrada(self):
        """Muestra la ventana de error cuando la entrada no es válida"""
        if isinstance(self.ventana_actual, VentanaInteraccion):
            self.ventana_actual.mostrar_error_captura()
            print("[ERROR] Entrada no válida - mostrando mensaje al usuario")

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
                print("[UI] set_modo_reproduccion(False) error:", e)

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
        if self.state == ST.MAIN:
            print("> Capture alguna de las siguientes opciones: facturacion | devolucion | dudas | otros")
        elif self.state == ST.DEV_MENU:
            print("> Estas son nuestras opciones para devolucion: producto  |  ninguno")
        elif self.state == ST.DEV_REASON:
            print("> Estas son nuestras opciones para producto: danado / defecto / equivocacion")
        elif self.state == ST.ASK_TICKET_YN:
            print("> Gestos: 'si' o 'no'")
        elif self.state == ST.WAIT_TICKET:
            print("> Captura el número de ticket:")
        elif self.state == ST.WAIT_PRODUCT:
            print("> CAPTURE EL NUMERO DEL PRODUCTO:")
        elif self.state == ST.MORE_PRODUCT:
            print("> ¿Hay otro producto? (si/no)")
            print("> Gestos: 'si' o 'no'")
        elif self.state == ST.RESP3_MAIN:
            print("> ¿Hay algo más en lo que pueda ayudar? (si/no)")
            print("> Gestos: 'si' o 'no'")
        elif self.state == ST.RESP3_NINGUNO:
            print("> ¿Hay algo más en lo que pueda ayudar? (si/no)")
            print("> Gestos: 'si' o 'no'")
        elif self.state == ST.RESP3_NO_TICKET:
            print("> Escribe: no  (seguirá a encuesta)")
            print("> Gesto: 'no'")
        elif self.state == ST.SURVEY:
            print("> Califica del 1 al 5:")

    def _on_txt_ui_guarded(self, s: str):
        try:
            self._on_txt_ui(s)
        except Exception as e:
            print("[UI] Excepción en entrada:", e)
            traceback.print_exc()
            self._print_prompt()

    def _on_txt_ui(self, s: str):
        if self.playing:
            print("Espera a que termine el video…")
            return

        v = _norm(s)

        if v.isdigit():
            if self.state == ST.WAIT_TICKET:
                self._handle_ticket_number(int(v))
                return
            if self.state == ST.WAIT_PRODUCT:
                self._handle_product_number(int(v))
                return
            if self.state == ST.SURVEY:
                n = int(v)
                if 1 <= n <= 5:
                    self.context["survey"] = n
                    self._mostrar_resumen_y_finalizar()
                else:
                    print("[ERROR] Respuesta inválida. Debe ser del 1 al 5.")
                    self._mostrar_error_entrada()
                    self._print_prompt()
                return

        if self.state == ST.MAIN:
            if v in {"devolucion","devolución"}:
                self.context = {
                    "branch": "devolucion",
                    "razon": None,
                    "ticket_num": None,
                    "ticket_bundle": None,
                    "productos": [],
                    "survey": None
                }
                self._enqueue_and_play(["resp11"], ST.DEV_MENU)
            else:
                print("[ERROR] Opción no válida. Por ahora sólo 'devolucion'.")
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.DEV_MENU:
            if v == "producto":
                self._enqueue_and_play(["resp12"], ST.DEV_REASON)
            elif v == "ninguno":
                self._enqueue_and_play(["resp2","resp3"], ST.RESP3_NINGUNO)
            else:
                print("[ERROR] Opción no válida. Escribe: producto | ninguno")
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.DEV_REASON:
            if v in {"danado","dañado","defecto","equivocacion","equivocación"}:
                self.context["razon"] = v
                self._enqueue_and_play(["resp9"], ST.ASK_TICKET_YN)
            else:
                print("[ERROR] Razón no válida. Opciones: danado | defecto | equivocacion")
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.ASK_TICKET_YN:
            if _yes(v):
                self._enqueue_and_play(["resp10"], ST.WAIT_TICKET)
            elif _no(v):
                self._enqueue_and_play(["resp6","resp3"], ST.RESP3_NO_TICKET)
            else:
                print("[ERROR] Respuesta no válida. Responde: si | no")
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.MORE_PRODUCT:
            if _yes(v):
                bundle = self.context.get("ticket_bundle")
                if bundle and isinstance(self.ventana_actual, VentanaInteraccion):
                    texto = render_ticket_text(bundle)
                    print("\n=== INFORMACIÓN DEL TICKET (para seleccionar otro) ===")
                    print(texto)
                    print("======================================================\n")
                    self._bloquear(True)
                    self.ventana_actual.mostrar_overlay_texto(
                        texto, ms=10_000,
                        on_done=lambda: (self._bloquear(False), self._set_state(ST.WAIT_PRODUCT))
                    )
                else:
                    self._set_state(ST.WAIT_PRODUCT)
            elif _no(v):
                self._enqueue_and_play(["resp4","resp8","resp3"], ST.RESP3_MAIN)
            else:
                print("[ERROR] Respuesta no válida. Responde: si | no")
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.RESP3_MAIN:
            if _yes(v):
                self._enqueue_and_play(["resp1"], ST.MAIN)
            elif _no(v):
                self._enqueue_and_play(["resp5"], ST.SURVEY)
            else:
                print("[ERROR] Respuesta no válida. Responde: si | no")
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.RESP3_NINGUNO:
            if _yes(v):
                self._enqueue_and_play(["resp1"], ST.MAIN)
            elif _no(v):
                self._enqueue_and_play(["resp4","resp5"], ST.SURVEY)
            else:
                print("[ERROR] Respuesta no válida. Responde: si | no")
                self._mostrar_error_entrada()
                self._print_prompt()

        elif self.state == ST.RESP3_NO_TICKET:
            if _no(v):
                self._enqueue_and_play(["resp4","resp5"], ST.SURVEY)
            else:
                print("[ERROR] Para este flujo, responde 'no'.")
                self._mostrar_error_entrada()
                self._print_prompt()

        else:
            self._set_state(ST.MAIN)

    def _handle_ticket_number(self, num: int):
        try:
            bundle = fetch_ticket_bundle(num)
        except Exception as e:
            print(f"[DB] Error al consultar ticket {num}: {e}")
            traceback.print_exc()
            self._mostrar_error_entrada()
            self._print_prompt()
            return

        if not bundle:
            print(f"[ERROR] No existe el ticket {num}. Intenta de nuevo.")
            self._mostrar_error_entrada()
            self._print_prompt()
            return

        texto = render_ticket_text(bundle)
        print("\n=== INFORMACIÓN DEL TICKET ===")
        print(texto)
        print("==============================\n")

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

        self._bloquear(True)
        self.ventana_actual.mostrar_overlay_texto(
            render_ticket_text(bundle), ms=10_000,
            on_done=lambda: (self._bloquear(False), self._set_state(ST.WAIT_PRODUCT))
        )

    def _handle_product_number(self, prod: int):
        bundle = self.context.get("ticket_bundle")
        if not bundle:
            print(f"[ERROR] No hay ticket cargado.")
            self._mostrar_error_entrada()
            self._print_prompt()
            return
        
        # Validar que el producto existe en el ticket
        productos_ids = [p["id"] for p in bundle.get("productos", [])]
        if prod not in productos_ids:
            print(f"[ERROR] El producto {prod} no existe en este ticket.")
            print(f"Productos disponibles: {productos_ids}")
            self._mostrar_error_entrada()
            self._print_prompt()
            return
        
        self.context["productos"].append(prod)
        print(f"[OK] Producto {prod} agregado correctamente")
        self._enqueue_and_play(["resp7"], ST.MORE_PRODUCT)

    def _mostrar_resumen_y_finalizar(self):
        print("\n╔════════════════════════════════════════════════════════╗")
        print("║          RESUMEN DE INTERACCIÓN                        ║")
        print("╚════════════════════════════════════════════════════════╝")
        print(f"  Rama:      {self.context.get('branch', 'N/A')}")
        print(f"  Razón:     {self.context.get('razon', 'N/A')}")
        print(f"  Ticket:    {self.context.get('ticket_num', 'N/A')}")
        print(f"  Productos: {self.context.get('productos', [])}")
        print(f"  Encuesta:  {self.context.get('survey', 'N/A')}/5")
        print("╚════════════════════════════════════════════════════════╝\n")
        print("¡Gracias por utilizar nuestro sistema!")
        print("La interacción ha finalizado.\n")
        print("Iniciando nueva interacción...\n")
        
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
            try:
                print("[DESCARGA] bienvenida.mp4 …")
                with requests.get(drive_api_url(self.FILE_ID_BIENVENIDA), stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in r.iter_content(1<<20):
                            if chunk:
                                f.write(chunk)
                print("[OK]", dest)
            except Exception as e:
                print("[ERR] No se pudo preparar bienvenida:", e)
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