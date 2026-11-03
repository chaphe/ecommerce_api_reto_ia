"""Configuración de runtime (P01).

Las credenciales viven fuera del código fuente. pydantic-settings las
inyecta desde variables de entorno y, en local, desde el archivo `.env`.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parámetros de la aplicación. Ningún secreto se hardcodea aquí."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Cadena SQLAlchemy completa, p.ej. mysql+pymysql://user:pass@host:3306/db
    database_url: str

    # Umbral y tasa del descuento de catálogo (regla de negocio P04).
    discount_threshold: float = 100.0
    discount_rate: float = 0.10


@lru_cache
def get_settings() -> Settings:
    """Cachea Settings para no releer el entorno en cada request."""
    return Settings()
