import customtkinter as ctk
from tkinter import Label
from PIL import Image, ImageTk
from pathlib import Path
from tkinter import font as tkfont
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import sys

# ------------------ CONFIG VISUAL ------------------

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Ventana de Respuesta Única")

# Intentar cargar imagen de fondo (si existe)
base_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
image_path = base_dir.parent / 'images' / 'fondo2.png'

try:
    imagen_fondo_original = Image.open(image_path)
    print(f"Imagen cargada")
except Exception as e:
    imagen_fondo_original = None
    print(f"Error cargando imagen de fondo")

# Barra superior azul con texto
barra_superior = ctk.CTkFrame(root, fg_color="#1881d7", corner_radius=0)
barra_superior.pack(fill='x')

fuente_barra = tkfont.Font(family="Arial", size=20, weight="bold", slant="italic")
titulo_label = Label(barra_superior, text="TT 2025-B004", font=fuente_barra, bg="#1881d7", fg="white")
titulo_label.place(relx=0.5, rely=0.5, anchor="center")

fondo_label = Label(root)
fondo_label.place(x=0, y=0)

# Recuadro para la imagen - inicial con tamaño definido en constructor
recuadro_video = ctk.CTkFrame(
    root,
    corner_radius=20,
    border_width=10,
    border_color="#F3D05C",
    fg_color="white",
    width=600,
    height=450
)
recuadro_video.place(x=100, y=100)

# Label para la imagen dentro del recuadro
label_imagen = Label(recuadro_video)
label_imagen.pack(expand=True, fill='both')

def redimensionar(event=None):
    w = root.winfo_width()
    h = root.winfo_height()
    if w < 100 or h < 100:
        return

    barra_alto = int(h * 0.07)
    barra_superior.configure(height=barra_alto)
    barra_superior.pack(fill='x')

    fondo_alto = h - barra_alto

    # Actualizar fondo si existe imagen
    if imagen_fondo_original:
        imagen_redim = imagen_fondo_original.resize((w, fondo_alto))
        bg_photo = ImageTk.PhotoImage(imagen_redim)
        fondo_label.configure(image=bg_photo)
        fondo_label.image = bg_photo
        fondo_label.place(x=0, y=barra_alto, width=w, height=fondo_alto)
        fondo_label.lower()
    else:
        fondo_label.configure(image='')
        fondo_label.image = None

    margen_x = int(w * 0.10)
    margen_y = int(fondo_alto * 0.05)

    ancho_recuadro = int(w * 0.80)
    alto_recuadro = int(ancho_recuadro * 3 / 4)

    if alto_recuadro > (fondo_alto - 2 * margen_y):
        alto_recuadro = fondo_alto - 2 * margen_y
        ancho_recuadro = int(alto_recuadro * 4 / 3)

    x = (w - ancho_recuadro) // 2
    y = barra_alto + ((fondo_alto - alto_recuadro) // 2)

    # Cambiar posición y tamaño con place_configure
    recuadro_video.place_configure(x=x, y=y, width=ancho_recuadro, height=alto_recuadro)

root.bind("<Configure>", redimensionar)

# ------------------ AUTENTICACIÓN GOOGLE DRIVE ------------------

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def autenticar_drive():
    creds = None
    token_path = 'token_drive.pickle'
    creds_path = (base_dir / '../../credentials.json').resolve()

    if not creds_path.exists():
        print(f"Error: No se encontró el archivo '{creds_path}'. Debes colocarlo en la ruta correcta.")
        sys.exit(1)

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    service = build('drive', 'v3', credentials=creds)
    return service

def obtener_id_imagen_por_nombre(nombre_archivo, service):
    try:
        query = f"name = '{nombre_archivo}' and mimeType contains 'image/' and trashed = false"
        results = service.files().list(q=query, spaces='drive', fields="files(id, name)", pageSize=1).execute()
        items = results.get('files', [])
        if items:
            print(f"Archivo '{nombre_archivo}' encontrado en Drive, id: {items[0]['id']}")
            return items[0]['id']
        else:
            print(f"No se encontró el archivo '{nombre_archivo}' en Drive.")
            return None
    except Exception as e:
        print(f"Error buscando archivo en Drive: {e}")
        return None

def mostrar_imagen_en_recuadro(nombre_imagen, service):
    file_id = obtener_id_imagen_por_nombre(nombre_imagen, service)
    if not file_id:
        return

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    print("Iniciando descarga...")
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"Descarga {int(status.progress() * 100)}% completada")

    fh.seek(0)
    tam_bytes = fh.getbuffer().nbytes
    print(f"Archivo descargado, tamaño: {tam_bytes} bytes")

    try:
        img = Image.open(fh)
        recuadro_w = recuadro_video.winfo_width()
        recuadro_h = recuadro_video.winfo_height()

        if recuadro_w < 10 or recuadro_h < 10:
            print("Esperando tamaño del recuadro...")
            root.after(300, lambda: mostrar_imagen_en_recuadro(nombre_imagen, service))
            return

        img = img.resize((recuadro_w, recuadro_h), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)

        label_imagen.configure(image=img_tk)
        label_imagen.image = img_tk
        print("Imagen mostrada correctamente.")
    except Exception as e:
        print(f"Error mostrando imagen: {e}")

# ------------------ EJECUCIÓN ------------------

if __name__ == '__main__':
    service = autenticar_drive()
    nombre_img = input("Nombre exacto de la imagen en Drive: ").strip()
    root.after(500, lambda: mostrar_imagen_en_recuadro(nombre_img, service))
    root.geometry("1280x720")
    root.resizable(True, True)
    root.mainloop()