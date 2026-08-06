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


def revisar_cobros_pendientes(db: Session) -> bool:
    """
    Revisa todos los proyectos con saldo pendiente de cobro (lo
    facturado menos lo efectivamente pagado) y, si hay alguno, manda un
    correo con el resumen. Devuelve True si mandó correo, False si no
    había nada pendiente.
    """
    proyectos = db.query(models.Proyecto).all()
    filas_data = []
    for p in proyectos:
        total_facturado = sum(o.subtotal for o in p.ordenes)
        total_pagado = sum(pago.monto for pago in p.pagos)
        saldo = total_facturado - total_pagado
        if saldo <= 0:
            continue

        negocio = db.query(models.Negocio).get(p.negocio_id)
        ultimo_pago = max(p.pagos, key=lambda pago: pago.fecha_pago) if p.pagos else None
        filas_data.append(
            {
                "proyecto": p.nombre,
                "cliente": p.cliente.nombre if p.cliente else "—",
                "negocio": negocio.nombre if negocio else "—",
                "facturado": total_facturado,
                "pagado": total_pagado,
                "saldo": saldo,
                "ultimo_pago_fecha": ultimo_pago.fecha_pago.date().isoformat() if ultimo_pago else "Sin pagos aún",
            }
        )

    if not filas_data:
        return False

    filas_data.sort(key=lambda f: f["saldo"], reverse=True)
    total_pendiente = sum(f["saldo"] for f in filas_data)
    filas_html = "".join(
        "<tr>"
        f"<td>{f['proyecto']}</td>"
        f"<td>{f['cliente']}</td>"
        f"<td>{f['negocio']}</td>"
        f"<td>S/ {f['facturado']:.2f}</td>"
        f"<td>S/ {f['pagado']:.2f}</td>"
        f"<td><strong>S/ {f['saldo']:.2f}</strong></td>"
        f"<td>{f['ultimo_pago_fecha']}</td>"
        "</tr>"
        for f in filas_data
    )

    cuerpo_html = f"""
    <h2>Cobros pendientes</h2>
    <p>Proyectos con saldo pendiente de cobro (total: S/ {total_pendiente:.2f}):</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
      <tr>
        <th>Proyecto</th><th>Cliente</th><th>Negocio</th><th>Facturado</th><th>Pagado</th><th>Saldo</th><th>Último pago</th>
      </tr>
      {filas_html}
    </table>
    """

    return enviar_alerta(
        asunto=f"Alerta: S/ {total_pendiente:.2f} en cobros pendientes ({len(filas_data)} proyecto(s))",
        cuerpo_html=cuerpo_html,
    )
