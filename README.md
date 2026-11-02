# Ecommerce API - Reto IA Tricode

API REST para gestión de ecommerce desarrollada con FastAPI, SQLAlchemy y MySQL.

## Requisitos

- Python 3.9+
- MySQL

## Instalación

1. Crear entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus credenciales de base de datos
```

4. Ejecutar la aplicación:
```bash
uvicorn main:app --reload
```

La API estará disponible en `http://localhost:8000`
Documentación interactiva en `http://localhost:8000/docs`

## Variables de entorno

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DATABASE_URL` | URL de conexión a MySQL | Ver `.env.example` |
| `ENVIRONMENT` | Entorno de ejecución (dev/prod) | `dev` |
| `CREATE_TABLES` | Crear tablas automáticamente | `true` |

## Seguridad

- Las credenciales se cargan desde variables de entorno
- Validación de emails únicos
- Transaccionalidad con rollback
- Validación de stock
- Timestamps en UTC

## Notas

- Para producción, usar Alembic para migraciones
- No commitear archivos `.env`
- Las contraseñas/credenciales nunca deben estar hardcodeadas
 
