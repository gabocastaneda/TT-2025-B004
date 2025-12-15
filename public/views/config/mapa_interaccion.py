# -*- coding: utf-8 -*-
# public/views/config/mapa_interaccion.py
from pathlib import Path
from .drive_config import drive_api_url

# IDs de tus videos en Drive (RESP1..RESP12)
FILE_IDS = {
    "resp1":  "17X-Es7X3L-663uEQRbncz3qOE3LjyKN4",
    "resp2":  "1zS7X51P84002qWdUlziuoS-0o2S0NtSs",
    "resp3":  "1tbtKvYQm0gGGCz-6kXnTJrrx4MHrImIu",
    "resp4":  "1YF9FlUbpVD3OWSRZ7MWY4i09kfec-KK1",
    "resp5":  "1QjLTdPivuMmcHYwddtDCCh0XaAu--N3U",
    "resp6":  "1IeRdyiffSu9n1VXjub-R1YBVmqjWq3pk",
    "resp7":  "12-uNCBj0enj1chd_ayOWyz_Ho9vWbD5l",
    "resp8":  "14V5BmifEOJ4wd2a-NjQ3Lsfhqc7cu0ic",
    "resp9":  "1uw19ZIb05_8hs6Z3NQgL8JY6Jmuzes94",
    "resp10": "1o3LMAkzNx9GSvTctDls6k_ptMhoHX72y",
    "resp11": "1ijbGb-A-nZoRwEprfMETI6K8snJiVydo",
    "resp12": "1aY0h292hYyOd4CbC89QSv1Ghy6tv0Diz",
    "resp13": "1175ePF_6B-MZILdVn8tpKtfRnrnZGnF1",
    "resp14": "16l2j8zy7hNlZuiBRFLRGzLggcnRiz4YY",
    "resp15": "1olB-zl4NGs_9GVJMLCauFR9oEXjX9gwd",
    "resp16": "1wZxqy4sKTZlIUwxZA1XE2uYgFbsZmooF",
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
