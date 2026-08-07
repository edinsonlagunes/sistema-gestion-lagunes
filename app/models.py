"""
Modelos del núcleo (Fase 1): negocios, colaboradores, usuarios,
finanzas (ingresos/egresos), proveedores, insumos y compras.

Fase 2 (POS Librería): catálogo de servicios, sesiones de caja
(apertura/cierre con arqueo) y ventas.

El módulo de Constructora (proyectos/servicios técnicos) se construye
en la siguiente fase sobre esta misma base.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.zona_horaria import ahora_peru


class Planilla(Base):
    """Planilla semanal: agrupa el pago de todos los colaboradores de un negocio en una semana."""
    __tablename__ = "planillas"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    estado = Column(String, nullable=False, default="borrador")  # borrador, pagada
    fecha_pago = Column(DateTime, nullable=True)

    negocio = relationship("Negocio")
    detalles = relationship("DetallePlanilla", back_populates="planilla", cascade="all, delete-orphan")


class DetallePlanilla(Base):
    """Lo que le corresponde a un colaborador dentro de una planilla: sueldo, faltas, tardanzas."""
    __tablename__ = "detalles_planilla"

    id = Column(Integer, primary_key=True, index=True)
    planilla_id = Column(Integer, ForeignKey("planillas.id"), nullable=False)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=False)
    sueldo_base = Column(Float, nullable=False, default=0)
    dias_falta = Column(Integer, nullable=False, default=0)
    monto_descuento_faltas = Column(Float, nullable=False, default=0)
    minutos_tardanza = Column(Integer, nullable=False, default=0)
    monto_descuento_tardanzas = Column(Float, nullable=False, default=0)
    otros_descuentos = Column(Float, nullable=False, default=0)
    observaciones = Column(String, nullable=True)

    planilla = relationship("Planilla", back_populates="detalles")
    colaborador = relationship("Colaborador")


class Documento(Base):
    """
    Documento con seguimiento de vencimiento: permisos municipales,
    archivo técnico, licitaciones, u otro. Puede estar ligado a un
    proyecto específico, o ser general de la empresa (ej. licencia de
    funcionamiento).
    """
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=True)
    tipo = Column(String, nullable=False)  # permiso_municipal, archivo_tecnico, licitacion, otro
    nombre = Column(String, nullable=False)
    numero = Column(String, nullable=True)  # numero de expediente/licencia/licitacion
    entidad = Column(String, nullable=True)  # municipalidad, entidad licitante, etc.
    fecha_emision = Column(DateTime, nullable=True)
    fecha_vencimiento = Column(DateTime, nullable=True)
    estado = Column(String, nullable=False, default="vigente")
    archivo_url = Column(String, nullable=True)
    observaciones = Column(String, nullable=True)
    responsable_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=True)

    negocio = relationship("Negocio")
    proyecto = relationship("Proyecto")
    responsable = relationship("Colaborador")


class Negocio(Base):
    """Constructora Lagunes / Librería."""
    __tablename__ = "negocios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)

    colaboradores = relationship("Colaborador", back_populates="negocio")
    insumos = relationship("Insumo", back_populates="negocio")
    ingresos = relationship("Ingreso", back_populates="negocio")
    egresos = relationship("Egreso", back_populates="negocio")


class Colaborador(Base):
    __tablename__ = "colaboradores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    rol = Column(String, nullable=False)  # admin, dibujante, cajero, ventas, etc.
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=ahora_peru)
    sueldo_semanal = Column(Float, nullable=True)
    hora_entrada_esperada = Column(String, nullable=True)  # "HH:MM", para calcular tardanzas
    cargo = Column(String, nullable=True)  # puesto dentro de la empresa, ej. "Jefe de Obra"
    profesion = Column(String, nullable=True)  # ej. "Arquitecto", "Ingeniero Civil"

    negocio = relationship("Negocio", back_populates="colaboradores")
    usuario = relationship("Usuario", back_populates="colaborador", uselist=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol_permiso = Column(String, nullable=False, default="colaborador")  # admin | colaborador — se mantiene por compatibilidad mientras se migra cada módulo al sistema de roles nuevo

    # --- Sistema de roles y permisos granular ---
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=True)  # rol editable (Finanzas, RRHH, Proyectista, etc.)
    es_superadmin = Column(Boolean, nullable=False, default=False)  # acceso total siempre, sin depender de permisos

    colaborador = relationship("Colaborador", back_populates="usuario")
    rol_asignado = relationship("Rol")
    permisos_especiales = relationship("PermisoEspecial", back_populates="usuario", cascade="all, delete-orphan")


class Rol(Base):
    """
    Un rol editable de la empresa (Administrador, Finanzas, Recursos
    Humanos, Proyectista...). El gerente general los crea, nombra y
    borra libremente desde la pantalla de administración — no son una
    lista fija en el código.
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    creado_en = Column(DateTime, default=ahora_peru)

    permisos = relationship("PermisoRol", back_populates="rol", cascade="all, delete-orphan")


