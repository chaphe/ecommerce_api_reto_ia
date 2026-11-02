# INFORME DE AUDITORÍA DE SEGURIDAD Y ARQUITECTURA - FastAPI E-Commerce API

## 1. VULNERABILIDADES DE SEGURIDAD Y CREDENCIALES EXPUESTAS

| Severidad | Ubicación | Hallazgo | Descripción | Recomendación |
|-----------|-----------|----------|-------------|---------------|
| CRÍTICA | `database.py:5` | Credenciales hardcodeadas | Cadena de conexión con `root:password123` expuesta en código fuente. | Usar variables de entorno (`.env`) con `python-dotenv` o gestor de secretos. Nunca commitear credenciales. |
| ALTA | `models.py:10` | Sin restricción UNIQUE en email | Campo `email` sin `unique=True`, permite emails duplicados. Puede generar colisiones de cuentas. | Añadir `unique=True, index=True` al campo email. Implementar validación a nivel de BD y aplicación. |
| ALTA | `main.py:12-17` | Sin validación/prevención de duplicados | `create_user` no verifica si the email ya existe. Permite registros duplicados. | Verificar existencia antes de crear: `db.query(User).filter(User.email==...).first()` y retornar 409 si existe. |
| ALTA | `main.py:31-41` | Sin verificación de stock | Se decrementa stock sin comprobar si hay suficiente (`prod.stock - 1` cuando stock es 0). Permite pedidos with stock negativo. | Validar `prod.stock >= cantidad_solicitada`. Si no hay suficiente, retornar 400. |
| ALTA | `main.py:43-46` | Sin validación transaccional/rollback | Si falla entre operaciones (crear orden, actualizar stocks) no hay manejo de excepciones con rollback. Puede dejar BD inconsistente. | Usar `try/except` con `db.rollback()` en caso de error. Considerar usar transacciones atómicas. |
| MEDIA | `main.py:30-42` | Lógica de descuento hardcodeada | Descuento fijo `-10` si precio > 100 sin justificación/configuración. Riesgo de lógica oculta. | Mover reglas de negocio a servicio/configuración. Documentar o parametrizar. |
| MEDIA | `main.py:32-35` | Posible race condition | Consulta producto y actualiza stock sin lock pesimista/optimista. Múltiples requests simultáneos pueden vender más stock del disponible. | Usar `with_for_update()` al leer producto, o implementar versionado/locks. |
| MEDIA | `schemas.py:5-6` | Sin validación de formato | `email` y `name` sin validadores Pydantic (`EmailStr`, longitud, etc.). | Usar `pydantic.EmailStr`, `Field(min_length/max_length)`, validaciones. |
| BAJA | `main.py:6` | Sin configuración de CORS/seguridad | FastAPI sin middlewares de seguridad (CORS, rate limiting, headers). | Añadir CORSMiddleware, TrustedHostMiddleware, rate limiting según necesidad. |

## 2. INEFICIENCIAS DE RENDIMIENTO

| Severidad | Ubicación | Hallazgo | Descripción | Recomendación |
|-----------|-----------|----------|-------------|---------------|
| ALTA | `main.py:21` | `time.sleep(2)` bloqueante | Sleep bloqueante en endpoint síncrono congela el worker. Reduce throughput drásticamente. | Eliminar sleep. Si es para pruebas, usar async/background tasks. Nunca usar sleep bloqueante en endpoints. |
| ALTA | `main.py:31-42` | N+1 queries | Por cada producto en `product_ids` se hace `db.query().filter().first()` individual. Con N productos = N+1 consultas. | Hacer una sola consulta: `db.query(Product).filter(Product.id.in_(order.product_ids)).all()`, luego mapear por ID. |
| MEDIA | `main.py:40-41` | `db.add(prod)` innecesario | SQLAlchemy rastrea objetos cargados en sesión; `add()` sobre objeto ya persistente es redundante. | Eliminar `db.add(prod)` cuando el objeto viene de query. |
| MEDIA | `models.py:8-9,14-17,21-24` | Sin índices estratégicos | Solo `primary_key` e `index=True` básicos. Faltan índices en `Order.user_id`, búsquedas frecuentes. | Añadir índices en FKs/búsquedas comunes. Considerar índices compuestos. |
| BAJA | `main.py:9` | `create_all()` en import | `create_all()` se ejecuta al importar módulo. En producción puede tener efectos no deseados, dificulta migraciones. | Usar Alembic para migraciones. Eliminar create_all() o controlar por entorno. |

## 3. ERRORES EN LA LÓGICA DE NEGOCIO

