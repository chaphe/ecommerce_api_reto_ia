"""Suite unitaria/API. Cada test sigue AAA: Arrange, Act, Assert."""

from fastapi import HTTPException
from fastapi.testclient import TestClient

import crud
import database


def test_get_products_pagination_limit_and_offset(client: TestClient, seed_data):
    # Arrange: catálogo sembrado ordenado por id (Alpha, Beta, Gamma, ...)
    ordered_names = [
        "Alpha",
        "Beta",
        "Gamma",
        "Delta",
        "Epsilon",
        "Laptop",
        "Agotado",
        "Cable",
    ]

    # Act
    page_1 = client.get("/products/", params={"limit": 3, "offset": 0})
    page_2 = client.get("/products/", params={"limit": 3, "offset": 3})
    page_tail = client.get("/products/", params={"limit": 10, "offset": 7})
    defaults = client.get("/products/")

    # Assert
    assert page_1.status_code == 200
    assert [item["name"] for item in page_1.json()] == ordered_names[0:3]
    assert [item["name"] for item in page_2.json()] == ordered_names[3:6]
    assert [item["name"] for item in page_tail.json()] == ordered_names[7:8]
    assert len(defaults.json()) == 8  # default limit=10, offset=0


def test_get_products_rejects_limit_over_max(client: TestClient):
    # Arrange / Act
    response = client.get("/products/", params={"limit": 101, "offset": -1})

    # Assert: Query(le=100) y Query(ge=0) → 422
    assert response.status_code == 422


def test_get_user_orders_returns_nested_product_names(client: TestClient, seed_data):
    # Arrange
    ana_id = seed_data["ana"].id

    # Act
    response = client.get(f"/users/{ana_id}/orders")

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    order = payload[0]
    assert order["id"] == seed_data["order"].id
    assert order["user_id"] == ana_id
    assert order["total_price"] == 220.0
    assert "created_at" in order
    assert order["product_names"] == ["Laptop", "Beta"]


def test_get_user_orders_empty_history_and_404(client: TestClient, seed_data):
    # Arrange / Act
    empty = client.get(f"/users/{seed_data['luis'].id}/orders")
    missing = client.get("/users/99999/orders")

    # Assert
    assert empty.status_code == 200
    assert empty.json() == []
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Usuario no encontrado"


def test_process_order_applies_percentage_discount(client: TestClient, seed_data):
    # Arrange: Laptop 200 > umbral 100 → 10% → 180.00; Cable 80 → sin descuento.
    laptop = seed_data["products"]["Laptop"]
    cable = seed_data["products"]["Cable"]
    payload = {
        "user_id": seed_data["ana"].id,
        "items": [
            {"product_id": laptop.id, "quantity": 2},
            {"product_id": cable.id, "quantity": 1},
        ],
    }

    # Act
    response = client.post("/orders/", json=payload)

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["total_price"] == 440.0  # (180 * 2) + 80
    by_product = {item["product_id"]: item for item in body["items"]}
    assert by_product[laptop.id]["unit_price"] == 180.0
    assert by_product[laptop.id]["quantity"] == 2
    assert by_product[cable.id]["unit_price"] == 80.0

    catalog = {item["id"]: item for item in client.get("/products/").json()}
    assert catalog[laptop.id]["stock"] == 3  # 5 - 2
    assert catalog[cable.id]["stock"] == 9  # 10 - 1


def test_process_order_rejects_out_of_stock(client: TestClient, seed_data):
    # Arrange
    agotado = seed_data["products"]["Agotado"]
    payload = {
        "user_id": seed_data["ana"].id,
        "items": [{"product_id": agotado.id, "quantity": 1}],
    }

    # Act
    response = client.post("/orders/", json=payload)

    # Assert
    assert response.status_code == 409
    assert "Stock insuficiente" in response.json()["detail"]
    assert "Agotado" in response.json()["detail"]


def test_process_order_user_not_found(client: TestClient, seed_data):
    # Arrange
    product_id = seed_data["products"]["Alpha"].id

    # Act
    response = client.post(
        "/orders/",
        json={"user_id": 99999, "items": [{"product_id": product_id, "quantity": 1}]},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Usuario no encontrado"


def test_process_order_missing_product(client: TestClient, seed_data):
    # Arrange / Act
    response = client.post(
        "/orders/",
        json={
            "user_id": seed_data["ana"].id,
            "items": [{"product_id": 99999, "quantity": 1}],
        },
    )

    # Assert
    assert response.status_code == 400
    assert "Productos inexistentes" in response.json()["detail"]


def test_process_order_internal_error_rolls_back(client: TestClient, seed_data, monkeypatch):
    # Arrange
    def _boom(*_args, **_kwargs):
        raise RuntimeError("fallo de infraestructura")

    monkeypatch.setattr("routers.orders.crud.create_order", _boom)

    # Act
    response = client.post(
        "/orders/",
        json={
            "user_id": seed_data["ana"].id,
            "items": [{"product_id": seed_data["products"]["Alpha"].id, "quantity": 1}],
        },
    )

    # Assert
    assert response.status_code == 500
    assert response.json()["detail"] == "Error al procesar la orden"


def test_create_user_and_duplicate_email(client: TestClient):
    # Arrange
    payload = {"name": "Marta", "email": "marta@test.com"}

    # Act
    created = client.post("/users/", json=payload)
    duplicate = client.post("/users/", json=payload)

    # Assert
    assert created.status_code == 200
    assert created.json()["email"] == "marta@test.com"
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "El email ya está registrado"


def test_get_db_closes_session(monkeypatch):
    # Arrange
    class DummySession:
        closed = False

        def close(self):
            self.closed = True

    dummy = DummySession()
    monkeypatch.setattr(database, "SessionLocal", lambda: dummy)

    # Act
    generator = database.get_db()
    session = next(generator)
    generator.close()

    # Assert
    assert session is dummy
    assert dummy.closed is True


def test_unit_price_without_discount_at_threshold():
    # Arrange / Act / Assert
    assert crud.unit_price_with_discount(100.0) == 100.0
    assert crud.unit_price_with_discount(50.0) == 50.0
    assert crud.unit_price_with_discount(200.0) == 180.0


def test_process_order_reraises_http_exception(client: TestClient, seed_data, monkeypatch):
    # Arrange
    def _raise_http(*_args, **_kwargs):
        raise HTTPException(status_code=418, detail="teapot")

    monkeypatch.setattr("routers.orders.crud.create_order", _raise_http)

    # Act
    response = client.post(
        "/orders/",
        json={
            "user_id": seed_data["ana"].id,
            "items": [{"product_id": seed_data["products"]["Alpha"].id, "quantity": 1}],
        },
    )

    # Assert
    assert response.status_code == 418
    assert response.json()["detail"] == "teapot"


def test_create_product(client: TestClient):
    # Arrange
    payload = {"name": "Monitor", "price": 300.0, "stock": 4}

    # Act
    response = client.post("/products/", json=payload)

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Monitor"
    assert body["price"] == 300.0
    assert body["stock"] == 4
    assert body["id"] > 0
