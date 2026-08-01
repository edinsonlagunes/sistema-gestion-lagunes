"""
Hora local de Perú, para que todo lo que el sistema registra y muestra
(asistencia, ventas, pagos, impresiones, caja...) quede en la hora real
del negocio, no en UTC.

Se guarda como datetime "naive" (sin marca de zona) pero con el valor de
la hora de Lima — así el navegador la muestra tal cual, sin tener que
convertir nada.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_PERU = ZoneInfo("America/Lima")


def ahora_peru() -> datetime:
    return datetime.now(ZONA_PERU).replace(tzinfo=None)
