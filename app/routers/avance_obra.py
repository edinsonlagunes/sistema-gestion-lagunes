from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db
from app.fotos_service import subir_foto
from app.permisos import requerir_permiso
from app.zona_horaria import ahora_peru

router = APIRouter(prefix="/avance-obra", tags=["Avance de obra"], dependencies=[Depends(obtener_usuario_actual)])

GRAVEDADES_VALIDAS = {"baja", "media", "alta"}


def _a_schema_partida(partida: models.Partida) -> schemas.PartidaOut:
    ultimo = max(partida.reportes, key=lambda r: r.fecha) if partida.reportes else None
    return schemas.PartidaOut(
        id=partida.id,
        proyecto_id=partida.proyecto_id,
        nombre=partida.nombre,
        orden=partida.orden,
        porcentaje_avance=ultimo.porcentaje_avance if ultimo else 0,
        ultimo_reporte_fecha=ultimo.fecha if ultimo else None,
    )


def _a_schema_reporte(r: models.ReporteAvance) -> schemas.ReporteAvanceOut:
    return schemas.ReporteAvanceOut(
        id=r.id,
        partida_id=r.partida_id,
        colaborador_id=r.colaborador_id,
        colaborador_nombre=r.colaborador.nombre if r.colaborador else None,
        fecha=r.fecha,
        porcentaje_avance=r.porcentaje_avance,
        descripcion=r.descripcion,
        tiene_incidencia=r.tiene_incidencia,
        incidencia_gravedad=r.incidencia_gravedad,
        incidencia_descripcion=r.incidencia_descripcion,
        incidencia_resuelta=r.incidencia_resuelta,
        fotos=[f.url for f in r.fotos],
    )


@router.get("/proyectos/{proyecto_id}/partidas", response_model=list[schemas.PartidaOut])
def listar_partidas(
    proyecto_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("avance_obra", "ver")),
):
    if not db.query(models.Proyecto).get(proyecto_id):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    partidas = (
        db.query(models.Partida)
        .filter(models.Partida.proyecto_id == proyecto_id)
        .order_by(models.Partida.orden)
        .all()
    )
    return [_a_schema_partida(p) for p in partidas]


@router.post("/proyectos/{proyecto_id}/partidas", response_model=schemas.PartidaOut)
def crear_partida(
    proyecto_id: int,
    data: schemas.PartidaCreate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("avance_obra", "editar")),
):
    """Crea una etapa/partida de obra (cimentación, estructura, acabados...) sobre la que luego se reporta avance."""
    if not db.query(models.Proyecto).get(proyecto_id):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    partida = models.Partida(proyecto_id=proyecto_id, nombre=data.nombre, orden=data.orden)
    db.add(partida)
    db.commit()
    db.refresh(partida)
    return _a_schema_partida(partida)


@router.patch("/partidas/{partida_id}", response_model=schemas.PartidaOut)
def editar_partida(
    partida_id: int,
    data: schemas.PartidaUpdate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("avance_obra", "editar")),
):
    partida = db.query(models.Partida).get(partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(partida, campo, valor)
    db.commit()
    db.refresh(partida)
    return _a_schema_partida(partida)


@router.delete("/partidas/{partida_id}", status_code=204)
def eliminar_partida(
    partida_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("avance_obra", "editar")),
):
    """Quita una partida y todos sus reportes/fotos asociados."""
    partida = db.query(models.Partida).get(partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    db.delete(partida)
    db.commit()
    return None


@router.get("/partidas/{partida_id}/reportes", response_model=list[schemas.ReporteAvanceOut])
def listar_reportes(
    partida_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("avance_obra", "ver")),
):
    partida = db.query(models.Partida).get(partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    reportes = sorted(partida.reportes, key=lambda r: r.fecha, reverse=True)
    return [_a_schema_reporte(r) for r in reportes]


@router.post("/partidas/{partida_id}/reportes", response_model=schemas.ReporteAvanceOut)
async def crear_reporte(
    partida_id: int,
    porcentaje_avance: float = Form(...),
    colaborador_id: int | None = Form(None),
    descripcion: str | None = Form(None),
    tiene_incidencia: bool = Form(False),
    incidencia_gravedad: str | None = Form(None),
    incidencia_descripcion: str | None = Form(None),
    fotos: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("avance_obra", "editar")),
):
    """
    Registra un reporte de avance de campo: el nuevo porcentaje
    (reemplaza al anterior, no se suma), una descripción de lo
    realizado, cualquier cantidad de fotos, y opcionalmente una
    incidencia. Las fotos se suben a Cloudinary; aquí solo se guarda
    la URL de cada una.
    """
    partida = db.query(models.Partida).get(partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    if not (0 <= porcentaje_avance <= 100):
        raise HTTPException(status_code=400, detail="El porcentaje de avance debe estar entre 0 y 100")
    if tiene_incidencia and incidencia_gravedad not in GRAVEDADES_VALIDAS:
        raise HTTPException(status_code=400, detail=f"Gravedad inválida. Usa una de: {sorted(GRAVEDADES_VALIDAS)}")
    if colaborador_id is not None and not db.query(models.Colaborador).get(colaborador_id):
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")

    reporte = models.ReporteAvance(
        partida_id=partida_id,
        colaborador_id=colaborador_id,
        fecha=ahora_peru(),
        porcentaje_avance=porcentaje_avance,
        descripcion=descripcion,
        tiene_incidencia=tiene_incidencia,
        incidencia_gravedad=incidencia_gravedad if tiene_incidencia else None,
        incidencia_descripcion=incidencia_descripcion if tiene_incidencia else None,
        incidencia_resuelta=False if tiene_incidencia else None,
    )
    db.add(reporte)
    db.flush()  # asigna reporte.id, para vincular las fotos

    for archivo in fotos:
        url = await subir_foto(archivo)
        db.add(models.FotoAvance(reporte_id=reporte.id, url=url))

    db.commit()
    db.refresh(reporte)
    return _a_schema_reporte(reporte)


@router.patch("/reportes/{reporte_id}/resolver-incidencia", response_model=schemas.ReporteAvanceOut)
def resolver_incidencia(
    reporte_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("avance_obra", "editar")),
):
    reporte = db.query(models.ReporteAvance).get(reporte_id)
    if not reporte or not reporte.tiene_incidencia:
        raise HTTPException(status_code=404, detail="Reporte o incidencia no encontrada")
    reporte.incidencia_resuelta = True
    db.commit()
    db.refresh(reporte)
    return _a_schema_reporte(reporte)


@router.get("/incidencias-abiertas", response_model=list[schemas.ReporteAvanceOut])
def incidencias_abiertas(
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("avance_obra", "ver")),
):
    """Todas las incidencias sin resolver, en cualquier proyecto — para tener un vistazo rápido de lo que necesita atención."""
    reportes = (
        db.query(models.ReporteAvance)
        .filter(models.ReporteAvance.tiene_incidencia.is_(True), models.ReporteAvance.incidencia_resuelta.is_(False))
        .all()
    )
    if negocio_id is not None:
        reportes = [r for r in reportes if r.partida.proyecto.negocio_id == negocio_id]
    reportes.sort(key=lambda r: r.fecha, reverse=True)
    return [_a_schema_reporte(r) for r in reportes]
