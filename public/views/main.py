# public/views/main.py
# -*- coding: utf-8 -*-
# public/views/main.py
import sys
from pathlib import Path

# Asegura que el PADRE de "public" esté en sys.path para que funcione "import public.*"
_THIS = Path(__file__).resolve()
root = None
for p in _THIS.parents:
    if (p / "public").is_dir():
        root = p
        break
if root and str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Importar las clases necesarias para el modelo antes de cualquier otra cosa
try:
    from backend.model_utils import SimpleScaler, SimpleLabelEncoder
    # Hacer que estén disponibles globalmente
    sys.modules['__main__'].SimpleScaler = SimpleScaler
    sys.modules['__main__'].SimpleLabelEncoder = SimpleLabelEncoder
    print("Clases del modelo cargadas correctamente")
except ImportError as e:
    print(f"No se pudieron cargar las clases del modelo: {e}")

from PyQt5.QtWidgets import QApplication
from public.views.gestor_app import GestorAplicacion

if __name__ == "__main__":
    app = QApplication(sys.argv)
    GestorAplicacion(app).run()