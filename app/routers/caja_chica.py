from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db
from app.permisos import requerir_permiso
from app.zona_horaria import ahora_peru

router = APIRouter(prefix="/caja-chica", tags=["Caja chica"], dependencies=[Depends(obtener_usuario_actual)])

TIPOS_VALIDOS = {"gasto", "reposicion"}


def _saldo(caja: models.CajaChica) -> float:
    saldo = caja.monto_fondo
    for m in caja.movimientos:
        saldo += m.monto if m.tipo == "reposicion" else -m.monto
    return saldo


def _a_detalle(caja: models.CajaChica) -> schemas.CajaChicaDetalle:
    return schemas.CajaChicaDetalle(
        id=caja.id,
        negocio_id=caja.negocio_id,
        nombre=caja.nombre,
        monto_fondo=caja.monto_fondo,
        saldo_actual=_saldo(caja),
        movimientos=caja.movimientos,
    )


@router.get("/", response_model=list[schemas.CajaChicaOut])
def listar_cajas(
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("caja_chica", "ver")),
):
    query = db.query(models.CajaChica)
    if negocio_id is not None:
        query = query.filter(models.CajaChica.negocio_id == negocio_id)
    return query.all()


@router.post("/", response_model=schemas.CajaChicaOut)
def crear_caja(
    data: schemas.CajaChicaCreate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("caja_chica", "editar")),
):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    caja = models.CajaChica(**data.model_dump())
    db.add(caja)
    db.commit()
    db.refresh(caja)
    return caja


@router.get("/{caja_id}", response_model=schemas.CajaChicaDetalle)
def obtener_caja(
    caja_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("caja_chica", "ver")),
):
    caja = db.query(models.CajaChica).get(caja_id)
    if not caja:
        raise HTTPException(status_code=404, detail="Caja chica no encontrada")
    return _a_detalle(caja)


@router.post("/{caja_id}/movimientos", response_model=schemas.CajaChicaDetalle)
def registrar_movimiento(
    caja_id: int,
    data: schemas.MovimientoCajaChicaCreate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("caja_chica", "editar")),
):
    """
    Registra un gasto menor (genera egreso real en finanzas, con
    categoría "caja_chica") o una reposición de fondo (solo repone el
    saldo disponible, no es un gasto nuevo — el gasto ya se contó cuando
    ocurrió). Exige permiso de Caja chica.
    """
    caja = db.query(models.CajaChica).get(caja_id)
    if not caja:
        raise HTTPException(status_code=404, detail="Caja chica no encontrada")
    if data.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Usa uno de: {sorted(TIPOS_VALIDOS)}")

    fecha = data.fecha or ahora_peru()
    movimiento = models.MovimientoCajaChica(
        caja_chica_id=caja.id,
        tipo=data.tipo,
        monto=data.monto,
        categoria=data.categoria,
        descripcion=data.descripcion,
        comprobante=data.comprobante,
        colaborador_id=data.colaborador_id,
        fecha=fecha,
    )
    db.add(movimiento)
    db.flush()

    if data.tipo == "gasto":
        egreso = models.Egreso(
            negocio_id=caja.negocio_id,
            categoria="caja_chica",
            monto=data.monto,
            descripcion=f"{caja.nombre} - {data.descripcion or data.categoria or 'gasto menor'}",
            fecha=fecha,
        )
        db.add(egreso)
        db.flush()
        movimiento.egreso_id = egreso.id

    db.commit()
    db.refresh(caja)
    return _a_detalle(caja)


@router.delete("/{caja_id}/movimientos/{movimiento_id}", response_model=schemas.CajaChicaDetalle)
def eliminar_movimiento(
    caja_id: int,
    movimiento_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("caja_chica", "editar")),
):
    """Quita un movimiento registrado por error, junto con su egreso si era un gasto. Exige permiso de Caja chica."""
    movimiento = (
        db.query(models.MovimientoCajaChica)
        .filter(models.MovimientoCajaChica.id == movimiento_id, models.MovimientoCajaChica.caja_chica_id == caja_id)
        .first()
    )
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")

    if movimiento.egreso_id:
        db.query(models.Egreso).filter(models.Egreso.id == movimiento.egreso_id).delete()

    db.delete(movimiento)
    db.commit()
    caja = db.query(models.CajaChica).get(caja_id)
    return _a_detalle(caja)
