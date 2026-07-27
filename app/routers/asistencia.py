from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/asistencia", tags=["Asistencia"])


def _a_schema(registro: models.Asistencia) -> schemas.Asistencia:
    horas = None
    if registro.hora_salida:
        horas = round((registro.hora_salida - registro.hora_entrada).total_seconds() / 3600, 2)
    return schemas.Asistencia(
        id=registro.id,
        colaborador_id=registro.colaborador_id,
        fecha=registro.fecha,
        hora_entrada=registro.hora_entrada,
        hora_salida=registro.hora_salida,
        horas_trabajadas=horas,
    )


@router.post("/entrada", response_model=schemas.Asistencia)
def marcar_entrada(data: schemas.AsistenciaMarcarRequest, db: Session = Depends(get_db)):
    colaborador = db.query(models.Colaborador).get(data.colaborador_id)
    if not colaborador:
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")

    abierta = (
        db.query(models.Asistencia)
        .filter(
            models.Asistencia.colaborador_id == data.colaborador_id,
            models.Asistencia.hora_salida.is_(None),
        )
        .first()
    )
    if abierta:
        raise HTTPException(
            status_code=400,
            detail="Este colaborador ya tiene una entrada marcada sin salida registrada",
        )

    registro = models.Asistencia(colaborador_id=data.colaborador_id)
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return _a_schema(registro)


@router.post("/salida", response_model=schemas.Asistencia)
def marcar_salida(data: schemas.AsistenciaMarcarRequest, db: Session = Depends(get_db)):
    registro = (
        db.query(models.Asistencia)
        .filter(
            models.Asistencia.colaborador_id == data.colaborador_id,
            models.Asistencia.hora_salida.is_(None),
        )
        .order_by(models.Asistencia.hora_entrada.desc())
        .first()
    )
    if not registro:
        raise HTTPException(
            status_code=400,
            detail="No hay una entrada abierta para este colaborador",
        )

    registro.hora_salida = datetime.utcnow()
    db.commit()
    db.refresh(registro)
    return _a_schema(registro)


@router.get("/en-turno", response_model=list[schemas.Asistencia])
def en_turno(negocio_id: int | None = None, db: Session = Depends(get_db)):
    """Quién tiene la entrada marcada y todavía no ha marcado salida."""
    query = db.query(models.Asistencia).filter(models.Asistencia.hora_salida.is_(None))
    if negocio_id is not None:
        query = query.join(models.Colaborador).filter(models.Colaborador.negocio_id == negocio_id)
    return [_a_schema(r) for r in query.all()]


@router.get("/", response_model=list[schemas.Asistencia])
def listar_asistencia(
    colaborador_id: int | None = None,
    fecha: date | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Asistencia)
    if colaborador_id is not None:
        query = query.filter(models.Asistencia.colaborador_id == colaborador_id)
    if fecha is not None:
        query = query.filter(models.Asistencia.fecha == fecha)
    registros = query.order_by(models.Asistencia.hora_entrada.desc()).all()
    return [_a_schema(r) for r in registros]
