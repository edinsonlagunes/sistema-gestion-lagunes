"""
Autenticación por token (JWT).

Cada login exitoso entrega un token que dura una jornada laboral
(8 horas). Los routers protegidos exigen ese token en el header
Authorization: Bearer <token> para dejar pasar cualquier request.

IMPORTANTE: en Railway, define la variable de entorno SECRET_KEY con un
valor propio y secreto (Settings -> Variables -> New Variable). Si no la
defines, se usa un valor de respaldo solo apto para pruebas locales.
"""
import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

SECRET_KEY = os.getenv("SECRET_KEY", "clave-de-desarrollo-cambiar-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas

# HTTPBearer hace que /docs muestre un simple cuadro para pegar el token,
# en vez del formulario de usuario/contraseña de OAuth2 (que espera un
# formato distinto al que usa nuestro endpoint de login).
security_scheme = HTTPBearer()


def crear_token(usuario_id: int) -> str:
    expira = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(usuario_id), "exp": expira}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    error_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión inválida o expirada, vuelve a iniciar sesión",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credenciales.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("sub")
        if usuario_id is None:
            raise error_credenciales
    except JWTError:
        raise error_credenciales

    usuario = db.query(models.Usuario).get(int(usuario_id))
    if usuario is None:
        raise error_credenciales
    return usuario


def requerir_admin(usuario: models.Usuario = Depends(obtener_usuario_actual)) -> models.Usuario:
    if usuario.rol_permiso != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol de administrador")
    return usuario
