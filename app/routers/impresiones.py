import csv
import io
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db

router = APIRouter(
    prefix="/impresiones", tags=["Impresiones (Fase 5)"], dependencies=[Depends(obtener_usuario_actual)]
)

# Columnas que debe traer el CSV, en este orden u orden de encabezado libre
# (se lee por nombre de columna, no por posición):
#   fecha, colaborador, equipo, tipo_trabajo, tamano, cantidad
COLUMNAS_CSV_REQUERIDAS = {"fecha", "colaborador", "equipo", "tipo_trabajo", "cantidad"}

FORMATOS_FECHA = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"]


def _parsear_fecha(valor: str) -> datetime:
    valor = valor.strip()
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(valor, formato)
        except ValueError:
            continue
    raise ValueError(f"No se pudo interpretar la fecha '{valor}'")


def _buscar_colaborador_por_nombre(db: Session, negocio_id: int, nombre: str):
    if not nombre:
        return None
    return (
        db.query(models.Colaborador)
        .filter(
            models.Colaborador.negocio_id == negocio_id,
            models.Colaborador.nombre.ilike(nombre.strip()),
        )
        .first()
    )


@router.post("/", response_model=schemas.RegistroImpresion)
def registrar_impresion(data: schemas.RegistroImpresionCreate, db: Session = Depends(get_db)):
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if data.colaborador_id and not db.query(models.Colaborador).get(data.colaborador_id):
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")

    registro = models.RegistroImpresion(
        negocio_id=data.negocio_id,
        colaborador_id=data.colaborador_id,
        equipo=data.equipo,
        tipo_trabajo=data.tipo_trabajo,
        tamano=data.tamano,
        cantidad=data.cantidad,
        fecha=data.fecha or datetime.utcnow(),
        origen="manual",
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@router.post("/importar-csv", response_model=schemas.ImportarCSVResultado)
async def importar_csv(
    negocio_id: int,
    archivo: UploadFile,
    db: Session = Depends(get_db),
):
    """
    Importa en bloque el reporte exportado por el software de conteo
    (PaperCut, YSoft SafeQ, o cualquier otro). El CSV debe tener columnas:
    fecha, colaborador, equipo, tipo_trabajo, tamano (opcional), cantidad.

    Si el nombre del colaborador no coincide con ninguno registrado, la fila
    igual se guarda (para no perder el dato), pero sin vincular colaborador_id
    — queda disponible el nombre original tal cual venía en el archivo.
    """
    if not db.query(models.Negocio).get(negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    contenido = (await archivo.read()).decode("utf-8-sig")
    lector = csv.DictReader(io.StringIO(contenido))

    if lector.fieldnames is None or not COLUMNAS_CSV_REQUERIDAS.issubset(
        {c.strip().lower() for c in lector.fieldnames}
    ):
        raise HTTPException(
            status_code=400,
            detail=f"El CSV debe tener las columnas: {sorted(COLUMNAS_CSV_REQUERIDAS)}",
        )

    procesadas = 0
    errores: list[str] = []

    for numero_fila, fila in enumerate(lector, start=2):  # fila 1 es el encabezado
        fila = {k.strip().lower(): (v.strip() if v else v) for k, v in fila.items()}
        try:
            fecha = _parsear_fecha(fila["fecha"])
            cantidad = float(fila["cantidad"])
            nombre_colaborador = fila.get("colaborador") or ""
            colaborador = _buscar_colaborador_por_nombre(db, negocio_id, nombre_colaborador)

            registro = models.RegistroImpresion(
                negocio_id=negocio_id,
                colaborador_id=colaborador.id if colaborador else None,
                colaborador_nombre_original=nombre_colaborador or None,
                equipo=fila["equipo"],
                tipo_trabajo=fila["tipo_trabajo"],
                tamano=fila.get("tamano") or None,
                cantidad=cantidad,
                fecha=fecha,
                origen="csv_import",
            )
            db.add(registro)
            procesadas += 1
        except (ValueError, KeyError) as exc:
            errores.append(f"Fila {numero_fila}: {exc}")

    db.commit()
    return schemas.ImportarCSVResultado(
        filas_procesadas=procesadas, filas_con_error=len(errores), errores=errores
    )


@router.get("/", response_model=list[schemas.RegistroImpresion])
def listar_impresiones(
    negocio_id: int | None = None,
    colaborador_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.RegistroImpresion)
    if negocio_id is not None:
        query = query.filter(models.RegistroImpresion.negocio_id == negocio_id)
    if colaborador_id is not None:
        query = query.filter(models.RegistroImpresion.colaborador_id == colaborador_id)
    return query.order_by(models.RegistroImpresion.fecha.desc()).all()


@router.get("/resumen", response_model=list[schemas.ResumenImpresionItem])
def resumen_impresiones(negocio_id: int, db: Session = Depends(get_db)):
    """
    Agrupa por colaborador + tipo de trabajo + tamaño + equipo, y estima el
    costo cruzando contra el precio vigente en el catálogo de servicios
    (mismo negocio, misma categoría y mismo tamaño).
    """
    registros = (
        db.query(models.RegistroImpresion)
        .filter(models.RegistroImpresion.negocio_id == negocio_id)
        .all()
    )

    grupos: dict[tuple, float] = defaultdict(float)
    for r in registros:
        nombre_colaborador = (
            r.colaborador.nombre if r.colaborador else (r.colaborador_nombre_original or "Sin identificar")
        )
        clave = (nombre_colaborador, r.tipo_trabajo, r.tamano, r.equipo)
        grupos[clave] += r.cantidad

    resultado = []
    for (colaborador, tipo_trabajo, tamano, equipo), total in grupos.items():
        servicio = (
            db.query(models.Servicio)
            .filter(
                models.Servicio.negocio_id == negocio_id,
                models.Servicio.categoria == tipo_trabajo,
                models.Servicio.tamano == tamano,
            )
            .first()
        )
        costo_estimado = (servicio.precio_unitario * total) if servicio else 0.0
        resultado.append(
            schemas.ResumenImpresionItem(
                colaborador=colaborador,
                tipo_trabajo=tipo_trabajo,
                tamano=tamano,
                equipo=equipo,
                total_cantidad=total,
                costo_estimado=costo_estimado,
            )
        )
    return resultado
