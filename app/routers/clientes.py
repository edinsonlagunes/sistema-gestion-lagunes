from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/clientes", tags=["Clientes"])


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
