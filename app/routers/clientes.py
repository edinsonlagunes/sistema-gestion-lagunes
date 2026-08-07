from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db

router = APIRouter(prefix="/clientes", tags=["Clientes"], dependencies=[Depends(obtener_usuario_actual)])


@router.get("/", response_model=list[schemas.Cliente])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(models.Cliente).all()


@router.post("/", response_model=schemas.Cliente)
def crear_cliente(data: schemas.ClienteCreate, db: Session = Depends(get_db)):
    cliente = models.Cliente(**data.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.patch("/{cliente_id}", response_model=schemas.Cliente)
def editar_cliente(cliente_id: int, data: schemas.ClienteUpdate, db: Session = Depends(get_db)):
    """Edita un cliente — típicamente para completarle el RUC/DNI antes de facturarle."""
    cliente = db.query(models.Cliente).get(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    db.commit()
    db.refresh(cliente)
    return cliente