| Severidad | Ubicación | Hallazgo | Descripción | Recomendación |
|-----------|-----------|----------|-------------|---------------|
| CRÍTICA | `schemas.py:15` | Diseño incompleto de OrderCreate | Comentario indica problema: no permite cantidades por producto. Solo lista de IDs asume cantidad 1 para todos. | Rediseñar: `List[OrderItem]` con `product_id` y `quantity`. Actualizar lógica para usar cantidades. |
| CRÍTICA | `main.py:40` | Asume cantidad 1 por producto | Siempre resta 1 unidad sin considerar cantidad solicitada. Lógica incorrecta para pedidos reales. | Usar cantidad del item. Validar stock >= cantidad. Restar cantidad correcta. |
| ALTA | `main.py:36-38` | Descuento no justificado | Descuento aplicado por precio (>100) no mencionado en requisitos, sin trazabilidad. Puede ser bug o regla oculta incorrecta. | Clarificar regla de negocio. Si es promoción, debe estar en configuración/servicio con tests. |
| ALTA | `main.py:43-46` | Orden creada sin validar todo el carrito | Si algún producto no existe se falla en medio del loop, pero los stocks ya modificados en memoria no se revierten (falta rollback). | Validar todos los productos primero (existencia, stock) antes de aplicar cambios. Hacer todo atómico. |
| ALTA | `main.py:30-42` | No verifica stock suficiente | Puede vender con stock 0 o negativo. | Validar `prod.stock >= quantity` para cada item. |
| MEDIA | `models.py:24` | `datetime.datetime.now` sin zona horaria | Usa hora local, no UTC. Problemático en sistemas distribuidos/multi-zona. | Usar `datetime.datetime.now(datetime.timezone.utc)` o `func.now()` con UTC. |
| MEDIA | `main.py:27-28` | Mensaje genérico | Mensaje "Usuario no encontrado" genérico. Correcto, pero sin logging. | Considerar logging para auditoría. |

## 4. VIOLACIONES DE ESTÁNDARES DE CODIFICACIÓN PEP 8

| Severidad | Ubicación | Hallazgo | Descripción | Recomendación |
|-----------|-----------|----------|-------------|---------------|
| MEDIA | `main.py:13` | Nombres de variables cortos/ambiguos | `U` no es descriptivo. Debe seguir snake_case y nombres claros. | Renombrar a `user` (minúscula). |
| MEDIA | `main.py:9` | Importaciones al nivel superior mezcladas | `import models, schemas, database` en una línea. PEP 8 prefiere imports por línea. | Separar: `import models` / `import schemas` / `import database` o usar imports absolutos/relativos consistentes. |
| MEDIA | `models.py:4` | Import no agrupado correctamente | Imports mezclan stdlib (`datetime`) con terceros/sqlalchemy. PEP 8 agrupa: stdlib, terceros, locales. | Organizar: stdlib, third-party (sqlalchemy), local (database). |
| MEDIA | `database.py:1-3,5,7-9,11` | Espacios en blanco excesivos | Múltiples líneas en blanco seguidas (líneas 4, 7). PEP 8 recomienda máximo 2 líneas en blanco entre definiciones top-level. | Limpiar espaciado. |
| MEDIA | `main.py:3,8,10` | Líneas en blanco excesivas | Muchas líneas en blanco entre imports/app/decoradores. | Seguir estilo consistente (1-2 líneas en blanco máximo). |
| BAJA | `models.py:26` | Comentarios TODO/problemas en código | Comentarios como "# PROBLEMA: ..." no deben estar en código de producción. | Mover a issues/tickets. Limpiar comentarios. |
| BAJA | `schemas.py:15` | Comentario inline en producción | Mismo caso. | Limpiar. |
| BAJA | `main.py:21` | Comentario o código de debug | `time.sleep(2)` parece debug/prueba, no producción. | Eliminar. |
| BAJA | General | Falta docstrings | Funciones/endpoints sin docstrings. | Añadir docstrings descriptivos. |
| BAJA | `main.py:17,22,46` | Tipado de retorno implícito | Funciones sin type hints de retorno. | Añadir `-> dict` o modelos de respuesta Pydantic. |

## RESUMEN EJECUTIVO

- **Críticos**: Credenciales expuestas, diseño incompleto de órdenes (sin cantidades), lógica de stock incorrecta.
- **Altos**: N+1 queries, sleep bloqueante, sin validación de stock/duplicados, falta de transaccionalidad.
- **Recomendación inmediata**: Remover credenciales, corregir modelo de órdenes con cantidades, eliminar sleep, implementar validación de stock, añadir UNIQUE a email, corregir manejo transaccional.

**Nota**: No se modificó código, solo se analizó según lo solicitado.
