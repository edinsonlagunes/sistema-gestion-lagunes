from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db
from app.permisos import requerir_permiso

router = APIRouter(
    prefix="/comprobantes-electronicos",
    tags=["Comprobantes electrónicos (SUNAT)"],
    dependencies=[Depends(obtener_usuario_actual)],
)


@router.get("/", response_model=list[schemas.ComprobanteElectronicoOut])
def listar_comprobantes(
    negocio_id: int | None = None,
    estado_sunat: str | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("finanzas", "ver")),
):
    """Historial de facturas/boletas emitidas — útil para revisar cuáles quedaron aceptadas u observadas por SUNAT."""
    query = db.query(models.ComprobanteElectronico)
    if negocio_id is not None:
        query = query.filter(models.ComprobanteElectronico.negocio_id == negocio_id)
    if estado_sunat is not None:
        query = query.filter(models.ComprobanteElectronico.estado_sunat == estado_sunat)
    return query.order_by(models.ComprobanteElectronico.fecha_emision.desc()).all()
