from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db

router = APIRouter(prefix="/caja", tags=["Caja"], dependencies=[Depends(obtener_usuario_actual)])


@router.get("/actual", response_model=schemas.CajaSesion | None)
def caja_actual(negocio_id: int, db: Session = Depends(get_db)):
    """Devuelve la sesión de caja abierta de ese negocio, si existe."""
    return (
        db.query(models.CajaSesion)
        .filter(models.CajaSesion.negocio_id == negocio_id, models.CajaSesion.estado == "abierta")
        .first()
    )


@router.post("/abrir", response_model=schemas.CajaSesion)
def abrir_caja(data: schemas.CajaAbrirRequest, db: Session = Depends(get_db)):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    ya_abierta = (
        db.query(models.CajaSesion)
        .filter(models.CajaSesion.negocio_id == data.negocio_id, models.CajaSesion.estado == "abierta")
        .first()
    )
    if ya_abierta:
        raise HTTPException(status_code=400, detail="Ya hay una caja abierta para este negocio")

    sesion = models.CajaSesion(
        negocio_id=data.negocio_id,
        colaborador_id=data.colaborador_id,
        monto_apertura=data.monto_apertura,
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion


@router.post("/{sesion_id}/cerrar", response_model=schemas.CajaSesion)
def cerrar_caja(sesion_id: int, data: schemas.CajaCerrarRequest, db: Session = Depends(get_db)):
    sesion = db.query(models.CajaSesion).get(sesion_id)
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión de caja no encontrada")
    if sesion.estado == "cerrada":
        raise HTTPException(status_code=400, detail="Esta caja ya está cerrada")

    # Solo las ventas en efectivo mueven el dinero físico de la caja.
    total_efectivo = sum(v.total for v in sesion.ventas if v.medio_pago == "efectivo")
    sesion.monto_cierre_esperado = sesion.monto_apertura + total_efectivo
    sesion.monto_cierre_reportado = data.monto_cierre_reportado
    sesion.fecha_cierre = datetime.utcnow()
    sesion.estado = "cerrada"

    db.commit()
    db.refresh(sesion)
    return sesion
