from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db
from app.zona_horaria import ahora_peru

router = APIRouter(prefix="/agenda", tags=["Agenda del estudio"], dependencies=[Depends(obtener_usuario_actual)])

TIPOS_VALIDOS = {"reunion", "visita_obra", "entrega", "otro"}
ESTADOS_VALIDOS = {"pendiente", "completado", "cancelado"}


@router.get("/", response_model=list[schemas.EventoAgendaOut])
def listar_eventos(
    negocio_id: int | None = None,
    proyecto_id: int | None = None,
    estado: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.EventoAgenda)
    if negocio_id is not None:
        query = query.filter(models.EventoAgenda.negocio_id == negocio_id)
    if proyecto_id is not None:
        query = query.filter(models.EventoAgenda.proyecto_id == proyecto_id)
    if estado is not None:
        query = query.filter(models.EventoAgenda.estado == estado)
    return query.order_by(models.EventoAgenda.fecha_inicio.asc()).all()


@router.get("/proximos", response_model=list[schemas.EventoAgendaOut])
def eventos_proximos(dias: int = 7, negocio_id: int | None = None, db: Session = Depends(get_db)):
    """Eventos pendientes dentro de los próximos N días (para un vistazo rápido de la semana)."""
    limite = ahora_peru() + timedelta(days=dias)
    query = db.query(models.EventoAgenda).filter(
        models.EventoAgenda.estado == "pendiente",
        models.EventoAgenda.fecha_inicio <= limite,
    )
    if negocio_id is not None:
        query = query.filter(models.EventoAgenda.negocio_id == negocio_id)
    return query.order_by(models.EventoAgenda.fecha_inicio.asc()).all()


@router.post("/", response_model=schemas.EventoAgendaOut)
def crear_evento(data: schemas.EventoAgendaCreate, db: Session = Depends(get_db)):
    """
    Agenda una reunión, visita de obra, entrega, u otro evento. Cualquier
    usuario logueado puede crear y coordinar la agenda — no requiere
    permisos de administrador, es coordinación operativa, no dinero.
    """
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if data.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Usa uno de: {sorted(TIPOS_VALIDOS)}")
    if data.proyecto_id and not db.query(models.Proyecto).get(data.proyecto_id):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    evento = models.EventoAgenda(**data.model_dump())
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


@router.patch("/{evento_id}", response_model=schemas.EventoAgendaOut)
def actualizar_evento(evento_id: int, data: schemas.EventoAgendaUpdate, db: Session = Depends(get_db)):
    evento = db.query(models.EventoAgenda).get(evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    datos = data.model_dump(exclude_unset=True)
    if "tipo" in datos and datos["tipo"] not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Usa uno de: {sorted(TIPOS_VALIDOS)}")
    if "estado" in datos and datos["estado"] not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Usa uno de: {sorted(ESTADOS_VALIDOS)}")

    for campo, valor in datos.items():
        setattr(evento, campo, valor)

    db.commit()
    db.refresh(evento)
    return evento


@router.delete("/{evento_id}", status_code=204)
def eliminar_evento(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(models.EventoAgenda).get(evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    db.delete(evento)
    db.commit()
    return None
