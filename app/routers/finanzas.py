from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db

router = APIRouter(prefix="/finanzas", tags=["Finanzas"], dependencies=[Depends(obtener_usuario_actual)])


@router.get("/ingresos", response_model=list[schemas.Ingreso])
def listar_ingresos(negocio_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Ingreso)
    if negocio_id is not None:
        query = query.filter(models.Ingreso.negocio_id == negocio_id)
    return query.order_by(models.Ingreso.fecha.desc()).all()


@router.post("/ingresos", response_model=schemas.Ingreso)
def crear_ingreso(data: schemas.IngresoCreate, db: Session = Depends(get_db)):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    ingreso = models.Ingreso(**data.model_dump())
    db.add(ingreso)
    db.commit()
    db.refresh(ingreso)
    return ingreso


@router.get("/egresos", response_model=list[schemas.Egreso])
def listar_egresos(negocio_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Egreso)
    if negocio_id is not None:
        query = query.filter(models.Egreso.negocio_id == negocio_id)
    return query.order_by(models.Egreso.fecha.desc()).all()


@router.post("/egresos", response_model=schemas.Egreso)
def crear_egreso(data: schemas.EgresoCreate, db: Session = Depends(get_db)):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    egreso = models.Egreso(**data.model_dump())
    db.add(egreso)
    db.commit()
    db.refresh(egreso)
    return egreso


@router.get("/resumen", response_model=list[schemas.ResumenNegocio])
def resumen(db: Session = Depends(get_db)):
    """Balance por negocio: base del futuro dashboard."""
    resultados = []
    for negocio in db.query(models.Negocio).all():
        total_ingresos = sum(i.monto for i in negocio.ingresos)
        total_egresos = sum(e.monto for e in negocio.egresos)
        insumos_bajo_stock = sum(
            1 for i in negocio.insumos if i.stock_actual <= i.stock_minimo
        )
        resultados.append(
            schemas.ResumenNegocio(
                negocio_id=negocio.id,
                negocio_nombre=negocio.nombre,
                total_ingresos=total_ingresos,
                total_egresos=total_egresos,
                balance=total_ingresos - total_egresos,
                insumos_bajo_stock=insumos_bajo_stock,
            )
        )
    return resultados
