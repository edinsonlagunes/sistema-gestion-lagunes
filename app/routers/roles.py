from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auditoria import registrar_auditoria
from app.auth import requerir_superadmin
from app.database import get_db
from app.permisos import MODULOS_SISTEMA, NIVELES_VALIDOS

router = APIRouter(prefix="/roles", tags=["Roles y permisos"], dependencies=[Depends(requerir_superadmin)])


def _a_schema(rol: models.Rol) -> schemas.RolOut:
    permisos_por_modulo = {p.modulo: p.nivel for p in rol.permisos}
    return schemas.RolOut(
        id=rol.id,
        nombre=rol.nombre,
        permisos=[
            schemas.PermisoRolOut(modulo=m, nivel=permisos_por_modulo.get(m, "sin_acceso"))
            for m in MODULOS_SISTEMA
        ],
    )


@router.get("/modulos")
def listar_modulos():
    """Los módulos del sistema sobre los que se puede dar permiso, y los niveles válidos."""
    return {"modulos": MODULOS_SISTEMA, "niveles": NIVELES_VALIDOS}


@router.get("/", response_model=list[schemas.RolOut])
def listar_roles(db: Session = Depends(get_db)):
    return [_a_schema(r) for r in db.query(models.Rol).order_by(models.Rol.nombre).all()]


