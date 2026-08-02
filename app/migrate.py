"""
Migración manual: agrega columnas nuevas a tablas que ya existían antes
de este cambio, y corrige datos que quedaron mal calculados por un
cambio de diseño (ver fix_ingresos_proyecto más abajo).

Base.metadata.create_all() (usado en app/main.py y app/seed.py) solo crea
tablas que todavía no existen — no modifica las que ya están creadas con
datos adentro. Cuando se le agrega una columna nueva a un modelo, hay que
agregarla a mano una sola vez con este script.

Ejecutar una sola vez, tanto en Railway (Console) como en tu base local
si ya tenías datos: python -m app.migrate
Es seguro correrlo varias veces — si ya no hay nada que corregir, no
hace nada.
"""
from sqlalchemy import inspect, text

from app import models
from app.database import SessionLocal, engine


def _tiene_columna(inspector, tabla, columna):
    return any(c["name"] == columna for c in inspector.get_columns(tabla))


def migrar_columnas():
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

        if not _tiene_columna(inspector, "registros_impresion", "equipo_id"):
            print("Agregando columna equipo_id a registros_impresion...")
            conn.execute(text("ALTER TABLE registros_impresion ADD COLUMN equipo_id INTEGER"))
            conn.commit()
        else:
            print("registros_impresion.equipo_id ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "ingresos", "pago_proyecto_id"):
            print("Agregando columna pago_proyecto_id a ingresos...")
            conn.execute(text("ALTER TABLE ingresos ADD COLUMN pago_proyecto_id INTEGER"))
            conn.commit()
        else:
            print("ingresos.pago_proyecto_id ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "egresos", "pago_proveedor_id"):
            print("Agregando columna pago_proveedor_id a egresos...")
            conn.execute(text("ALTER TABLE egresos ADD COLUMN pago_proveedor_id INTEGER"))
            conn.commit()
        else:
            print("egresos.pago_proveedor_id ya existe — nada que hacer.")


def fix_ingresos_proyecto():
    """
    Corrige el error de diseño donde facturar una orden generaba un
    ingreso por el total, como si ya se hubiera cobrado. Dos pasos:
      1. Borra los ingresos viejos que se crearon así (ligados a una
         orden_servicio_id) — sobrestimaban lo cobrado.
      2. Crea el ingreso real para cada pago que ya se había registrado
         y que, por el error, nunca generó su ingreso correspondiente.
    Idempotente: en la segunda corrida no queda nada por corregir.
    """
    db = SessionLocal()
    try:
        borrados = (
            db.query(models.Ingreso)
            .filter(models.Ingreso.orden_servicio_id.isnot(None))
            .delete(synchronize_session=False)
        )
        if borrados:
            print(f"Se quitaron {borrados} ingreso(s) generados incorrectamente al facturar órdenes.")
        else:
            print("No había ingresos viejos de órdenes que corregir.")

        etiquetas_tipo = {"adelanto": "Adelanto", "cuota": "Cuota", "pago_final": "Pago final", "otro": "Pago"}
        creados = 0
        for pago in db.query(models.PagoProyecto).all():
            ya_existe = (
                db.query(models.Ingreso).filter(models.Ingreso.pago_proyecto_id == pago.id).first()
            )
            if ya_existe:
                continue
            proyecto = db.query(models.Proyecto).get(pago.proyecto_id)
            if not proyecto:
                continue
            db.add(
                models.Ingreso(
                    negocio_id=proyecto.negocio_id,
                    monto=pago.monto,
                    medio_pago=pago.medio_pago,
                    descripcion=f"{etiquetas_tipo.get(pago.tipo, 'Pago')} - Proyecto '{proyecto.nombre}'",
                    fecha=pago.fecha_pago,
                    pago_proyecto_id=pago.id,
                )
            )
            creados += 1

        if creados:
            print(f"Se crearon {creados} ingreso(s) para pagos que no lo tenían.")
        else:
            print("No había pagos sin su ingreso correspondiente.")

        db.commit()
    finally:
        db.close()


def fix_egresos_proveedor():
    """
    Corrige el mismo error de diseño, ahora del lado de los proveedores:
    registrar una compra generaba un egreso automático por el total,
    como si ya se le hubiera pagado al proveedor. Borra esos egresos
    viejos (se identifican por su categoría y descripción exactas, las
    que usaba el código anterior, y por no tener un pago vinculado).
    Idempotente.
    """
    db = SessionLocal()
    try:
        borrados = (
            db.query(models.Egreso)
            .filter(
                models.Egreso.categoria == "compra_insumo",
                models.Egreso.pago_proveedor_id.is_(None),
                models.Egreso.descripcion.like("Compra de%"),
            )
            .delete(synchronize_session=False)
        )
        if borrados:
            print(f"Se quitaron {borrados} egreso(s) generados incorrectamente al registrar compras.")
        else:
            print("No había egresos viejos de compras que corregir.")
        db.commit()
    finally:
        db.close()


def migrar():
    migrar_columnas()
    fix_ingresos_proyecto()
    fix_egresos_proveedor()
    print("Migración completa.")


if __name__ == "__main__":
    migrar()
