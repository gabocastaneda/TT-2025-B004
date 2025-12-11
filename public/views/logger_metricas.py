# -*- coding: utf-8 -*-
# public/views/logger_metricas.py
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import threading

class LoggerMetricas:
    """Sistema de logging y métricas para el gestor de aplicación"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path / "logs"
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.archivo_metricas = self.base_path / "metricas.json"
        self.archivo_log = self.base_path / "sistema_log.txt"
        self.archivo_errores = self.base_path / "errores_captura.txt"
        
        self.lock = threading.Lock()
        self.sesion_activa = False
        self._inicializar_metricas()
    
    def _inicializar_metricas(self):
        """Carga o crea archivo de métricas"""
        if self.archivo_metricas.exists():
            try:
                with open(self.archivo_metricas, 'r', encoding='utf-8') as f:
                    self.metricas = json.load(f)
            except:
                self.metricas = self._estructura_metricas_vacia()
        else:
            self.metricas = self._estructura_metricas_vacia()
            self._guardar_metricas()
    
    def _estructura_metricas_vacia(self) -> Dict[str, Any]:
        """Estructura inicial de métricas"""
        return {
            "total_usos": 0,
            "ramas": {
                "devolucion": 0,
                "facturacion": 0,
                "aclaracion": 0,
                "dudas": 0,
                "otros": 0
            },
            "razones_devolucion": {
                "danado": 0,
                "defecto": 0,
                "equivocacion": 0,
                "ninguno": 0
            },
            "calificaciones": {
                "1_estrella": 0,
                "2_estrellas": 0,
                "3_estrellas": 0,
                "4_estrellas": 0,
                "5_estrellas": 0,
                "promedio": 0.0
            },
            "errores_captura": {
                "MAIN": 0,
                "DEV_MENU": 0,
                "DEV_REASON": 0,
                "ASK_TICKET_YN": 0,
                "WAIT_TICKET": 0,
                "WAIT_PRODUCT": 0,
                "MORE_PRODUCT": 0,
                "RESP3_MAIN": 0,
                "RESP3_NINGUNO": 0,
                "RESP3_NO_TICKET": 0,
                "SURVEY": 0
            },
            "sin_solucion": 0,  # Cuando captura "ninguno" y no se puede ayudar
            "alertas_usabilidad": 0,
            "inactividad_timeout": 0,
            "ultima_actualizacion": None
        }
    
    def _guardar_metricas(self):
        """Guarda métricas en archivo JSON"""
        with self.lock:
            self.metricas["ultima_actualizacion"] = datetime.now().isoformat()
            try:
                with open(self.archivo_metricas, 'w', encoding='utf-8') as f:
                    json.dump(self.metricas, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self._log_error(f"Error guardando métricas: {e}")
    
    def _log_evento(self, mensaje: str):
        """Escribe evento en log de texto"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{timestamp}] {mensaje}\n"
        try:
            with open(self.archivo_log, 'a', encoding='utf-8') as f:
                f.write(linea)
        except Exception as e:
            print(f"Error escribiendo log: {e}")
    
    def _log_error(self, mensaje: str):
        """Escribe error en log de errores"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{timestamp}] {mensaje}\n"
        try:
            with open(self.archivo_errores, 'a', encoding='utf-8') as f:
                f.write(linea)
        except Exception as e:
            print(f"Error escribiendo log de errores: {e}")
    
    # ========== MÉTODOS PÚBLICOS DE REGISTRO ==========
    
    def registrar_inicio_sesion(self):
        """Registra el inicio de una nueva sesión"""
        with self.lock:
            if not self.sesion_activa:
                self.metricas["total_usos"] += 1
                self.sesion_activa = True
        self._guardar_metricas()
        self._log_evento(f"INICIO DE SESIÓN #{self.metricas['total_usos']}")
    
    def registrar_rama(self, rama: str):
        """Registra qué rama seleccionó el usuario"""
        rama_norm = rama.lower()
        with self.lock:
            if rama_norm in self.metricas["ramas"]:
                self.metricas["ramas"][rama_norm] += 1
            else:
                self.metricas["ramas"][rama_norm] = 1
        self._guardar_metricas()
        self._log_evento(f"RAMA SELECCIONADA: {rama}")
    
    def registrar_razon_devolucion(self, razon: str):
        """Registra la razón de devolución"""
        razon_norm = razon.lower()
        with self.lock:
            if razon_norm in self.metricas["razones_devolucion"]:
                self.metricas["razones_devolucion"][razon_norm] += 1
            else:
                self.metricas["razones_devolucion"][razon_norm] = 1
        self._guardar_metricas()
        self._log_evento(f"RAZÓN DEVOLUCIÓN: {razon}")
    
    def registrar_calificacion(self, calificacion: int):
        """Registra la calificación de la encuesta (1-5)"""
        if not (1 <= calificacion <= 5):
            return
        
        key = f"{calificacion}_estrella{'s' if calificacion > 1 else ''}"
        
        with self.lock:
            self.metricas["calificaciones"][key] += 1
            
            # Recalcular promedio
            total = sum(self.metricas["calificaciones"][f"{i}_estrella{'s' if i > 1 else ''}"] 
                       for i in range(1, 6))
            if total > 0:
                suma_ponderada = sum(i * self.metricas["calificaciones"][f"{i}_estrella{'s' if i > 1 else ''}"] 
                                    for i in range(1, 6))
                self.metricas["calificaciones"]["promedio"] = round(suma_ponderada / total, 2)
        
        self._guardar_metricas()
        self._log_evento(f"CALIFICACIÓN: {calificacion} estrellas (Promedio: {self.metricas['calificaciones']['promedio']})")
    
    def registrar_error_captura(self, estado: str, entrada: str):
        """Registra un error de captura en un estado específico"""
        with self.lock:
            if estado in self.metricas["errores_captura"]:
                self.metricas["errores_captura"][estado] += 1
            else:
                self.metricas["errores_captura"][estado] = 1
        self._guardar_metricas()
        self._log_error(f"ERROR EN {estado} - Entrada: '{entrada}'")
    
    def registrar_sin_solucion(self):
        """Registra cuando se selecciona 'ninguno' y no se puede ayudar"""
        with self.lock:
            self.metricas["sin_solucion"] += 1
        self._guardar_metricas()
        self._log_evento("SIN SOLUCIÓN - Usuario seleccionó 'ninguno'")
    
    def registrar_alerta_usabilidad(self, estado: str, intentos: int):
        """Registra cuando se dispara una alerta de usabilidad (3 errores)"""
        with self.lock:
            self.metricas["alertas_usabilidad"] += 1
        self._guardar_metricas()
        self._log_evento(f"ALERTA USABILIDAD - Estado: {estado}, Intentos fallidos: {intentos}")
    
    def registrar_timeout_inactividad(self):
        """Registra cuando hay timeout por inactividad"""
        with self.lock:
            self.metricas["inactividad_timeout"] += 1
        self._guardar_metricas()
        self._log_evento("TIMEOUT POR INACTIVIDAD")
    
    def registrar_fin_sesion(self, exito: bool = True):
        """Registra el fin de una sesión (ciclo completo)"""
        if not self.sesion_activa:
            return
        
        with self.lock:
            self.sesion_activa = False
        
        estado = "EXITOSA" if exito else "INCOMPLETA"
        self._log_evento(f"FIN DE CICLO - {estado}")
        self._log_evento("-" * 60)
    
    def registrar_cierre_aplicacion(self):
        """Registra el cierre completo de la aplicación"""
        self._log_evento("="*70)
        self._log_evento("APLICACIÓN CERRADA")
        self._log_evento("="*70)
        self._log_evento("")
        
        # Guardar métricas finales
        self._guardar_metricas()
        
        # Exportar reporte automático
        self.exportar_reporte_txt(f"reporte_cierre_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    # ========== MÉTODOS DE CONSULTA ==========
    
    def obtener_reporte_completo(self) -> str:
        """Genera un reporte de texto con todas las métricas"""
        m = self.metricas
        
        lineas = []
        lineas.append("=" * 70)
        lineas.append("REPORTE DE MÉTRICAS DEL SISTEMA")
        lineas.append("=" * 70)
        lineas.append(f"Última actualización: {m.get('ultima_actualizacion', 'N/A')}")
        lineas.append("")
        
        # Uso general
        lineas.append("USO GENERAL")
        lineas.append(f"  Total de usos: {m['total_usos']}")
        lineas.append("")
        
        # Ramas
        lineas.append("RAMAS SELECCIONADAS")
        for rama, count in m["ramas"].items():
            porcentaje = (count / m['total_usos'] * 100) if m['total_usos'] > 0 else 0
            lineas.append(f"  {rama.capitalize():<15}: {count:>4} ({porcentaje:>5.1f}%)")
        lineas.append("")
        
        # Razones de devolución
        lineas.append("RAZONES DE DEVOLUCIÓN")
        total_dev = sum(m["razones_devolucion"].values())
        for razon, count in m["razones_devolucion"].items():
            porcentaje = (count / total_dev * 100) if total_dev > 0 else 0
            lineas.append(f"  {razon.capitalize():<15}: {count:>4} ({porcentaje:>5.1f}%)")
        lineas.append("")
        
        # Calificaciones
        lineas.append("CALIFICACIONES")
        lineas.append(f"  Promedio: {m['calificaciones']['promedio']:.2f} / 5.00")
        for i in range(5, 0, -1):
            key = f"{i}_estrella{'s' if i > 1 else ''}"
            count = m["calificaciones"][key]
            estrellas = "★" * i + "☆" * (5-i)
            lineas.append(f"  {estrellas} ({i}): {count:>4}")
        lineas.append("")
        
        # Errores por sección
        lineas.append("ERRORES DE CAPTURA POR SECCIÓN")
        total_errores = sum(m["errores_captura"].values())
        lineas.append(f"  Total de errores: {total_errores}")
        for estado, count in sorted(m["errores_captura"].items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                porcentaje = (count / total_errores * 100) if total_errores > 0 else 0
                lineas.append(f"  {estado:<20}: {count:>4} ({porcentaje:>5.1f}%)")
        lineas.append("")
        
        # Estadísticas adicionales
        lineas.append("ESTADÍSTICAS ADICIONALES")
        lineas.append(f"  Sin solución: {m['sin_solucion']}")
        lineas.append(f"  Alertas de usabilidad: {m['alertas_usabilidad']}")
        lineas.append(f"  Timeouts por inactividad: {m['inactividad_timeout']}")
        lineas.append("")
        lineas.append("=" * 70)
        
        return "\n".join(lineas)
    
    def exportar_reporte_txt(self, nombre_archivo: Optional[str] = None):
        """Exporta el reporte completo a un archivo .txt"""
        if nombre_archivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"reporte_{timestamp}.txt"
        
        ruta = self.base_path / nombre_archivo
        reporte = self.obtener_reporte_completo()
        
        try:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(reporte)
            print(f"Reporte exportado: {ruta}")
            return str(ruta)
        except Exception as e:
            print(f"Error exportando reporte: {e}")
            return None
    
    def resetear_metricas(self):
        """Resetea todas las métricas (usar con precaución)"""
        respaldo = self.base_path / f"metricas_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(self.archivo_metricas, 'r', encoding='utf-8') as f:
                contenido = f.read()
            with open(respaldo, 'w', encoding='utf-8') as f:
                f.write(contenido)
            print(f"✅ Respaldo creado: {respaldo}")
        except:
            pass
        
        self.metricas = self._estructura_metricas_vacia()
        self._guardar_metricas()
        self._log_evento("🔄 MÉTRICAS RESETEADAS")
        print("✅ Métricas reseteadas")