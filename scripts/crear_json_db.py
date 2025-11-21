import json
from pathlib import Path

# Estructura de datos convertida desde tu SQL
def crear_json_database():
    """Crea los archivos JSON desde la base de datos SQL"""
    
    # 1. Turnos
    turnos = {
        "1": {"idTurno": 1, "NombreTurno": "Matutino"},
        "2": {"idTurno": 2, "NombreTurno": "Vespertino"},
        "3": {"idTurno": 3, "NombreTurno": "Nocturno"}
    }
    
    # 2. Encargados
    encargados = {
        "LORM750404DD4": {
            "RFCEncargado": "LORM750404DD4",
            "NombreEncargado": "Maria",
            "ApPaterno": "Lopez",
            "ApMaterno": "Ramirez",
            "Telefono": "5511223344",
            "Correo": "maria.lopez@tienda.com",
            "idTurno": 1
        },
        "ROGE800505EE5": {
            "RFCEncargado": "ROGE800505EE5",
            "NombreEncargado": "Carlos",
            "ApPaterno": "Gonzalez",
            "ApMaterno": "Romero",
            "Telefono": "5522334455",
            "Correo": "carlos.gonzalez@tienda.com",
            "idTurno": 2
        },
        "SAVA880115FF6": {
            "RFCEncargado": "SAVA880115FF6",
            "NombreEncargado": "Ana",
            "ApPaterno": "Solis",
            "ApMaterno": "Vargas",
            "Telefono": "5533445566",
            "Correo": "ana.solis@tienda.com",
            "idTurno": 1
        },
        "HERL920320GG7": {
            "RFCEncargado": "HERL920320GG7",
            "NombreEncargado": "Luis",
            "ApPaterno": "Hernandez",
            "ApMaterno": "Lopez",
            "Telefono": "5544556677",
            "Correo": "luis.hernandez@tienda.com",
            "idTurno": 2
        },
        "MART850625HH8": {
            "RFCEncargado": "MART850625HH8",
            "NombreEncargado": "Teresa",
            "ApPaterno": "Martinez",
            "ApMaterno": "Garcia",
            "Telefono": "5555667788",
            "Correo": "teresa.martinez@tienda.com",
            "idTurno": 3
        }
    }
    
    # 3. Áreas
    areas = {
        "10": {
            "CodigoArea": 10,
            "NombreArea": "Electrónica",
            "RFCEncargado": "LORM750404DD4"
        },
        "20": {
            "CodigoArea": 20,
            "NombreArea": "Ropa y Accesorios",
            "RFCEncargado": "ROGE800505EE5"
        },
        "30": {
            "CodigoArea": 30,
            "NombreArea": "Hogar y Jardín",
            "RFCEncargado": "SAVA880115FF6"
        },
        "40": {
            "CodigoArea": 40,
            "NombreArea": "Juguetería",
            "RFCEncargado": "HERL920320GG7"
        },
        "50": {
            "CodigoArea": 50,
            "NombreArea": "Deportes",
            "RFCEncargado": "MART850625HH8"
        }
    }
    
    # 4. Descuentos
    descuentos = {
        "1": {
            "idDescuento": 1,
            "Valor": 15.00,
            "Tipo": "Porcentaje",
            "FechaInicio": "2025-10-01",
            "FechaFin": "2025-10-31",
            "Estado": "Activo"
        },
        "2": {
            "idDescuento": 2,
            "Valor": 50.00,
            "Tipo": "MontoFijo",
            "FechaInicio": "2025-10-15",
            "FechaFin": "2025-10-25",
            "Estado": "Activo"
        },
        "3": {
            "idDescuento": 3,
            "Valor": 10.00,
            "Tipo": "Porcentaje",
            "FechaInicio": "2025-09-01",
            "FechaFin": "2025-09-30",
            "Estado": "Inactivo"
        }
    }
    
    # 5. Productos (CON CAMPO DE IMAGEN)
    productos = {
        "101": {
            "idProducto": 101,
            "NombreProducto": "Televisión LED 50\"",
            "PrecioProducto": 8500.00,
            "Descripcion": "Smart TV 4K UHD",
            "Disponibilidad": True,
            "CodigoArea": 10,
            "idDescuento": 2,
            "ImagenURL": "productos/tv_led_50.jpg"
        },
        "102": {
            "idProducto": 102,
            "NombreProducto": "Laptop Gamer",
            "PrecioProducto": 22000.00,
            "Descripcion": "Laptop con tarjeta gráfica dedicada",
            "Disponibilidad": True,
            "CodigoArea": 10,
            "idDescuento": None,
            "ImagenURL": "productos/laptop_gamer.jpg"
        },
        "103": {
            "idProducto": 103,
            "NombreProducto": "Audífonos Bluetooth",
            "PrecioProducto": 1800.00,
            "Descripcion": "Cancelación de ruido activa, 20hrs de batería",
            "Disponibilidad": True,
            "CodigoArea": 10,
            "idDescuento": 1,
            "ImagenURL": "productos/audifonos_bt.jpg"
        },
        "104": {
            "idProducto": 104,
            "NombreProducto": "Mouse Inalámbrico",
            "PrecioProducto": 450.00,
            "Descripcion": "Mouse ergonómico recargable",
            "Disponibilidad": True,
            "CodigoArea": 10,
            "idDescuento": None,
            "ImagenURL": "productos/mouse_wireless.jpg"
        },
        "105": {
            "idProducto": 105,
            "NombreProducto": "Teclado Mecánico RGB",
            "PrecioProducto": 2100.00,
            "Descripcion": "Switch azul, layout en español",
            "Disponibilidad": True,
            "CodigoArea": 10,
            "idDescuento": 2,
            "ImagenURL": "productos/teclado_rgb.jpg"
        },
        "201": {
            "idProducto": 201,
            "NombreProducto": "Camisa de Lino",
            "PrecioProducto": 750.00,
            "Descripcion": "Camisa casual manga larga",
            "Disponibilidad": True,
            "CodigoArea": 20,
            "idDescuento": 1,
            "ImagenURL": "productos/camisa_lino.jpg"
        },
        "202": {
            "idProducto": 202,
            "NombreProducto": "Zapatos de Piel",
            "PrecioProducto": 1200.00,
            "Descripcion": "Zapatos formales color negro",
            "Disponibilidad": True,
            "CodigoArea": 20,
            "idDescuento": 1,
            "ImagenURL": "productos/zapatos_piel.jpg"
        },
        "203": {
            "idProducto": 203,
            "NombreProducto": "Jeans de Mezclilla",
            "PrecioProducto": 899.00,
            "Descripcion": "Corte recto, color azul oscuro",
            "Disponibilidad": True,
            "CodigoArea": 20,
            "idDescuento": None,
            "ImagenURL": "productos/jeans.jpg"
        },
        "204": {
            "idProducto": 204,
            "NombreProducto": "Cinturón de Piel",
            "PrecioProducto": 500.00,
            "Descripcion": "Hebilla de acero inoxidable",
            "Disponibilidad": True,
            "CodigoArea": 20,
            "idDescuento": 1,
            "ImagenURL": "productos/cinturon.jpg"
        },
        "301": {
            "idProducto": 301,
            "NombreProducto": "Cafetera de Goteo",
            "PrecioProducto": 950.00,
            "Descripcion": "Capacidad 12 tazas, programable",
            "Disponibilidad": True,
            "CodigoArea": 30,
            "idDescuento": 2,
            "ImagenURL": "productos/cafetera.jpg"
        },
        "302": {
            "idProducto": 302,
            "NombreProducto": "Juego de Sábanas Queen",
            "PrecioProducto": 1100.00,
            "Descripcion": "Algodón 400 hilos, color blanco",
            "Disponibilidad": True,
            "CodigoArea": 30,
            "idDescuento": None,
            "ImagenURL": "productos/sabanas_queen.jpg"
        },
        "303": {
            "idProducto": 303,
            "NombreProducto": "Podadora Eléctrica",
            "PrecioProducto": 3200.00,
            "Descripcion": "1500W, bolsa recolectora",
            "Disponibilidad": True,
            "CodigoArea": 30,
            "idDescuento": None,
            "ImagenURL": "productos/podadora.jpg"
        },
        "401": {
            "idProducto": 401,
            "NombreProducto": "Bloques de Construcción (Set Grande)",
            "PrecioProducto": 1500.00,
            "Descripcion": "+500 piezas, edad 5+",
            "Disponibilidad": True,
            "CodigoArea": 40,
            "idDescuento": 1,
            "ImagenURL": "productos/bloques.jpg"
        },
        "402": {
            "idProducto": 402,
            "NombreProducto": "Muñeca Articulada",
            "PrecioProducto": 600.00,
            "Descripcion": "Incluye 3 cambios de ropa",
            "Disponibilidad": True,
            "CodigoArea": 40,
            "idDescuento": None,
            "ImagenURL": "productos/muneca.jpg"
        },
        "403": {
            "idProducto": 403,
            "NombreProducto": "Auto a Control Remoto",
            "PrecioProducto": 750.00,
            "Descripcion": "Batería recargable, escala 1:16",
            "Disponibilidad": False,
            "CodigoArea": 40,
            "idDescuento": None,
            "ImagenURL": "productos/auto_rc.jpg"
        },
        "501": {
            "idProducto": 501,
            "NombreProducto": "Balón de Fútbol No. 5",
            "PrecioProducto": 680.00,
            "Descripcion": "Balón oficial de liga, piel sintética",
            "Disponibilidad": True,
            "CodigoArea": 50,
            "idDescuento": None,
            "ImagenURL": "productos/balon_futbol.jpg"
        },
        "502": {
            "idProducto": 502,
            "NombreProducto": "Tapete de Yoga",
            "PrecioProducto": 490.00,
            "Descripcion": "6mm de grosor, antiderrapante",
            "Disponibilidad": True,
            "CodigoArea": 50,
            "idDescuento": 1,
            "ImagenURL": "productos/tapete_yoga.jpg"
        },
        "503": {
            "idProducto": 503,
            "NombreProducto": "Pesas (Set de 2)",
            "PrecioProducto": 1300.00,
            "Descripcion": "Mancuernas ajustables de 20kg (10kg c/u)",
            "Disponibilidad": True,
            "CodigoArea": 50,
            "idDescuento": 2,
            "ImagenURL": "productos/pesas_set.jpg"
        }
    }
    
    # 6. Clientes
    clientes = {
        "1": {
            "idCliente": 1,
            "RFCCliente": "GOPJ850101AA1",
            "Direccion": "Calle Falsa 123, Col Centro",
            "TelefonoCliente": "5512345678",
            "CorreoCliente": "juan.perez@email.com"
        },
        "2": {
            "idCliente": 2,
            "RFCCliente": "GAML880202BB2",
            "Direccion": "Av. Siempre Viva 742",
            "TelefonoCliente": "5587654321",
            "CorreoCliente": "ana.garcia@email.com"
        },
        "3": {
            "idCliente": 3,
            "RFCCliente": "SARM900303CC3",
            "Direccion": "Blvd. de los Sueños 45",
            "TelefonoCliente": "5555555555",
            "CorreoCliente": "miguel.sanchez@email.com"
        }
    }
    
    # 7. Tickets
    tickets = {
        "1001": {
            "NumTicket": 1001,
            "FechaCompra": "2025-10-20 13:45:10",
            "idCliente": 1
        },
        "1002": {
            "NumTicket": 1002,
            "FechaCompra": "2025-10-20 15:10:25",
            "idCliente": 2
        }
    }
    
    # 8. Ticket Detalle
    ticket_detalle = {
        "1": {
            "idTicketDetalle": 1,
            "NumTicket": 1001,
            "idProducto": 101,
            "Cantidad": 1,
            "PrecioVenta": 8450.00
        },
        "2": {
            "idTicketDetalle": 2,
            "NumTicket": 1001,
            "idProducto": 201,
            "Cantidad": 2,
            "PrecioVenta": 637.50
        },
        "3": {
            "idTicketDetalle": 3,
            "NumTicket": 1002,
            "idProducto": 102,
            "Cantidad": 1,
            "PrecioVenta": 22000.00
        },
        "4": {
            "idTicketDetalle": 4,
            "NumTicket": 1002,
            "idProducto": 201,
            "Cantidad": 1,
            "PrecioVenta": 637.50
        },
        "5": {
            "idTicketDetalle": 5,
            "NumTicket": 1002,
            "idProducto": 202,
            "Cantidad": 1,
            "PrecioVenta": 1020.00
        }
    }
    
    # 9. Casos de seguimiento
    num_seguimiento = {
        "1": {
            "idCaso": 1,
            "idCliente": 1,
            "TipoCaso": "DUD",
            "FechaCreacion": "2025-10-18 14:30:00"
        },
        "2": {
            "idCaso": 2,
            "idCliente": 2,
            "TipoCaso": "DEV",
            "FechaCreacion": "2025-10-19 10:15:00"
        },
        "3": {
            "idCaso": 3,
            "idCliente": 1,
            "TipoCaso": "ACL",
            "FechaCreacion": "2025-10-20 11:00:00"
        }
    }
    
    # Crear directorio en public/data
    # Asume que el script está en /scripts y necesita crear /public/data
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    data_dir = project_root / "public" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Creando archivos JSON en: {data_dir}\n")
    
    # Guardar cada archivo
    archivos = {
        "turnos.json": turnos,
        "encargados.json": encargados,
        "areas.json": areas,
        "descuentos.json": descuentos,
        "productos.json": productos,
        "clientes.json": clientes,
        "tickets.json": tickets,
        "ticket_detalle.json": ticket_detalle,
        "num_seguimiento.json": num_seguimiento
    }
    
    for nombre, datos in archivos.items():
        with open(data_dir / nombre, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        print(f"✅ Creado: {nombre}")
    
    print("\n🎉 ¡Todos los archivos JSON creados exitosamente!")

if __name__ == "__main__":
    crear_json_database()