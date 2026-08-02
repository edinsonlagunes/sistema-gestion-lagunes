from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import (
    agenda,
    asistencia,
    caja,
    caja_chica,
    clientes,
    colaboradores,
    compras,
    documentos,
    finanzas,
    impresiones,
    insumos,
    mantenimientos,
    negocios,
    planillas,
    proyectos,
    puestos_trabajo,
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


@app.get("/")
def raiz():
    return {
        "status": "ok",
        "sistema": "Gestión Lagunes - Fase 1 a 5 completas",
    }
