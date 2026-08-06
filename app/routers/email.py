from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.alertas import revisar_documentos_por_vencer
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
