"""
Emisión de comprobantes electrónicos (factura/boleta) vía NubeFacT,
Operador de Servicios Electrónicos (OSE) autorizado por SUNAT.

IMPORTANTE: en Railway, define las variables de entorno NUBEFACT_RUTA
y NUBEFACT_TOKEN — las sacas de tu cuenta de NubeFacT, en "Api
(Integración)". Mientras se prueba todo, usa los valores del ambiente
DEMO; cuando funcione bien, se reemplazan por los de producción (son
distintos, hay que activar la cuenta con la SUNAT primero).

NOTA para la primera prueba real: el formato exacto que espera
NubeFacT puede variar según su versión de API — el código de aquí
sigue su esquema estándar documentado, pero la primera vez que se
pruebe contra el DEMO real hay que revisar la respuesta y ajustar
nombres de campo si algo no calza exactamente. No hay forma de
comprobar esto sin hacer una llamada real primero.
"""
import os
from datetime import datetime

import requests

from app import models

NUBEFACT_RUTA = os.environ.get("NUBEFACT_RUTA", "")
NUBEFACT_TOKEN = os.environ.get("NUBEFACT_TOKEN", "")

TIPO_COMPROBANTE_CODIGO = {"factura": 1, "boleta": 2}
TIPO_DOCUMENTO_CODIGO = {"DNI": 1, "RUC": 6}
PORCENTAJE_IGV = 18.00


def siguiente_correlativo(db, negocio_id: int, tipo: str) -> tuple[str, int]:
    """
    Devuelve (serie, numero) para el siguiente comprobante de este
    negocio + tipo, y avanza el contador de una vez (para que dos
    emisiones al mismo tiempo no repitan número). Crea la serie con un
    valor por defecto la primera vez que se usa ese negocio + tipo.
    """
    serie_default = "FFF1" if tipo == "factura" else "BBB1"
    registro = (
        db.query(models.SerieComprobante)
        .filter(models.SerieComprobante.negocio_id == negocio_id, models.SerieComprobante.tipo == tipo)
        .first()
    )
    if not registro:
        registro = models.SerieComprobante(
            negocio_id=negocio_id, tipo=tipo, serie=serie_default, siguiente_numero=1
        )
        db.add(registro)
        db.flush()

    numero = registro.siguiente_numero
    registro.siguiente_numero += 1
    return registro.serie, numero


def emitir_comprobante(
    tipo: str,
    serie: str,
    numero: int,
    cliente_nombre: str,
    cliente_documento_tipo: str | None,
    cliente_documento_numero: str | None,
    items: list[dict],
) -> dict:
    """
    Emite un comprobante ante SUNAT vía NubeFacT.

    `items` es una lista de dicts, cada uno con: descripcion, cantidad,
    valor_unitario (precio SIN IGV), precio_unitario (precio CON IGV),
    subtotal, igv, total — todos en soles.

    Devuelve un dict con: aceptado (bool), estado (str: aceptado |
    observado | error), mensaje (str), enlace_pdf, enlace_xml. Nunca
    lanza una excepción — si algo falla, lo dice en el resultado, para
    que quien llama decida qué hacer (ej. avisarle a la persona que la
    venta se guardó pero el comprobante no se pudo emitir).
    """
    if not NUBEFACT_RUTA or not NUBEFACT_TOKEN:
        return {
            "aceptado": False,
            "estado": "error",
            "mensaje": "NUBEFACT_RUTA o NUBEFACT_TOKEN no están configurados en el servidor.",
            "enlace_pdf": None,
            "enlace_xml": None,
        }

    total_gravada = round(sum(i["subtotal"] for i in items), 2)
    total_igv = round(sum(i["igv"] for i in items), 2)
    total = round(sum(i["total"] for i in items), 2)

    documento_tipo_codigo = TIPO_DOCUMENTO_CODIGO.get(cliente_documento_tipo or "DNI", 1)
    documento_numero = cliente_documento_numero or "00000000"

    payload = {
        "operacion": "generar_comprobante",
        "tipo_de_comprobante": TIPO_COMPROBANTE_CODIGO.get(tipo, 2),
        "serie": serie,
        "numero": numero,
        "sunat_transaction": 1,
        "cliente_tipo_de_documento": documento_tipo_codigo,
        "cliente_numero_de_documento": documento_numero,
        "cliente_denominacion": cliente_nombre,
        "cliente_direccion": "",
        "cliente_email": "",
        "fecha_de_emision": datetime.now().strftime("%d-%m-%Y"),
        "moneda": 1,
        "porcentaje_de_igv": PORCENTAJE_IGV,
        "total_gravada": total_gravada,
        "total_igv": total_igv,
        "total": total,
        "enviar_automaticamente_a_la_sunat": True,
        "enviar_automaticamente_al_cliente": False,
        "items": [
            {
                "unidad_de_medida": "NIU",
                "codigo": "P001",
                "descripcion": item["descripcion"],
                "cantidad": item["cantidad"],
                "valor_unitario": item["valor_unitario"],
                "precio_unitario": item["precio_unitario"],
                "subtotal": item["subtotal"],
                "tipo_de_igv": 1,
                "igv": item["igv"],
                "total": item["total"],
            }
            for item in items
        ],
    }

    try:
        respuesta = requests.post(
            NUBEFACT_RUTA,
            json=payload,
            headers={"Authorization": f"Token token={NUBEFACT_TOKEN}"},
            timeout=30,
        )
        datos = respuesta.json()
    except Exception as error:
        return {
            "aceptado": False,
            "estado": "error",
            "mensaje": f"No se pudo conectar con NubeFacT: {error}",
            "enlace_pdf": None,
            "enlace_xml": None,
        }

    if respuesta.status_code != 200:
        return {
            "aceptado": False,
            "estado": "error",
            "mensaje": str(datos.get("errors") or datos.get("mensaje") or datos),
            "enlace_pdf": None,
            "enlace_xml": None,
        }

    aceptado = bool(datos.get("aceptada_por_sunat"))
    mensaje = datos.get("sunat_description") or datos.get("sunat_note") or ""
    if not mensaje:
        # No vino en los campos esperados — guardamos la respuesta completa
        # para poder ver cómo se llama el campo correcto en la práctica.
        mensaje = f"[respuesta completa, campo de mensaje no identificado] {datos}"
    return {
        "aceptado": aceptado,
        "estado": "aceptado" if aceptado else "observado",
        "mensaje": mensaje,
        "enlace_pdf": datos.get("enlace_del_pdf") or datos.get("enlace"),
        "enlace_xml": datos.get("enlace_del_xml"),
    }
