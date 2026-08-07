from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db
from app.permisos import requerir_permiso
from app.zona_horaria import ahora_peru

router = APIRouter(tags=["Mantenimiento de equipos"], dependencies=[Depends(obtener_usuario_actual)])


def _a_schema(m: models.Mantenimiento) -> schemas.MantenimientoOut:
    dias = None
    if m.fecha_proximo:
        dias = (m.fecha_proximo - ahora_peru().date()).days
    return schemas.MantenimientoOut(
        id=m.id,
        equipo_id=m.equipo_id,
        tipo=m.tipo,
        fecha_realizado=m.fecha_realizado,
        fecha_proximo=m.fecha_proximo,
        descripcion=m.descripcion,
        costo=m.costo,
        responsable_id=m.responsable_id,
        proveedor_id=m.proveedor_id,
        dias_para_proximo=dias,
    )


@router.get("/mantenimientos/proximos", response_model=list[schemas.MantenimientoOut])
def mantenimientos_proximos(
    dias: int = 30,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("mantenimientos", "ver")),
):
    """Mantenimientos programados dentro de los próximos N días, o ya vencidos."""
    limite = ahora_peru().date() + timedelta(days=dias)
    mantenimientos = (
        db.query(models.Mantenimiento).filter(models.Mantenimiento.fecha_proximo.isnot(None)).all()
    )
    proximos = [m for m in mantenimientos if m.fecha_proximo <= limite]
    proximos.sort(key=lambda m: m.fecha_proximo)
    return [_a_schema(m) for m in proximos]


@router.get("/equipos/{equipo_id}/mantenimientos", response_model=list[schemas.MantenimientoOut])
def listar_mantenimientos(
    equipo_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("mantenimientos", "ver")),
):
    equipo = db.query(models.Equipo).get(equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return [_a_schema(m) for m in equipo.mantenimientos]


@router.post("/equipos/{equipo_id}/mantenimientos", response_model=schemas.MantenimientoOut)
def registrar_mantenimiento(
    equipo_id: int,
    data: schemas.MantenimientoCreate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("mantenimientos", "editar")),
):
    """
    Registra un mantenimiento (preventivo o correctivo) de un equipo, y
    de paso puede programar el próximo. Si tuvo costo y se asume pagado
    al momento, genera el egreso real. Exige permiso de Mantenimientos.
    """
    equipo = db.query(models.Equipo).get(equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    mantenimiento = models.Mantenimiento(
        equipo_id=equipo_id,
        tipo=data.tipo,
        fecha_realizado=data.fecha_realizado or ahora_peru(),
        fecha_proximo=data.fecha_proximo,
        descripcion=data.descripcion,
        costo=data.costo,
        responsable_id=data.responsable_id,
        proveedor_id=data.proveedor_id,
    )
    db.add(mantenimiento)

    if data.costo and data.generar_egreso:
        puesto = db.query(models.PuestoTrabajo).get(equipo.puesto_id)
        db.add(
            models.Egreso(
                negocio_id=puesto.negocio_id,
                categoria="mantenimiento",
                monto=data.costo,
                descripcion=f"Mantenimiento {equipo.nombre} - {data.descripcion or data.tipo}",
                fecha=mantenimiento.fecha_realizado,
            )
        )

    db.commit()
    db.refresh(mantenimiento)
    return _a_schema(mantenimiento)


@router.patch("/equipos/{equipo_id}/mantenimientos/{mantenimiento_id}", response_model=schemas.MantenimientoOut)
def actualizar_mantenimiento(
    equipo_id: int,
    mantenimiento_id: int,
    data: schemas.MantenimientoUpdate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("mantenimientos", "editar")),
):
    """Edita un mantenimiento (ej. reprogramar el próximo). Exige permiso de Mantenimientos."""
    mantenimiento = (
        db.query(models.Mantenimiento)
        .filter(models.Mantenimiento.id == mantenimiento_id, models.Mantenimiento.equipo_id == equipo_id)
        .first()
    )
    if not mantenimiento:
        raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(mantenimiento, campo, valor)

    db.commit()
    db.refresh(mantenimiento)
    return _a_schema(mantenimiento)


@router.delete("/equipos/{equipo_id}/mantenimientos/{mantenimiento_id}", status_code=204)
def eliminar_mantenimiento(
    equipo_id: int,
    mantenimiento_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("mantenimientos", "editar")),
):
    mantenimiento = (
        db.query(models.Mantenimiento)
        .filter(models.Mantenimiento.id == mantenimiento_id, models.Mantenimiento.equipo_id == equipo_id)
        .first()
    )
    if not mantenimiento:
        raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")
    db.delete(mantenimiento)
    db.commit()
    return None
