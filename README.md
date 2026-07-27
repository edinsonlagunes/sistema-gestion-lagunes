# Sistema de Gestión Lagunes — Backend (núcleo, Fase 1)

Backend en FastAPI + PostgreSQL (SQLite en desarrollo local) que cubre la
**Fase 1** del roadmap: negocios, colaboradores, usuarios, finanzas
(ingresos/egresos), proveedores, insumos y compras — con el stock y la caja
sincronizados automáticamente.

Probado y funcionando: login, creación de negocios/colaboradores/insumos,
y el flujo de compra (sube stock + genera egreso) contra una base real.

## 1. Instalación local (PowerShell)

```powershell
# Desde la carpeta backend/
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Cargar los datos iniciales (los dos negocios + usuario admin)
python -m app.seed

# Levantar el servidor
uvicorn app.main:app --reload
```

Con eso, la API queda disponible en `http://localhost:8000` y la
documentación interactiva (para probar cada endpoint desde el navegador)
en `http://localhost:8000/docs`.

**Usuario creado por el seed**: `admin` / `cambiar123` — cámbiala apenas
entres (por ahora no hay endpoint de "cambiar contraseña"; se agrega en la
siguiente fase junto con el login por token).

## 2. Qué contiene esta Fase 1

| Endpoint | Qué hace |
|---|---|
| `POST /usuarios/login` | Login (usuario/contraseña) |
| `GET/POST /negocios/` | Constructora Lagunes / Librería |
| `GET/POST /colaboradores/` | Personal por negocio |
| `POST /usuarios/` | Crear usuario ligado a un colaborador |
| `GET/POST /finanzas/ingresos` | Registrar ingresos |
| `GET/POST /finanzas/egresos` | Registrar egresos |
| `GET /finanzas/resumen` | Balance por negocio + alerta de insumos bajos — la base del futuro dashboard |
| `GET/POST /insumos/` | Inventario por negocio |
| `GET/POST /proveedores/` | Proveedores |
| `GET/POST /compras/` | Registrar compra: **sube el stock y genera el egreso automáticamente** |

### Fase 2 — POS de la Librería (agregada)

| Endpoint | Qué hace |
|---|---|
| `GET/POST /servicios/` | Catálogo: impresión B/N, color, tamaño, escaneo, copia, anillado, enmicado, sellos. Cada servicio puede vincularse a un insumo (`insumo_id` + `consumo_insumo_por_unidad`) para que la venta descuente stock sola |
| `GET /caja/actual?negocio_id=` | Consulta si hay una caja abierta |
| `POST /caja/abrir` | Abre caja con un monto inicial |
| `POST /caja/{id}/cerrar` | Cierra caja con arqueo: compara lo esperado (apertura + ventas en efectivo) contra lo contado físicamente |
| `GET/POST /ventas/` | Registra una venta con uno o más ítems. En una sola operación: calcula el total, genera el ingreso en finanzas, y descuenta el insumo vinculado a cada servicio |

**Reglas de negocio ya probadas**: no se puede vender sin caja abierta, y
una vez cerrada la caja no se pueden registrar más ventas hasta abrir una
nueva.

### Fase 3 — Módulo Constructora (agregada)

| Endpoint | Qué hace |
|---|---|
| `GET/POST /clientes/` | Clientes de la Constructora |
| `GET/POST /proyectos/` | Proyectos (filtrables por negocio, cliente o estado) |
| `GET /proyectos/{id}` | Detalle: todas las órdenes de servicio entregadas y el total facturado |
| `PATCH /proyectos/{id}/estado` | cotizacion → en_proceso → entregado (o cancelado) |
| `POST /proyectos/{id}/ordenes` | Registra un servicio técnico entregado (plano, expediente, estudio de suelos, ploteo). Calcula el subtotal, genera el ingreso y descuenta el insumo vinculado — igual mecanismo que el POS |

**Reutiliza el mismo catálogo `/servicios/`** que ya usa la Librería (basta
con crear los servicios técnicos con `negocio_id` de la Constructora) — así
planos, expedientes, estudios de suelos y ploteos se manejan con el mismo
mecanismo de precios e insumos que ya está probado.

