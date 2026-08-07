from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db
from app.permisos import requerir_permiso

router = APIRouter(prefix="/colaboradores", tags=["Colaboradores"], dependencies=[Depends(obtener_usuario_actual)])


@router.get("/", response_model=list[schemas.Colaborador])
def listar_colaboradores(
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("colaboradores", "ver")),
):
    query = db.query(models.Colaborador)
    if negocio_id is not None:
        query = query.filter(models.Colaborador.negocio_id == negocio_id)
    return query.all()


@router.post("/", response_model=schemas.Colaborador)
def crear_colaborador(
    data: schemas.ColaboradorCreate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("colaboradores", "editar")),
):
    negocio = db.query(models.Negocio).get(data.negocio_id)
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    colaborador = models.Colaborador(**data.model_dump())
    db.add(colaborador)
    db.commit()
    db.refresh(colaborador)
    return colaborador


@router.get("/{colaborador_id}", response_model=schemas.Colaborador)
def obtener_colaborador(
    colaborador_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("colaboradores", "ver")),
):
    colaborador = db.query(models.Colaborador).get(colaborador_id)
    if not colaborador:
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")
    return colaborador


@router.patch("/{colaborador_id}", response_model=schemas.Colaborador)
def actualizar_colaborador(
    colaborador_id: int,
    data: schemas.ColaboradorUpdate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("colaboradores", "editar")),
):
    """Edita nombre, rol, sueldo semanal u horario esperado. Exige permiso de Colaboradores."""
    colaborador = db.query(models.Colaborador).get(colaborador_id)
    if not colaborador:
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(colaborador, campo, valor)

    db.commit()
    db.refresh(colaborador)
    return colaborador
