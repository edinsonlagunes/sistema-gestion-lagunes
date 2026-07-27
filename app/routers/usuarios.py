from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import crear_token, requerir_admin
from app.database import get_db
from app.security import hash_password, verify_password

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=schemas.Usuario)
def crear_usuario(
    data: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    """Solo un administrador puede dar de alta nuevos usuarios."""
    colaborador = db.query(models.Colaborador).get(data.colaborador_id)
    if not colaborador:
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")
    existente = db.query(models.Usuario).filter(models.Usuario.username == data.username).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ese nombre de usuario ya existe")

    usuario = models.Usuario(
        colaborador_id=data.colaborador_id,
        username=data.username,
        password_hash=hash_password(data.password),
        rol_permiso=data.rol_permiso,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/login")
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.username == data.username).first()
    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    colaborador = usuario.colaborador
    token = crear_token(usuario.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario_id": usuario.id,
        "username": usuario.username,
        "rol_permiso": usuario.rol_permiso,
        "colaborador": colaborador.nombre,
        "negocio_id": colaborador.negocio_id,
    }