class PermisoRol(Base):
    """
    El nivel de acceso que tiene un rol sobre un módulo del sistema.
    nivel: sin_acceso | ver | editar
    """
    __tablename__ = "permisos_rol"

    id = Column(Integer, primary_key=True, index=True)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    modulo = Column(String, nullable=False)  # "proyectos", "finanzas", etc. — ver app/permisos.py
    nivel = Column(String, nullable=False, default="sin_acceso")

    rol = relationship("Rol", back_populates="permisos")


class PermisoEspecial(Base):
    """
    Permiso adicional sobre un módulo, otorgado a UNA persona en
    particular, por encima de lo que le da su rol — para casos
    puntuales (ej. delegarle a alguien la edición de Finanzas por un
    tiempo) sin cambiarle el rol ni afectar a nadie más. Se puede
    quitar en cualquier momento; al quitarse, la persona vuelve a
    depender solo de su rol.
    nivel: ver | editar
    """
    __tablename__ = "permisos_especiales"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    modulo = Column(String, nullable=False)
    nivel = Column(String, nullable=False)
    otorgado_en = Column(DateTime, default=ahora_peru)

    usuario = relationship("Usuario", back_populates="permisos_especiales")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    contacto = Column(String, nullable=True)  # nombre de la persona de contacto
    telefono = Column(String, nullable=True)
    direccion = Column(String, nullable=True)

    compras = relationship("Compra", back_populates="proveedor")
    pagos = relationship("PagoProveedor", back_populates="proveedor", cascade="all, delete-orphan")


class Insumo(Base):
    __tablename__ = "insumos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    nombre = Column(String, nullable=False)
    unidad = Column(String, nullable=False)  # hoja, litro, unidad, etc.
    stock_actual = Column(Float, default=0)
    stock_minimo = Column(Float, default=0)

    negocio = relationship("Negocio", back_populates="insumos")
    compras = relationship("Compra", back_populates="insumo")


class Compra(Base):
    __tablename__ = "compras"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    cantidad = Column(Float, nullable=False)
    costo = Column(Float, nullable=False)
    fecha = Column(DateTime, default=ahora_peru)

    proveedor = relationship("Proveedor", back_populates="compras")
    insumo = relationship("Insumo", back_populates="compras")


class Ingreso(Base):
    __tablename__ = "ingresos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    monto = Column(Float, nullable=False)
    medio_pago = Column(String, nullable=False, default="efectivo")
    descripcion = Column(String, nullable=True)
    fecha = Column(DateTime, default=ahora_peru)
    orden_servicio_id = Column(Integer, ForeignKey("ordenes_servicio.id"), nullable=True)  # ya no se usa para crear ingresos nuevos, se deja por compatibilidad
    pago_proyecto_id = Column(Integer, ForeignKey("pagos_proyecto.id"), nullable=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True)
    tipo_comprobante = Column(String, nullable=True)  # factura, boleta, sin_comprobante...

    negocio = relationship("Negocio", back_populates="ingresos")


