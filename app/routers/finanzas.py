import calendar
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.auditoria import registrar_auditoria
from app.auth import obtener_usuario_actual
from app.database import get_db
from app.permisos import requerir_permiso
from app.zona_horaria import ahora_peru

router = APIRouter(prefix="/finanzas", tags=["Finanzas"], dependencies=[Depends(obtener_usuario_actual)])


@router.get("/ingresos", response_model=list[schemas.Ingreso])
def listar_ingresos(
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("finanzas", "ver")),
):
    query = db.query(models.Ingreso)
    if negocio_id is not None:
        query = query.filter(models.Ingreso.negocio_id == negocio_id)
    return query.order_by(models.Ingreso.fecha.desc()).all()


@router.post("/ingresos", response_model=schemas.Ingreso)
def crear_ingreso(
    data: schemas.IngresoCreate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("finanzas", "editar")),
):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    ingreso = models.Ingreso(**data.model_dump())
    db.add(ingreso)
    db.flush()
    registrar_auditoria(
        db, _permiso, "crear", "ingreso", ingreso.id,
        f"S/ {ingreso.monto:.2f} - {ingreso.descripcion or 'sin descripción'}",
    )
    db.commit()
    db.refresh(ingreso)
    return ingreso


@router.get("/egresos", response_model=list[schemas.Egreso])
def listar_egresos(
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("finanzas", "ver")),
):
    query = db.query(models.Egreso)
    if negocio_id is not None:
        query = query.filter(models.Egreso.negocio_id == negocio_id)
    return query.order_by(models.Egreso.fecha.desc()).all()


@router.post("/egresos", response_model=schemas.Egreso)
def crear_egreso(
    data: schemas.EgresoCreate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("finanzas", "editar")),
):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if data.proyecto_id is not None and not db.query(models.Proyecto).get(data.proyecto_id):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    egreso = models.Egreso(**data.model_dump())
    db.add(egreso)
    db.flush()
    registrar_auditoria(
        db, _permiso, "crear", "egreso", egreso.id,
        f"S/ {egreso.monto:.2f} - {egreso.descripcion or egreso.categoria}",
    )
    db.commit()
    db.refresh(egreso)
    return egreso


@router.get("/resumen", response_model=list[schemas.ResumenNegocio])
def resumen(db: Session = Depends(get_db)):
    """
    Balance por negocio: el que ya usan todos en el Dashboard general.
    A propósito NO exige permiso de Finanzas — es el resumen que ve
    cualquier persona logueada en la pantalla principal.
    """
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
    _permiso: models.Usuario = Depends(requerir_permiso("finanzas", "ver")),
):
    """
    Todo el movimiento de caja de un día — cada ingreso y egreso, uno por
    uno, con el total y el balance. A diferencia de /resumen (que ve
    cualquier usuario logueado), esta vista con el detalle completo exige
    permiso de Finanzas.
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
            venta_id=i.venta_id,
            tipo_comprobante=i.tipo_comprobante,
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
            tipo_comprobante=e.tipo_comprobante,
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
    _permiso: models.Usuario = Depends(requerir_permiso("conciliacion", "ver")),
):
    """
    El día agrupado por colaborador (con su puesto de trabajo, si tiene
    uno asignado): cuánto vendió, cuántas ventas hizo, y cuántas
    impresiones se registraron a su nombre — para que el encargado de
    caja haga el cuadre con cada persona, stand por stand. Exige permiso
    de Conciliación.
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
            v.colaborador_id,
            {"total_ventas": 0.0, "cantidad_ventas": 0, "total_impresiones": 0.0, "total_impresiones_estimado": 0.0},
        )
        datos["total_ventas"] += v.total
        datos["cantidad_ventas"] += 1

    for r in impresiones:
        if r.colaborador_id is None:
            continue
        datos = acumulado.setdefault(
            r.colaborador_id,
            {"total_ventas": 0.0, "cantidad_ventas": 0, "total_impresiones": 0.0, "total_impresiones_estimado": 0.0},
        )
        datos["total_impresiones"] += r.cantidad
        servicio = (
            db.query(models.Servicio)
            .filter(
                models.Servicio.negocio_id == r.negocio_id,
                models.Servicio.categoria == r.tipo_trabajo,
                models.Servicio.tamano == r.tamano,
            )
            .first()
        )
        if servicio:
            datos["total_impresiones_estimado"] += servicio.precio_unitario * r.cantidad

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
                total_impresiones_estimado=datos["total_impresiones_estimado"],
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
    periodo: str = Query(..., pattern="^(diario|semanal|mensual|anual)$"),
    fecha: date | None = None,
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("finanzas", "ver")),
):
    """
    Balance de ingresos/egresos para un periodo completo: el día, la
    semana (lunes a domingo), el mes, o el año que contiene la fecha
    dada (o la de hoy, si no se especifica). Exige permiso de Finanzas.
    """
    referencia = fecha or ahora_peru().date()

    if periodo == "diario":
        desde = hasta = referencia
    elif periodo == "semanal":
        desde = referencia - timedelta(days=referencia.weekday())
        hasta = desde + timedelta(days=6)
    elif periodo == "mensual":
        desde = referencia.replace(day=1)
        ultimo_dia = calendar.monthrange(referencia.year, referencia.month)[1]
        hasta = referencia.replace(day=ultimo_dia)
    else:  # anual
        desde = referencia.replace(month=1, day=1)
        hasta = referencia.replace(month=12, day=31)

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


