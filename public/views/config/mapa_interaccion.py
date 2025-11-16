# -*- coding: utf-8 -*-
# public/views/config/mapa_interaccion.py
from pathlib import Path
from .drive_config import drive_api_url

# IDs de tus videos en Drive (RESP1..RESP12)
FILE_IDS = {
    "resp1":  "1WLdcRihoMKNU9STGm_jyxihVDIuu7utF",
    "resp2":  "1mLAVSOfkrCeMb4QyZQVuV1_7Czf1NRSZ",
    "resp3":  "1svMBy5hKXiTV8nj3_m_gyJm_Z7tKEOHR",
    "resp4":  "1PNxmAsO5FwW6DLdLoTkmm238kMnw0cPe",
    "resp5":  "19JfS48rHWuzQ-8L6H2_Yy9ge6iLjWL9T",
    "resp6":  "1hWsA13IQ71s5shAdebWAi6nO1R_hkdVb",
    "resp7":  "1PiTd28XD7EJn6NuU4hJkOlqy7EvGZdjX",
    "resp8":  "1bmCcSOi805pE1pxIeErHuvYjxCgEl9yj",
    "resp9":  "1fqoRTW3aHB5QVERIJ57Zsyg4CPq1rHum",
    "resp10": "1lf1QbBsc7PezfOzL4Lu87SIs7FqttYP8",
    "resp11": "1GfcRMiBg9Ms_NYHm_xgeZgMV7py1MXEO",
    "resp12": "1ph3JeDhbaowhOwlQwgukTrEbmjlQYjua",
}

def _src(name: str, video_dir: Path) -> str:
    """Devuelve ruta local si existe, o URL de Drive API si no."""
    p = Path(video_dir) / f"{name}.mp4"
    return str(p) if p.is_file() else drive_api_url(FILE_IDS[name])

def build_mapa_videos_interaccion(video_dir: Path) -> dict:
    vd = Path(video_dir)
    RESP = {k: _src(k, vd) for k in FILE_IDS.keys()}

    # Comandos -> RESP (en VentanaInteraccion)
    return {
        "resp1": RESP["resp1"], "resp3": RESP["resp3"], "resp5": RESP["resp5"],
        "resp7": RESP["resp7"], "resp9": RESP["resp9"], "resp10": RESP["resp10"],
        "resp11": RESP["resp11"], "resp12": RESP["resp12"],

        # Menú devolución
        "devolucion": RESP["resp11"], "devolución": RESP["resp11"],
        "producto": RESP["resp12"], "ninguno": RESP["resp1"],

        # Ramas
        "dañado": RESP["resp9"], "danado": RESP["resp9"],
        "defecto": RESP["resp9"],
        "equivocacion": RESP["resp9"], "equivocación": RESP["resp9"],

        "si": RESP["resp10"], "sí": RESP["resp10"],
        "no": RESP["resp3"],
    }
