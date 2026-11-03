# Ecommerce API

API REST de comercio electrónico construida con **FastAPI** y **SQLAlchemy**. Expone el ciclo comercial mínimo de un marketplace: alta de clientes, catálogo de productos con paginación y un checkout transaccional (descuento, control de stock y persistencia de líneas de pedido).

El dominio cubre tres agregados:

| Agregado | Responsabilidad |
| --- | --- |
| **Usuario** | Identidad del comprador. El email es único a nivel de base de datos. |
| **Producto** | SKU con precio de lista y existencias. |
| **Orden** | Cabecera (`orders`) + detalle (`order_items`) con cantidad y precio unitario ya descontado. |

Público objetivo: equipos backend que consuman el servicio desde un storefront, un BFF o un canal interno. La especificación viva está en Swagger UI (`/docs`) y ReDoc (`/redoc`).

---

## Arquitectura

La aplicación sigue una separación en capas. El borde HTTP no ejecuta SQL; el ORM no conoce FastAPI.

```text
┌─────────────────────────────────────────────────────────────┐
│  Cliente HTTP (storefront, Postman, TestClient)             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Capa de presentación — FastAPI                             │
│  main.py  ·  routers/users.py · products.py · orders.py     │
│  OpenAPI: summary, tags, responses 400/404/500              │
└────────────────────────────┬────────────────────────────────┘
                             │ schemas.py (Pydantic v2)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Capa de aplicación / acceso a datos — crud.py              │
│  Casos de uso: alta, listado paginado, historial, checkout  │
└────────────────────────────┬────────────────────────────────┘
                             │ models.py (SQLAlchemy ORM)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Capa de infraestructura                                    │
│  database.py (sesión)  ·  config.py (pydantic-settings)     │
│  MySQL (runtime)  ·  SQLite :memory: (pytest)               │
└─────────────────────────────────────────────────────────────┘
```

**Flujo de una petición:** el router valida el contrato Pydantic, obtiene una sesión vía `Depends(get_db)` y delega en `crud`. El checkout abre una transacción con bloqueo pesimista de stock; un fallo dispara `rollback`. La configuración (URL de base de datos, umbral y tasa de descuento) se inyecta desde el entorno; no hay secretos en el código fuente.

Relaciones persistidas: `User` 1—N `Order` 1—N `OrderItem` N—1 `Product`.

---

## Requisitos previos

- Python **3.11** o **3.12** (3.14 no está validado con las versiones fijadas de Pydantic).
- MySQL 8.x escuchando en local (o un contenedor equivalente) y un schema vacío, por ejemplo `ecommerce_db`.
- `pip` actualizado. No se utiliza Pipfile; las dependencias están fijadas en `requirements.txt`.

Clonar el repositorio y crear un entorno virtual:

```bash
git clone <url-del-repositorio>
cd ecommerce_api_reto_ia

python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` incluye runtime (FastAPI, Uvicorn, SQLAlchemy, PyMySQL, pydantic-settings) y herramientas de prueba (`pytest`, `pytest-cov`, `httpx`).

---

## Variables de entorno

Los secretos no se commitean. Copiar la plantilla y ajustar valores reales:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

| Variable | Obligatorio | Descripción |
| --- | --- | --- |
| `DATABASE_URL` | Sí | Cadena SQLAlchemy. Ejemplo: `mysql+pymysql://USER:PASSWORD@localhost:3306/ecommerce_db` |
| `DISCOUNT_THRESHOLD` | No (default `100`) | Precio de lista a partir del cual aplica descuento |
| `DISCOUNT_RATE` | No (default `0.10`) | Tasa (0.10 = 10 %) |

`config.py` carga estos valores con **pydantic-settings** (archivo `.env` + variables del proceso). El archivo `.env` está en `.gitignore`.

Crear la base en MySQL antes del primer arranque:

