# ===== PRUEBA GOOGLE API / PYQT FOTOS Y VIDEOS=====

import os
import io
import cv2
import sys
import pickle
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QVBoxLayout, QHBoxLayout, QMessageBox, QLineEdit,
                             QPushButton, QFrame)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QPixmap, QImage, QPalette, QBrush
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from PIL import Image

# CONFIGURACIÓN GOOGLE DRIVE
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def autenticar_drive():
    """Autenticación con Google Drive usando OAuth2"""
    creds = None
    cred_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../credentials.json"))

    if os.path.exists("token.pkl"):
        with open("token.pkl", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            #Uso de local server
            creds = flow.run_local_server(port=0)

        with open("token.pkl", "wb") as token:
            pickle.dump(creds, token)

    return build("drive", "v3", credentials=creds)


def descargar_archivo(service, nombre_archivo, carpeta_destino="temp"):
    """Descarga de archivo - Google Drive por nombre"""
    os.makedirs(carpeta_destino, exist_ok=True)
    resultados = service.files().list(
        q=f"name='{nombre_archivo}'",
        fields="files(id, name)"
    ).execute()

    items = resultados.get("files", [])
    if not items:
        raise FileNotFoundError(f"No se encontró el archivo '{nombre_archivo}' en Drive")

    file_id = items[0]["id"]
    request = service.files().get_media(fileId=file_id)
    ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

    with io.FileIO(ruta_destino, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    return ruta_destino

# CLASE PRINCIPAL DE LA APLICACIÓN
class DriveViewerApp(QMainWindow):
    def __init__(self, nombre_archivo):
        super().__init__()
        self.service = None
        self.cap = None
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.mostrar_frame_video)
        self.ruta_actual = None
        self.nombre_archivo = nombre_archivo
        
        self.initUI()
        self.autenticar()
        
    def initUI(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("Visor desde Google Drive")
        self.setFixedSize(900, 600)
        
        # Configuración de fondo
        ruta_fondo = os.path.abspath(os.path.join(os.path.dirname(__file__), "../images/fondo2.png"))
        if os.path.exists(ruta_fondo):
            palette = QPalette()
            pixmap = QPixmap(ruta_fondo).scaled(900, 600)
            palette.setBrush(QPalette.Window, QBrush(pixmap))
            self.setPalette(palette)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Recuadro para imagen/video
        self.recuadro = QFrame()
        self.recuadro.setFixedSize(600, 400)
        self.recuadro.setStyleSheet("""
            QFrame {
                background-color: black;
                border-radius: 15px;
            }
        """)
        
        # Layout para el recuadro
        recuadro_layout = QVBoxLayout(self.recuadro)
        self.contenido_label = QLabel()
        self.contenido_label.setAlignment(Qt.AlignCenter)
        self.contenido_label.setStyleSheet("color: white;")
        self.contenido_label.setText("Cargando...")
        recuadro_layout.addWidget(self.contenido_label)
        
        # Widgets de layout principal
        layout.addWidget(self.recuadro, alignment=Qt.AlignCenter)
        
    def autenticar(self):
        """Realiza la autenticación con Google Drive"""
        try:
            self.service = autenticar_drive()
            self.cargar_archivo()
        except Exception as e:
            QMessageBox.critical(self, "Error de autenticación", str(e))
    
    def cargar_archivo(self):
        """Carga el archivo desde Google Drive usando el nombre proporcionado"""
        if not self.nombre_archivo:
            QMessageBox.warning(self, "Advertencia", "No se proporcionó un nombre de archivo")
            return
            
        try:
            ruta_descargada = descargar_archivo(self.service, self.nombre_archivo)
            self.ruta_actual = ruta_descargada
            
            # Comparación Imagen/Video
            extension = os.path.splitext(ruta_descargada)[1].lower()
            if extension in [".png", ".jpg", ".jpeg"]:
                self.mostrar_imagen(ruta_descargada)
            elif extension in [".mp4", ".avi", ".mov"]:
                self.reproducir_video(ruta_descargada)
            else:
                QMessageBox.warning(self, "Formato no soportado", f"El archivo {extension} no es compatible")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def mostrar_imagen(self, ruta):
        """Muestra una imagen en el recuadro"""
        try:
            img = Image.open(ruta)
            img = img.resize((600, 400), Image.Resampling.LANCZOS)
            img.save("temp_img.png")  # Guarda temporalmente para cargar con QPixmap
            
            pixmap = QPixmap("temp_img.png")
            self.contenido_label.setPixmap(pixmap)
            os.remove("temp_img.png")  # Elimina archivo temporal
            
        except Exception as e:
            QMessageBox.critical(self, "Error mostrando imagen", str(e))
    
    def reproducir_video(self, ruta):
        """Reproduce un video dentro del recuadro"""
        if self.cap:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(ruta)
        
        # Obtención de metadatos del video
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duracion = total_frames / fps if fps > 0 else 0
        ancho = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        calidad = ancho * alto  #Resolución - Calidad
        
        print("\n=== Datos del Video ===")
        print(f"⏱ Tiempo de reproducción: {duracion:.2f} segundos")
        print(f"🎞 FPS: {fps:.2f}")
        print(f"📐 Dimensiones: {ancho} x {alto}")
        print(f"📊 Calidad (resolución total): {calidad} píxeles\n")
        
        # Reproducción de video
        self.video_timer.start(30)  #Estandarización a 30 fps
    
    def mostrar_frame_video(self):
        """Muestra un frame del video"""
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image).scaled(600, 400, Qt.KeepAspectRatio)
                self.contenido_label.setPixmap(pixmap)
            else:
                # Señalización de video terminado
                self.video_timer.stop()
                self.cap.release()
                self.cap = None
                
                # Espera de 2 segundos antes de borrar
                QTimer.singleShot(2000, self.borrar_archivo_actual)
    
    def borrar_archivo_actual(self):
        """Elimina el archivo actual si existe"""
        if self.ruta_actual and os.path.exists(self.ruta_actual):
            try:
                os.remove(self.ruta_actual)
                print(f"Archivo eliminado: {self.ruta_actual}")
            except Exception as e:
                print(f"Error borrando archivo {self.ruta_actual}: {e}")
    
    def closeEvent(self, event):
        """Maneja el cierre de la aplicación"""
        # Limpieza de recursos
        if self.cap:
            self.cap.release()
        
        # Limpieza de carpeta temp
        temp_dir = os.path.join(os.path.dirname(__file__), "temp")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        event.accept()

# EJECUCIÓN DE LA APLICACIÓN
if __name__ == "__main__":
    # Obtención de nombre del archivo 
    if len(sys.argv) > 1:
        nombre_archivo = sys.argv[1]
    else:
        # Si no se proporcionó un argumento, se pide por input
        nombre_archivo = input("Nombre exacto de la imagen o video en Drive: ").strip()
    
    app = QApplication(sys.argv)
    viewer = DriveViewerApp(nombre_archivo)
    viewer.show()
    sys.exit(app.exec_())