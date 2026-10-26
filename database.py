from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PROBLEMA DE SEGURIDAD Y BUENAS PRÁCTICAS: Credenciales en duro y sin variables de entorno
DATABASE_URL = "mysql+pymysql://root:password123@localhost:3306/ecommerce_db"

# PROBLEMA DE RENDIMIENTO: Sin configuración de connection pooling para producción
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        # Faltaba cerrar la sesión adecuadamente en ciertos flujos de excepción
        db.close()
