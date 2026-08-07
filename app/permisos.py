"""
Sistema de permisos: cada usuario tiene un rol (opcional) que le da un
nivel de acceso por módulo, y puede además tener permisos especiales
individuales que se suman por encima del rol sin afectar a nadie más.
Un superadministrador (Usuario.es_superadmin) siempre tiene acceso total.

Ver también:
- app/models.py — tablas Rol, PermisoRol, PermisoEspecial
- app/routers/roles.py — CRUD para administrar todo esto
- app/migrate.py — MODULOS_INICIALES / ROLES_INICIALES (deben coincidir con MODULOS_SISTEMA de aquí)
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.auth import obtener_usuario_actual
from app.database import get_db

MODULOS_SISTEMA = [
    "proyectos", "compras", "colaboradores", "finanzas", "documentos",
    "caja_chica", "planillas", "asistencia", "ventas_impresiones",
    "conciliacion", "mantenimientos", "agenda", "avance_obra",
]

NIVELES_VALIDOS = ["sin_acceso", "ver", "editar"]
_RANGO_NIVEL = {"sin_acceso": 0, "ver": 1, "editar": 2}


def nivel_efectivo(usuario: models.Usuario, modulo: str, db: Session) -> str:
    """
    El nivel de acceso real de un usuario sobre un módulo: el mayor
    entre lo que le da su rol y cualquier permiso especial que tenga
    para ese módulo en particular. Un superadministrador siempre tiene
    "editar" en todo.
    """
    if usuario.es_superadmin:
        return "editar"

    nivel_rol = "sin_acceso"
    if usuario.rol_id:
        permiso_rol = (
            db.query(models.PermisoRol)
            .filter(models.PermisoRol.rol_id == usuario.rol_id, models.PermisoRol.modulo == modulo)
            .first()
        )
        if permiso_rol:
            nivel_rol = permiso_rol.nivel

    permiso_especial = (
        db.query(models.PermisoEspecial)
        .filter(models.PermisoEspecial.usuario_id == usuario.id, models.PermisoEspecial.modulo == modulo)
        .first()
    )
    nivel_especial = permiso_especial.nivel if permiso_especial else "sin_acceso"

    return nivel_rol if _RANGO_NIVEL[nivel_rol] >= _RANGO_NIVEL[nivel_especial] else nivel_especial


def requerir_permiso(modulo: str, nivel_minimo: str = "ver"):
    """
    Dependencia de FastAPI: exige que el usuario tenga al menos
    `nivel_minimo` de acceso sobre `modulo`. Ejemplo de uso en un router:

        from app.permisos import requerir_permiso

        router = APIRouter(
            prefix="/finanzas",
            dependencies=[Depends(requerir_permiso("finanzas", "ver"))],
        )

        @router.post("/ingresos", dependencies=[Depends(requerir_permiso("finanzas", "editar"))])
        def crear_ingreso(...): ...
    """
    def _verificar(
        usuario: models.Usuario = Depends(obtener_usuario_actual),
        db: Session = Depends(get_db),
    ) -> models.Usuario:
        nivel = nivel_efectivo(usuario, modulo, db)
        if _RANGO_NIVEL[nivel] < _RANGO_NIVEL[nivel_minimo]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes acceso de '{nivel_minimo}' en el módulo '{modulo}'",
            )
        return usuario

    return _verificar


def permisos_de_usuario(usuario: models.Usuario, db: Session) -> dict[str, str]:
    """Diccionario modulo -> nivel_efectivo, pensado para mandarlo al frontend (ej. en el login)."""
    return {modulo: nivel_efectivo(usuario, modulo, db) for modulo in MODULOS_SISTEMA}
