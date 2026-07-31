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
| `GET/POST /servicios/` | Catálogo: impresión B/N, color, tamaño, escaneo, copia, anillado, enmicado, sellos. Cada servicio puede vincularse a un insumo (`insumo_id` + `consumo_insumo_por_unidad`) para que la venta descuente stock sola. **Crear, editar (`PATCH /servicios/{id}`) y quitar (`DELETE /servicios/{id}`) son acciones exclusivas de administradores** — cualquier usuario logueado puede ver el catálogo, pero no modificarlo |
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
| `GET/POST /proyectos/` | Proyectos (filtrables por negocio, cliente o estado). Al crear, se puede indicar `tipo_proyecto` con cualquier texto — normalmente uno del catálogo de `/tipos-proyecto/` |
| `GET/POST /tipos-proyecto/` | Catálogo editable de tipos de proyecto/servicio (elaboración de planos, ejecución de obra, supervisión, consultoría, o lo que tu empresa ofrezca). Crear, editar (`PATCH`) y quitar (`DELETE`) son exclusivos de administradores — cualquier usuario logueado puede ver la lista para elegir al crear un proyecto |
| `GET /proyectos/{id}` | Detalle: todas las órdenes de servicio entregadas y el total facturado |
| `PATCH /proyectos/{id}/estado` | cotizacion → en_proceso → entregado (o cancelado) |
| `PATCH /proyectos/{id}` | Editar nombre, tipo de proyecto, cliente o fecha estimada de entrega — **solo administradores** |
| `POST /proyectos/{id}/ordenes` | Registra un servicio técnico entregado (plano, expediente, estudio de suelos, ploteo). Calcula el subtotal, genera el ingreso y descuenta el insumo vinculado — igual mecanismo que el POS |
| `PATCH /proyectos/{id}/ordenes/{orden_id}` | Corrige la cantidad de una orden ya registrada, ajustando el ingreso y el insumo por la diferencia — **solo administradores** |
| `DELETE /proyectos/{id}/ordenes/{orden_id}` | Quita una orden registrada por error: revierte el ingreso y devuelve el insumo al stock — **solo administradores** |
| `POST /proyectos/{id}/pagos` | Registra un pago recibido (adelanto, cuota o pago final), con monto, fecha del depósito y medio de pago — genera el ingreso real en finanzas — **solo administradores** |
| `PATCH/DELETE /proyectos/{id}/pagos/{pago_id}` | Corrige o quita un pago ya registrado — **solo administradores** |
| `GET /proyectos/resumen-pagos?negocio_id=` | Para el Dashboard: proyectos con saldo pendiente (facturado − pagado), con el monto y fecha del último pago. No incluye proyectos ya cancelados |

**Reutiliza el mismo catálogo `/servicios/`** que ya usa la Librería (basta
con crear los servicios técnicos con `negocio_id` de la Constructora) — así
planos, expedientes, estudios de suelos y ploteos se manejan con el mismo
mecanismo de precios e insumos que ya está probado.

**Sobre el dinero — facturado vs. cobrado (corregido)**: a diferencia del
POS (donde el cliente paga en el momento), en la Constructora facturar un
servicio (una orden) **ya no genera ingreso**. El ingreso solo se genera
al registrar un **pago real** (ver sección de Pagos más abajo), por el
monto efectivamente cobrado — así el Dashboard nunca muestra como
"ingreso" algo que todavía está pendiente de cobro.

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

### Fase 5 — Registro de impresiones/ploteos (agregada)

Esta fase no incluye instalar PaperCut/YSoft por ti (eso implica comprar
licencias e instalarlo en tus PCs/impresoras — un paso físico aparte). Lo
que sí construí es la pieza que recibe y organiza esos conteos, para que
cuando instales ese software solo haga falta conectar su reporte aquí.

| Endpoint | Qué hace |
|---|---|
| `POST /impresiones/` | Registrar un conteo manual (mientras no tengas un software automático, o para completar algo puntual) |
| `POST /impresiones/importar-csv?negocio_id=` | Sube en bloque el reporte exportado por PaperCut/YSoft (o cualquier otro) como CSV |
| `GET /impresiones/?negocio_id=&colaborador_id=` | Historial de conteos |
| `GET /impresiones/resumen?negocio_id=` | Total de páginas/m² por colaborador, agrupado también por tipo de trabajo, tamaño y equipo — con el costo estimado, cruzando contra el precio vigente en `/servicios/` |

**Formato del CSV a importar** — columnas por nombre de encabezado (no importa el orden):
```
fecha,colaborador,equipo,tipo_trabajo,tamano,cantidad
2026-07-20,Juan Perez,HP-LaserJet-01,impresion_bn,A4,120
```
- `fecha`: acepta `AAAA-MM-DD`, `AAAA-MM-DD HH:MM:SS`, `DD/MM/AAAA` o `DD/MM/AAAA HH:MM:SS`.
- `colaborador`: se busca por nombre exacto (sin distinguir mayúsculas) dentro del mismo negocio. Si no coincide con nadie, la fila **igual se guarda** — no se pierde el dato — pero queda sin vincular a un colaborador del sistema.
- `tipo_trabajo`: usa las mismas categorías que ya usas en `/servicios/` (`impresion_bn`, `impresion_color`, `escaneo`, `ploteo`, etc.) para que el costo estimado se calcule bien.
- Filas con errores (fecha o cantidad inválida) se reportan una por una en la respuesta, sin frenar la importación de las demás.

