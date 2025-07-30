import customtkinter as ctk
from tkinter import Label
from PIL import Image, ImageTk
import cv2
from pathlib import Path
from tkinter import font as tkfont

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Ventana de Interacción")

base_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
image_path = base_dir.parent / 'images' / 'fondo2.png'
try:
    bg_image_original = Image.open(image_path)
except Exception as e:
    print(f"Error cargando imagen de fondo: {e}")
    bg_image_original = None

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

barra_alto = int(screen_height * 0.1)
fondo_alto = screen_height - barra_alto

root.geometry(f"{screen_width}x{screen_height}")
root.resizable(True, True)

# Barra superior azul
barra_superior = ctk.CTkFrame(root, fg_color="#1881d7", height=barra_alto, corner_radius=0)
barra_superior.pack(fill='x')

fuente_barra = tkfont.Font(family="Arial", size=20, weight="bold", slant="italic")
titulo_label = Label(
    barra_superior,
    text="TT 2025-B004",
    font=fuente_barra,
    bg="#1881d7",
    fg="white"
)
titulo_label.place(relx=0.5, rely=0.5, anchor="center")

fondo_label = Label(root)
fondo_label.place(x=0, y=barra_alto)
bg_photo = [None]

def actualizar_fondo(event=None):
    w = root.winfo_width()
    h = root.winfo_height()
    fondo_h = h - int(h * 0.1)
    barra = int(h * 0.1)
    if bg_image_original:
        bg_img = bg_image_original.resize((w, fondo_h))
        bg_photo[0] = ImageTk.PhotoImage(bg_img)
        fondo_label.configure(image=bg_photo[0])
        fondo_label.image = bg_photo[0]
        fondo_label.place(x=0, y=barra, width=w, height=fondo_h)
        fondo_label.lower()

root.bind("<Configure>", actualizar_fondo)

margen_izq = int(screen_width * 0.05)
margen_der = int(screen_width * 0.05)
separacion = int(screen_width * 0.05)
area_util_ancho = screen_width - margen_izq - margen_der

recuadro_width = (area_util_ancho - separacion) // 2
recuadro_height = int(recuadro_width * 0.75)

video_y = int(screen_height * 0.25)
video_x = (screen_width - recuadro_width) // 2  # Centrado horizontalmente

recuadro_video = ctk.CTkFrame(
    root,
    width=recuadro_width,
    height=recuadro_height,
    corner_radius=10,
    border_width=10,
    border_color="#F3D05C",
    fg_color="white"
)
recuadro_video.place(x=video_x, y=video_y)

video_label = Label(recuadro_video, bg="white")
video_label.place(relx=0.5, rely=0.5, anchor="center",
                  width=recuadro_width - 20, height=recuadro_height - 20)

video_path = "https://www.googleapis.com/drive/v3/files/11E-HHfWT_sZhL6-WxTgEJcfGJQ_X3DyB?alt=media&key=AIzaSyAWW-xLcA9ZMiFZLUyHODYT9KMKTUf7RiU"
cap = cv2.VideoCapture(video_path)

def mostrar_frame():
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  
        ret, frame = cap.read()
    if ret:
        frame = cv2.flip(frame, 1)
        label_w = recuadro_width - 20
        label_h = recuadro_height - 20
        if frame.shape[1] != label_w or frame.shape[0] != label_h:
            frame = cv2.resize(frame, (label_w, label_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imagen = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(imagen)
        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)
    root.after(30, mostrar_frame) 

mostrar_frame()

def cerrar():
    cap.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", cerrar)
root.mainloop()
