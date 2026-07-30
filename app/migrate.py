"""
Migración manual: agrega columnas nuevas a tablas que ya existían antes
de este cambio.

Base.metadata.create_all() (usado en app/main.py y app/seed.py) solo crea
tablas que todavía no existen — no modifica las que ya están creadas con
datos adentro. Cuando se le agrega una columna nueva a un modelo (como
tipo_proyecto a Proyecto, u orden_servicio_id a Ingreso), hay que
agregarla a mano una sola vez con este script.

Ejecutar una sola vez, tanto en Railway (Console) como en tu base local
si ya tenías datos: python -m app.migrate
Es seguro correrlo varias veces — si la columna ya existe, no hace nada.
"""
from sqlalchemy import inspect, text

from app.database import engine


def _tiene_columna(inspector, tabla, columna):
    return any(c["name"] == columna for c in inspector.get_columns(tabla))


def migrar():
    inspector = inspect(engine)

    with engine.connect() as conn:
        if not _tiene_columna(inspector, "proyectos", "tipo_proyecto"):
            print("Agregando columna tipo_proyecto a proyectos...")
            conn.execute(text("ALTER TABLE proyectos ADD COLUMN tipo_proyecto VARCHAR"))
            conn.commit()
        else:
            print("proyectos.tipo_proyecto ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "ingresos", "orden_servicio_id"):
            print("Agregando columna orden_servicio_id a ingresos...")
            conn.execute(text("ALTER TABLE ingresos ADD COLUMN orden_servicio_id INTEGER"))
            conn.commit()
        else:
            print("ingresos.orden_servicio_id ya existe — nada que hacer.")

    print("Migración completa.")


if __name__ == "__main__":
    migrar()
