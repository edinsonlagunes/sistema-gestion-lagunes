from fastapi import APIRouter, Depends

from app.auth import requerir_admin
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
