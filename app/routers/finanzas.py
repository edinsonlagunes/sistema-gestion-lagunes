import calendar
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual, requerir_admin
from app.database import get_db
from app.zona_horaria import ahora_peru

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
    """Balance por negocio: el que ya usan todos en el Dashboard."""
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


def _rango_del_dia(dia: date) -> tuple[datetime, datetime]:
    return datetime.combine(dia, time.min), datetime.combine(dia, time.max)


@router.get("/movimientos-dia", response_model=schemas.MovimientosDiaResumen)
def movimientos_dia(
    fecha: date | None = None,
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Todo el movimiento de caja de un día — cada ingreso y egreso, uno por
    uno, con el total y el balance. A diferencia de /resumen (que ve
    cualquier usuario logueado), esta vista con el detalle completo es
    exclusiva de administradores.
    """
    dia = fecha or ahora_peru().date()
    inicio, fin = _rango_del_dia(dia)

    query_ingresos = db.query(models.Ingreso).filter(models.Ingreso.fecha >= inicio, models.Ingreso.fecha <= fin)
    query_egresos = db.query(models.Egreso).filter(models.Egreso.fecha >= inicio, models.Egreso.fecha <= fin)
    if negocio_id is not None:
        query_ingresos = query_ingresos.filter(models.Ingreso.negocio_id == negocio_id)
        query_egresos = query_egresos.filter(models.Egreso.negocio_id == negocio_id)

    ingresos = query_ingresos.all()
    egresos = query_egresos.all()

    movimientos = [
        schemas.MovimientoFinanciero(
            tipo="ingreso",
            id=i.id,
            negocio_id=i.negocio_id,
            monto=i.monto,
            medio_pago=i.medio_pago,
            descripcion=i.descripcion,
            fecha=i.fecha,
        )
        for i in ingresos
    ] + [
        schemas.MovimientoFinanciero(
            tipo="egreso",
            id=e.id,
            negocio_id=e.negocio_id,
            monto=e.monto,
            categoria=e.categoria,
            descripcion=e.descripcion,
            fecha=e.fecha,
        )
        for e in egresos
    ]
    movimientos.sort(key=lambda m: m.fecha, reverse=True)

    total_ingresos = sum(i.monto for i in ingresos)
    total_egresos = sum(e.monto for e in egresos)

    return schemas.MovimientosDiaResumen(
        fecha=dia,
        total_ingresos=total_ingresos,
        total_egresos=total_egresos,
        balance=total_ingresos - total_egresos,
        movimientos=movimientos,
    )


@router.get("/conciliacion-diaria", response_model=schemas.ConciliacionDiaria)
def conciliacion_diaria(
    fecha: date | None = None,
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
):
    """
    El día agrupado por colaborador (con su puesto de trabajo, si tiene
    uno asignado): cuánto vendió, cuántas ventas hizo, y cuántas
    impresiones se registraron a su nombre — para que el encargado de
    caja haga el cuadre con cada persona, stand por stand.
    """
    dia = fecha or ahora_peru().date()
    inicio, fin = _rango_del_dia(dia)

    query_ventas = db.query(models.Venta).filter(models.Venta.fecha >= inicio, models.Venta.fecha <= fin)
    if negocio_id is not None:
        query_ventas = query_ventas.filter(models.Venta.negocio_id == negocio_id)
    ventas = query_ventas.all()

    query_impresiones = db.query(models.RegistroImpresion).filter(
        models.RegistroImpresion.fecha >= inicio, models.RegistroImpresion.fecha <= fin
    )
    if negocio_id is not None:
        query_impresiones = query_impresiones.filter(models.RegistroImpresion.negocio_id == negocio_id)
    impresiones = query_impresiones.all()

    puestos_por_colaborador: dict[int, str] = {}
    query_puestos = db.query(models.PuestoTrabajo)
    if negocio_id is not None:
        query_puestos = query_puestos.filter(models.PuestoTrabajo.negocio_id == negocio_id)
    for puesto in query_puestos.all():
        if puesto.colaborador_id:
            puestos_por_colaborador[puesto.colaborador_id] = puesto.nombre

    acumulado: dict[int, dict] = {}

    for v in ventas:
        datos = acumulado.setdefault(
            v.colaborador_id, {"total_ventas": 0.0, "cantidad_ventas": 0, "total_impresiones": 0.0}
        )
        datos["total_ventas"] += v.total
        datos["cantidad_ventas"] += 1

    for r in impresiones:
        if r.colaborador_id is None:
            continue
        datos = acumulado.setdefault(
            r.colaborador_id, {"total_ventas": 0.0, "cantidad_ventas": 0, "total_impresiones": 0.0}
        )
        datos["total_impresiones"] += r.cantidad

    resultado = []
    for colaborador_id, datos in acumulado.items():
        colaborador = db.query(models.Colaborador).get(colaborador_id)
        resultado.append(
            schemas.ConciliacionColaborador(
                colaborador_id=colaborador_id,
                colaborador_nombre=colaborador.nombre if colaborador else f"Colaborador #{colaborador_id}",
                puesto_nombre=puestos_por_colaborador.get(colaborador_id),
                total_ventas=datos["total_ventas"],
                cantidad_ventas=datos["cantidad_ventas"],
                total_impresiones=datos["total_impresiones"],
            )
        )
    resultado.sort(key=lambda r: r.total_ventas, reverse=True)

    query_cajas = db.query(models.CajaSesion).filter(
        models.CajaSesion.fecha_apertura >= inicio, models.CajaSesion.fecha_apertura <= fin
    )
    if negocio_id is not None:
        query_cajas = query_cajas.filter(models.CajaSesion.negocio_id == negocio_id)

    return schemas.ConciliacionDiaria(fecha=dia, por_colaborador=resultado, cajas_del_dia=query_cajas.all())


@router.get("/reporte", response_model=schemas.ReporteBalance)
def reporte_balance(
    periodo: str = Query(..., pattern="^(diario|semanal|mensual)$"),
    fecha: date | None = None,
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Balance de ingresos/egresos para un periodo completo: el día, la
    semana (lunes a domingo) o el mes que contiene la fecha dada (o la
    de hoy, si no se especifica). Solo administradores.
    """
    referencia = fecha or ahora_peru().date()

    if periodo == "diario":
        desde = hasta = referencia
    elif periodo == "semanal":
        desde = referencia - timedelta(days=referencia.weekday())
        hasta = desde + timedelta(days=6)
    else:
        desde = referencia.replace(day=1)
        ultimo_dia = calendar.monthrange(referencia.year, referencia.month)[1]
        hasta = referencia.replace(day=ultimo_dia)

    inicio_dt = datetime.combine(desde, time.min)
    fin_dt = datetime.combine(hasta, time.max)

    query_ingresos = db.query(models.Ingreso).filter(models.Ingreso.fecha >= inicio_dt, models.Ingreso.fecha <= fin_dt)
    query_egresos = db.query(models.Egreso).filter(models.Egreso.fecha >= inicio_dt, models.Egreso.fecha <= fin_dt)
    if negocio_id is not None:
        query_ingresos = query_ingresos.filter(models.Ingreso.negocio_id == negocio_id)
        query_egresos = query_egresos.filter(models.Egreso.negocio_id == negocio_id)

    ingresos = query_ingresos.all()
    egresos = query_egresos.all()
    total_ingresos = sum(i.monto for i in ingresos)
    total_egresos = sum(e.monto for e in egresos)

    return schemas.ReporteBalance(
        periodo=periodo,
        fecha_desde=desde,
        fecha_hasta=hasta,
        total_ingresos=total_ingresos,
        total_egresos=total_egresos,
        balance=total_ingresos - total_egresos,
        cantidad_movimientos=len(ingresos) + len(egresos),
    )
