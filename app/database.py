"""
Conexión a la base de datos.

Por defecto usa SQLite local (para desarrollo/pruebas).
En Railway, define la variable de entorno DATABASE_URL con tu conexión
de PostgreSQL y el sistema la usará automáticamente, sin cambiar código.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lagunes.db")

# Railway a veces entrega la URL como "postgres://" (formato antiguo).
# SQLAlchemy 2.x exige "postgresql://" explícito, o falla al conectar.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Usamos el driver psycopg v3, que trae su propia copia de libpq incluida
# (evita depender de una librería del sistema operativo que a veces falta
# en el entorno de Railway).
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# SQLite necesita este argumento extra; PostgreSQL no.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
