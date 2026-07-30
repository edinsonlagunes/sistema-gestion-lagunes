from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual, requerir_admin
from app.database import get_db

router = APIRouter(prefix="/proyectos", tags=["Proyectos (Constructora)"], dependencies=[Depends(obtener_usuario_actual)])

ESTADOS_VALIDOS = {"cotizacion", "en_proceso", "entregado", "cancelado"}


def _a_detalle(proyecto: models.Proyecto) -> schemas.ProyectoDetalle:
    total = sum(o.subtotal for o in proyecto.ordenes)
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
        total_facturado=total,
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
    un expediente, un estudio de suelos, un ploteo...). Igual que en el
    POS: calcula el subtotal con el precio vigente del catálogo, genera
    el ingreso en finanzas, y descuenta el insumo vinculado si lo tiene
    (por ejemplo, papel y tinta de plotter).
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
    db.flush()  # asigna orden.id, para poder vincular el ingreso

    if servicio.insumo_id and servicio.consumo_insumo_por_unidad:
        insumo = db.query(models.Insumo).get(servicio.insumo_id)
        if insumo:
            insumo.stock_actual -= servicio.consumo_insumo_por_unidad * data.cantidad

    db.add(
        models.Ingreso(
            negocio_id=proyecto.negocio_id,
            monto=subtotal,
            medio_pago="por cobrar",
            descripcion=f"Proyecto '{proyecto.nombre}' - {servicio.nombre}",
            orden_servicio_id=orden.id,
        )
    )

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
    subtotal con el precio que se usó en su momento, ajusta el ingreso
    correspondiente en finanzas, y corrige el stock del insumo vinculado
    por la diferencia. Solo administradores.
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

    ingreso = (
        db.query(models.Ingreso).filter(models.Ingreso.orden_servicio_id == orden.id).first()
    )
    if ingreso:
        ingreso.monto = orden.subtotal

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
    revierte el ingreso en finanzas y devuelve el insumo consumido al
    stock. Solo administradores.
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

    db.query(models.Ingreso).filter(models.Ingreso.orden_servicio_id == orden.id).delete()
    db.delete(orden)
    db.commit()

    proyecto = db.query(models.Proyecto).get(proyecto_id)
    return _a_detalle(proyecto)
