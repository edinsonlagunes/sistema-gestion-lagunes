from datetime import time as hora_tipo, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual, requerir_admin
from app.database import get_db
from app.zona_horaria import ahora_peru

router = APIRouter(prefix="/planillas", tags=["Planillas"], dependencies=[Depends(obtener_usuario_actual)])

DIAS_LABORABLES_SEMANA = 6  # lunes a sábado
HORAS_JORNADA = 8


def _valor_dia(sueldo_semanal: float) -> float:
    return sueldo_semanal / DIAS_LABORABLES_SEMANA


def _valor_minuto(sueldo_semanal: float) -> float:
    return _valor_dia(sueldo_semanal) / (HORAS_JORNADA * 60)


def _a_detalle(planilla: models.Planilla) -> schemas.PlanillaDetalle:
    detalles_out = []
    total_neto = 0.0
    for d in planilla.detalles:
        neto = d.sueldo_base - d.monto_descuento_faltas - d.monto_descuento_tardanzas - d.otros_descuentos
        total_neto += neto
        detalles_out.append(
            schemas.DetallePlanillaOut(
                id=d.id,
                planilla_id=d.planilla_id,
                colaborador_id=d.colaborador_id,
                sueldo_base=d.sueldo_base,
                dias_falta=d.dias_falta,
                monto_descuento_faltas=d.monto_descuento_faltas,
                minutos_tardanza=d.minutos_tardanza,
                monto_descuento_tardanzas=d.monto_descuento_tardanzas,
                otros_descuentos=d.otros_descuentos,
                observaciones=d.observaciones,
                monto_neto=round(neto, 2),
            )
        )
    return schemas.PlanillaDetalle(
        id=planilla.id,
        negocio_id=planilla.negocio_id,
        fecha_inicio=planilla.fecha_inicio,
        fecha_fin=planilla.fecha_fin,
        estado=planilla.estado,
        fecha_pago=planilla.fecha_pago,
        detalles=detalles_out,
        total_neto=round(total_neto, 2),
    )


@router.get("/", response_model=list[schemas.PlanillaOut])
def listar_planillas(negocio_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Planilla)
    if negocio_id is not None:
        query = query.filter(models.Planilla.negocio_id == negocio_id)
    return query.order_by(models.Planilla.fecha_inicio.desc()).all()


