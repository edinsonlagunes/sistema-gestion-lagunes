from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import requerir_superadmin
from app.database import get_db

router = APIRouter(
    prefix="/auditoria",
    tags=["Auditoría"],
    dependencies=[Depends(requerir_superadmin)],
)


@router.get("/", response_model=list[schemas.RegistroAuditoriaOut])
def listar_auditoria(
    entidad: str | None = None,
    usuario_id: int | None = None,
    limite: int = 200,
    db: Session = Depends(get_db),
):
    """Historial de acciones sensibles (dinero, permisos, accesos). Solo superadministrador."""
    query = db.query(models.RegistroAuditoria)
    if entidad is not None:
        query = query.filter(models.RegistroAuditoria.entidad == entidad)
    if usuario_id is not None:
        query = query.filter(models.RegistroAuditoria.usuario_id == usuario_id)
    return query.order_by(models.RegistroAuditoria.fecha.desc()).limit(limite).all()
