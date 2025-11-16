# -*- coding: utf-8 -*-
# public/views/config/drive_config.py

# API Key (la que me diste)
API_KEY = "AIzaSyCPQezDLouT6Lwc0JHG6QpxWPrukz_2Jac"

def drive_api_url(file_id: str) -> str:
    """Arma la URL de descarga directa (Google Drive v3)."""
    return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={API_KEY}"
