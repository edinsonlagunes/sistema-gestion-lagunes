from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual, requerir_admin
from app.database import get_db

router = APIRouter(prefix="/negocios", tags=["Negocios"], dependencies=[Depends(obtener_usuario_actual)])


@router.get("/", response_model=list[schemas.Negocio])
def listar_negocios(db: Session = Depends(get_db)):
    return db.query(models.Negocio).all()


@router.post("/", response_model=schemas.Negocio)
def crear_negocio(data: schemas.NegocioCreate, db: Session = Depends(get_db)):
    existente = db.query(models.Negocio).filter(models.Negocio.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un negocio con ese nombre")
    negocio = models.Negocio(**data.model_dump())
    db.add(negocio)
    db.commit()
    db.refresh(negocio)
    return negocio


@router.patch("/{negocio_id}", response_model=schemas.Negocio)
def renombrar_negocio(
    negocio_id: int,
    data: schemas.NegocioCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """Cambia el nombre de un negocio. Solo administradores."""
    negocio = db.query(models.Negocio).get(negocio_id)
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    existente = (
        db.query(models.Negocio)
        .filter(models.Negocio.nombre == data.nombre, models.Negocio.id != negocio_id)
        .first()
    )
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un negocio con ese nombre")
    negocio.nombre = data.nombre
    db.commit()
    db.refresh(negocio)
    return negocio
