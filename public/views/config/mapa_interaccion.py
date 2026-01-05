# -*- coding: utf-8 -*-
# public/views/config/mapa_interaccion.py
from pathlib import Path
from .drive_config import drive_api_url

# IDs de tus videos en Drive (RESP1..RESP12)
FILE_IDS = {
    "resp1":  "11QD05QPhpNpzyMhKGcXzEIP2kNieRU4t",
    "resp2":  "1OEW_8BVgRXL-FhyT_KtYeHFawJYikkzz",
    "resp3":  "1Tiz90eD0XhrH_MJtyKLOmWxdQRTclpaD",
    "resp4":  "1n9Mbunt4o-HiMtB-QOLJIBJN50tkNey-",
    "resp5":  "1caf1xHtq5jWBIb9aNyePsqOQrKFZXZSg",
    "resp6":  "1rCP50HMJZwEYONRD47xuQuWnrLu4CFk2",
    "resp7":  "1V-TbgJdQGPjpZunPJ8woc5umnkW39kMf",
    "resp8":  "1V-TbgJdQGPjpZunPJ8woc5umnkW39kMf",
    "resp9":  "1kqnt5f49_OSPBfcEfhY3dx0CF2H3-Rrl",
    "resp10": "1KPVPoVhiVPg8sf4GcabjLeJ6LpAIX9KZ",
    "resp11": "13PCE-oGQOXwtrbdHJBN0KCfQoaOa90YD",
    "resp12": "1AuIuYEbzhF1o8JuJdK1KsXBdt8sk0ots",
    "resp13": "13Zcz63g-huVsvmuthtjV3alChQWH-1r6",
    "resp14": "1nXXzS_mA-KdYSc5ePEvToBPsbMU3wdPA",
    "resp15": "156ZZJFpx1L30k1qWyhMe1JP7i4ng0zCn",
    "resp16": "124S-T6XkLmybqwldXig7y-LXE8lPN7_V",
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
