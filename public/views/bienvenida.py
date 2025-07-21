import tkinter as tk
from tkinter import Label, Frame
from PIL import Image, ImageTk
from pathlib import Path

# Configuración de ventana principal
root = tk.Tk()
root.title("Ventana de Bienvenida")
root.geometry("1366x978")
root.resizable(False, False)

# Barra superior azul
barra_superior = Frame(root, bg="#1881d7", height=95)
barra_superior.pack(fill='x')

# Ruta de imagen de fondo ===
base_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
image_path = base_dir.parent / 'images' / 'fondo.png' 

# Imagen de fondo adaptada al tamaño completo de ventana (menos barra superior)
try:
    bg_image = Image.open(image_path).resize((1366, 918))  # 978 - 60
    bg_photo = ImageTk.PhotoImage(bg_image)
    fondo_label = Label(root, image=bg_photo)
    fondo_label.place(x=0, y=60, width=1366, height=918)
    fondo_label.lower()
except Exception as e:
    print(f"Error cargando imagen de fondo: {e}")

# Recuadro de video (temporal)
recuadro_video = Frame(
    root,
    bg='white',
    highlightbackground="#F3D05C",
    highlightthickness=4,
    width=600,
    height=600
)
recuadro_video.place(x=40, y=100)

# Texto lateral
titulo = Label(root, text="TT 2025–B004", font=("Arial", 24, "bold"), anchor="w")
titulo.place(x=750, y=110)

hola = Label(root, text="¡Hola! 😁", font=("Arial", 22, "bold"), anchor="w")
hola.place(x=750, y=150)

bienvenida = Label(root, text="Bienvenido, por\nfavor presiona el", font=("Arial", 22), anchor="w", justify="left")
bienvenida.place(x=750, y=190)

palabra_boton = Label(root, text="botón", font=("Arial", 22, "bold"), anchor="w")
palabra_boton.place(x=750, y=265)

# Asegura que todo esté al frente del fondo
titulo.lift()
hola.lift()
bienvenida.lift()
palabra_boton.lift()
recuadro_video.lift()

root.mainloop()
