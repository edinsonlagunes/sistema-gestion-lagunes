from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db

router = APIRouter(prefix="/compras", tags=["Compras"], dependencies=[Depends(obtener_usuario_actual)])


@router.get("/", response_model=list[schemas.Compra])
def listar_compras(negocio_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Compra)
    if negocio_id is not None:
        query = query.filter(models.Compra.negocio_id == negocio_id)
    return query.order_by(models.Compra.fecha.desc()).all()


@router.post("/", response_model=schemas.Compra)
def registrar_compra(data: schemas.CompraCreate, db: Session = Depends(get_db)):
    """
    Registra una compra de insumo: sube el stock automáticamente. NO
    genera egreso — eso solo pasa cuando se registra un pago real al
    proveedor (ver /proveedores/{id}/pagos), para no contar como pagado
    algo que todavía está pendiente (cuenta por pagar).
    """
    insumo = db.query(models.Insumo).get(data.insumo_id)
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    if not db.query(models.Proveedor).get(data.proveedor_id):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    compra = models.Compra(**data.model_dump())
    db.add(compra)

    insumo.stock_actual += data.cantidad

    db.commit()
    db.refresh(compra)
    return compra
