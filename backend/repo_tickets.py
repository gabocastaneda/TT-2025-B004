# -*- coding: utf-8 -*-
# backend/repo_tickets.py - Consultas usando JSON en lugar de MySQL

import json
from pathlib import Path
from typing import Optional, Dict, List, Any

# Ruta a los archivos JSON (TT-2025-B004/public/data/)
DATA_DIR = Path(__file__).resolve().parent.parent / "public" / "data"

def _cargar_json(nombre: str) -> Dict:
    """Carga un archivo JSON desde el directorio data/"""
    try:
        ruta = DATA_DIR / nombre
        if not ruta.exists():
            print(f"⚠️  Archivo no encontrado: {ruta}")
            return {}
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error cargando {nombre}: {e}")
        return {}

def fetch_ticket_bundle(num_ticket: int) -> Optional[Dict[str, Any]]:
    """
    Consulta información completa de un ticket desde JSON.
    Retorna un diccionario con toda la info o None si no existe.
    """
    try:
        # Cargar datos
        tickets = _cargar_json("tickets.json")
        clientes = _cargar_json("clientes.json")
        ticket_detalle = _cargar_json("ticket_detalle.json")
        productos = _cargar_json("productos.json")
        descuentos = _cargar_json("descuentos.json")
        
        # Buscar ticket
        ticket_key = str(num_ticket)
        if ticket_key not in tickets:
            print(f"❌ Ticket {num_ticket} no encontrado")
            return None
        
        ticket = tickets[ticket_key]
        
        # Buscar cliente
        cliente_id = str(ticket["idCliente"])
        if cliente_id not in clientes:
            print(f"⚠️  Cliente {cliente_id} no encontrado")
            return None
        
        cliente = clientes[cliente_id]
        
        # Buscar detalles del ticket (productos comprados)
        items: List[Dict] = []
        total = 0.0
        
        for detalle in ticket_detalle.values():
            if detalle["NumTicket"] == num_ticket:
                prod_id = str(detalle["idProducto"])
                
                if prod_id not in productos:
                    print(f"⚠️  Producto {prod_id} no encontrado")
                    continue
                
                producto = productos[prod_id]
                
                # Calcular descuento si aplica
                descuento_info = None
                if producto.get("idDescuento"):
                    desc_id = str(producto["idDescuento"])
                    if desc_id in descuentos:
                        descuento_info = descuentos[desc_id]
                
                # Subtotal del item
                subtotal = detalle["PrecioVenta"] * detalle["Cantidad"]
                total += subtotal
                
                items.append({
                    "idProducto": producto["idProducto"],
                    "NombreProducto": producto["NombreProducto"],
                    "Descripcion": producto.get("Descripcion", ""),
                    "Cantidad": detalle["Cantidad"],
                    "PrecioUnitario": detalle["PrecioVenta"],
                    "Subtotal": subtotal,
                    "ImagenURL": producto.get("ImagenURL", ""),
                    "Descuento": descuento_info
                })
        
        # Construir bundle completo
        bundle = {
            "NumTicket": ticket["NumTicket"],
            "FechaCompra": ticket["FechaCompra"],
            "Cliente": {
                "idCliente": cliente["idCliente"],
                "RFCCliente": cliente["RFCCliente"],
                "Direccion": cliente.get("Direccion", ""),
                "TelefonoCliente": cliente.get("TelefonoCliente", ""),
                "CorreoCliente": cliente.get("CorreoCliente", "")
            },
            "Items": items,
            "Total": round(total, 2)
        }
        
        return bundle
        
    except Exception as e:
        print(f"❌ Error en fetch_ticket_bundle: {e}")
        import traceback
        traceback.print_exc()
        return None

def render_ticket_text(bundle: Dict[str, Any]) -> str:
    """
    Convierte el bundle en texto formateado para mostrar en terminal/overlay.
    """
    if not bundle:
        return "❌ No hay información del ticket"
    
    lines = []
    lines.append("=" * 60)
    lines.append(f"         TICKET #{bundle['NumTicket']}")
    lines.append("=" * 60)
    lines.append(f"Fecha: {bundle['FechaCompra']}")
    lines.append("")
    
    # Info del cliente
    cli = bundle["Cliente"]
    lines.append("CLIENTE:")
    lines.append(f"  RFC: {cli['RFCCliente']}")
    lines.append(f"  Dirección: {cli.get('Direccion', 'N/A')}")
    lines.append(f"  Teléfono: {cli.get('TelefonoCliente', 'N/A')}")
    lines.append(f"  Correo: {cli.get('CorreoCliente', 'N/A')}")
    lines.append("")
    
    # Items
    lines.append("PRODUCTOS COMPRADOS:")
    lines.append("-" * 60)
    
    for idx, item in enumerate(bundle["Items"], 1):
        lines.append(f"{idx}. {item['NombreProducto']} (ID: {item['idProducto']})")
        lines.append(f"   Descripción: {item['Descripcion']}")
        lines.append(f"   Cantidad: {item['Cantidad']} x ${item['PrecioUnitario']:.2f}")
        
        if item.get("Descuento"):
            desc = item["Descuento"]
            lines.append(f"   💰 Descuento aplicado: {desc['Tipo']} - {desc['Valor']}")
        
        if item.get("ImagenURL"):
            lines.append(f"   🖼️  Imagen: {item['ImagenURL']}")
        
        lines.append(f"   Subtotal: ${item['Subtotal']:.2f}")
        lines.append("")
    
    lines.append("-" * 60)
    lines.append(f"TOTAL: ${bundle['Total']:.2f}")
    lines.append("=" * 60)
    
    return "\n".join(lines)

# Función auxiliar para consultar producto por ID
def obtener_producto(id_producto: int) -> Optional[Dict]:
    """Obtiene información de un producto específico"""
    try:
        productos = _cargar_json("productos.json")
        prod_key = str(id_producto)
        
        if prod_key not in productos:
            print(f"❌ Producto {id_producto} no encontrado")
            return None
        
        return productos[prod_key]
    except Exception as e:
        print(f"❌ Error obteniendo producto: {e}")
        return None

# Función auxiliar para listar productos por área
def listar_productos_por_area(codigo_area: int) -> List[Dict]:
    """Lista todos los productos de un área específica"""
    try:
        productos = _cargar_json("productos.json")
        return [p for p in productos.values() if p["CodigoArea"] == codigo_area]
    except Exception as e:
        print(f"❌ Error listando productos: {e}")
        return []