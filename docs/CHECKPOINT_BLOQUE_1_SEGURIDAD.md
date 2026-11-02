# CHECKPOINT BLOQUE 1 - SEGURIDAD - CREDENCIALES, VALIDACIÓN Y TRANSACCIONALIDAD

**Rama:** `fix/security-and-architecture-corrections`  
**Fecha:** 2026-11-01  
**Estado:** Completado  
**Objetivo:** Eliminar credenciales hardcodeadas, mejorar validación, asegurar transaccionalidad

## Cambios realizados

| Tarea | Archivo | Descripción |
|---|---|---|
| 1.1 | `database.py` | Conexión migrada a variables de entorno desde `config.py`. Eliminadas credenciales hardcodeadas. |
| 1.2 | `models.py` | Añadido `unique=True, index=True, nullable=False` a email. Añadidos `nullable=False` a campos. Añadido índice a `user_id` en Order. Añadido `relationship` a Order. Usa `timezone.utc`. |
| 1.3 | `main.py` | Validación de email duplicado con retorno 409. Manejo transaccional con try/except/rollback. |
| 1.4 | `schemas.py` | Añadidos validadores con `EmailStr`, `Field(min_length/max_length)`, `gt/gt=0/ge`. |
| 1.4b | `main.py` | Transaccionalidad en create_user y process_order. |
| 1.5 | `models.py` | `created_at` usa `datetime.datetime.now(datetime.timezone.utc)`. |
| 1.6 | `main.py` | `create_all()` controlado por entorno. Eliminado `time.sleep(2)`. Añadida validación de stock >= 1. |

## Verificación de items

- [x] `database.py` ya no contiene credenciales en texto claro
- [x] Registro duplicado retorna 409
- [x] Registro válido crea usuario correctamente
- [x] Transacciones con rollback implementadas
- [x] Timezone UTC aplicado
- [x] Email con validación y restricción unique
- [x] `create_all()` controlado por entorno
- [x] Sin cambios en lógica funcional no relacionados

## Archivos modificados
- database.py
- models.py
- schemas.py
- main.py

## Archivos nuevos
- config.py (BLOQUE 0)
- .env.example (BLOQUE 0)

## Rollback
```bash
git reset --hard HEAD  # volver al estado anterior
# o revertir por archivo
```

## Siguiente paso
Proceder con **BLOQUE 2: CORRECCIÓN DE LÓGICA DE NEGOCIO - ÓRDENES, STOCK Y DESCUENTOS**