class Egreso(Base):
    __tablename__ = "egresos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    categoria = Column(String, nullable=False)  # compra_insumo, planilla, servicios, etc.
    monto = Column(Float, nullable=False)
    descripcion = Column(String, nullable=True)
    fecha = Column(DateTime, default=ahora_peru)
    pago_proveedor_id = Column(Integer, ForeignKey("pagos_proveedor.id"), nullable=True)
    tipo_comprobante = Column(String, nullable=True)  # factura, boleta, sin_comprobante...
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=True)  # gasto asignado directo a un proyecto (opcional)

    negocio = relationship("Negocio", back_populates="egresos")
    proyecto = relationship("Proyecto", back_populates="egresos_directos")


class PagoProveedor(Base):
    """
    Un pago realizado a un proveedor. Separado de Compra a propósito —
    comprar (recibir el insumo) y pagar son dos momentos distintos; la
    diferencia entre lo comprado y lo pagado es la cuenta por pagar.
    """
    __tablename__ = "pagos_proveedor"

    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    monto = Column(Float, nullable=False)
    fecha_pago = Column(DateTime, nullable=False, default=ahora_peru)
    medio_pago = Column(String, nullable=False, default="transferencia")
    descripcion = Column(String, nullable=True)

    proveedor = relationship("Proveedor", back_populates="pagos")
    negocio = relationship("Negocio")


class CajaChica(Base):
    """Fondo fijo para gastos menores de oficina, separado de la caja del POS."""
    __tablename__ = "cajas_chicas"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    nombre = Column(String, nullable=False, default="Caja chica")
    monto_fondo = Column(Float, nullable=False, default=0)

    negocio = relationship("Negocio")
    movimientos = relationship(
        "MovimientoCajaChica", back_populates="caja_chica", cascade="all, delete-orphan", order_by="MovimientoCajaChica.fecha"
    )


class MovimientoCajaChica(Base):
    """Un gasto menor (genera egreso real) o una reposición de fondo (no genera egreso)."""
    __tablename__ = "movimientos_caja_chica"

    id = Column(Integer, primary_key=True, index=True)
    caja_chica_id = Column(Integer, ForeignKey("cajas_chicas.id"), nullable=False)
    tipo = Column(String, nullable=False)  # gasto, reposicion
    monto = Column(Float, nullable=False)
    categoria = Column(String, nullable=True)  # utiles, transporte, limpieza, otros (solo gastos)
    descripcion = Column(String, nullable=True)
    comprobante = Column(String, nullable=True)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=True)
    fecha = Column(DateTime, default=ahora_peru)
    egreso_id = Column(Integer, ForeignKey("egresos.id"), nullable=True)  # solo para gastos

    caja_chica = relationship("CajaChica", back_populates="movimientos")
    colaborador = relationship("Colaborador")


class Servicio(Base):
    """Catálogo de la Librería: impresión, escaneo, copia, anillado, etc."""
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    nombre = Column(String, nullable=False)  # "Impresión A4 B/N", "Anillado", "Sello"
    categoria = Column(String, nullable=False)  # impresion_bn, impresion_color, escaneo, copia, anillado, enmicado, sello, tipeo, otro
    tamano = Column(String, nullable=True)  # A4, A3, A2, A1, A0 (si aplica)
    precio_unitario = Column(Float, nullable=False)
    unidad = Column(String, nullable=False, default="unidad")  # hoja, unidad, servicio
    activo = Column(Boolean, default=True)

    # Vínculo opcional a un insumo: si se define, cada venta descuenta stock solo.
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=True)
    consumo_insumo_por_unidad = Column(Float, nullable=False, default=0)

    insumo = relationship("Insumo")


class CajaSesion(Base):
    """Apertura/cierre de caja diaria, con arqueo."""
    __tablename__ = "caja_sesiones"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=False)
    fecha_apertura = Column(DateTime, default=ahora_peru)
    monto_apertura = Column(Float, nullable=False, default=0)
    fecha_cierre = Column(DateTime, nullable=True)
    monto_cierre_esperado = Column(Float, nullable=True)
    monto_cierre_reportado = Column(Float, nullable=True)
    estado = Column(String, nullable=False, default="abierta")  # abierta | cerrada

    ventas = relationship("Venta", back_populates="caja_sesion")


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    caja_sesion_id = Column(Integer, ForeignKey("caja_sesiones.id"), nullable=False)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=False)
    cliente = Column(String, nullable=True)
    medio_pago = Column(String, nullable=False, default="efectivo")
    total = Column(Float, nullable=False, default=0)
    fecha = Column(DateTime, default=ahora_peru)

    caja_sesion = relationship("CajaSesion", back_populates="ventas")
    items = relationship("VentaItem", back_populates="venta", cascade="all, delete-orphan")


class VentaItem(Base):
    __tablename__ = "venta_items"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False)
    cantidad = Column(Float, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    venta = relationship("Venta", back_populates="items")
    servicio = relationship("Servicio")


class TipoProyecto(Base):
    """
    Catálogo editable de tipos de proyecto/servicio de la Constructora
    (elaboración de planos, ejecución de obra, supervisión, consultoría
    estructural, etc.). A diferencia de una lista fija en el código, el
    administrador puede agregar y editar estos tipos según lo que la
    empresa realmente ofrezca.
    """
    __tablename__ = "tipos_proyecto"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    nombre = Column(String, nullable=False)


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    contacto = Column(String, nullable=True)
    documento_tipo = Column(String, nullable=True)  # RUC (factura) o DNI (boleta)
    documento_numero = Column(String, nullable=True)

    proyectos = relationship("Proyecto", back_populates="cliente")


class Proyecto(Base):
    """Proyecto de la Constructora: agrupa los servicios técnicos entregados a un cliente."""
    __tablename__ = "proyectos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    nombre = Column(String, nullable=False)
    tipo_proyecto = Column(String, nullable=True)  # texto libre, respaldado por el catálogo TipoProyecto
    estado = Column(String, nullable=False, default="cotizacion")  # cotizacion, en_proceso, entregado, cancelado
    fecha_inicio = Column(DateTime, default=ahora_peru)
    fecha_entrega_estimada = Column(DateTime, nullable=True)
    presupuesto = Column(Float, nullable=True)  # monto planeado, para comparar contra lo facturado

    cliente = relationship("Cliente", back_populates="proyectos")
    ordenes = relationship("OrdenServicio", back_populates="proyecto", cascade="all, delete-orphan")
    pagos = relationship(
        "PagoProyecto", back_populates="proyecto", cascade="all, delete-orphan", order_by="PagoProyecto.fecha_pago"
    )
    contratos = relationship("Contrato", back_populates="proyecto", cascade="all, delete-orphan")
    registros_tiempo = relationship("RegistroTiempo", back_populates="proyecto", cascade="all, delete-orphan")
    ampliaciones = relationship(
        "AmpliacionPlazo", back_populates="proyecto", cascade="all, delete-orphan", order_by="AmpliacionPlazo.fecha_registro"
    )
    partidas = relationship(
        "Partida", back_populates="proyecto", cascade="all, delete-orphan", order_by="Partida.orden"
    )
    egresos_directos = relationship("Egreso", back_populates="proyecto")


class AmpliacionPlazo(Base):
    """
    Registro de una ampliación (extensión) del plazo de entrega de un
    proyecto — conserva la fecha anterior y el motivo, para tener el
    historial de cada vez que se extendió, no solo la fecha actual.
    """
    __tablename__ = "ampliaciones_plazo"

    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    fecha_entrega_anterior = Column(DateTime, nullable=True)
    fecha_entrega_nueva = Column(DateTime, nullable=False)
    motivo = Column(String, nullable=True)
    fecha_registro = Column(DateTime, default=ahora_peru)

    proyecto = relationship("Proyecto", back_populates="ampliaciones")


class Contrato(Base):
    """Un contrato (o adenda) asociado a un proyecto."""
    __tablename__ = "contratos"

    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    numero = Column(String, nullable=True)  # "CONT-2026-001"
    fecha_firma = Column(DateTime, nullable=True)
    monto_contrato = Column(Float, nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin_estimada = Column(DateTime, nullable=True)
    estado = Column(String, nullable=False, default="vigente")  # vigente, finalizado, rescindido
    archivo_url = Column(String, nullable=True)  # link al documento (Drive, etc.)
    observaciones = Column(String, nullable=True)

    proyecto = relationship("Proyecto", back_populates="contratos")


class RegistroTiempo(Base):
    """Horas dedicadas por un colaborador a un proyecto, en una fecha dada."""
    __tablename__ = "registros_tiempo"

    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=False)
    fecha = Column(Date, default=lambda: ahora_peru().date())
    horas = Column(Float, nullable=False)
    descripcion = Column(String, nullable=True)

    proyecto = relationship("Proyecto", back_populates="registros_tiempo")
    colaborador = relationship("Colaborador")


class OrdenServicio(Base):
    """
    Un servicio técnico entregado dentro de un proyecto (un plano, un
    expediente técnico, un estudio de suelos, un ploteo...). Al crearse,
    genera el ingreso correspondiente y descuenta insumos igual que en el POS.
    """
    __tablename__ = "ordenes_servicio"

    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=False)
    cantidad = Column(Float, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    fecha = Column(DateTime, default=ahora_peru)
    estado = Column(String, nullable=False, default="entregado")  # pendiente, entregado
    fecha = Column(DateTime, default=ahora_peru)

    proyecto = relationship("Proyecto", back_populates="ordenes")
    servicio = relationship("Servicio")
    colaborador = relationship("Colaborador")


class PagoProyecto(Base):
    """
    Un pago recibido contra un proyecto: el adelanto inicial, cada cuota,
    o el pago final. Separado de OrdenServicio a propósito — lo facturado
    (suma de órdenes) y lo efectivamente cobrado (suma de pagos) son dos
    cosas distintas; la diferencia es el saldo pendiente.
    """
    __tablename__ = "pagos_proyecto"

    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    monto = Column(Float, nullable=False)
    fecha_pago = Column(DateTime, nullable=False, default=ahora_peru)
    tipo = Column(String, nullable=False, default="cuota")  # adelanto, cuota, pago_final, otro
    medio_pago = Column(String, nullable=False, default="efectivo")
    descripcion = Column(String, nullable=True)

    proyecto = relationship("Proyecto", back_populates="pagos")


class PuestoTrabajo(Base):
    """
    Un stand/puesto de trabajo (mostrador de la librería, mesa de dibujo,
    etc.), con un colaborador a cargo y sus equipos (computadoras,
    fotocopiadoras, impresoras). Sirve de base para la conciliación
    diaria: comparar lo vendido/impreso de cada puesto contra su encargado.
    """
    __tablename__ = "puestos_trabajo"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    nombre = Column(String, nullable=False)  # "Stand 1", "Mostrador principal", etc.
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=True)

    negocio = relationship("Negocio")
    colaborador = relationship("Colaborador")
    equipos = relationship("Equipo", back_populates="puesto", cascade="all, delete-orphan")


class Equipo(Base):
    """Una computadora, fotocopiadora, impresora o plotter asignada a un puesto de trabajo."""
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True, index=True)
    puesto_id = Column(Integer, ForeignKey("puestos_trabajo.id"), nullable=False)
    tipo = Column(String, nullable=False)  # computadora, fotocopiadora, impresora, plotter
    nombre = Column(String, nullable=False)  # "PC-01", "Canon IR2006", etc.

    puesto = relationship("PuestoTrabajo", back_populates="equipos")
    mantenimientos = relationship("Mantenimiento", back_populates="equipo", cascade="all, delete-orphan")


class Mantenimiento(Base):
    """Un mantenimiento (preventivo o correctivo) realizado o programado para un equipo."""
    __tablename__ = "mantenimientos"

    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    tipo = Column(String, nullable=False, default="preventivo")  # preventivo, correctivo
    fecha_realizado = Column(DateTime, nullable=True)
    fecha_proximo = Column(Date, nullable=True)  # próximo mantenimiento programado
    descripcion = Column(String, nullable=True)
    costo = Column(Float, nullable=True)
    responsable_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)

    equipo = relationship("Equipo", back_populates="mantenimientos")
    responsable = relationship("Colaborador")
    proveedor = relationship("Proveedor")


class EventoAgenda(Base):
    """Un evento de la agenda del estudio: reunión, visita de obra, entrega, etc."""
    __tablename__ = "eventos_agenda"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    tipo = Column(String, nullable=False, default="reunion")  # reunion, visita_obra, entrega, otro
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)
    ubicacion = Column(String, nullable=True)
    responsable_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=True)
    estado = Column(String, nullable=False, default="pendiente")  # pendiente, completado, cancelado

    negocio = relationship("Negocio")
    proyecto = relationship("Proyecto")
    responsable = relationship("Colaborador")


class Asistencia(Base):
    """Registro de entrada/salida de un colaborador (Fase 4)."""
    __tablename__ = "asistencias"

    id = Column(Integer, primary_key=True, index=True)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=False)
    fecha = Column(Date, default=lambda: ahora_peru().date())
    hora_entrada = Column(DateTime, default=ahora_peru)
    hora_salida = Column(DateTime, nullable=True)

    colaborador = relationship("Colaborador")


class RegistroImpresion(Base):
    """
    Conteo de impresiones/ploteos (Fase 5). Se alimenta de dos formas:
    - Manual: un registro a la vez (POST /impresiones/).
    - Importado: subiendo el reporte que exporte el software de conteo
      (PaperCut, YSoft SafeQ, u otro) como CSV (POST /impresiones/importar-csv).

    El costo estimado no se guarda aquí: se calcula al pedir el resumen,
    cruzando categoria/tamaño contra el catálogo de servicios ya existente.
    """
    __tablename__ = "registros_impresion"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=True)
    colaborador_nombre_original = Column(String, nullable=True)  # tal cual venía en el CSV
    equipo = Column(String, nullable=False)  # nombre/IP de la impresora o plotter (texto libre, como venía del CSV)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=True)  # vínculo opcional al catálogo formal
    tipo_trabajo = Column(String, nullable=False)  # impresion_bn, impresion_color, escaneo, ploteo
    tamano = Column(String, nullable=True)  # A4, A3, A2, A1, A0
    cantidad = Column(Float, nullable=False)  # páginas o m2, según el tipo
    fecha = Column(DateTime, default=ahora_peru)
    origen = Column(String, nullable=False, default="manual")  # manual, csv_import

    negocio = relationship("Negocio")
    colaborador = relationship("Colaborador")


class Partida(Base):
    """
    Una etapa o partida de obra dentro de un proyecto (cimentación,
    estructura, acabados, instalaciones, etc.) — catálogo editable por
    proyecto, sobre el que se reporta el avance desde campo. El
    porcentaje de avance de una partida es el de su reporte más
    reciente (no se guarda aparte, para no tener dos fuentes de verdad).
    """
    __tablename__ = "partidas"

    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    nombre = Column(String, nullable=False)
    orden = Column(Integer, nullable=False, default=0)

    proyecto = relationship("Proyecto", back_populates="partidas")
    reportes = relationship(
        "ReporteAvance", back_populates="partida", cascade="all, delete-orphan", order_by="ReporteAvance.fecha"
    )


class ReporteAvance(Base):
    """
    Un reporte de avance de campo sobre una partida específica: el
    nuevo porcentaje (valor absoluto, no incremento), una descripción
    de lo realizado, fotos, y opcionalmente una incidencia (problema,
    retraso, algo que requiere atención).
    """
    __tablename__ = "reportes_avance"

    id = Column(Integer, primary_key=True, index=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=True)
    fecha = Column(DateTime, default=ahora_peru)
    porcentaje_avance = Column(Float, nullable=False)
    descripcion = Column(String, nullable=True)
    tiene_incidencia = Column(Boolean, nullable=False, default=False)
    incidencia_gravedad = Column(String, nullable=True)  # baja, media, alta
    incidencia_descripcion = Column(String, nullable=True)
    incidencia_resuelta = Column(Boolean, nullable=True)

    partida = relationship("Partida", back_populates="reportes")
    colaborador = relationship("Colaborador")
    fotos = relationship("FotoAvance", back_populates="reporte", cascade="all, delete-orphan")


class FotoAvance(Base):
    """Una foto asociada a un reporte de avance. Solo se guarda la URL — el archivo vive en Cloudinary."""
    __tablename__ = "fotos_avance"

    id = Column(Integer, primary_key=True, index=True)
    reporte_id = Column(Integer, ForeignKey("reportes_avance.id"), nullable=False)
    url = Column(String, nullable=False)

    reporte = relationship("ReporteAvance", back_populates="fotos")


class SerieComprobante(Base):
    """
    Serie y siguiente correlativo disponible para cada negocio + tipo de
    comprobante (ej. Imprenta + boleta = serie "B001"). SUNAT exige que
    el correlativo suba de 1 en 1, sin saltos ni repetirse — esta tabla
    es la única fuente de verdad para el siguiente número.
    """
    __tablename__ = "series_comprobante"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    tipo = Column(String, nullable=False)  # factura, boleta
    serie = Column(String, nullable=False)  # "F001", "B001"
    siguiente_numero = Column(Integer, nullable=False, default=1)

    negocio = relationship("Negocio")


class ComprobanteElectronico(Base):
    """
    Registro de cada factura/boleta electrónica emitida vía el OSE
    (NubeFacT). Guarda el resultado real de SUNAT, no solo la intención
    de facturar — para tener trazabilidad completa y poder reintentar
    si algo falló.
    """
    __tablename__ = "comprobantes_electronicos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    tipo = Column(String, nullable=False)  # factura, boleta
    serie = Column(String, nullable=False)
    numero = Column(Integer, nullable=False)
    cliente_nombre = Column(String, nullable=False)
    cliente_documento_tipo = Column(String, nullable=True)
    cliente_documento_numero = Column(String, nullable=True)
    subtotal = Column(Float, nullable=False)
    igv = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    fecha_emision = Column(DateTime, default=ahora_peru)
    estado_sunat = Column(String, nullable=False, default="pendiente")  # pendiente, aceptado, rechazado, observado
    enlace_pdf = Column(String, nullable=True)
    enlace_xml = Column(String, nullable=True)
    respuesta_sunat = Column(String, nullable=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True)
    pago_proyecto_id = Column(Integer, ForeignKey("pagos_proyecto.id"), nullable=True)

    negocio = relationship("Negocio")
    venta = relationship("Venta")
    pago_proyecto = relationship("PagoProyecto")


class RegistroAuditoria(Base):
    """
    Quién hizo qué y cuándo, para las acciones sensibles del sistema
    (dinero, permisos, accesos). No se guarda para absolutamente todo
    — se enfoca en lo que de verdad importa auditar. Nunca se edita ni
    se borra una vez creado.
    """
    __tablename__ = "registros_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_username = Column(String, nullable=True)  # copia textual, para que sobreviva aunque se borre el usuario
    accion = Column(String, nullable=False)  # crear, editar, eliminar
    entidad = Column(String, nullable=False)  # "ingreso", "egreso", "pago_proyecto", "rol", "usuario", etc.
    entidad_id = Column(Integer, nullable=True)
    detalle = Column(String, nullable=True)  # descripción legible de qué cambió
    fecha = Column(DateTime, default=ahora_peru)

    usuario = relationship("Usuario")
