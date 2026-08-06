from datetime import datetime, timedelta

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


TOLERANCIA_DISCREPANCIA = 1.15  # misma tolerancia que usa la pantalla de Conciliación


def _hay_discrepancia(total_impresiones_estimado: float, total_ventas: float) -> bool:
    if not total_impresiones_estimado or total_impresiones_estimado <= 0:
        return False
    return total_impresiones_estimado > total_ventas * TOLERANCIA_DISCREPANCIA


def revisar_conciliacion(db: Session) -> bool:
    """
    Revisa el día de ayer, negocio por negocio, buscando colaboradores
    cuyas impresiones estimadas superan en más de 15% lo que vendieron
    ese día (la misma regla que usa la pantalla de Conciliación). Si
    encuentra alguna discrepancia, manda un correo con el detalle.
    """
    dia = ahora_peru().date() - timedelta(days=1)
    inicio = datetime.combine(dia, datetime.min.time())
    fin = datetime.combine(dia, datetime.max.time())

    filas_data = []
    for negocio in db.query(models.Negocio).all():
        ventas = (
            db.query(models.Venta)
            .filter(models.Venta.negocio_id == negocio.id, models.Venta.fecha >= inicio, models.Venta.fecha <= fin)
            .all()
        )
        impresiones = (
            db.query(models.RegistroImpresion)
            .filter(
                models.RegistroImpresion.negocio_id == negocio.id,
                models.RegistroImpresion.fecha >= inicio,
                models.RegistroImpresion.fecha <= fin,
            )
            .all()
        )

        acumulado: dict[int, dict] = {}
        for v in ventas:
            if v.colaborador_id is None:
                continue
            datos = acumulado.setdefault(v.colaborador_id, {"total_ventas": 0.0, "total_impresiones_estimado": 0.0})
            datos["total_ventas"] += v.total

        for r in impresiones:
            if r.colaborador_id is None:
                continue
            datos = acumulado.setdefault(r.colaborador_id, {"total_ventas": 0.0, "total_impresiones_estimado": 0.0})
            servicio = (
                db.query(models.Servicio)
                .filter(
                    models.Servicio.negocio_id == r.negocio_id,
                    models.Servicio.categoria == r.tipo_trabajo,
                    models.Servicio.tamano == r.tamano,
                )
                .first()
            )
            if servicio:
                datos["total_impresiones_estimado"] += servicio.precio_unitario * r.cantidad

        for colaborador_id, datos in acumulado.items():
            if not _hay_discrepancia(datos["total_impresiones_estimado"], datos["total_ventas"]):
                continue
            colaborador = db.query(models.Colaborador).get(colaborador_id)
            filas_data.append(
                {
                    "negocio": negocio.nombre,
                    "colaborador": colaborador.nombre if colaborador else f"Colaborador #{colaborador_id}",
                    "ventas": datos["total_ventas"],
                    "impresiones_estimado": datos["total_impresiones_estimado"],
                }
            )

    if not filas_data:
        return False

    filas_html = "".join(
        "<tr>"
        f"<td>{f['negocio']}</td>"
        f"<td>{f['colaborador']}</td>"
        f"<td>S/ {f['ventas']:.2f}</td>"
        f"<td>S/ {f['impresiones_estimado']:.2f}</td>"
        "</tr>"
        for f in filas_data
    )

    cuerpo_html = f"""
    <h2>Discrepancias de conciliación — {dia.isoformat()}</h2>
    <p>Colaboradores cuyas impresiones estimadas superan en más de 15% lo que vendieron ese día:</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
      <tr>
        <th>Negocio</th><th>Colaborador</th><th>Vendido</th><th>Impresiones (estimado)</th>
      </tr>
      {filas_html}
    </table>
    """

    return enviar_alerta(
        asunto=f"Alerta: {len(filas_data)} discrepancia(s) de conciliación — {dia.isoformat()}",
        cuerpo_html=cuerpo_html,
    )
