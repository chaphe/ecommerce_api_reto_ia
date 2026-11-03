"""Fixtures de infraestructura: SQLite in-memory, seed data y TestClient."""

import os

# Debe ejecutarse antes de importar config/database: evita pegarle a MySQL de .env.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import models
from main import app

# StaticPool: todas las sesiones comparten el mismo :memory: (si no, cada
# conexión abre una BD vacía distinta).
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_fks(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _skip_catalog_sleep(monkeypatch):
    """El catálogo espera 2s; en CI/tests se sustituye por un await inmediato."""

    async def _instant(_seconds=0):
        return None

    monkeypatch.setattr("routers.products.asyncio.sleep", _instant)


@pytest.fixture
def db_session():
    """Crea el esquema, entrega una sesión y limpia al terminar el test."""
    models.Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        models.Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seed_data(db_session):
    """Mocks de usuarios, productos (con/sin stock y con/sin descuento) y una orden."""
    ana = models.User(name="Ana", email="ana@test.com")
    luis = models.User(name="Luis", email="luis@test.com")
    db_session.add_all([ana, luis])
    db_session.flush()

    catalog = [
        models.Product(name="Alpha", price=10.0, stock=100),
        models.Product(name="Beta", price=20.0, stock=100),
        models.Product(name="Gamma", price=30.0, stock=100),
        models.Product(name="Delta", price=40.0, stock=100),
        models.Product(name="Epsilon", price=50.0, stock=100),
        models.Product(name="Laptop", price=200.0, stock=5),
        models.Product(name="Agotado", price=150.0, stock=0),
        models.Product(name="Cable", price=80.0, stock=10),
    ]
    db_session.add_all(catalog)
    db_session.flush()

    by_name = {product.name: product for product in catalog}
    order = models.Order(user_id=ana.id, total_price=220.0)
    db_session.add(order)
    db_session.flush()
    db_session.add_all(
        [
            models.OrderItem(
                order_id=order.id,
                product_id=by_name["Laptop"].id,
                quantity=1,
                unit_price=180.0,
            ),
            models.OrderItem(
                order_id=order.id,
                product_id=by_name["Beta"].id,
                quantity=2,
                unit_price=20.0,
            ),
        ]
    )
    db_session.commit()

    for entity in (ana, luis, order, *catalog):
        db_session.refresh(entity)

    return {
        "ana": ana,
        "luis": luis,
        "products": by_name,
        "order": order,
    }


@pytest.fixture
def client(db_session, seed_data):
    """TestClient con override de get_db sobre la sesión SQLite sembrada."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[database.get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
