import customtkinter as ctk
from tkinter import Label, font as tkfont
from PIL import Image, ImageTk
from pathlib import Path

# Inicializar customtkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Configuración de ventana principal
root = ctk.CTk()
root.title("Ventana de Bienvenida")

# Detectar resolución de pantalla
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Altura de la barra superior
barra_alto = int(screen_height * 0.1)
fondo_alto = screen_height - barra_alto

# Configurar ventana al tamaño de la pantalla
root.geometry(f"{screen_width}x{screen_height}")
root.resizable(True, True)

# Barra superior azul
barra_superior = ctk.CTkFrame(root, fg_color="#1881d7", height=barra_alto, corner_radius=0)
barra_superior.pack(fill='x')

# Ruta de imagen de fondo
base_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
image_path = base_dir.parent / 'images' / 'fondo.png'

# Ruta absoluta de fuente proporcionada
font_path = base_dir.parent / "public" / "styles" / "Bevan.ttf"

# Cargar imagen de fondo
try:
    bg_image = Image.open(image_path).resize((screen_width, fondo_alto))
    bg_photo = ImageTk.PhotoImage(bg_image)
    fondo_label = Label(root, image=bg_photo)
    fondo_label.place(x=0, y=barra_alto, width=screen_width, height=fondo_alto)
    fondo_label.lower()
except Exception as e:
    print(f"Error cargando imagen de fondo: {e}")

# Recuadro de video
video_width = int(screen_width * 0.5)
video_height = int(screen_height * 0.7)
video_x = int(screen_width * 0.05)
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

# Coordenadas del texto
texto_width = int(screen_width * 0.35)
texto_x = int(screen_width * 0.60)
texto_y = video_y

# Función para escalar fuente
def escalar_fuente(tamaño_base):
    ancho = texto_width
    size = max(tamaño_base, int(ancho * 0.07))  # aumenta escala de fuente
    try:
        return tkfont.Font(file=font_path, size=size)
    except Exception as e:
        print("Error cargando fuente Bevan, se usará fuente por defecto.")
        return ("Segoe UI", size, "bold")

# Etiquetas con fuente grande, sin fondo
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

# Actualizar fuentes dinámicamente si cambia tamaño ventana
def actualizar_fuentes(event=None):
    titulo.configure(font=escalar_fuente(28))
    hola.configure(font=escalar_fuente(24))
    bienvenida.configure(font=escalar_fuente(24))

root.bind("<Configure>", actualizar_fuentes)

# Asegurar que estén visibles
recuadro_video.lift()
titulo.lift()
hola.lift()
bienvenida.lift()

# Iniciar
root.mainloop()