**Cuando instales PaperCut o YSoft**: ambos permiten exportar reportes de
uso como CSV/Excel de forma periódica (programada o manual). El siguiente
paso, cuando llegues ahí, es adaptar ese export al formato de columnas de
arriba (o pedirme que ajuste el importador al formato exacto que traiga)
para automatizar la carga.

### Puestos de trabajo, equipos, y dashboard financiero completo (agregado)

| Endpoint | Qué hace |
|---|---|
| `GET/POST /puestos-trabajo/` | Stands/puestos de trabajo (mostrador, mesa de dibujo…), cada uno con un colaborador a cargo. Crear/editar/quitar — **solo administradores** |
| `POST/DELETE /puestos-trabajo/{id}/equipos` | Agregar o quitar computadoras/fotocopiadoras/impresoras/plotters de un puesto — **solo administradores** |
| `GET /finanzas/movimientos-dia?fecha=&negocio_id=` | Todo el movimiento de caja de un día — cada ingreso y egreso, uno por uno, con el balance — **solo administradores** |
| `GET /finanzas/conciliacion-diaria?fecha=&negocio_id=` | El día agrupado por colaborador (y su puesto/equipos): cuánto vendió, cuántas ventas, cuántas impresiones. Pensado para que el encargado de caja haga el cuadre — accesible a cualquier usuario logueado |
| `GET /finanzas/reporte?periodo=diario\|semanal\|mensual&fecha=&negocio_id=` | Balance del periodo completo (el día, la semana lunes-domingo, o el mes) — **solo administradores** |

**Nota**: el envío automático de estos reportes por correo (diario/semanal/mensual)
no está construido todavía — requiere conectar un servicio de email
(Resend, SendGrid, Gmail SMTP, etc.), que es una decisión y una cuenta
aparte. Por ahora los reportes se ven en el Dashboard; cuando quieras dar
ese paso, lo vemos.

## 3. Cuando el modelo de datos cambia (migraciones)

`Base.metadata.create_all()` (usado al arrancar el servidor y en el seed)
**crea tablas nuevas, pero no modifica las que ya existen con datos
adentro**. Cada vez que se agregue una columna a un modelo que ya estaba
en uso (como pasó con `tipo_proyecto` en `Proyecto`), hay que correr una
vez:

```powershell
python -m app.migrate
```

(o en Railway, desde la pestaña **Console** del servicio, igual que
corriste `python -m app.seed`). Es seguro correrlo varias veces — si la
columna ya existe, no hace nada. `app/migrate.py` lista exactamente qué
columnas agrega.

## 4. Autenticación (agregada)

Todos los endpoints, salvo `POST /usuarios/login`, ahora exigen iniciar sesión.

- **Login**: `POST /usuarios/login` con `username`/`password` — devuelve un `access_token` (válido 8 horas, una jornada laboral) que hay que mandar en cada request como header `Authorization: Bearer <token>`.
- **Crear usuarios**: `POST /usuarios/` ahora solo lo puede hacer alguien con `rol_permiso: admin` — el resto de endpoints los puede usar cualquier usuario logueado.
- **Probarlo desde `/docs`**: hay un botón **"Authorize"** (con un candado) arriba a la derecha de la documentación interactiva. Ahí pegas el `access_token` que te devolvió el login (sin la palabra "Bearer", `/docs` la agrega sola), y desde ese momento todos los "Try it out" quedan autenticados.

**Importante — variable `SECRET_KEY`**: el token se firma con esta clave. Trae un valor de respaldo solo para pruebas locales; **antes de que el sistema quede en manos de tus colaboradores**, genera una clave propia:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
y agrégala como variable de entorno `SECRET_KEY` en Railway (Variables → New Variable) y en tu `.env` local. Si la cambias, todas las sesiones activas se cierran (no pasa nada grave, solo hay que volver a hacer login).

## 5. Desplegar en Railway

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

## 6. Siguiente paso sugerido

Con esto, las 5 fases del roadmap original ya están construidas y
probadas. Lo que queda pendiente no es backend, sino:

- **Instalar PaperCut o YSoft** en tus PCs/impresoras (paso físico) y
  luego automatizar la carga de su reporte hacia `/impresiones/importar-csv`.
- **Una interfaz visual** (pantallas, no solo `/docs`) para que tus
  colaboradores —cajeros, dibujantes— usen el sistema día a día sin tener
  que tocar la documentación técnica de la API. Es el paso natural ahora
  que el backend completo ya funciona y está asegurado.
