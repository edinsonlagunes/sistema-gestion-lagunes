"""
Carga los datos iniciales: los dos negocios (Constructora Lagunes y
Librería) y un usuario administrador para poder empezar a usar el sistema.

Ejecutar una sola vez: python -m app.seed
"""
from app.database import Base, SessionLocal, engine
from app.models import Colaborador, Negocio, Usuario
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    if not db.query(Negocio).first():
        constructora = Negocio(nombre="Constructora Lagunes")
        libreria = Negocio(nombre="Librería")
        db.add_all([constructora, libreria])
        db.commit()
        db.refresh(constructora)

        admin_colaborador = Colaborador(
            nombre="Edinson Lagunes",
            negocio_id=constructora.id,
            rol="admin",
        )
        db.add(admin_colaborador)
        db.commit()
        db.refresh(admin_colaborador)

        admin_usuario = Usuario(
            colaborador_id=admin_colaborador.id,
            username="admin",
            password_hash=hash_password("cambiar123"),
            rol_permiso="admin",
        )
        db.add(admin_usuario)
        db.commit()

        print("Datos iniciales creados:")
        print("  Negocios: Constructora Lagunes, Librería")
        print("  Usuario admin -> username: admin / password: cambiar123")
        print("  IMPORTANTE: cambia esta contraseña apenas entres al sistema.")
    else:
        print("Ya existían negocios en la base de datos; no se volvió a sembrar.")
finally:
    db.close()
