from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/servicios", tags=["Servicios (POS)"])


@router.get("/", response_model=list[schemas.Servicio])
def listar_servicios(negocio_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Servicio).filter(models.Servicio.activo.is_(True))
    if negocio_id is not None:
        query = query.filter(models.Servicio.negocio_id == negocio_id)
    return query.all()


@router.post("/", response_model=schemas.Servicio)
def crear_servicio(data: schemas.ServicioCreate, db: Session = Depends(get_db)):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if data.insumo_id and not db.query(models.Insumo).get(data.insumo_id):
        raise HTTPException(status_code=404, detail="Insumo no encontrado")

    servicio = models.Servicio(**data.model_dump())
    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    return servicio
