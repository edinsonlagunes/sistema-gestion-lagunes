"""
Respaldo de la base de datos completa, sin depender de pg_dump (no hay
garantía de que esté instalado en el servidor) — lee cada tabla
directo con SQLAlchemy y sube un archivo JSON a Cloudinary (la misma
cuenta que ya usas para las fotos de avance de obra; Cloudinary
también admite archivos que no son imágenes, como "raw").

Es un respaldo de emergencia para no perder los datos, no un
reemplazo de backups nativos de Postgres — no incluye índices,
triggers, ni "restaurar a un punto exacto en el tiempo". Si más
adelante subes al plan Pro de Railway, ese sí te da eso de forma
nativa y sin mantener este código.
"""
import io
import json
import os
from datetime import date, datetime

import cloudinary
import cloudinary.uploader

from app.database import Base, engine
from app.zona_horaria import ahora_peru

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.environ.get("CLOUDINARY_API_KEY", ""),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", ""),
    secure=True,
)


def _serializar(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def _generar_respaldo() -> dict:
    """Lee todas las tablas de la base de datos, tal cual están definidas en los modelos."""
    datos = {}
    with engine.connect() as conn:
        for tabla in Base.metadata.sorted_tables:
            resultado = conn.execute(tabla.select())
            columnas = list(resultado.keys())
            datos[tabla.name] = [
                {col: _serializar(valor) for col, valor in zip(columnas, fila)}
                for fila in resultado.fetchall()
            ]
    return datos


def respaldar_base_de_datos() -> dict:
    """
    Genera el respaldo completo y lo sube a Cloudinary como archivo.
    Devuelve un dict con: exitoso (bool), mensaje (str), enlace (str o None).
    """
    if not os.environ.get("CLOUDINARY_CLOUD_NAME"):
        return {"exitoso": False, "mensaje": "Cloudinary no está configurado en el servidor.", "enlace": None}

    try:
        datos = _generar_respaldo()
        contenido = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        nombre_archivo = f"respaldo-{ahora_peru().strftime('%Y-%m-%d-%H%M')}"
        resultado = cloudinary.uploader.upload(
            io.BytesIO(contenido),
            resource_type="raw",
            public_id=nombre_archivo,
            folder="respaldos_base_datos",
        )
        total_filas = sum(len(filas) for filas in datos.values())
        return {
            "exitoso": True,
            "mensaje": f"{len(datos)} tabla(s), {total_filas} fila(s) en total, respaldadas correctamente.",
            "enlace": resultado.get("secure_url"),
        }
    except Exception as error:
        return {"exitoso": False, "mensaje": f"Error al generar el respaldo: {error}", "enlace": None}
