from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual, requerir_admin
from app.database import get_db

router = APIRouter(prefix="/proyectos", tags=["Proyectos (Constructora)"], dependencies=[Depends(obtener_usuario_actual)])

ESTADOS_VALIDOS = {"cotizacion", "en_proceso", "entregado", "cancelado"}


def _a_detalle(proyecto: models.Proyecto) -> schemas.ProyectoDetalle:
    total_facturado = sum(o.subtotal for o in proyecto.ordenes)
    total_pagado = sum(p.monto for p in proyecto.pagos)
    return schemas.ProyectoDetalle(
        id=proyecto.id,
        negocio_id=proyecto.negocio_id,
        cliente_id=proyecto.cliente_id,
        nombre=proyecto.nombre,
        tipo_proyecto=proyecto.tipo_proyecto,
        estado=proyecto.estado,
        fecha_inicio=proyecto.fecha_inicio,
        fecha_entrega_estimada=proyecto.fecha_entrega_estimada,
        ordenes=proyecto.ordenes,
        pagos=proyecto.pagos,
        total_facturado=total_facturado,
        total_pagado=total_pagado,
        saldo_pendiente=total_facturado - total_pagado,
    )


@router.get("/", response_model=list[schemas.Proyecto])
def listar_proyectos(
    negocio_id: int | None = None,
    cliente_id: int | None = None,
    estado: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Proyecto)
    if negocio_id is not None:
        query = query.filter(models.Proyecto.negocio_id == negocio_id)
    if cliente_id is not None:
        query = query.filter(models.Proyecto.cliente_id == cliente_id)
    if estado is not None:
        query = query.filter(models.Proyecto.estado == estado)
    return query.order_by(models.Proyecto.fecha_inicio.desc()).all()


@router.post("/", response_model=schemas.Proyecto)
def crear_proyecto(data: schemas.ProyectoCreate, db: Session = Depends(get_db)):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if not db.query(models.Cliente).get(data.cliente_id):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if data.estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Usa uno de: {sorted(ESTADOS_VALIDOS)}")

    proyecto = models.Proyecto(**data.model_dump())
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)
    return proyecto


@router.get("/resumen-pagos", response_model=list[schemas.ResumenPagoProyecto])
def resumen_pagos(negocio_id: int | None = None, db: Session = Depends(get_db)):
    """
    Para el Dashboard: por cada proyecto, cuánto se ha facturado, cuánto
    se ha cobrado, cuánto falta, y cuándo fue el último pago (el adelanto,
    si todavía no hay más pagos). Solo incluye proyectos con saldo
    pendiente, ordenados del que más debe al que menos.
    """
    query = db.query(models.Proyecto)
    if negocio_id is not None:
        query = query.filter(models.Proyecto.negocio_id == negocio_id)
    proyectos = query.all()

    resultado = []
    for p in proyectos:
        total_facturado = sum(o.subtotal for o in p.ordenes)
        total_pagado = sum(pago.monto for pago in p.pagos)
        saldo = total_facturado - total_pagado
        if saldo <= 0:
            continue

        ultimo_pago = max(p.pagos, key=lambda pago: pago.fecha_pago) if p.pagos else None
        resultado.append(
            schemas.ResumenPagoProyecto(
                proyecto_id=p.id,
                nombre=p.nombre,
                tipo_proyecto=p.tipo_proyecto,
                total_facturado=total_facturado,
                total_pagado=total_pagado,
                saldo_pendiente=saldo,
                ultimo_pago_monto=ultimo_pago.monto if ultimo_pago else None,
                ultimo_pago_fecha=ultimo_pago.fecha_pago if ultimo_pago else None,
            )
        )

    resultado.sort(key=lambda r: r.saldo_pendiente, reverse=True)
    return resultado


