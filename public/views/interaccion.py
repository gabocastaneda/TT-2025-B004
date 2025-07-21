import tkinter as tk
from tkinter import Label, Frame
from PIL import Image, ImageTk
from pathlib import Path
import cv2

# Configuración de ventana principal
root = tk.Tk()
root.title("Ventana de Interacción")
root.geometry("1366x978")
root.resizable(False, False)

# Barra superior azul
barra_superior = Frame(root, bg="#1881d7", height=95)
barra_superior.pack(fill='x')

# Ruta de imagen de fondo
base_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
image_path = base_dir.parent / 'images' / 'fondo.png' 

# Imagen de fondo
try:
    bg_image = Image.open(image_path).resize((1366, 883))  # 978 - 95
    bg_photo = ImageTk.PhotoImage(bg_image)
    fondo_label = Label(root, image=bg_photo)
    fondo_label.place(x=0, y=95, width=1366, height=883)
    fondo_label.lower()
except Exception as e:
    print(f"Error cargando imagen de fondo: {e}")

# Recuadro de video 1 (izquierda) con cámara en vivo
recuadro_video1 = Frame(
    root,
    bg='white',
    highlightbackground="#F3D05C",
    highlightthickness=4,
    width=500,
    height=500
)
recuadro_video1.place(x=70, y=140)

video_label = Label(recuadro_video1)
video_label.pack()

# Recuadro de video 2 (derecha) vacío
recuadro_video2 = Frame(
    root,
    bg='white',
    highlightbackground="#F3D05C",
    highlightthickness=4,
    width=500,
    height=500
)
recuadro_video2.place(x=700, y=140)

# Levantar elementos sobre fondo
recuadro_video1.lift()
recuadro_video2.lift()

# Captura de cámara 
cap = cv2.VideoCapture(0)

def mostrar_frame():
    ret, frame = cap.read()
    if ret:
        frame = cv2.flip(frame, 1)  # Inversión de la camara
        frame = cv2.resize(frame, (500, 500))  
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imagen = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=imagen)
        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)
    root.after(10, mostrar_frame)

mostrar_frame()

# Cierre de cámara al cerrar ventana
def cerrar():
    cap.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", cerrar)
root.mainloop()
