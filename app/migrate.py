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

# IMPORTANTE: antes de correr la migración, cambia esto por tu username
# real de administrador (el que usas para iniciar sesión en el sistema).
# Sirve para marcarte como superadministrador con acceso total.
USUARIO_SUPERADMIN = "admin"


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

        if not _tiene_columna(inspector, "proyectos", "presupuesto"):
            print("Agregando columna presupuesto a proyectos...")
            conn.execute(text("ALTER TABLE proyectos ADD COLUMN presupuesto FLOAT"))
            conn.commit()
        else:
            print("proyectos.presupuesto ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "colaboradores", "sueldo_semanal"):
            print("Agregando columna sueldo_semanal a colaboradores...")
            conn.execute(text("ALTER TABLE colaboradores ADD COLUMN sueldo_semanal FLOAT"))
            conn.commit()
        else:
            print("colaboradores.sueldo_semanal ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "colaboradores", "hora_entrada_esperada"):
            print("Agregando columna hora_entrada_esperada a colaboradores...")
            conn.execute(text("ALTER TABLE colaboradores ADD COLUMN hora_entrada_esperada VARCHAR"))
            conn.commit()
        else:
            print("colaboradores.hora_entrada_esperada ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "ingresos", "venta_id"):
            print("Agregando columna venta_id a ingresos...")
            conn.execute(text("ALTER TABLE ingresos ADD COLUMN venta_id INTEGER"))
            conn.commit()
        else:
            print("ingresos.venta_id ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "ordenes_servicio", "fecha"):
            print("Agregando columna fecha a ordenes_servicio...")
            conn.execute(text("ALTER TABLE ordenes_servicio ADD COLUMN fecha TIMESTAMP"))
            conn.commit()
        else:
            print("ordenes_servicio.fecha ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "colaboradores", "cargo"):
            print("Agregando columna cargo a colaboradores...")
            conn.execute(text("ALTER TABLE colaboradores ADD COLUMN cargo VARCHAR"))
            conn.commit()
        else:
            print("colaboradores.cargo ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "colaboradores", "profesion"):
            print("Agregando columna profesion a colaboradores...")
            conn.execute(text("ALTER TABLE colaboradores ADD COLUMN profesion VARCHAR"))
            conn.commit()
        else:
            print("colaboradores.profesion ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "ingresos", "tipo_comprobante"):
            print("Agregando columna tipo_comprobante a ingresos...")
            conn.execute(text("ALTER TABLE ingresos ADD COLUMN tipo_comprobante VARCHAR"))
            conn.commit()
        else:
            print("ingresos.tipo_comprobante ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "egresos", "tipo_comprobante"):
            print("Agregando columna tipo_comprobante a egresos...")
            conn.execute(text("ALTER TABLE egresos ADD COLUMN tipo_comprobante VARCHAR"))
            conn.commit()
        else:
            print("egresos.tipo_comprobante ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "proveedores", "telefono"):
            print("Agregando columna telefono a proveedores...")
            conn.execute(text("ALTER TABLE proveedores ADD COLUMN telefono VARCHAR"))
            conn.commit()
        else:
            print("proveedores.telefono ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "proveedores", "direccion"):
            print("Agregando columna direccion a proveedores...")
            conn.execute(text("ALTER TABLE proveedores ADD COLUMN direccion VARCHAR"))
            conn.commit()
        else:
            print("proveedores.direccion ya existe — nada que hacer.")

        # --- Sistema de roles y permisos ---
        if not _tiene_columna(inspector, "usuarios", "rol_id"):
            print("Agregando columna rol_id a usuarios...")
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN rol_id INTEGER"))
            conn.commit()
        else:
            print("usuarios.rol_id ya existe — nada que hacer.")

        if not _tiene_columna(inspector, "usuarios", "es_superadmin"):
            print("Agregando columna es_superadmin a usuarios...")
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN es_superadmin BOOLEAN DEFAULT FALSE"))
            conn.commit()
        else:
            print("usuarios.es_superadmin ya existe — nada que hacer.")


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


def fix_fechas_ordenes():
    """
    Las órdenes de servicio creadas antes de que existiera la columna
    fecha quedan con fecha=NULL — se les asigna la fecha de inicio de
    su proyecto como mejor aproximación disponible, para que puedan
    aparecer en los reportes por periodo. Idempotente.
    """
    db = SessionLocal()
    try:
        ordenes_sin_fecha = db.query(models.OrdenServicio).filter(models.OrdenServicio.fecha.is_(None)).all()
        for orden in ordenes_sin_fecha:
            proyecto = db.query(models.Proyecto).get(orden.proyecto_id)
            if proyecto:
                orden.fecha = proyecto.fecha_inicio
        if ordenes_sin_fecha:
            print(f"Se completó la fecha de {len(ordenes_sin_fecha)} orden(es) de servicio antigua(s).")
        else:
            print("No había órdenes de servicio sin fecha.")
        db.commit()
    finally:
        db.close()


def fix_ventas_sin_vinculo():
    """
    Los ingresos de ventas creadas antes de que existiera la columna
    venta_id quedaron sin ese vínculo — se identifican por su
    descripción ("Venta #N") y se les asigna el id de esa venta, para
    que el botón de quitar una venta mal registrada pueda encontrarlas.
    Idempotente.
    """
    db = SessionLocal()
    try:
        pendientes = db.query(models.Ingreso).filter(models.Ingreso.venta_id.is_(None)).all()
        vinculados = 0
        for ingreso in pendientes:
            if not ingreso.descripcion or not ingreso.descripcion.startswith("Venta #"):
                continue
            resto = ingreso.descripcion[len("Venta #"):]
            numero = ""
            for caracter in resto:
                if caracter.isdigit():
                    numero += caracter
                else:
                    break
            if not numero:
                continue
            venta = db.query(models.Venta).get(int(numero))
            if venta and venta.negocio_id == ingreso.negocio_id:
                ingreso.venta_id = venta.id
                vinculados += 1
        if vinculados:
            print(f"Se vinculó {vinculados} ingreso(s) de ventas antiguas con su venta_id.")
        else:
            print("No había ingresos de ventas antiguas por vincular.")
        db.commit()
    finally:
        db.close()


def renombrar_negocio_constructora():
    """
    Cambia el nombre del negocio "Constructora Lagunes" a "Estudio de
    Arquitectura e Ingeniería", si todavía no se ha hecho. Idempotente
    — si ya se renombró, no hace nada.
    """
    db = SessionLocal()
    try:
        negocio = db.query(models.Negocio).filter(models.Negocio.nombre == "Constructora Lagunes").first()
        if negocio:
            negocio.nombre = "Estudio de Arquitectura e Ingeniería"
            db.commit()
            print("Se renombró 'Constructora Lagunes' a 'Estudio de Arquitectura e Ingeniería'.")
        else:
            print("El negocio 'Constructora Lagunes' ya no existe con ese nombre — nada que renombrar.")
    finally:
        db.close()


def renombrar_negocio_libreria():
    """
    Cambia el nombre del negocio "Librería" a "Imprenta", si todavía no
    se ha hecho. Idempotente — si ya se renombró, no hace nada.
    """
    db = SessionLocal()
    try:
        negocio = db.query(models.Negocio).filter(models.Negocio.nombre == "Librería").first()
        if negocio:
            negocio.nombre = "Imprenta"
            db.commit()
            print("Se renombró 'Librería' a 'Imprenta'.")
        else:
            print("El negocio 'Librería' ya no existe con ese nombre — nada que renombrar.")
    finally:
        db.close()


def crear_negocio_constructora():
    """
    Crea el negocio "Constructora" (ejecución de obras), separado del
    Estudio de Arquitectura e Ingeniería (diseño/expedientes) — la
    empresa opera como tres líneas de negocio distintas. Idempotente.
    """
    db = SessionLocal()
    try:
        existente = db.query(models.Negocio).filter(models.Negocio.nombre == "Constructora").first()
        if existente:
            print("El negocio 'Constructora' ya existe — nada que crear.")
        else:
            db.add(models.Negocio(nombre="Constructora"))
            db.commit()
            print("Se creó el negocio 'Constructora'.")
    finally:
        db.close()


# Módulos del sistema sobre los que se define acceso por rol. Debe
# coincidir con app/permisos.py.
MODULOS_INICIALES = [
    "proyectos", "compras", "colaboradores", "finanzas", "documentos",
    "caja_chica", "planillas", "asistencia", "ventas_impresiones",
    "conciliacion", "mantenimientos", "agenda",
]

# Roles de partida sugeridos — se pueden editar, renombrar o borrar
# desde la pantalla de administración una vez que exista; esto solo
# les da un punto de arranque razonable.
ROLES_INICIALES = {
    "Administrador": {modulo: "editar" for modulo in MODULOS_INICIALES},
    "Finanzas": {
        "finanzas": "editar", "caja_chica": "editar", "compras": "ver",
        "ventas_impresiones": "ver", "conciliacion": "ver",
    },
    "Recursos Humanos": {
        "colaboradores": "editar", "asistencia": "editar", "planillas": "editar",
    },
    "Proyectista": {
        "proyectos": "editar", "documentos": "editar", "agenda": "editar",
    },
}


def seed_roles_iniciales():
    """
    Crea los roles de partida (Administrador, Finanzas, Recursos
    Humanos, Proyectista) con permisos razonables por defecto, si
    todavía no existe ningún rol con ese nombre. Editable después desde
    el sistema — esto es solo el punto de arranque. Idempotente.
    """
    db = SessionLocal()
    try:
        creados = 0
        for nombre_rol, permisos_modulo in ROLES_INICIALES.items():
            existente = db.query(models.Rol).filter(models.Rol.nombre == nombre_rol).first()
            if existente:
                continue
            rol = models.Rol(nombre=nombre_rol)
            db.add(rol)
            db.flush()  # para tener rol.id antes de crear sus permisos
            for modulo in MODULOS_INICIALES:
                db.add(
                    models.PermisoRol(
                        rol_id=rol.id,
                        modulo=modulo,
                        nivel=permisos_modulo.get(modulo, "sin_acceso"),
                    )
                )
            creados += 1
        if creados:
            print(f"Se crearon {creados} rol(es) inicial(es): {', '.join(ROLES_INICIALES.keys())}.")
        else:
            print("Los roles iniciales ya existían — nada que crear.")
        db.commit()
    finally:
        db.close()


def marcar_superadmin():
    """
    Marca tu usuario (definido en USUARIO_SUPERADMIN, arriba del
    archivo) como superadministrador: acceso total al sistema siempre,
    sin depender de roles ni permisos. Idempotente.
    """
    if USUARIO_SUPERADMIN == "CAMBIAR_POR_TU_USERNAME":
        print("AVISO: no se marcó ningún superadministrador — edita USUARIO_SUPERADMIN al inicio de este archivo con tu username real y vuelve a correr la migración.")
        return

    db = SessionLocal()
    try:
        usuario = db.query(models.Usuario).filter(models.Usuario.username == USUARIO_SUPERADMIN).first()
        if not usuario:
            print(f"AVISO: no se encontró ningún usuario con username '{USUARIO_SUPERADMIN}' — revisa que esté bien escrito.")
            return
        if usuario.es_superadmin:
            print(f"El usuario '{USUARIO_SUPERADMIN}' ya era superadministrador — nada que hacer.")
        else:
            usuario.es_superadmin = True
            db.commit()
            print(f"Se marcó a '{USUARIO_SUPERADMIN}' como superadministrador.")
    finally:
        db.close()


def migrar():
    migrar_columnas()
    fix_ingresos_proyecto()
    fix_egresos_proveedor()
    fix_fechas_ordenes()
    fix_ventas_sin_vinculo()
    renombrar_negocio_constructora()
    renombrar_negocio_libreria()
    crear_negocio_constructora()
    seed_roles_iniciales()
    marcar_superadmin()
    print("Migración completa.")


if __name__ == "__main__":
    migrar()
