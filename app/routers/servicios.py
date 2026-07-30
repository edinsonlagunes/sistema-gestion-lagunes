from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual, requerir_admin
from app.database import get_db

router = APIRouter(prefix="/servicios", tags=["Servicios (POS)"], dependencies=[Depends(obtener_usuario_actual)])


@router.get("/", response_model=list[schemas.Servicio])
def listar_servicios(
    negocio_id: int | None = None,
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(models.Servicio)
    if not incluir_inactivos:
        query = query.filter(models.Servicio.activo.is_(True))
    if negocio_id is not None:
        query = query.filter(models.Servicio.negocio_id == negocio_id)
    return query.all()


@router.post("/", response_model=schemas.Servicio)
def crear_servicio(
    data: schemas.ServicioCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """Solo un administrador puede agregar servicios al catálogo."""
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if data.insumo_id and not db.query(models.Insumo).get(data.insumo_id):
        raise HTTPException(status_code=404, detail="Insumo no encontrado")

    servicio = models.Servicio(**data.model_dump())
    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    return servicio


@router.patch("/{servicio_id}", response_model=schemas.Servicio)
def actualizar_servicio(
    servicio_id: int,
    data: schemas.ServicioUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """Solo un administrador puede modificar nombre, precio u otros datos del servicio."""
    servicio = db.query(models.Servicio).get(servicio_id)
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(servicio, campo, valor)

    db.commit()
    db.refresh(servicio)
    return servicio


@router.delete("/{servicio_id}", status_code=204)
def eliminar_servicio(
    servicio_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Solo un administrador puede quitar un servicio. No se borra de la base
    de datos (para no romper las ventas/órdenes ya registradas con ese
    servicio) — se marca como inactivo y desaparece del catálogo.
    """
    servicio = db.query(models.Servicio).get(servicio_id)
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    servicio.activo = False
    db.commit()
    return None
