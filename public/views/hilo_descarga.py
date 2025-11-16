import sys
import os
import time
import requests
import re # Necesario para extraer el ID y el token de confirmación
import shutil
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from pathlib import Path

class HiloDescarga(QThread):
    senal_descarga_terminada = pyqtSignal(str, str) 
    
    def __init__(self, url_video):
        super().__init__()
        self.url_video = url_video
        self.dir_guardado = Path(__file__).resolve().parents[1] / 'videos'  # .../public/videos  (bien)

    def _extraer_id_y_nombre(self):
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', self.url_video)
        if not match:
            return None, None
        file_id = match.group(1)
        nombre_base = f"descargado_{file_id[:8]}.mp4"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        return download_url, nombre_base

    def run(self):
        download_url, nombre_archivo = self._extraer_id_y_nombre()
        
        if not download_url:
            print("Error: No se pudo extraer el ID del archivo de Google Drive.")
            self.senal_descarga_terminada.emit("Error de URL", None)
            return

        self.dir_guardado.mkdir(parents=True, exist_ok=True)
        ruta_guardado_permanente = self.dir_guardado / nombre_archivo
        
        if ruta_guardado_permanente.is_file():
             print(f"El archivo ya existe: {ruta_guardado_permanente}. Saltando descarga.")
             self.senal_descarga_terminada.emit(nombre_archivo, str(ruta_guardado_permanente))
             return

        print(f"Iniciando descarga")
        start_time = time.time()
        
        session = requests.Session()
        response = session.get(download_url, stream=True)
        
        if "confirm" in response.text:
            m = re.search(r"confirm=([0-9A-Za-z_]+)", response.text)
            if m:
                confirm_token = m.group(1)
                download_url_confirmed = download_url + "&confirm=" + confirm_token
                response = session.get(download_url_confirmed, stream=True)
            else:
                print("Error: No se encontró el token de confirmación.")
                self.senal_descarga_terminada.emit(nombre_archivo, None)
                return

        try:
            response.raise_for_status()
            
            with open(ruta_guardado_permanente, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk: 
                        f.write(chunk)
            
            end_time = time.time()
            download_time = end_time - start_time
            
            print(f"Video '{nombre_archivo}' descargado y guardado en: {ruta_guardado_permanente}")
            print(f"Tiempo de descarga: {download_time:.2f} segundos.")
            
            self.senal_descarga_terminada.emit(nombre_archivo, str(ruta_guardado_permanente))
            
        except requests.exceptions.RequestException as e:
            print(f"Error al descargar el video '{nombre_archivo}' de Google Drive: {e}")
            if ruta_guardado_permanente.is_file():
                ruta_guardado_permanente.unlink()
            self.senal_descarga_terminada.emit(nombre_archivo, None)