@router.post("/", response_model=schemas.RolOut)
def crear_rol(
    data: schemas.RolCreate,
    db: Session = Depends(get_db),
    _superadmin: models.Usuario = Depends(requerir_superadmin),
):
    """Crea un rol nuevo (ej. "Imprenta", "Caja", "Stand 1") con los permisos que le des por módulo."""
    existente = db.query(models.Rol).filter(models.Rol.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")

    permisos_pedidos = data.permisos or {}
    for nivel in permisos_pedidos.values():
        if nivel not in NIVELES_VALIDOS:
            raise HTTPException(status_code=400, detail=f"Nivel inválido: '{nivel}'. Usa uno de: {NIVELES_VALIDOS}")

    rol = models.Rol(nombre=data.nombre)
    db.add(rol)
    db.flush()  # para tener rol.id antes de crear sus permisos
    for modulo in MODULOS_SISTEMA:
        db.add(models.PermisoRol(rol_id=rol.id, modulo=modulo, nivel=permisos_pedidos.get(modulo, "sin_acceso")))
    registrar_auditoria(db, _superadmin, "crear", "rol", rol.id, f"Rol '{rol.nombre}'")
    db.commit()
    db.refresh(rol)
    return _a_schema(rol)


@router.patch("/{rol_id}", response_model=schemas.RolOut)
def actualizar_rol(
    rol_id: int,
    data: schemas.RolUpdate,
    db: Session = Depends(get_db),
    _superadmin: models.Usuario = Depends(requerir_superadmin),
):
    """Renombra un rol y/o cambia sus permisos por módulo. Manda solo lo que quieras cambiar."""
    rol = db.query(models.Rol).get(rol_id)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    cambios = []
    if data.nombre is not None:
        duplicado = db.query(models.Rol).filter(models.Rol.nombre == data.nombre, models.Rol.id != rol_id).first()
        if duplicado:
            raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")
        cambios.append(f"nombre -> '{data.nombre}'")
        rol.nombre = data.nombre

    if data.permisos:
        for modulo, nivel in data.permisos.items():
            if modulo not in MODULOS_SISTEMA:
                raise HTTPException(status_code=400, detail=f"Módulo desconocido: '{modulo}'")
            if nivel not in NIVELES_VALIDOS:
                raise HTTPException(status_code=400, detail=f"Nivel inválido: '{nivel}'. Usa uno de: {NIVELES_VALIDOS}")
            permiso = (
                db.query(models.PermisoRol)
                .filter(models.PermisoRol.rol_id == rol_id, models.PermisoRol.modulo == modulo)
                .first()
            )
            if permiso:
                permiso.nivel = nivel
            else:
                db.add(models.PermisoRol(rol_id=rol_id, modulo=modulo, nivel=nivel))
            cambios.append(f"{modulo} -> {nivel}")

    if cambios:
        registrar_auditoria(db, _superadmin, "editar", "rol", rol.id, "; ".join(cambios))

    db.commit()
    db.refresh(rol)
    return _a_schema(rol)


@router.delete("/{rol_id}", status_code=204)
def eliminar_rol(
    rol_id: int,
    db: Session = Depends(get_db),
    _superadmin: models.Usuario = Depends(requerir_superadmin),
):
    """
    Borra un rol. A quien lo tuviera asignado no se le borra el
    usuario ni pierde acceso a lo que tenga por permiso especial —
    simplemente queda sin rol (tendrás que asignarle uno nuevo).
    """
    rol = db.query(models.Rol).get(rol_id)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    registrar_auditoria(db, _superadmin, "eliminar", "rol", rol.id, f"Rol '{rol.nombre}'")
    db.query(models.Usuario).filter(models.Usuario.rol_id == rol_id).update({"rol_id": None})
    db.delete(rol)
    db.commit()
    return None


@router.patch("/asignar/{usuario_id}", response_model=schemas.Usuario)
def asignar_rol(
    usuario_id: int,
    data: schemas.AsignarRolRequest,
    db: Session = Depends(get_db),
    _superadmin: models.Usuario = Depends(requerir_superadmin),
):
    """Asigna (o quita, mandando rol_id: null) el rol de una persona."""
    usuario = db.query(models.Usuario).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if data.rol_id is not None and not db.query(models.Rol).get(data.rol_id):
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    usuario.rol_id = data.rol_id
    registrar_auditoria(
        db, _superadmin, "editar", "usuario", usuario.id,
        f"Rol asignado a '{usuario.username}' -> {data.rol_id or 'ninguno'}",
    )
    db.commit()
    db.refresh(usuario)
    return usuario


# ---------- Permisos especiales por persona ----------

@router.post("/permisos-especiales", response_model=schemas.PermisoEspecialOut)
def otorgar_permiso_especial(
    data: schemas.PermisoEspecialCreate,
    db: Session = Depends(get_db),
    _superadmin: models.Usuario = Depends(requerir_superadmin),
):
    """
    Le da a UNA persona acceso extra a un módulo, por encima de lo que
    le da su rol, sin afectar a nadie más. Si ya tenía un permiso
    especial en ese módulo, lo actualiza en vez de duplicarlo.
    """
    usuario = db.query(models.Usuario).get(data.usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if data.modulo not in MODULOS_SISTEMA:
        raise HTTPException(status_code=400, detail=f"Módulo desconocido: '{data.modulo}'")
    if data.nivel not in ("ver", "editar"):
        raise HTTPException(status_code=400, detail="El nivel especial debe ser 'ver' o 'editar'")

    existente = (
        db.query(models.PermisoEspecial)
        .filter(models.PermisoEspecial.usuario_id == data.usuario_id, models.PermisoEspecial.modulo == data.modulo)
        .first()
    )
    detalle = f"'{usuario.username}' -> {data.modulo}: {data.nivel}"
    if existente:
        existente.nivel = data.nivel
        registrar_auditoria(db, _superadmin, "editar", "permiso_especial", existente.id, detalle)
        db.commit()
        db.refresh(existente)
        return existente

    permiso = models.PermisoEspecial(usuario_id=data.usuario_id, modulo=data.modulo, nivel=data.nivel)
    db.add(permiso)
    db.flush()
    registrar_auditoria(db, _superadmin, "crear", "permiso_especial", permiso.id, detalle)
    db.commit()
    db.refresh(permiso)
    return permiso


@router.delete("/permisos-especiales/{permiso_id}", status_code=204)
def quitar_permiso_especial(
    permiso_id: int,
    db: Session = Depends(get_db),
    _superadmin: models.Usuario = Depends(requerir_superadmin),
):
    """Quita el permiso especial — la persona vuelve a depender solo de su rol en ese módulo."""
    permiso = db.query(models.PermisoEspecial).get(permiso_id)
    if not permiso:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    registrar_auditoria(
        db, _superadmin, "eliminar", "permiso_especial", permiso.id,
        f"usuario_id {permiso.usuario_id} -> {permiso.modulo}",
    )
    db.delete(permiso)
    db.commit()
    return None


@router.get("/permisos-especiales/usuario/{usuario_id}", response_model=list[schemas.PermisoEspecialOut])
def listar_permisos_especiales(usuario_id: int, db: Session = Depends(get_db)):
    return db.query(models.PermisoEspecial).filter(models.PermisoEspecial.usuario_id == usuario_id).all()
