import customtkinter as ctk
from tkinter import Label
from PIL import Image, ImageTk
from pathlib import Path

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Ventana de Bienvenida")

# ---- Calcular rutas absolutas ----
base_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
image_path = base_dir.parent / "images" / "fondo.png"

try:
    bg_image_original = Image.open(image_path)
except Exception as e:
    print(f"Error cargando imagen de fondo: {e}")
    bg_image_original = None

# ---- Barra superior azul ----
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
barra_alto = int(screen_height * 0.1)
root.geometry(f"{screen_width}x{screen_height}")
root.resizable(True, True)

barra_superior = ctk.CTkFrame(root, fg_color="#1881d7", height=barra_alto, corner_radius=0)
barra_superior.pack(fill='x')

# ---- Fondo (Label) ----
fondo_label = Label(root)
fondo_label.place(x=0, y=barra_alto)
bg_photo = [None]  # Para mantener la referencia

# ---- Recuadro de video ----
video_width = int(screen_width * 0.3)
video_height = int(screen_height * 0.7)
video_x = int(screen_width * 0.15)
video_y = int(screen_height * 0.15)
recuadro_video = ctk.CTkFrame(
    root,
    width=video_width,
    height=video_height,
    corner_radius=30,
    border_width=6,
    border_color="#F3D05C",
    fg_color="white"
)
recuadro_video.place(x=video_x, y=video_y)

# ---- Texto principal ----
texto_width = int(screen_width * 0.35)
texto_x = int(screen_width * 0.60)
texto_y = video_y

def escalar_fuente(tamaño_base):
    ancho = texto_width
    size = max(tamaño_base, int(ancho * 0.07))
    return ("Segoe UI", size, "bold")

titulo = ctk.CTkLabel(root, text="¡HOLA, BIENVENIDO!",
    font=escalar_fuente(28),
    wraplength=texto_width - 20,
    anchor="center", justify="center",
    text_color="black", bg_color="transparent")
titulo.place(x=texto_x, y=texto_y)

hola = ctk.CTkLabel(root, text="SOMOS UN SISTEMA DE APOYO PARA PERSONAS SORDAS",
    font=escalar_fuente(24),
    wraplength=texto_width - 20,
    anchor="center", justify="center",
    text_color="black", bg_color="transparent")
hola.place(x=texto_x, y=texto_y + 100)

bienvenida = ctk.CTkLabel(root, text="POR FAVOR, COLOCATE EN EL ÁREA DESIGNADA",
    font=escalar_fuente(24),
    wraplength=texto_width - 20,
    anchor="center", justify="center",
    text_color="black", bg_color="transparent")
bienvenida.place(x=texto_x, y=texto_y + 200)

# ---- Handler para resize: actualiza fondo y mantiene referencias ----
def actualizar_todo(event=None):
    w = root.winfo_width()
    h = root.winfo_height()
    barra = int(h * 0.1)
    fondo_alto = h - barra
    if bg_image_original:
        bg_img = bg_image_original.resize((w, fondo_alto))
        bg_photo[0] = ImageTk.PhotoImage(bg_img)
        fondo_label.configure(image=bg_photo[0])
        fondo_label.image = bg_photo[0]
        fondo_label.place(x=0, y=barra, width=w, height=fondo_alto)
        fondo_label.lower()
    # (Opcional) Puedes recalcular los lugares de los otros widgets aquí para mayor responsividad

root.bind("<Configure>", actualizar_todo)

# ---- Asegura que los widgets estén en el orden superior ----
recuadro_video.lift()
titulo.lift()
hola.lift()
bienvenida.lift()

root.mainloop()
