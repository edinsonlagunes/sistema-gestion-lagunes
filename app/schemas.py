from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------- Negocio ----------
class NegocioBase(BaseModel):
    nombre: str


class NegocioCreate(NegocioBase):
    pass


class Negocio(NegocioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Colaborador ----------
class ColaboradorBase(BaseModel):
    nombre: str
    negocio_id: int
    rol: str
    activo: bool = True
    sueldo_semanal: Optional[float] = None
    hora_entrada_esperada: Optional[str] = None  # "HH:MM"


class ColaboradorCreate(ColaboradorBase):
    pass


class ColaboradorUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None
    sueldo_semanal: Optional[float] = None
    hora_entrada_esperada: Optional[str] = None


class Colaborador(ColaboradorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    creado_en: datetime


# ---------- Usuario ----------
class UsuarioCreate(BaseModel):
    colaborador_id: int
    username: str
    password: str
    rol_permiso: str = "colaborador"


class Usuario(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    colaborador_id: int
    username: str
    rol_permiso: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- Proveedor ----------
class ProveedorBase(BaseModel):
    nombre: str
    contacto: Optional[str] = None


class ProveedorCreate(ProveedorBase):
    pass


class Proveedor(ProveedorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PagoProveedorCreate(BaseModel):
    monto: float
    fecha_pago: Optional[datetime] = None
    medio_pago: str = "transferencia"
    descripcion: Optional[str] = None


class PagoProveedorUpdate(BaseModel):
    monto: Optional[float] = None
    fecha_pago: Optional[datetime] = None
    medio_pago: Optional[str] = None
    descripcion: Optional[str] = None


class PagoProveedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    proveedor_id: int
    negocio_id: int
    monto: float
    fecha_pago: datetime
    medio_pago: str
    descripcion: Optional[str] = None


class ProveedorDetalle(Proveedor):
    total_comprado: float
    total_pagado: float
    saldo_pendiente: float
    pagos: list[PagoProveedorOut]


class ResumenPagoProveedor(BaseModel):
    proveedor_id: int
    proveedor_nombre: str
    total_comprado: float
    total_pagado: float
    saldo_pendiente: float
    ultimo_pago_monto: Optional[float] = None
    ultimo_pago_fecha: Optional[datetime] = None


# ---------- Insumo ----------
class InsumoBase(BaseModel):
    negocio_id: int
    nombre: str
    unidad: str
    stock_actual: float = 0
    stock_minimo: float = 0


class InsumoCreate(InsumoBase):
    pass


class Insumo(InsumoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Compra (descuenta stock, genera egreso) ----------
class CompraCreate(BaseModel):
    negocio_id: int
    proveedor_id: int
    insumo_id: int
    cantidad: float
    costo: float


class Compra(CompraCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha: datetime


# ---------- Ingreso ----------
class IngresoCreate(BaseModel):
    negocio_id: int
    monto: float
    medio_pago: str = "efectivo"
    descripcion: Optional[str] = None


class Ingreso(IngresoCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha: datetime


# ---------- Egreso ----------
class EgresoCreate(BaseModel):
    negocio_id: int
    categoria: str
    monto: float
    descripcion: Optional[str] = None


class Egreso(EgresoCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha: datetime


# ---------- Servicio (catálogo Librería) ----------
class ServicioBase(BaseModel):
    negocio_id: int
    nombre: str
    categoria: str
    tamano: Optional[str] = None
    precio_unitario: float
    unidad: str = "unidad"
    activo: bool = True
    insumo_id: Optional[int] = None
    consumo_insumo_por_unidad: float = 0


class ServicioCreate(ServicioBase):
    pass


class ServicioUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    tamano: Optional[str] = None
    precio_unitario: Optional[float] = None
    unidad: Optional[str] = None
    activo: Optional[bool] = None
    insumo_id: Optional[int] = None
    consumo_insumo_por_unidad: Optional[float] = None


class Servicio(ServicioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Caja ----------
class CajaAbrirRequest(BaseModel):
    negocio_id: int
    colaborador_id: int
    monto_apertura: float = 0


class CajaCerrarRequest(BaseModel):
    monto_cierre_reportado: float


class CajaSesion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negocio_id: int
    colaborador_id: int
    fecha_apertura: datetime
    monto_apertura: float
    fecha_cierre: Optional[datetime] = None
    monto_cierre_esperado: Optional[float] = None
    monto_cierre_reportado: Optional[float] = None
    estado: str


# ---------- Ventas ----------
class VentaItemCreate(BaseModel):
    servicio_id: int
    cantidad: float


class VentaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    servicio_id: int
    cantidad: float
    precio_unitario: float
    subtotal: float


class VentaCreate(BaseModel):
    negocio_id: int
    colaborador_id: int
    medio_pago: str = "efectivo"
    cliente: Optional[str] = None
    items: list[VentaItemCreate]


class Venta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negocio_id: int
    caja_sesion_id: int
    colaborador_id: int
    cliente: Optional[str] = None
    medio_pago: str
    total: float
    fecha: datetime
    items: list[VentaItemOut]


# ---------- Tipos de proyecto (catálogo editable) ----------
class TipoProyectoCreate(BaseModel):
    negocio_id: int
    nombre: str


class TipoProyectoUpdate(BaseModel):
    nombre: str


class TipoProyecto(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negocio_id: int
    nombre: str


# ---------- Clientes ----------
class ClienteBase(BaseModel):
    nombre: str
    contacto: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class Cliente(ClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Proyectos (Constructora) ----------
class ProyectoBase(BaseModel):
    negocio_id: int
    cliente_id: int
    nombre: str
    tipo_proyecto: Optional[str] = None
    estado: str = "cotizacion"
    fecha_entrega_estimada: Optional[datetime] = None
    presupuesto: Optional[float] = None


class ProyectoCreate(ProyectoBase):
    pass


class ProyectoEstadoUpdate(BaseModel):
    estado: str


class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo_proyecto: Optional[str] = None
    cliente_id: Optional[int] = None
    fecha_inicio: Optional[datetime] = None
    fecha_entrega_estimada: Optional[datetime] = None
    presupuesto: Optional[float] = None


class OrdenServicioCreate(BaseModel):
    servicio_id: int
    colaborador_id: int
    cantidad: float


class OrdenServicioUpdate(BaseModel):
    cantidad: float


class OrdenServicioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    servicio_id: int
    colaborador_id: int
    cantidad: float
    precio_unitario: float
    subtotal: float
    estado: str
    fecha: datetime


class Proyecto(ProyectoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha_inicio: datetime


class PagoProyectoCreate(BaseModel):
    monto: float
    fecha_pago: Optional[datetime] = None
    tipo: str = "cuota"  # adelanto, cuota, pago_final, otro
    medio_pago: str = "efectivo"
    descripcion: Optional[str] = None


class PagoProyectoUpdate(BaseModel):
    monto: Optional[float] = None
    fecha_pago: Optional[datetime] = None
    tipo: Optional[str] = None
    medio_pago: Optional[str] = None
    descripcion: Optional[str] = None


class PagoProyectoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    proyecto_id: int
    monto: float
    fecha_pago: datetime
    tipo: str
    medio_pago: str
    descripcion: Optional[str] = None


class ResumenPagoProyecto(BaseModel):
    proyecto_id: int
    nombre: str
    tipo_proyecto: Optional[str] = None
    total_facturado: float
    total_pagado: float
    saldo_pendiente: float
    ultimo_pago_monto: Optional[float] = None
    ultimo_pago_fecha: Optional[datetime] = None


class ContratoCreate(BaseModel):
    numero: Optional[str] = None
    fecha_firma: Optional[datetime] = None
    monto_contrato: Optional[float] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin_estimada: Optional[datetime] = None
    estado: str = "vigente"  # vigente, finalizado, rescindido
    archivo_url: Optional[str] = None
    observaciones: Optional[str] = None


class ContratoUpdate(BaseModel):
    numero: Optional[str] = None
    fecha_firma: Optional[datetime] = None
    monto_contrato: Optional[float] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin_estimada: Optional[datetime] = None
    estado: Optional[str] = None
    archivo_url: Optional[str] = None
    observaciones: Optional[str] = None


class ContratoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    proyecto_id: int
    numero: Optional[str] = None
    fecha_firma: Optional[datetime] = None
    monto_contrato: Optional[float] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin_estimada: Optional[datetime] = None
    estado: str
    archivo_url: Optional[str] = None
    observaciones: Optional[str] = None


class RegistroTiempoCreate(BaseModel):
    colaborador_id: int
    fecha: Optional[date] = None
    horas: float
    descripcion: Optional[str] = None


class RegistroTiempoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    proyecto_id: int
    colaborador_id: int
    fecha: date
    horas: float
    descripcion: Optional[str] = None


class AmpliacionPlazoCreate(BaseModel):
    fecha_entrega_nueva: datetime
    motivo: Optional[str] = None


class AmpliacionPlazoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    proyecto_id: int
    fecha_entrega_anterior: Optional[datetime] = None
    fecha_entrega_nueva: datetime
    motivo: Optional[str] = None
    fecha_registro: datetime


class ProyectoDetalle(Proyecto):
    ordenes: list[OrdenServicioOut]
    pagos: list[PagoProyectoOut]
    contratos: list[ContratoOut]
    registros_tiempo: list[RegistroTiempoOut]
    ampliaciones: list[AmpliacionPlazoOut]
    total_facturado: float
    total_pagado: float
    saldo_pendiente: float
    total_horas: float
    porcentaje_presupuesto_ejecutado: Optional[float] = None


# ---------- Mantenimiento de equipos ----------
class MantenimientoCreate(BaseModel):
    tipo: str = "preventivo"  # preventivo, correctivo
    fecha_realizado: Optional[datetime] = None
    fecha_proximo: Optional[date] = None
    descripcion: Optional[str] = None
    costo: Optional[float] = None
    responsable_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    generar_egreso: bool = True  # si tiene costo, registrar el egreso ahora mismo (se asumió pagado al momento)


class MantenimientoUpdate(BaseModel):
    tipo: Optional[str] = None
    fecha_realizado: Optional[datetime] = None
    fecha_proximo: Optional[date] = None
    descripcion: Optional[str] = None
    costo: Optional[float] = None
    responsable_id: Optional[int] = None
    proveedor_id: Optional[int] = None


class MantenimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    equipo_id: int
    tipo: str
    fecha_realizado: Optional[datetime] = None
    fecha_proximo: Optional[date] = None
    descripcion: Optional[str] = None
    costo: Optional[float] = None
    responsable_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    dias_para_proximo: Optional[int] = None


# ---------- Agenda del estudio ----------
class EventoAgendaCreate(BaseModel):
    negocio_id: int
    proyecto_id: Optional[int] = None
    titulo: str
    descripcion: Optional[str] = None
    tipo: str = "reunion"  # reunion, visita_obra, entrega, otro
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    ubicacion: Optional[str] = None
    responsable_id: Optional[int] = None
    estado: str = "pendiente"


class EventoAgendaUpdate(BaseModel):
    proyecto_id: Optional[int] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    tipo: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    ubicacion: Optional[str] = None
    responsable_id: Optional[int] = None
    estado: Optional[str] = None


class EventoAgendaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negocio_id: int
    proyecto_id: Optional[int] = None
    titulo: str
    descripcion: Optional[str] = None
    tipo: str
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    ubicacion: Optional[str] = None
    responsable_id: Optional[int] = None
    estado: str


# ---------- Planillas (pagos semanales) ----------
class PlanillaGenerar(BaseModel):
    negocio_id: int
    fecha_inicio: date
    fecha_fin: date


class DetallePlanillaUpdate(BaseModel):
    otros_descuentos: Optional[float] = None
    observaciones: Optional[str] = None


class DetallePlanillaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    planilla_id: int
    colaborador_id: int
    sueldo_base: float
    dias_falta: int
    monto_descuento_faltas: float
    minutos_tardanza: int
    monto_descuento_tardanzas: float
    otros_descuentos: float
    observaciones: Optional[str] = None
    monto_neto: float


class PlanillaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negocio_id: int
    fecha_inicio: date
    fecha_fin: date
    estado: str
    fecha_pago: Optional[datetime] = None


class PlanillaDetalle(PlanillaOut):
    detalles: list[DetallePlanillaOut]
    total_neto: float


# ---------- Documentos (permisos, archivo técnico, licitaciones) ----------
class DocumentoCreate(BaseModel):
    negocio_id: int
    proyecto_id: Optional[int] = None
    tipo: str  # permiso_municipal, archivo_tecnico, licitacion, otro
    nombre: str
    numero: Optional[str] = None
    entidad: Optional[str] = None
    fecha_emision: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    estado: str = "vigente"
    archivo_url: Optional[str] = None
    observaciones: Optional[str] = None
    responsable_id: Optional[int] = None


class DocumentoUpdate(BaseModel):
    proyecto_id: Optional[int] = None
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    numero: Optional[str] = None
    entidad: Optional[str] = None
    fecha_emision: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    estado: Optional[str] = None
    archivo_url: Optional[str] = None
    observaciones: Optional[str] = None
    responsable_id: Optional[int] = None


class DocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negocio_id: int
    proyecto_id: Optional[int] = None
    tipo: str
    nombre: str
    numero: Optional[str] = None
    entidad: Optional[str] = None
    fecha_emision: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    estado: str
    archivo_url: Optional[str] = None
    observaciones: Optional[str] = None
    responsable_id: Optional[int] = None
    dias_para_vencer: Optional[int] = None


# ---------- Puestos de trabajo y equipos ----------
class EquipoCreate(BaseModel):
    tipo: str  # computadora, fotocopiadora, impresora, plotter
    nombre: str


class EquipoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    puesto_id: int
    tipo: str
    nombre: str


class PuestoTrabajoCreate(BaseModel):
    negocio_id: int
    nombre: str
    colaborador_id: Optional[int] = None


class PuestoTrabajoUpdate(BaseModel):
    nombre: Optional[str] = None
    colaborador_id: Optional[int] = None


class PuestoTrabajoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negocio_id: int
    nombre: str
    colaborador_id: Optional[int] = None
    equipos: list[EquipoOut]


# ---------- Asistencia ----------
class AsistenciaMarcarRequest(BaseModel):
    colaborador_id: int


class Asistencia(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    colaborador_id: int
    fecha: date
    hora_entrada: datetime
    hora_salida: Optional[datetime] = None
    horas_trabajadas: Optional[float] = None


# ---------- Caja chica ----------
class CajaChicaCreate(BaseModel):
    negocio_id: int
    nombre: str = "Caja chica"
    monto_fondo: float = 0


class MovimientoCajaChicaCreate(BaseModel):
    tipo: str  # gasto, reposicion
    monto: float
    categoria: Optional[str] = None
    descripcion: Optional[str] = None
    comprobante: Optional[str] = None
    colaborador_id: Optional[int] = None
    fecha: Optional[datetime] = None


class MovimientoCajaChicaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    caja_chica_id: int
    tipo: str
    monto: float
    categoria: Optional[str] = None
    descripcion: Optional[str] = None
    comprobante: Optional[str] = None
    colaborador_id: Optional[int] = None
    fecha: datetime


class CajaChicaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negocio_id: int
    nombre: str
    monto_fondo: float


class CajaChicaDetalle(CajaChicaOut):
    saldo_actual: float
    movimientos: list[MovimientoCajaChicaOut]


# ---------- Registros de impresión/ploteo (Fase 5) ----------
class RegistroImpresionCreate(BaseModel):
    negocio_id: int
    colaborador_id: Optional[int] = None
    equipo: str
    tipo_trabajo: str
    tamano: Optional[str] = None
    cantidad: float
    fecha: Optional[datetime] = None


class RegistroImpresion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negocio_id: int
    colaborador_id: Optional[int] = None
    colaborador_nombre_original: Optional[str] = None
    equipo: str
    tipo_trabajo: str
    tamano: Optional[str] = None
    cantidad: float
    fecha: datetime
    origen: str


class ImportarCSVResultado(BaseModel):
    filas_procesadas: int
    filas_con_error: int
    errores: list[str]


class ResumenImpresionItem(BaseModel):
    colaborador: str
    tipo_trabajo: str
    tamano: Optional[str] = None
    equipo: str
    total_cantidad: float
    costo_estimado: float


# ---------- Dashboard ----------
class ResumenNegocio(BaseModel):
    negocio_id: int
    negocio_nombre: str
    total_ingresos: float
    total_egresos: float
    balance: float
    insumos_bajo_stock: int


# ---------- Movimientos del día, conciliación y reportes (solo admin) ----------
class MovimientoFinanciero(BaseModel):
    tipo: str  # ingreso | egreso
    id: int
    negocio_id: int
    monto: float
    medio_pago: Optional[str] = None  # solo en ingresos
    categoria: Optional[str] = None  # solo en egresos
    descripcion: Optional[str] = None
    fecha: datetime
    venta_id: Optional[int] = None  # si el ingreso viene de una venta del POS, para poder corregirla ahí mismo


class MovimientosDiaResumen(BaseModel):
    fecha: date
    total_ingresos: float
    total_egresos: float
    balance: float
    movimientos: list[MovimientoFinanciero]


class ConciliacionColaborador(BaseModel):
    colaborador_id: int
    colaborador_nombre: str
    puesto_nombre: Optional[str] = None
    total_ventas: float
    cantidad_ventas: int
    total_impresiones: float


class ConciliacionDiaria(BaseModel):
    fecha: date
    por_colaborador: list[ConciliacionColaborador]
    cajas_del_dia: list[CajaSesion]


class ReporteBalance(BaseModel):
    periodo: str  # diario, semanal, mensual, anual
    fecha_desde: date
    fecha_hasta: date
    total_ingresos: float
    total_egresos: float
    balance: float
    cantidad_movimientos: int


class PuntoSerieFinanciera(BaseModel):
    etiqueta: str  # "2026-08-02", "2026-S31", "2026-08", "2026"
    fecha_inicio: date
    fecha_fin: date
    total_ingresos: float
    total_egresos: float
    balance: float
    ventas_cantidad: int
    ventas_total: float
    proyectos_facturado: float
    proyectos_cobrado: float
