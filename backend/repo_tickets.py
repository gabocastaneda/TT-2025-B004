from typing import Dict, Any, List, Optional
from .db import get_conn

def fetch_ticket_bundle(num_ticket: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT t.NumTicket, t.FechaCompra, c.idCliente, c.RFCCliente,
                   c.Direccion, c.TelefonoCliente, c.CorreoCliente
            FROM ticket t
            JOIN cliente c ON c.idCliente = t.idCliente
            WHERE t.NumTicket = %s
        """, (num_ticket,))
        ticket = cur.fetchone()
        if not ticket:
            return None

        cur.execute("""
            SELECT td.idTicketDetalle, td.NumTicket, td.idProducto,
                   td.Cantidad, td.PrecioVenta,
                   p.NombreProducto, p.PrecioProducto, p.Descripcion, p.CodigoArea
            FROM ticket_detalle td
            JOIN producto p ON p.idProducto = td.idProducto
            WHERE td.NumTicket = %s
            ORDER BY td.idTicketDetalle
        """, (num_ticket,))
        detalles = cur.fetchall()

        return {
            "ticket": ticket,
            "cliente": {
                "idCliente": ticket["idCliente"],
                "RFCCliente": ticket["RFCCliente"],
                "Direccion": ticket["Direccion"],
                "TelefonoCliente": ticket["TelefonoCliente"],
                "CorreoCliente": ticket["CorreoCliente"],
            },
            "detalles": detalles,
        }

def render_ticket_text(bundle: Dict[str, Any]) -> str:
    t = bundle["ticket"]
    c = bundle["cliente"]
    dets: List[Dict[str, Any]] = bundle["detalles"]

    lines = []
    lines.append("============ TICKET ENCONTRADO ============")
    lines.append(f"NumTicket: {t['NumTicket']}  |  FechaCompra: {t['FechaCompra']}")
    lines.append("------------ CLIENTE ----------------------")
    lines.append(f"ID: {c['idCliente']}  RFC: {c['RFCCliente']}")
    lines.append(f"Tel: {c['TelefonoCliente']}  Correo: {c['CorreoCliente']}")
    lines.append(f"Dirección: {c['Direccion']}")
    lines.append("------------ PRODUCTOS --------------------")
    if not dets:
        lines.append("(Sin renglones en ticket_detalle)")
    else:
        for d in dets:
            lines.append(
                f"#{d['idTicketDetalle']}  idProducto={d['idProducto']}  "
                f"Nombre={d['NombreProducto']}  Cant={d['Cantidad']}  "
                f"P.Unit={d['PrecioProducto']}  P.Venta={d['PrecioVenta']}"
            )
    lines.append("===========================================")
    return "\n".join(lines)
