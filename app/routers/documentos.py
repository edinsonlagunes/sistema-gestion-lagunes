from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import obtener_usuario_actual
from app.database import get_db
from app.permisos import requerir_permiso
from app.zona_horaria import ahora_peru

router = APIRouter(prefix="/documentos", tags=["Documentos"], dependencies=[Depends(obtener_usuario_actual)])

TIPOS_VALIDOS = {"permiso_municipal", "archivo_tecnico", "licitacion", "otro"}


def _a_schema(doc: models.Documento) -> schemas.DocumentoOut:
    dias = None
    if doc.fecha_vencimiento:
        dias = (doc.fecha_vencimiento.date() - ahora_peru().date()).days
    return schemas.DocumentoOut(
        id=doc.id,
        negocio_id=doc.negocio_id,
        proyecto_id=doc.proyecto_id,
        tipo=doc.tipo,
        nombre=doc.nombre,
        numero=doc.numero,
        entidad=doc.entidad,
        fecha_emision=doc.fecha_emision,
        fecha_vencimiento=doc.fecha_vencimiento,
        estado=doc.estado,
        archivo_url=doc.archivo_url,
        observaciones=doc.observaciones,
        responsable_id=doc.responsable_id,
        dias_para_vencer=dias,
    )


@router.get("/", response_model=list[schemas.DocumentoOut])
def listar_documentos(
    negocio_id: int | None = None,
    proyecto_id: int | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("documentos", "ver")),
):
    query = db.query(models.Documento)
    if negocio_id is not None:
        query = query.filter(models.Documento.negocio_id == negocio_id)
    if proyecto_id is not None:
        query = query.filter(models.Documento.proyecto_id == proyecto_id)
    if tipo is not None:
        query = query.filter(models.Documento.tipo == tipo)
    if estado is not None:
        query = query.filter(models.Documento.estado == estado)
    documentos = query.order_by(models.Documento.fecha_vencimiento.asc().nullslast()).all()
    return [_a_schema(d) for d in documentos]


@router.get("/vencimientos-proximos", response_model=list[schemas.DocumentoOut])
def vencimientos_proximos(
    dias: int = 30,
    negocio_id: int | None = None,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("documentos", "ver")),
):
    """
    Documentos que vencen dentro de los próximos N días, o que ya
    vencieron — para poder darles seguimiento antes de que se conviertan
    en un problema (una licencia caducada, una licitación cerrada).
    """
    limite = ahora_peru().date() + timedelta(days=dias)
    query = db.query(models.Documento).filter(models.Documento.fecha_vencimiento.isnot(None))
    if negocio_id is not None:
        query = query.filter(models.Documento.negocio_id == negocio_id)

    documentos = [
        d for d in query.all() if d.fecha_vencimiento.date() <= limite
    ]
    documentos.sort(key=lambda d: d.fecha_vencimiento)
    return [_a_schema(d) for d in documentos]


@router.post("/", response_model=schemas.DocumentoOut)
def crear_documento(
    data: schemas.DocumentoCreate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("documentos", "editar")),
):
    """Registra un permiso municipal, un documento de archivo técnico, o una licitación. Exige permiso de Documentos."""
    if not db.query(models.Negocio).get(data.negocio_id):
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if data.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Usa uno de: {sorted(TIPOS_VALIDOS)}")
    if data.proyecto_id and not db.query(models.Proyecto).get(data.proyecto_id):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    documento = models.Documento(**data.model_dump())
    db.add(documento)
    db.commit()
    db.refresh(documento)
    return _a_schema(documento)


@router.get("/{documento_id}", response_model=schemas.DocumentoOut)
def obtener_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("documentos", "ver")),
):
    documento = db.query(models.Documento).get(documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return _a_schema(documento)


@router.patch("/{documento_id}", response_model=schemas.DocumentoOut)
def actualizar_documento(
    documento_id: int,
    data: schemas.DocumentoUpdate,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("documentos", "editar")),
):
    """Edita un documento (ej. renovar su fecha de vencimiento, cambiar su estado). Exige permiso de Documentos."""
    documento = db.query(models.Documento).get(documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    datos = data.model_dump(exclude_unset=True)
    if "tipo" in datos and datos["tipo"] not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Usa uno de: {sorted(TIPOS_VALIDOS)}")

    for campo, valor in datos.items():
        setattr(documento, campo, valor)

    db.commit()
    db.refresh(documento)
    return _a_schema(documento)


@router.delete("/{documento_id}", status_code=204)
def eliminar_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    _permiso: models.Usuario = Depends(requerir_permiso("documentos", "editar")),
):
    documento = db.query(models.Documento).get(documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    db.delete(documento)
    db.commit()
    return None
