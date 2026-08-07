from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.alertas import revisar_cobros_pendientes, revisar_conciliacion, revisar_documentos_por_vencer
from app.database import Base, SessionLocal, engine
from app.routers import (
    agenda,
    asistencia,
    avance_obra,
    caja,
    caja_chica,
    clientes,
    colaboradores,
    compras,
    comprobantes,
    documentos,
    email,
    finanzas,
    impresiones,
    insumos,
    mantenimientos,
    negocios,
    planillas,
    proyectos,
    puestos_trabajo,
    roles,
    servicios,
    tipos_proyecto,
    usuarios,
    ventas,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Gestión Lagunes",
    description="Núcleo: negocios, colaboradores, usuarios, finanzas, insumos y compras.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajustar a tu dominio real antes de producción
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(negocios.router)
app.include_router(planillas.router)
app.include_router(colaboradores.router)
app.include_router(usuarios.router)
app.include_router(finanzas.router)
app.include_router(insumos.router)
app.include_router(insumos.proveedores_router)
app.include_router(agenda.router)
app.include_router(mantenimientos.router)
app.include_router(compras.router)
app.include_router(documentos.router)
app.include_router(servicios.router)
app.include_router(caja.router)
app.include_router(caja_chica.router)
app.include_router(ventas.router)
app.include_router(clientes.router)
app.include_router(proyectos.router)
app.include_router(tipos_proyecto.router)
app.include_router(puestos_trabajo.router)
app.include_router(asistencia.router)
app.include_router(impresiones.router)
app.include_router(email.router)
app.include_router(roles.router)
app.include_router(avance_obra.router)
app.include_router(comprobantes.router)


def _job_documentos_por_vencer():
    db = SessionLocal()
    try:
        revisar_documentos_por_vencer(db)
    finally:
        db.close()


def _job_cobros_pendientes():
    db = SessionLocal()
    try:
        revisar_cobros_pendientes(db)
    finally:
        db.close()


def _job_conciliacion():
    db = SessionLocal()
    try:
        revisar_conciliacion(db)
    finally:
        db.close()


scheduler = BackgroundScheduler(timezone="America/Lima")
scheduler.add_job(_job_documentos_por_vencer, "cron", hour=7, minute=0)
scheduler.add_job(_job_cobros_pendientes, "cron", hour=7, minute=5)
scheduler.add_job(_job_conciliacion, "cron", hour=7, minute=10)
scheduler.start()


@app.get("/")
def raiz():
    return {
        "status": "ok",
        "sistema": "Gestión Lagunes - Fase 1 a 5 completas",
    }
