"""
Subida de fotos a Cloudinary para los reportes de avance de obra.
Railway/Postgres no está pensado para guardar archivos pesados — el
backend solo guarda la URL que Cloudinary devuelve.

IMPORTANTE: en Railway, define las variables de entorno
CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY y CLOUDINARY_API_SECRET
(las encuentras en el dashboard de Cloudinary, sección "API Keys").
"""
import os

import cloudinary
import cloudinary.uploader
from fastapi import UploadFile

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.environ.get("CLOUDINARY_API_KEY", ""),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", ""),
    secure=True,
)


async def subir_foto(archivo: UploadFile) -> str:
    """
    Sube una foto a Cloudinary y devuelve su URL pública. A propósito
    deja que la excepción se propague si algo falla (a diferencia del
    correo, donde una alerta perdida no es grave) — si una foto de
    campo no se pudo subir, quien reporta debe verlo en el momento,
    no perderla en silencio.
    """
    contenido = await archivo.read()
    resultado = cloudinary.uploader.upload(contenido, folder="avance_obra")
    return resultado["secure_url"]
