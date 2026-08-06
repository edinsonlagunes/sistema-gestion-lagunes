from datetime import timedelta

from sqlalchemy.orm import Session

from app import models
from app.email_service import enviar_alerta
from app.zona_horaria import ahora_peru

DIAS_ALERTA_DOCUMENTOS = 15


def _fila_documento(doc: models.Documento) -> str:
    dias = (doc.fecha_vencimiento.date() - ahora_peru().date()).days
    if dias < 0:
        estado_texto = f"<strong style='color:#b91c1c'>VENCIDO hace {abs(dias)} día(s)</strong>"
    elif dias == 0:
        estado_texto = "<strong style='color:#b45309'>Vence HOY</strong>"
    else:
        estado_texto = f"Vence en {dias} día(s)"

    negocio_nombre = doc.negocio.nombre if doc.negocio else "—"
    proyecto_nombre = doc.proyecto.nombre if doc.proyecto else "—"

    return (
        "<tr>"
        f"<td>{doc.nombre}</td>"
        f"<td>{negocio_nombre}</td>"
        f"<td>{proyecto_nombre}</td>"
        f"<td>{doc.fecha_vencimiento.date().isoformat()}</td>"
        f"<td>{estado_texto}</td>"
        "</tr>"
    )


def revisar_documentos_por_vencer(db: Session) -> bool:
    """
    Revisa documentos vencidos o que vencen dentro de DIAS_ALERTA_DOCUMENTOS
    días. Si encuentra alguno, manda un correo con el resumen y devuelve
    True. Si no hay nada que avisar, no manda nada y devuelve False.
    """
    limite = ahora_peru().date() + timedelta(days=DIAS_ALERTA_DOCUMENTOS)
    documentos = (
        db.query(models.Documento)
        .filter(models.Documento.fecha_vencimiento.isnot(None))
        .all()
    )
    documentos = [d for d in documentos if d.fecha_vencimiento.date() <= limite]
    documentos.sort(key=lambda d: d.fecha_vencimiento)

    if not documentos:
        return False

    filas = "".join(_fila_documento(d) for d in documentos)
    cuerpo_html = f"""
    <h2>Documentos vencidos o por vencer</h2>
    <p>Documentos con vencimiento en los próximos {DIAS_ALERTA_DOCUMENTOS} días, o ya vencidos:</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
      <tr>
        <th>Documento</th><th>Negocio</th><th>Proyecto</th><th>Vence</th><th>Estado</th>
      </tr>
      {filas}
    </table>
    """

    return enviar_alerta(
        asunto=f"Alerta: {len(documentos)} documento(s) vencidos o por vencer",
        cuerpo_html=cuerpo_html,
    )
