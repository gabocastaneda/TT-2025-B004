import customtkinter as ctk
from tkinter import Label
from PIL import Image, ImageTk
from pathlib import Path
import cv2

# Inicializar customtkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Configuración ventana principal
root = ctk.CTk()
root.title("Ventana de Interacción")

# Detectar resolución pantalla
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Altura barra superior (10% alto pantalla)
barra_alto = int(screen_height * 0.1)
fondo_alto = screen_height - barra_alto

# Configurar ventana tamaño pantalla
root.geometry(f"{screen_width}x{screen_height}")
root.resizable(True, True)

# Barra superior azul
barra_superior = ctk.CTkFrame(root, fg_color="#1881d7", height=barra_alto, corner_radius=0)
barra_superior.pack(fill='x')

# Ruta imagen fondo
base_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
image_path = base_dir.parent / 'images' / 'fondo.png'

# Imagen fondo escalada
try:
    bg_image = Image.open(image_path).resize((screen_width, fondo_alto))
    bg_photo = ImageTk.PhotoImage(bg_image)
    fondo_label = Label(root, image=bg_photo)
    fondo_label.place(x=0, y=barra_alto, width=screen_width, height=fondo_alto)
    fondo_label.lower()
except Exception as e:
    print(f"Error cargando imagen de fondo: {e}")

# Definir márgenes y tamaños
margen_izq = int(screen_width * 0.05)       # 5% margen izquierdo
margen_der = int(screen_width * 0.05)       # 5% margen derecho
separacion = int(screen_width * 0.05)       # 5% espacio entre recuadros

area_util_ancho = screen_width - margen_izq - margen_der  # 90% ancho total

# Cada recuadro ocupa la mitad del área útil menos la separación
video_width = (area_util_ancho - separacion) // 2
video_height = int(screen_height * 0.7)
video_y = int(screen_height * 0.15)

video1_x = margen_izq
video2_x = margen_izq + video_width + separacion

# Crear recuadro cámara (izquierda)
recuadro_video1 = ctk.CTkFrame(
    root,
    width=video_width,
    height=video_height,
    corner_radius=30,
    border_width=6,
    border_color="#F3D05C",
    fg_color="white"
)
recuadro_video1.place(x=video1_x, y=video_y)

video_label = Label(recuadro_video1, bg="white")
video_label.pack(expand=True, fill="both")

# Crear recuadro video (derecha)
recuadro_video2 = ctk.CTkFrame(
    root,
    width=video_width,
    height=video_height,
    corner_radius=30,
    border_width=6,
    border_color="#F3D05C",
    fg_color="white"
)
recuadro_video2.place(x=video2_x, y=video_y)

# Levantar recuadros sobre fondo
recuadro_video1.lift()
recuadro_video2.lift()

# Captura cámara
cap = cv2.VideoCapture(0)

def mostrar_frame():
    ret, frame = cap.read()
    if ret:
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (video_width, video_height))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imagen = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(imagen)
        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)
    root.after(10, mostrar_frame)

mostrar_frame()

def cerrar():
    cap.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", cerrar)
root.mainloop()
