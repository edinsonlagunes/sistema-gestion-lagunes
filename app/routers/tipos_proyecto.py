from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual, requerir_admin
from app.database import get_db

router = APIRouter(
    prefix="/tipos-proyecto", tags=["Tipos de proyecto"], dependencies=[Depends(obtener_usuario_actual)]
)


@router.get("/", response_model=list[schemas.TipoProyecto])
def listar_tipos_proyecto(negocio_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.TipoProyecto)
    if negocio_id is not None:
        query = query.filter(models.TipoProyecto.negocio_id == negocio_id)
    return query.order_by(models.TipoProyecto.nombre).all()


@router.post("/", response_model=schemas.TipoProyecto)
def crear_tipo_proyecto(
    data: schemas.TipoProyectoCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """Solo un administrador puede agregar tipos de proyecto al catálogo."""
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    tipo = models.TipoProyecto(**data.model_dump())
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


@router.patch("/{tipo_id}", response_model=schemas.TipoProyecto)
def actualizar_tipo_proyecto(
    tipo_id: int,
    data: schemas.TipoProyectoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    tipo = db.query(models.TipoProyecto).get(tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de proyecto no encontrado")
    tipo.nombre = data.nombre
    db.commit()
    db.refresh(tipo)
    return tipo


@router.delete("/{tipo_id}", status_code=204)
def eliminar_tipo_proyecto(
    tipo_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Quita un tipo del catálogo. Los proyectos que ya tenían este tipo
    asignado conservan el texto (no se ven afectados) — solo deja de
    aparecer como opción para proyectos nuevos.
    """
    tipo = db.query(models.TipoProyecto).get(tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de proyecto no encontrado")
    db.delete(tipo)
    db.commit()
    return None