def _clave_periodo(fecha, agrupacion: str):
    d = fecha.date() if hasattr(fecha, "date") else fecha
    if agrupacion == "dia":
        return d.isoformat(), d, d
    if agrupacion == "semana":
        inicio = d - timedelta(days=d.weekday())
        fin = inicio + timedelta(days=6)
        iso_year, iso_week, _ = d.isocalendar()
        return f"{iso_year}-S{iso_week:02d}", inicio, fin
    if agrupacion == "mes":
        inicio = d.replace(day=1)
        fin = d.replace(day=calendar.monthrange(d.year, d.month)[1])
        return f"{d.year}-{d.month:02d}", inicio, fin
    # anio
    return str(d.year), date(d.year, 1, 1), date(d.year, 12, 31)


@router.get("/serie", response_model=list[schemas.PuntoSerieFinanciera])
def serie_financiera(
    agrupacion: str = Query(..., pattern="^(dia|semana|mes|anio)$"),
    negocio_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("finanzas", "ver")),
):
    """
    Ingresos, egresos, ventas del POS, y facturación/cobros de proyectos
    de la Constructora, agrupados por día, semana, mes o año — para
    tener el control de ingresos y egresos de toda la empresa a lo
    largo del tiempo, no solo de un periodo puntual. Exige permiso de
    Finanzas.
    """
    hoy = ahora_peru().date()
    if hasta is None:
        hasta = hoy
    if desde is None:
        if agrupacion == "dia":
            desde = hasta - timedelta(days=29)
        elif agrupacion == "semana":
            desde = hasta - timedelta(weeks=11)
        elif agrupacion == "mes":
            referencia = hasta.replace(day=1)
            for _ in range(11):
                referencia = (referencia - timedelta(days=1)).replace(day=1)
            desde = referencia
        else:  # anio
            desde = hasta.replace(year=hasta.year - 4, month=1, day=1)

    inicio_dt = datetime.combine(desde, time.min)
    fin_dt = datetime.combine(hasta, time.max)

    query_ingresos = db.query(models.Ingreso).filter(models.Ingreso.fecha >= inicio_dt, models.Ingreso.fecha <= fin_dt)
    query_egresos = db.query(models.Egreso).filter(models.Egreso.fecha >= inicio_dt, models.Egreso.fecha <= fin_dt)
    query_ventas = db.query(models.Venta).filter(models.Venta.fecha >= inicio_dt, models.Venta.fecha <= fin_dt)
    query_ordenes = (
        db.query(models.OrdenServicio)
        .join(models.Proyecto)
        .filter(models.OrdenServicio.fecha >= inicio_dt, models.OrdenServicio.fecha <= fin_dt)
    )
    query_pagos = (
        db.query(models.PagoProyecto)
        .join(models.Proyecto)
        .filter(models.PagoProyecto.fecha_pago >= inicio_dt, models.PagoProyecto.fecha_pago <= fin_dt)
    )
    if negocio_id is not None:
        query_ingresos = query_ingresos.filter(models.Ingreso.negocio_id == negocio_id)
        query_egresos = query_egresos.filter(models.Egreso.negocio_id == negocio_id)
        query_ventas = query_ventas.filter(models.Venta.negocio_id == negocio_id)
        query_ordenes = query_ordenes.filter(models.Proyecto.negocio_id == negocio_id)
        query_pagos = query_pagos.filter(models.Proyecto.negocio_id == negocio_id)

    buckets: dict[str, dict] = {}

    def bucket(fecha):
        clave, f_inicio, f_fin = _clave_periodo(fecha, agrupacion)
        if clave not in buckets:
            buckets[clave] = {
                "etiqueta": clave,
                "fecha_inicio": f_inicio,
                "fecha_fin": f_fin,
                "total_ingresos": 0.0,
                "total_egresos": 0.0,
                "ventas_cantidad": 0,
                "ventas_total": 0.0,
                "proyectos_facturado": 0.0,
                "proyectos_cobrado": 0.0,
            }
        return buckets[clave]

    for i in query_ingresos.all():
        bucket(i.fecha)["total_ingresos"] += i.monto
    for e in query_egresos.all():
        bucket(e.fecha)["total_egresos"] += e.monto
    for v in query_ventas.all():
        b = bucket(v.fecha)
        b["ventas_cantidad"] += 1
        b["ventas_total"] += v.total
    for o in query_ordenes.all():
        if o.fecha:
            bucket(o.fecha)["proyectos_facturado"] += o.subtotal
    for p in query_pagos.all():
        bucket(p.fecha_pago)["proyectos_cobrado"] += p.monto

    resultado = [
        schemas.PuntoSerieFinanciera(
            etiqueta=b["etiqueta"],
            fecha_inicio=b["fecha_inicio"],
            fecha_fin=b["fecha_fin"],
            total_ingresos=round(b["total_ingresos"], 2),
            total_egresos=round(b["total_egresos"], 2),
            balance=round(b["total_ingresos"] - b["total_egresos"], 2),
            ventas_cantidad=b["ventas_cantidad"],
            ventas_total=round(b["ventas_total"], 2),
            proyectos_facturado=round(b["proyectos_facturado"], 2),
            proyectos_cobrado=round(b["proyectos_cobrado"], 2),
        )
        for b in buckets.values()
    ]
    resultado.sort(key=lambda r: r.fecha_inicio)
    return resultado