@router.get("/{proyecto_id}", response_model=schemas.ProyectoDetalle)
def obtener_proyecto(proyecto_id: int, db: Session = Depends(get_db)):
    proyecto = db.query(models.Proyecto).get(proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return _a_detalle(proyecto)


@router.patch("/{proyecto_id}/estado", response_model=schemas.Proyecto)
def cambiar_estado(proyecto_id: int, data: schemas.ProyectoEstadoUpdate, db: Session = Depends(get_db)):
    proyecto = db.query(models.Proyecto).get(proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if data.estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Usa uno de: {sorted(ESTADOS_VALIDOS)}")

    proyecto.estado = data.estado
    db.commit()
    db.refresh(proyecto)
    return proyecto


@router.patch("/{proyecto_id}", response_model=schemas.Proyecto)
def actualizar_proyecto(
    proyecto_id: int,
    data: schemas.ProyectoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Editar los datos generales del proyecto (nombre, tipo, cliente, fecha
    estimada de entrega). Solo un administrador puede hacerlo — el estado
    (cotización/en proceso/etc.) se sigue manejando aparte, con
    PATCH /proyectos/{id}/estado.
    """
    proyecto = db.query(models.Proyecto).get(proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    datos = data.model_dump(exclude_unset=True)
    if "cliente_id" in datos and not db.query(models.Cliente).get(datos["cliente_id"]):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    for campo, valor in datos.items():
        setattr(proyecto, campo, valor)

    db.commit()
    db.refresh(proyecto)
    return proyecto


@router.post("/{proyecto_id}/ordenes", response_model=schemas.ProyectoDetalle)
def registrar_orden_servicio(
    proyecto_id: int, data: schemas.OrdenServicioCreate, db: Session = Depends(get_db)
):
    """
    Registra un servicio técnico entregado dentro del proyecto (un plano,
    un expediente, un estudio de suelos, un ploteo...). Calcula el
    subtotal con el precio vigente del catálogo (eso es lo FACTURADO) y
    descuenta el insumo vinculado si lo tiene. NO genera ingreso — eso
    solo pasa cuando se registra un pago real (ver /pagos), para no
    contar como cobrado algo que todavía no llegó.
    """
    proyecto = db.query(models.Proyecto).get(proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    servicio = db.query(models.Servicio).get(data.servicio_id)
    if not servicio or not servicio.activo:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    if not db.query(models.Colaborador).get(data.colaborador_id):
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")

    subtotal = servicio.precio_unitario * data.cantidad

    orden = models.OrdenServicio(
        proyecto_id=proyecto.id,
        servicio_id=servicio.id,
        colaborador_id=data.colaborador_id,
        cantidad=data.cantidad,
        precio_unitario=servicio.precio_unitario,
        subtotal=subtotal,
    )
    db.add(orden)

    if servicio.insumo_id and servicio.consumo_insumo_por_unidad:
        insumo = db.query(models.Insumo).get(servicio.insumo_id)
        if insumo:
            insumo.stock_actual -= servicio.consumo_insumo_por_unidad * data.cantidad

    db.commit()
    db.refresh(proyecto)
    return _a_detalle(proyecto)


@router.patch("/{proyecto_id}/ordenes/{orden_id}", response_model=schemas.ProyectoDetalle)
def actualizar_orden_servicio(
    proyecto_id: int,
    orden_id: int,
    data: schemas.OrdenServicioUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Corrige la cantidad de un servicio ya registrado en el proyecto (por
    ejemplo, si se anotaron mal los m² de un ploteo). Recalcula el
    subtotal (lo facturado) con el precio que se usó en su momento, y
    corrige el stock del insumo vinculado por la diferencia. No toca
    ingresos — esos van aparte, ligados a los pagos reales. Solo
    administradores.
    """
    orden = (
        db.query(models.OrdenServicio)
        .filter(models.OrdenServicio.id == orden_id, models.OrdenServicio.proyecto_id == proyecto_id)
        .first()
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")

    cantidad_anterior = orden.cantidad
    diferencia = data.cantidad - cantidad_anterior

    orden.cantidad = data.cantidad
    orden.subtotal = orden.precio_unitario * data.cantidad

    servicio = db.query(models.Servicio).get(orden.servicio_id)
    if servicio and servicio.insumo_id and servicio.consumo_insumo_por_unidad and diferencia != 0:
        insumo = db.query(models.Insumo).get(servicio.insumo_id)
        if insumo:
            insumo.stock_actual -= servicio.consumo_insumo_por_unidad * diferencia

    db.commit()
    proyecto = db.query(models.Proyecto).get(proyecto_id)
    return _a_detalle(proyecto)


@router.delete("/{proyecto_id}/ordenes/{orden_id}", response_model=schemas.ProyectoDetalle)
def eliminar_orden_servicio(
    proyecto_id: int,
    orden_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Quita un servicio que se había registrado por error en el proyecto:
    baja lo facturado y devuelve el insumo consumido al stock. No toca
    ingresos. Solo administradores.
    """
    orden = (
        db.query(models.OrdenServicio)
        .filter(models.OrdenServicio.id == orden_id, models.OrdenServicio.proyecto_id == proyecto_id)
        .first()
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")

    servicio = db.query(models.Servicio).get(orden.servicio_id)
    if servicio and servicio.insumo_id and servicio.consumo_insumo_por_unidad:
        insumo = db.query(models.Insumo).get(servicio.insumo_id)
        if insumo:
            insumo.stock_actual += servicio.consumo_insumo_por_unidad * orden.cantidad

    db.delete(orden)
    db.commit()

    proyecto = db.query(models.Proyecto).get(proyecto_id)
    return _a_detalle(proyecto)


@router.post("/{proyecto_id}/pagos", response_model=schemas.ProyectoDetalle)
def registrar_pago(
    proyecto_id: int,
    data: schemas.PagoProyectoCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Registra un pago recibido contra el proyecto — el adelanto inicial,
    una cuota, o el pago final. Esto SÍ genera el ingreso en finanzas
    (por el monto realmente cobrado, con su fecha y medio de pago real)
    — a diferencia de facturar una orden, que no mueve caja todavía.
    Solo administradores.
    """
    proyecto = db.query(models.Proyecto).get(proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    pago = models.PagoProyecto(
        proyecto_id=proyecto.id,
        monto=data.monto,
        fecha_pago=data.fecha_pago or datetime.utcnow(),
        tipo=data.tipo,
        medio_pago=data.medio_pago,
        descripcion=data.descripcion,
    )
    db.add(pago)
    db.flush()  # asigna pago.id, para poder vincular el ingreso

    etiquetas_tipo = {"adelanto": "Adelanto", "cuota": "Cuota", "pago_final": "Pago final", "otro": "Pago"}
    db.add(
        models.Ingreso(
            negocio_id=proyecto.negocio_id,
            monto=pago.monto,
            medio_pago=pago.medio_pago,
            descripcion=f"{etiquetas_tipo.get(pago.tipo, 'Pago')} - Proyecto '{proyecto.nombre}'",
            fecha=pago.fecha_pago,
            pago_proyecto_id=pago.id,
        )
    )

    db.commit()
    db.refresh(proyecto)
    return _a_detalle(proyecto)


@router.patch("/{proyecto_id}/pagos/{pago_id}", response_model=schemas.ProyectoDetalle)
def actualizar_pago(
    proyecto_id: int,
    pago_id: int,
    data: schemas.PagoProyectoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """Corrige un pago ya registrado (monto, fecha, tipo) y su ingreso vinculado. Solo administradores."""
    pago = (
        db.query(models.PagoProyecto)
        .filter(models.PagoProyecto.id == pago_id, models.PagoProyecto.proyecto_id == proyecto_id)
        .first()
    )
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(pago, campo, valor)

    ingreso = db.query(models.Ingreso).filter(models.Ingreso.pago_proyecto_id == pago.id).first()
    if ingreso:
        ingreso.monto = pago.monto
        ingreso.fecha = pago.fecha_pago
        ingreso.medio_pago = pago.medio_pago

    db.commit()
    proyecto = db.query(models.Proyecto).get(proyecto_id)
    return _a_detalle(proyecto)


@router.delete("/{proyecto_id}/pagos/{pago_id}", response_model=schemas.ProyectoDetalle)
def eliminar_pago(
    proyecto_id: int,
    pago_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """Quita un pago registrado por error, junto con el ingreso que había generado. Solo administradores."""
    pago = (
        db.query(models.PagoProyecto)
        .filter(models.PagoProyecto.id == pago_id, models.PagoProyecto.proyecto_id == proyecto_id)
        .first()
    )
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    db.query(models.Ingreso).filter(models.Ingreso.pago_proyecto_id == pago.id).delete()
    db.delete(pago)
    db.commit()
    proyecto = db.query(models.Proyecto).get(proyecto_id)
    return _a_detalle(proyecto)
