import os
import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")

REMITENTE = os.environ.get("EMAIL_REMITENTE", "onboarding@resend.dev")
DESTINATARIOS = [
    correo.strip()
    for correo in os.environ.get("EMAIL_DESTINATARIOS", "").split(",")
    if correo.strip()
]


def enviar_alerta(asunto: str, cuerpo_html: str, destinatarios: list[str] | None = None) -> bool:
    """
    Envía un correo de alerta o reporte a través de Resend.
    Devuelve True si Resend aceptó el envío, False si falló — nunca lanza
    una excepción, para que un error de correo no tumbe el proceso que lo llama
    (ej. un chequeo diario de documentos por vencer).
    """
    if not resend.api_key:
        print("RESEND_API_KEY no está configurada en las variables de entorno — no se envió el correo.")
        return False

    destinos = destinatarios or DESTINATARIOS
    if not destinos:
        print("No hay destinatarios configurados (EMAIL_DESTINATARIOS) — no se envió el correo.")
        return False

    try:
        resend.Emails.send({
            "from": f"Sistema Lagunes <{REMITENTE}>",
            "to": destinos,
            "subject": asunto,
            "html": cuerpo_html,
        })
        return True
    except Exception as error:
        print(f"Error enviando correo con Resend: {error}")
        return False