```sql
CREATE DATABASE ecommerce_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Al iniciar, FastAPI ejecuta `Base.metadata.create_all` y materializa `users`, `products`, `orders` y `order_items`. En un esquema ya existente, `create_all` **no** altera columnas; hay que recrear o migrar si el modelo cambió.

---

## Arranque local (Uvicorn)

Con el entorno virtual activo y `.env` configurado:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

| Recurso | URL |
| --- | --- |
| API | http://127.0.0.1:8000 |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| OpenAPI JSON | http://127.0.0.1:8000/openapi.json |

Comprobación rápida del catálogo (paginación: `limit` default 10, máximo 100; `offset` default 0):

```bash
curl "http://127.0.0.1:8000/products/?limit=10&offset=0"
```

Checkout (descuento 10 % si `price > 100`; stock insuficiente → 409):

```bash
curl -X POST "http://127.0.0.1:8000/orders/" ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\": 1, \"items\": [{\"product_id\": 1, \"quantity\": 2}]}"
```

Historial con nombres de producto:

```bash
curl "http://127.0.0.1:8000/users/1/orders"
```

---

## Contenedores (Docker)

Infraestructura inmutable: la API se construye con un **Dockerfile multi-stage** (`python:3.11-slim`, `PYTHONDONTWRITEBYTECODE=1`, dependencias con `--no-cache-dir`, proceso **no root**, Uvicorn en `0.0.0.0:8000`). Compose orquesta dos servicios en la red bridge `ecommerce_internal`:

| Servicio | Imagen | Puertos | Persistencia |
| --- | --- | --- | --- |
| `api` | build local (`ecommerce-api:1.0.0`) | 8000 | — |
| `db` | `mysql:8` | 3306 | volumen nombrado `mysql_data` |

`api` espera a que `db` esté healthy. Dentro de la red, el hostname de MySQL es **`db`** (no `localhost`). Compose inyecta `DATABASE_URL` apuntando a ese host.

Requisitos: Docker Engine + Docker Compose v2.

```bash
docker compose up --build -d
```

| Recurso | URL |
| --- | --- |
| API | http://127.0.0.1:8000 |
| Swagger | http://127.0.0.1:8000/docs |
| MySQL (host) | 127.0.0.1:3306 |

Opcional: un `.env` en la raíz con `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, `DISCOUNT_THRESHOLD` y `DISCOUNT_RATE` (defaults: `password123`, `ecommerce_db`, `100`, `0.10`).

```bash
docker compose logs -f api
docker compose ps
docker compose down
```

`docker compose down -v` elimina también `mysql_data` (se pierde el estado de la BD).

Solo construir la imagen de la API:

```bash
docker build -t ecommerce-api:1.0.0 .
```

---

## Pruebas y cobertura

La suite vive en `tests/`. `conftest.py` levanta **SQLite en memoria**, siembra usuarios/productos/órdenes y sustituye `get_db` en el `TestClient`. El `asyncio.sleep` del catálogo se anula para no inflar el tiempo de CI.

```bash
python -m pytest
```

Ese comando ya incluye cobertura: `pytest.ini` define `--cov` sobre `main`, `crud`, `schemas`, `models`, `config`, `database` y `routers`, más `--cov-report=term-missing`.

Equivalente explícito (objetivo: **> 70 %** de líneas):

```bash
python -m pytest --cov=main --cov=crud --cov=schemas --cov=models --cov=config --cov=database --cov=routers --cov-report=term-missing
```

Informe HTML:

```bash
python -m pytest --cov=main --cov=crud --cov=schemas --cov=models --cov=config --cov=database --cov=routers --cov-report=term-missing --cov-report=html
```

Abrir `htmlcov/index.html`. Este repositorio **no** usa un paquete llamado `app`; `pytest --cov=app` no mide estas módulos.

Los tests cubren paginación, historial anidado (`product_names`), descuento en checkout y errores (404, 409 sin stock, 400 producto inexistente, 422 de validación).

---

## Contratos HTTP (resumen)

| Método | Ruta | Tag | Éxito |
| --- | --- | --- | --- |
| `POST` | `/users/` | users | Usuario creado |
| `GET` | `/users/{user_id}/orders` | users | Historial; 404 si el usuario no existe |
| `POST` | `/products/` | products | Producto creado |
| `GET` | `/products/` | products | Lista paginada |
| `POST` | `/orders/` | orders | Orden con ítems y total |

Errores documentados en OpenAPI para todos los endpoints: **400**, **404**, **500** (`ErrorResponse`). Checkout y alta de usuario también declaran **409** (stock / email duplicado). FastAPI añade **422** cuando falla la validación Pydantic.

---

## Licencia y alcance

Proyecto académico (reto de ingeniería de software). No incluye autenticación, pasarela de pagos ni migraciones Alembic; esas capacidades quedan fuera del perímetro actual.
