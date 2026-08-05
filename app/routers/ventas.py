from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual, requerir_admin
from app.database import get_db

router = APIRouter(prefix="/ventas", tags=["Ventas (POS)"], dependencies=[Depends(obtener_usuario_actual)])


@router.get("/", response_model=list[schemas.Venta])
def listar_ventas(
    negocio_id: int | None = None,
    caja_sesion_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Venta)
    if negocio_id is not None:
        query = query.filter(models.Venta.negocio_id == negocio_id)
    if caja_sesion_id is not None:
        query = query.filter(models.Venta.caja_sesion_id == caja_sesion_id)
    return query.order_by(models.Venta.fecha.desc()).all()


@router.post("/", response_model=schemas.Venta)
def registrar_venta(data: schemas.VentaCreate, db: Session = Depends(get_db)):
    """
    Registra una venta con uno o más ítems del catálogo.

    En una sola operación:
    1. Calcula el total a partir del precio vigente de cada servicio.
    2. Genera el ingreso correspondiente en finanzas.
    3. Descuenta el stock de cualquier insumo vinculado a los servicios vendidos
       (por ejemplo, "Impresión A4 B/N" descuenta hojas de papel bond).
    Requiere una caja abierta para el negocio.
    """
    if not data.items:
        raise HTTPException(status_code=400, detail="La venta necesita al menos un ítem")

    caja_abierta = (
        db.query(models.CajaSesion)
        .filter(models.CajaSesion.negocio_id == data.negocio_id, models.CajaSesion.estado == "abierta")
        .first()
    )
    if not caja_abierta:
        raise HTTPException(status_code=400, detail="Debes abrir la caja antes de registrar ventas")

    venta = models.Venta(
        negocio_id=data.negocio_id,
        caja_sesion_id=caja_abierta.id,
        colaborador_id=data.colaborador_id,
        cliente=data.cliente,
        medio_pago=data.medio_pago,
        total=0,
    )
    db.add(venta)
    db.flush()  # asigna venta.id sin cerrar la transacción

    total = 0.0
    for item in data.items:
        servicio = db.query(models.Servicio).get(item.servicio_id)
        if not servicio or not servicio.activo:
            raise HTTPException(status_code=404, detail=f"Servicio {item.servicio_id} no encontrado")

        subtotal = servicio.precio_unitario * item.cantidad
        total += subtotal

        db.add(
            models.VentaItem(
                venta_id=venta.id,
                servicio_id=servicio.id,
                cantidad=item.cantidad,
                precio_unitario=servicio.precio_unitario,
                subtotal=subtotal,
            )
        )

        if servicio.insumo_id and servicio.consumo_insumo_por_unidad:
            insumo = db.query(models.Insumo).get(servicio.insumo_id)
            if insumo:
                insumo.stock_actual -= servicio.consumo_insumo_por_unidad * item.cantidad

    venta.total = total
    db.add(
        models.Ingreso(
            negocio_id=data.negocio_id,
            monto=total,
            medio_pago=data.medio_pago,
            descripcion=f"Venta #{venta.id}" + (f" - {data.cliente}" if data.cliente else ""),
            venta_id=venta.id,
            tipo_comprobante=data.tipo_comprobante,
        )
    )

    db.commit()
    db.refresh(venta)
    return venta


@router.delete("/{venta_id}", status_code=204)
def eliminar_venta(
    venta_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """
    Quita una venta registrada por error: revierte el ingreso que había
    generado y devuelve al stock cualquier insumo que se hubiera
    descontado. Solo administradores.
    """
    venta = db.query(models.Venta).get(venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    for item in venta.items:
        servicio = db.query(models.Servicio).get(item.servicio_id)
        if servicio and servicio.insumo_id and servicio.consumo_insumo_por_unidad:
            insumo = db.query(models.Insumo).get(servicio.insumo_id)
            if insumo:
                insumo.stock_actual += servicio.consumo_insumo_por_unidad * item.cantidad

    # Ventas creadas antes de que existiera el vínculo venta_id no lo tienen
    # guardado — como respaldo, se busca también por su descripción exacta.
    db.query(models.Ingreso).filter(
        (models.Ingreso.venta_id == venta.id)
        | (
            (models.Ingreso.venta_id.is_(None))
            & (models.Ingreso.negocio_id == venta.negocio_id)
            & (models.Ingreso.descripcion.like(f"Venta #{venta.id} -%") | (models.Ingreso.descripcion == f"Venta #{venta.id}"))
        )
    ).delete(synchronize_session=False)

    db.delete(venta)
    db.commit()
    return None
