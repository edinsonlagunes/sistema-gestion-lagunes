from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/colaboradores", tags=["Colaboradores"])


@router.get("/", response_model=list[schemas.Colaborador])
def listar_colaboradores(negocio_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Colaborador)
    if negocio_id is not None:
        query = query.filter(models.Colaborador.negocio_id == negocio_id)
    return query.all()


@router.post("/", response_model=schemas.Colaborador)
def crear_colaborador(data: schemas.ColaboradorCreate, db: Session = Depends(get_db)):
    negocio = db.query(models.Negocio).get(data.negocio_id)
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    colaborador = models.Colaborador(**data.model_dump())
    db.add(colaborador)
    db.commit()
    db.refresh(colaborador)
    return colaborador


@router.get("/{colaborador_id}", response_model=schemas.Colaborador)
def obtener_colaborador(colaborador_id: int, db: Session = Depends(get_db)):
    colaborador = db.query(models.Colaborador).get(colaborador_id)
    if not colaborador:
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")
    return colaborador
