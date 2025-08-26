# ===== PRUEBA GOOGLE API / THINKER FOTOS Y VIDEOS=====

import os
import io
import cv2
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from PIL import Image, ImageTk
import shutil

# =============================
# CONFIGURACIÓN GOOGLE DRIVE
# =============================
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
            # CORRECCIÓN → usamos navegador local
            creds = flow.run_local_server(port=0)

        with open("token.pkl", "wb") as token:
            pickle.dump(creds, token)

    return build("drive", "v3", credentials=creds)


def descargar_archivo(service, nombre_archivo, carpeta_destino="temp"):
    """Descarga un archivo desde Google Drive por nombre"""
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


# =============================
# FUNCIONES PARA MOSTRAR
# =============================
def mostrar_imagen(ruta, label):
    """Muestra una imagen en el recuadro"""
    try:
        img = Image.open(ruta)
        img = img.resize((600, 400), Image.Resampling.LANCZOS)
        imgtk = ImageTk.PhotoImage(img)
        label.imgtk = imgtk
        label.configure(image=imgtk)
    except Exception as e:
        messagebox.showerror("Error mostrando imagen", str(e))

def reproducir_video(ruta, label):
    """Reproduce un video dentro del recuadro y lo elimina después de terminar"""
    cap = cv2.VideoCapture(ruta)

    # Obtener metadatos del video
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duracion = total_frames / fps if fps > 0 else 0
    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    calidad = ancho * alto  # resolución total como "calidad"

    def mostrar_frame():
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = img.resize((600, 400), Image.Resampling.LANCZOS)
            imgtk = ImageTk.PhotoImage(image=img)
            label.imgtk = imgtk
            label.configure(image=imgtk)
            label.after(30, mostrar_frame)
        else:
            cap.release()

            # Mostrar info del video antes de borrar
            print("\n=== Datos del Video ===")
            print(f"⏱ Tiempo de reproducción: {duracion:.2f} segundos")
            print(f"🎞 FPS: {fps:.2f}")
            print(f"📐 Dimensiones: {ancho} x {alto}")
            print(f"📊 Calidad (resolución total): {calidad} píxeles\n")

            # Esperar 2 segundos antes de borrar
            label.after(2000, lambda: borrar_archivo(ruta))

    mostrar_frame()


def borrar_archivo(ruta):
    """Elimina un archivo específico si existe"""
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
            print(f"Archivo eliminado: {ruta}")
    except Exception as e:
        print(f"Error borrando archivo {ruta}: {e}")


# =============================
# INTERFAZ PRINCIPAL
# =============================
app = ctk.CTk()
app.title("Visor desde Google Drive")
app.geometry("900x600")

# Fondo
ruta_fondo = os.path.abspath(os.path.join(os.path.dirname(__file__), "../images/fondo2.png"))
try:
    fondo_img = Image.open(ruta_fondo)
    fondo_img = fondo_img.resize((900, 600), Image.Resampling.LANCZOS)
    fondo_ctk = ImageTk.PhotoImage(fondo_img)

    fondo_label = tk.Label(app, image=fondo_ctk)
    fondo_label.place(x=0, y=0, relwidth=1, relheight=1)
except Exception as e:
    print("Error cargando imagen de fondo:", e)

# Recuadro para imagen/video
recuadro = ctk.CTkFrame(app, width=600, height=400, corner_radius=15, fg_color="black")
recuadro.place(x=150, y=100)

contenido_label = ctk.CTkLabel(recuadro, text="")
contenido_label.pack(expand=True)

# =============================
# LIMPIEZA AUTOMÁTICA
# =============================
def limpiar_temp():
    """Elimina carpeta temp al cerrar app"""
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    app.destroy()

app.protocol("WM_DELETE_WINDOW", limpiar_temp)

# =============================
# FLUJO PRINCIPAL
# =============================
if __name__ == "__main__":
    try:
        service = autenticar_drive()
        nombre_archivo = input("Nombre exacto de la imagen o video en Drive: ")
        ruta_descargada = descargar_archivo(service, nombre_archivo)

        # Detectar si es imagen o video
        extension = os.path.splitext(ruta_descargada)[1].lower()
        if extension in [".png", ".jpg", ".jpeg"]:
            mostrar_imagen(ruta_descargada, contenido_label)
        elif extension in [".mp4", ".avi", ".mov"]:
            reproducir_video(ruta_descargada, contenido_label)
        else:
            messagebox.showwarning("Formato no soportado", f"El archivo {extension} no es compatible")

    except Exception as e:
        messagebox.showerror("Error", str(e))

    app.mainloop()
