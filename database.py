"""Sesión de SQLAlchemy. La URL se obtiene de Settings, nunca en texto plano."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import get_settings

# P01: la conexión se construye con el secreto inyectado por el entorno.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Generador de sesión por request. Cierra siempre el socket al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
