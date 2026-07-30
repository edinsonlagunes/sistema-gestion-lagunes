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


class ColaboradorCreate(ColaboradorBase):
    pass


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


class ProyectoCreate(ProyectoBase):
    pass


class ProyectoEstadoUpdate(BaseModel):
    estado: str


class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo_proyecto: Optional[str] = None
    cliente_id: Optional[int] = None
    fecha_entrega_estimada: Optional[datetime] = None


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


class ProyectoDetalle(Proyecto):
    ordenes: list[OrdenServicioOut]
    total_facturado: float


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