@router.post("/generar", response_model=schemas.PlanillaDetalle)
def generar_planilla(
    data: schemas.PlanillaGenerar,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Genera el borrador de la planilla semanal: por cada colaborador
    activo con sueldo asignado, calcula automáticamente sus faltas
    (días laborables sin asistencia registrada, lunes a sábado) y
    tardanzas (minutos de diferencia contra su hora de entrada
    esperada, si la tiene configurada). El admin revisa y puede ajustar
    antes de pagar — nada se descuenta todavía en este paso.
    """
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if data.fecha_fin < data.fecha_inicio:
        raise HTTPException(status_code=400, detail="La fecha de fin no puede ser anterior a la de inicio")

    planilla = models.Planilla(negocio_id=data.negocio_id, fecha_inicio=data.fecha_inicio, fecha_fin=data.fecha_fin)
    db.add(planilla)
    db.flush()

    dias_del_periodo = (data.fecha_fin - data.fecha_inicio).days + 1
    dias_laborables = [
        data.fecha_inicio + timedelta(days=i)
        for i in range(dias_del_periodo)
        if (data.fecha_inicio + timedelta(days=i)).weekday() != 6  # excluye domingo
    ]

    colaboradores = (
        db.query(models.Colaborador)
        .filter(
            models.Colaborador.negocio_id == data.negocio_id,
            models.Colaborador.activo.is_(True),
            models.Colaborador.sueldo_semanal.isnot(None),
        )
        .all()
    )

    for colaborador in colaboradores:
        asistencias = (
            db.query(models.Asistencia)
            .filter(
                models.Asistencia.colaborador_id == colaborador.id,
                models.Asistencia.fecha >= data.fecha_inicio,
                models.Asistencia.fecha <= data.fecha_fin,
            )
            .all()
        )
        dias_con_asistencia = {a.fecha for a in asistencias}
        dias_falta = sum(1 for dia in dias_laborables if dia not in dias_con_asistencia)

        minutos_tardanza = 0
        hora_esperada = None
        if colaborador.hora_entrada_esperada:
            try:
                hh, mm = colaborador.hora_entrada_esperada.split(":")
                hora_esperada = hora_tipo(int(hh), int(mm))
            except (ValueError, AttributeError):
                hora_esperada = None

        if hora_esperada:
            esperada_min = hora_esperada.hour * 60 + hora_esperada.minute
            for a in asistencias:
                hora_real = a.hora_entrada.time()
                real_min = hora_real.hour * 60 + hora_real.minute
                if real_min > esperada_min:
                    minutos_tardanza += real_min - esperada_min

        valor_dia = _valor_dia(colaborador.sueldo_semanal)
        valor_minuto = _valor_minuto(colaborador.sueldo_semanal)

        detalle = models.DetallePlanilla(
            planilla_id=planilla.id,
            colaborador_id=colaborador.id,
            sueldo_base=colaborador.sueldo_semanal,
            dias_falta=dias_falta,
            monto_descuento_faltas=round(dias_falta * valor_dia, 2),
            minutos_tardanza=minutos_tardanza,
            monto_descuento_tardanzas=round(minutos_tardanza * valor_minuto, 2),
        )
        db.add(detalle)

    db.commit()
    db.refresh(planilla)
    return _a_detalle(planilla)


@router.get("/{planilla_id}", response_model=schemas.PlanillaDetalle)
def obtener_planilla(planilla_id: int, db: Session = Depends(get_db)):
    planilla = db.query(models.Planilla).get(planilla_id)
    if not planilla:
        raise HTTPException(status_code=404, detail="Planilla no encontrada")
    return _a_detalle(planilla)


@router.patch("/{planilla_id}/detalles/{detalle_id}", response_model=schemas.PlanillaDetalle)
def ajustar_detalle(
    planilla_id: int,
    detalle_id: int,
    data: schemas.DetallePlanillaUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """Ajusta un detalle antes de pagar (ej. agregar otro descuento). Solo administradores."""
    planilla = db.query(models.Planilla).get(planilla_id)
    if not planilla:
        raise HTTPException(status_code=404, detail="Planilla no encontrada")
    if planilla.estado == "pagada":
        raise HTTPException(status_code=400, detail="Esta planilla ya fue pagada, no se puede editar")

    detalle = (
        db.query(models.DetallePlanilla)
        .filter(models.DetallePlanilla.id == detalle_id, models.DetallePlanilla.planilla_id == planilla_id)
        .first()
    )
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(detalle, campo, valor)

    db.commit()
    db.refresh(planilla)
    return _a_detalle(planilla)


@router.post("/{planilla_id}/pagar", response_model=schemas.PlanillaDetalle)
def pagar_planilla(
    planilla_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Marca la planilla como pagada y genera el egreso en finanzas por el
    total neto (ya con los descuentos aplicados). Una vez pagada, ya no
    se puede editar. Solo administradores.
    """
    planilla = db.query(models.Planilla).get(planilla_id)
    if not planilla:
        raise HTTPException(status_code=404, detail="Planilla no encontrada")
    if planilla.estado == "pagada":
        raise HTTPException(status_code=400, detail="Esta planilla ya fue pagada")
    if not planilla.detalles:
        raise HTTPException(status_code=400, detail="La planilla no tiene colaboradores — genera el borrador primero")

    total_neto = sum(
        d.sueldo_base - d.monto_descuento_faltas - d.monto_descuento_tardanzas - d.otros_descuentos
        for d in planilla.detalles
    )

    planilla.estado = "pagada"
    planilla.fecha_pago = ahora_peru()

    db.add(
        models.Egreso(
            negocio_id=planilla.negocio_id,
            categoria="planilla",
            monto=round(total_neto, 2),
            descripcion=f"Planilla {planilla.fecha_inicio} a {planilla.fecha_fin}",
            fecha=planilla.fecha_pago,
        )
    )

    db.commit()
    db.refresh(planilla)
    return _a_detalle(planilla)


@router.delete("/{planilla_id}", status_code=204)
def eliminar_planilla(
    planilla_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """Elimina un borrador de planilla (no se puede eliminar una ya pagada). Solo administradores."""
    planilla = db.query(models.Planilla).get(planilla_id)
    if not planilla:
        raise HTTPException(status_code=404, detail="Planilla no encontrada")
    if planilla.estado == "pagada":
        raise HTTPException(status_code=400, detail="No se puede eliminar una planilla ya pagada")
    db.delete(planilla)
    db.commit()
    return None
