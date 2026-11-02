# CHECKPOINT BLOQUE 2 - CORRECCIÓN DE LÓGICA DE NEGOCIO - ÓRDENES, STOCK Y DESCUENTOS

**Rama:** `fix/security-and-architecture-corrections`  
**Fecha:** 2026-11-01  
**Estado:** Completado  
**Objetivo:** Corregir diseño de órdenes con cantidades, validar stock, hacer procesamiento atómico

## Cambios realizados

| Tarea | Archivo | Descripción |
|---|---|---|
| 2.1 | `schemas.py` | Creado `OrderItem` con `product_id`, `quantity` (gt=0). `OrderCreate` ahora usa `items: List[OrderItem]`. Eliminado diseño con solo `product_ids`. |
| 2.2 | `main.py` | Reescrito `process_order` para usar cantidades. Obtención de productos con `in_()` (evita N+1). Validación de existencia y stock antes de aplicar cambios. Descuento aplicado por item multiplicado por cantidad. |
| 2.2b | `main.py` | Transaccionalidad completa con try/except/rollback. Rollback en HTTPException y excepciones generales. |
| 2.3 | `main.py` | Eliminado `db.add(prod)` innecesario (objetos ya rastreados). |

## Verificación de items

- [x] Pedido con cantidades múltiples funciona
- [x] Stock insuficiente retorna 400 con mensaje claro
- [x] Producto inexistente retorna 400
- [x] Stock se decrementa correctamente por cantidad
- [x] Total calculado correctamente (precio con descuento * cantidad)
- [x] Transacción atómica con rollback
- [x] Sin N+1 queries
- [x] Validación de todos los items antes de modificar stock

## Archivos modificados
- schemas.py
- main.py

## Notas
- El descuento de -10 si precio > 100 se mantiene por ahora (se revisará en bloque posterior si se desea parametrizar)
- Formato de orden cambió: ahora requiere `items` con `product_id` y `quantity`

## Rollback
```bash
git reset --hard HEAD
```

## Siguiente paso
Proceder con **BLOQUE 3: RENDIMIENTO - ELIMINAR BLOQUEO, N+1 Y MEJORAS**
