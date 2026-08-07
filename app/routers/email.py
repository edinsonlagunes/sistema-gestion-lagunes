from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.alertas import (
    ejecutar_respaldo_diario,
    revisar_cobros_pendientes,
    revisar_conciliacion,
    revisar_documentos_por_vencer,
    revisar_stock_bajo,
)
from app.auth import requerir_admin
from app.database import get_db
from app.email_service import enviar_alerta

router = APIRouter(prefix="/admin", tags=["email"])


@router.post("/probar-email")
def probar_email(usuario=Depends(requerir_admin)):
    """
    Ruta de prueba: confirma que el envío de correos vía Resend está
    funcionando de punta a punta (Railway -> Resend -> bandeja de entrada).
    """
    enviado = enviar_alerta(
        asunto="Prueba — Sistema de Gestión Lagunes",
        cuerpo_html="<p>Si estás leyendo esto, el envío de correos ya está funcionando.</p>",
    )
    return {"enviado": enviado}


@router.post("/revisar-documentos")
def revisar_documentos(usuario=Depends(requerir_admin), db: Session = Depends(get_db)):
    """
    Dispara manualmente la revisión de documentos por vencer (la misma
    que corre sola todos los días). Útil para probarla sin esperar a la
    hora programada.
    """
    enviado = revisar_documentos_por_vencer(db)
    return {
        "enviado": enviado,
        "mensaje": (
            "Se encontraron documentos por vencer y se envió el correo."
            if enviado
            else "No hay documentos vencidos ni por vencer en este momento — no se envió correo."
        ),
    }


@router.post("/revisar-cobros")
def revisar_cobros(usuario=Depends(requerir_admin), db: Session = Depends(get_db)):
    """
    Dispara manualmente la revisión de cobros pendientes (la misma que
    corre sola todos los días). Útil para probarla sin esperar a la
    hora programada.
    """
    enviado = revisar_cobros_pendientes(db)
    return {
        "enviado": enviado,
        "mensaje": (
            "Se encontraron proyectos con saldo pendiente y se envió el correo."
            if enviado
            else "No hay proyectos con saldo pendiente de cobro en este momento — no se envió correo."
        ),
    }


@router.post("/revisar-conciliacion")
def revisar_conciliacion_ruta(usuario=Depends(requerir_admin), db: Session = Depends(get_db)):
    """
    Dispara manualmente la revisión de discrepancias de conciliación del
    día de ayer (la misma que corre sola todos los días). Útil para
    probarla sin esperar a la hora programada.
    """
    enviado = revisar_conciliacion(db)
    return {
        "enviado": enviado,
        "mensaje": (
            "Se encontraron discrepancias de conciliación y se envió el correo."
            if enviado
            else "No hay discrepancias de conciliación en el día de ayer — no se envió correo."
        ),
    }


@router.post("/revisar-stock")
def revisar_stock(usuario=Depends(requerir_admin), db: Session = Depends(get_db)):
    """
    Dispara manualmente la revisión de insumos con stock bajo (la misma
    que corre sola todos los días). Útil para probarla sin esperar a la
    hora programada.
    """
    enviado = revisar_stock_bajo(db)
    return {
        "enviado": enviado,
        "mensaje": (
            "Se encontraron insumos con stock bajo y se envió el correo."
            if enviado
            else "No hay insumos con stock bajo en este momento — no se envió correo."
        ),
    }


@router.post("/ejecutar-respaldo")
def ejecutar_respaldo(usuario=Depends(requerir_admin)):
    """
    Dispara manualmente el respaldo diario de la base de datos (el
    mismo que corre solo todos los días). Útil para probarlo sin
    esperar a la hora programada.
    """
    enviado = ejecutar_respaldo_diario()
    return {"correo_enviado": enviado}
