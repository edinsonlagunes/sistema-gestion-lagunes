"""
Registro de auditoría: quién hizo qué y cuándo, para las acciones
sensibles del sistema (dinero, permisos, accesos). No registra
absolutamente todo — se llama explícitamente desde las rutas que
mueven dinero o cambian accesos, no desde cada lectura o consulta.
"""
from sqlalchemy.orm import Session

from app import models


def registrar_auditoria(
    db: Session,
    usuario: "models.Usuario | None",
    accion: str,
    entidad: str,
    entidad_id: int | None,
    detalle: str,
) -> None:
    """
    Guarda una línea de auditoría. No hace commit por su cuenta — se
    apoya en el commit que ya va a hacer la ruta que la llama, para no
    duplicar ida y vuelta a la base de datos.
    """
    db.add(
        models.RegistroAuditoria(
            usuario_id=usuario.id if usuario else None,
            usuario_username=usuario.username if usuario else None,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=detalle,
        )
    )
