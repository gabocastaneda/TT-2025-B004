import customtkinter as ctk
from tkinter import Label
from PIL import Image, ImageTk
from pathlib import Path

# Configuración visual
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Crear ventana principal
root = ctk.CTk()
root.title("Ventana de Respuesta Única")

# Ruta de imagen de fondo
base_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
image_path = base_dir.parent / 'images' / 'fondo.png'

# Cargar imagen de fondo original
try:
    imagen_fondo_original = Image.open(image_path)
except Exception as e:
    print(f"Error cargando imagen de fondo: {e}")
    imagen_fondo_original = None

# Barra superior azul
barra_superior = ctk.CTkFrame(root, fg_color="#1881d7", corner_radius=0)
barra_superior.pack(fill='x')

# Fondo visual
fondo_label = Label(root)
fondo_label.place(x=0, y=0)

# Recuadro de video
recuadro_video = ctk.CTkFrame(
    root,
    corner_radius=30,
    border_width=6,
    border_color="#F3D05C",
    fg_color="white"
)

# Redimensionamiento dinámico
def redimensionar(event=None):
    w = root.winfo_width()
    h = root.winfo_height()

    if w < 100 or h < 100:
        return

    barra_alto = int(h * 0.07)
    barra_superior.configure(height=barra_alto)
    barra_superior.pack(fill='x')

    fondo_alto = h - barra_alto

    # Actualizar fondo
    if imagen_fondo_original:
        imagen_redim = imagen_fondo_original.resize((w, fondo_alto))
        bg_photo = ImageTk.PhotoImage(imagen_redim)
        fondo_label.configure(image=bg_photo)
        fondo_label.image = bg_photo
        fondo_label.place(x=0, y=barra_alto, width=w, height=fondo_alto)
        fondo_label.lower()

    # Márgenes
    margen_x = int(w * 0.10)  # 10% margen horizontal
    margen_y = int(fondo_alto * 0.05)  # 5% margen vertical

    ancho_recuadro = int(w * 0.80)  # Solo 80% del ancho
    alto_recuadro = int(ancho_recuadro * 3 / 4)  # Relación 4:3

    # Ajustar si alto excede espacio disponible
    if alto_recuadro > (fondo_alto - 2 * margen_y):
        alto_recuadro = fondo_alto - 2 * margen_y
        ancho_recuadro = int(alto_recuadro * 4 / 3)

    x = (w - ancho_recuadro) // 2
    y = barra_alto + ((fondo_alto - alto_recuadro) // 2)

    recuadro_video.configure(width=ancho_recuadro, height=alto_recuadro)
    recuadro_video.place(x=x, y=y)

# Vincular evento
root.bind("<Configure>", redimensionar)

# Tamaño inicial
root.geometry("1280x720")
root.resizable(True, True)

root.mainloop()
