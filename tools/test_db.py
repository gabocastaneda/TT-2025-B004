# tools/test_db.py
from pathlib import Path
import sys

# Asegura que el raíz del repo esté en sys.path (dos niveles arriba de este archivo)
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.repo_tickets import fetch_ticket_bundle, render_ticket_text

if __name__ == "__main__":
    # Elige un ticket que sí exista (tu dump mostró 1001 y 1002)
    num = 1001
    bundle = fetch_ticket_bundle(num)
    if not bundle:
        print(f"No existe el ticket {num}")
    else:
        print(render_ticket_text(bundle))
