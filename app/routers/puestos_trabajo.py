from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual, requerir_admin
from app.database import get_db

router = APIRouter(
    prefix="/puestos-trabajo", tags=["Puestos de trabajo"], dependencies=[Depends(obtener_usuario_actual)]
)


@router.get("/", response_model=list[schemas.PuestoTrabajoOut])
def listar_puestos(negocio_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.PuestoTrabajo)
    if negocio_id is not None:
        query = query.filter(models.PuestoTrabajo.negocio_id == negocio_id)
    return query.order_by(models.PuestoTrabajo.nombre).all()


@router.post("/", response_model=schemas.PuestoTrabajoOut)
def crear_puesto(
    data: schemas.PuestoTrabajoCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if data.colaborador_id and not db.query(models.Colaborador).get(data.colaborador_id):
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")

    puesto = models.PuestoTrabajo(**data.model_dump())
    db.add(puesto)
    db.commit()
    db.refresh(puesto)
    return puesto


@router.patch("/{puesto_id}", response_model=schemas.PuestoTrabajoOut)
def actualizar_puesto(
    puesto_id: int,
    data: schemas.PuestoTrabajoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    puesto = db.query(models.PuestoTrabajo).get(puesto_id)
    if not puesto:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(puesto, campo, valor)

    db.commit()
    db.refresh(puesto)
    return puesto


@router.delete("/{puesto_id}", status_code=204)
def eliminar_puesto(
    puesto_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    puesto = db.query(models.PuestoTrabajo).get(puesto_id)
    if not puesto:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")
    db.delete(puesto)
    db.commit()
    return None


@router.post("/{puesto_id}/equipos", response_model=schemas.PuestoTrabajoOut)
def agregar_equipo(
    puesto_id: int,
    data: schemas.EquipoCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    puesto = db.query(models.PuestoTrabajo).get(puesto_id)
    if not puesto:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")

    equipo = models.Equipo(puesto_id=puesto_id, tipo=data.tipo, nombre=data.nombre)
    db.add(equipo)
    db.commit()
    db.refresh(puesto)
    return puesto


@router.delete("/{puesto_id}/equipos/{equipo_id}", response_model=schemas.PuestoTrabajoOut)
def quitar_equipo(
    puesto_id: int,
    equipo_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    equipo = (
        db.query(models.Equipo)
        .filter(models.Equipo.id == equipo_id, models.Equipo.puesto_id == puesto_id)
        .first()
    )
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    db.delete(equipo)
    db.commit()
    puesto = db.query(models.PuestoTrabajo).get(puesto_id)
    return puesto
