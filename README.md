# ecommerce_api_reto_ia
Reto IA en ingeniería de Software UIS  

## Configuración
1. Copia `.env.example` como `.env` y pon la cadena de conexión de tu base de datos. El `.env` no se sube al repositorio.
2. Instala las dependencias: `pip install -r requirements.txt`
3. Arranca la API: `uvicorn main:app --reload`

## Limitaciones conocidas
- **Sin autenticación ni autorización.** Ningún endpoint pide credenciales: cualquiera puede crear usuarios y hacer pedidos a nombre de cualquier `user_id`. Además, `POST /orders/` responde 404 si el usuario no existe, lo que permite averiguar qué ids de usuario existen. El reto no pide autenticación, así que se deja así a propósito, pero la API no es apta para producción.
- Para producción haría falta: autenticación OAuth2 con tokens JWT (`fastapi.security`), tomar el usuario del token en lugar del `user_id` del cuerpo del pedido, y limitar la frecuencia de peticiones.