**Nota sobre el dinero**: a diferencia del POS (donde el cliente paga en el
momento), en la Constructora el ingreso se registra con `medio_pago: "por
cobrar"` apenas se entrega el servicio — es una simplificación útil para
llevar la cuenta, pero técnicamente no distingue todavía entre "facturado"
y "cobrado". Si te interesa que el sistema separe cuentas por cobrar de
ingresos ya cobrados, es un ajuste puntual para cuando lo necesites.

### Fase 4 — Asistencia de colaboradores (agregada)

| Endpoint | Qué hace |
|---|---|
| `POST /asistencia/entrada` | Marca entrada de un colaborador (bloquea una segunda entrada sin salida previa) |
| `POST /asistencia/salida` | Marca salida y calcula automáticamente las horas trabajadas |
| `GET /asistencia/en-turno?negocio_id=` | Quién está trabajando ahora mismo — útil como vista rápida de "quién está en la tienda/oficina" |
| `GET /asistencia/?colaborador_id=&fecha=` | Historial de asistencia, filtrable por colaborador o fecha |

Lo que falta a propósito para más adelante (ya está en el roadmap):
integración con PaperCut/YSoft para el conteo de impresiones (Fase 5, la
última).

## 3. Desplegar en Railway

### Paso A — Subir el código a GitHub

Dentro de la carpeta `backend` (donde ya corriste `pip install`), en PowerShell:

```powershell
git init
git add .
git commit -m "Sistema de gestión Lagunes - nucleo + POS + Constructora + asistencia"
```

Ahora, en tu navegador:
1. Entra a github.com (con tu cuenta `edinsonlagunes`) → botón **New repository**.
2. Nómbralo, por ejemplo, `sistema-gestion-lagunes`. Déjalo **privado** (es
   el sistema interno de tu negocio). No marques "Add a README" — ya
   tenemos uno.
3. Copia los 2-3 comandos que GitHub te muestra bajo "…or push an existing
   repository from the command line" — se ven así (usa los que a ti te
   muestre, con tu usuario y nombre de repo exactos):

```powershell
git remote add origin https://github.com/edinsonlagunes/sistema-gestion-lagunes.git
git branch -M main
git push -u origin main
```

Te va a pedir iniciar sesión en GitHub (usuario/contraseña o token) —
eso lo haces tú directamente en la ventana que se abre, nunca me
compartas esa contraseña ni el token a mí.

### Paso B — Crear el proyecto en Railway

1. En railway.app → **New Project → Deploy from GitHub repo** → selecciona
   `sistema-gestion-lagunes`.
2. Dentro de ese mismo proyecto de Railway, clic en **New → Database →
   Add PostgreSQL**.
3. Entra al servicio del backend (no al de Postgres) → pestaña
   **Variables** → **New Variable → Add Reference** → selecciona la
   variable `DATABASE_URL` del servicio de Postgres. Así quedan
   conectados sin copiar nada a mano.
4. El **Procfile** que ya viene en el proyecto (`web: uvicorn app.main:app
   --host 0.0.0.0 --port $PORT`) hace que Railway detecte el comando de
   arranque solo — no deberías necesitar configurarlo a mano, pero si el
   deploy falla por "no start command", pégalo en Settings → Deploy →
   Custom Start Command.
5. Railway hace el primer deploy automáticamente. Espera a que el estado
   quede en verde ("Active").

### Paso C — Cargar los datos iniciales en la nube

Con la [Railway CLI](https://docs.railway.com/guides/cli) instalada
(`npm i -g @railway/cli`), desde la carpeta `backend`:

```powershell
railway login
railway link
railway run python -m app.seed
```

Esto crea los dos negocios y el usuario `admin` directamente en tu base
de PostgreSQL de Railway (solo se hace una vez).

### Paso D — Probarlo

Railway te da una URL pública (algo como
`https://sistema-gestion-lagunes-production.up.railway.app`). Entra a
`<esa-url>/docs` desde cualquier PC o el celular — ya no depende de que
tu computadora esté encendida.

**Nota de seguridad**: por ahora el sistema no tiene login por token
(sesión), así que cualquiera con la URL puede usar la API si la conoce.
Está bien para probarlo tú mismo, pero antes de darle acceso a tus
colaboradores conviene agregar autenticación por token — es un ajuste
puntual, dime cuando quieras que lo hagamos.

## 4. Siguiente paso sugerido

Con esto ya en la nube, sigue la **Fase 5: integración con PaperCut/YSoft**
para el conteo de impresiones/ploteos.
