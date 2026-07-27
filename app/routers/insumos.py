from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/insumos", tags=["Insumos"])
proveedores_router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


@router.get("/", response_model=list[schemas.Insumo])
def listar_insumos(negocio_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Insumo)
    if negocio_id is not None:
        query = query.filter(models.Insumo.negocio_id == negocio_id)
    return query.all()


@router.post("/", response_model=schemas.Insumo)
def crear_insumo(data: schemas.InsumoCreate, db: Session = Depends(get_db)):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    insumo = models.Insumo(**data.model_dump())
    db.add(insumo)
    db.commit()
    db.refresh(insumo)
    return insumo


@proveedores_router.get("/", response_model=list[schemas.Proveedor])
def listar_proveedores(db: Session = Depends(get_db)):
    return db.query(models.Proveedor).all()


@proveedores_router.post("/", response_model=schemas.Proveedor)
def crear_proveedor(data: schemas.ProveedorCreate, db: Session = Depends(get_db)):
    proveedor = models.Proveedor(**data.model_dump())
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor
