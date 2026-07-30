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
    creado_en = Column(DateTime, default=datetime.utcnow)

    negocio = relationship("Negocio", back_populates="colaboradores")
    usuario = relationship("Usuario", back_populates="colaborador", uselist=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol_permiso = Column(String, nullable=False, default="colaborador")  # admin | colaborador

    colaborador = relationship("Colaborador", back_populates="usuario")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    contacto = Column(String, nullable=True)

    compras = relationship("Compra", back_populates="proveedor")


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
    fecha = Column(DateTime, default=datetime.utcnow)

    proveedor = relationship("Proveedor", back_populates="compras")
    insumo = relationship("Insumo", back_populates="compras")


class Ingreso(Base):
    __tablename__ = "ingresos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    monto = Column(Float, nullable=False)
    medio_pago = Column(String, nullable=False, default="efectivo")
    descripcion = Column(String, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    orden_servicio_id = Column(Integer, ForeignKey("ordenes_servicio.id"), nullable=True)

    negocio = relationship("Negocio", back_populates="ingresos")


class Egreso(Base):
    __tablename__ = "egresos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    categoria = Column(String, nullable=False)  # compra_insumo, planilla, servicios, etc.
    monto = Column(Float, nullable=False)
    descripcion = Column(String, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)

    negocio = relationship("Negocio", back_populates="egresos")


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
    fecha_apertura = Column(DateTime, default=datetime.utcnow)
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
    fecha = Column(DateTime, default=datetime.utcnow)

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

    proyectos = relationship("Proyecto", back_populates="cliente")


class Proyecto(Base):
    """Proyecto de la Constructora: agrupa los servicios técnicos entregados a un cliente."""
    __tablename__ = "proyectos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    nombre = Column(String, nullable=False)
    tipo_proyecto = Column(String, nullable=True)  # elaboracion_planos, ejecucion_obra, otro
    estado = Column(String, nullable=False, default="cotizacion")  # cotizacion, en_proceso, entregado, cancelado
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_entrega_estimada = Column(DateTime, nullable=True)

    cliente = relationship("Cliente", back_populates="proyectos")
    ordenes = relationship("OrdenServicio", back_populates="proyecto", cascade="all, delete-orphan")


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
    estado = Column(String, nullable=False, default="entregado")  # pendiente, entregado
    fecha = Column(DateTime, default=datetime.utcnow)

    proyecto = relationship("Proyecto", back_populates="ordenes")
    servicio = relationship("Servicio")
    colaborador = relationship("Colaborador")


class Asistencia(Base):
    """Registro de entrada/salida de un colaborador (Fase 4)."""
    __tablename__ = "asistencias"

    id = Column(Integer, primary_key=True, index=True)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=False)
    fecha = Column(Date, default=lambda: datetime.utcnow().date())
    hora_entrada = Column(DateTime, default=datetime.utcnow)
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
    equipo = Column(String, nullable=False)  # nombre/IP de la impresora o plotter
    tipo_trabajo = Column(String, nullable=False)  # impresion_bn, impresion_color, escaneo, ploteo
    tamano = Column(String, nullable=True)  # A4, A3, A2, A1, A0
    cantidad = Column(Float, nullable=False)  # páginas o m2, según el tipo
    fecha = Column(DateTime, default=datetime.utcnow)
    origen = Column(String, nullable=False, default="manual")  # manual, csv_import

    negocio = relationship("Negocio")
    colaborador = relationship("Colaborador")