@router.get("/comprobantes", response_model=list[schemas.ResumenComprobante])
def resumen_comprobantes(
    negocio_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("finanzas", "ver")),
):
    """
    Agrupa ingresos y egresos por tipo de comprobante (factura, boleta,
    sin comprobante...) — para saber cuánto de lo cobrado/pagado tiene
    respaldo formal. Sin fechas, considera todo el historial. Exige
    permiso de Finanzas.
    """
    query_ingresos = db.query(models.Ingreso)
    query_egresos = db.query(models.Egreso)
    if negocio_id is not None:
        query_ingresos = query_ingresos.filter(models.Ingreso.negocio_id == negocio_id)
        query_egresos = query_egresos.filter(models.Egreso.negocio_id == negocio_id)
    if desde is not None:
        inicio_dt = datetime.combine(desde, time.min)
        query_ingresos = query_ingresos.filter(models.Ingreso.fecha >= inicio_dt)
        query_egresos = query_egresos.filter(models.Egreso.fecha >= inicio_dt)
    if hasta is not None:
        fin_dt = datetime.combine(hasta, time.max)
        query_ingresos = query_ingresos.filter(models.Ingreso.fecha <= fin_dt)
        query_egresos = query_egresos.filter(models.Egreso.fecha <= fin_dt)

    acumulado: dict[str, dict] = {}

    def bucket(tipo):
        clave = tipo or "sin_especificar"
        if clave not in acumulado:
            acumulado[clave] = {"cantidad_ingresos": 0, "total_ingresos": 0.0, "cantidad_egresos": 0, "total_egresos": 0.0}
        return acumulado[clave]

    for i in query_ingresos.all():
        b = bucket(i.tipo_comprobante)
        b["cantidad_ingresos"] += 1
        b["total_ingresos"] += i.monto
    for e in query_egresos.all():
        b = bucket(e.tipo_comprobante)
        b["cantidad_egresos"] += 1
        b["total_egresos"] += e.monto

    resultado = [
        schemas.ResumenComprobante(
            tipo_comprobante=clave,
            cantidad_ingresos=b["cantidad_ingresos"],
            total_ingresos=round(b["total_ingresos"], 2),
            cantidad_egresos=b["cantidad_egresos"],
            total_egresos=round(b["total_egresos"], 2),
        )
        for clave, b in acumulado.items()
    ]
    resultado.sort(key=lambda r: r.total_ingresos + r.total_egresos, reverse=True)
    return resultado
