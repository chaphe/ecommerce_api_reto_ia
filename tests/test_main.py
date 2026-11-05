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
    client.post("/auth/login", json={"email": "luis@test.com", "password": "Luis-password-123"})
    empty = client.get(f"/users/{seed_data['luis'].id}/orders")
    missing = client.get("/users/99999/orders")

    # Assert
    assert empty.status_code == 200
    assert empty.json() == []
    assert missing.status_code == 403
    assert "otro usuario" in missing.json()["detail"]


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
    assert response.status_code == 403
    assert "otro usuario" in response.json()["detail"]


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
    client.post("/auth/login", json={"email": "admin@test.com", "password": "Admin-password-123"})
    client.headers.update({"X-CSRF-Token": client.get("/auth/csrf").json()["csrf_token"]})
    payload = {"name": "Marta", "email": "marta@test.com", "password": "Marta-password-123", "role": "buyer"}

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

    client.post("/auth/login", json={"email": "admin@test.com", "password": "Admin-password-123"})
    client.headers.update({"X-CSRF-Token": client.get("/auth/csrf").json()["csrf_token"]})
    response = client.post("/products/", json=payload)

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Monitor"
    assert body["price"] == 300.0
    assert body["stock"] == 4
    assert body["id"] > 0


def test_admin_dashboard_renders_live_metrics(client: TestClient, seed_data):
    client.post("/auth/login", json={"email": "admin@test.com", "password": "Admin-password-123"})
    response = client.get("/admin")

    assert response.status_code == 200
    assert "Resumen de la tienda" in response.text
    assert "8" in response.text
    assert "Órdenes recientes" in response.text


def test_buyer_cannot_access_admin_or_other_order_history(client: TestClient, seed_data):
    assert client.get("/admin").status_code == 403
    assert client.get(f"/users/{seed_data['luis'].id}/orders").status_code == 403


def test_auth_register_login_profile_and_csrf(client: TestClient):
    client.post("/auth/logout", headers={"X-CSRF-Token": client.get("/auth/csrf").json()["csrf_token"]})
    registered = client.post(
        "/auth/register",
        json={"name": "Marta", "email": "marta-auth@test.com", "password": "Marta-password-123"},
    )
    assert registered.status_code == 201
    assert client.get("/auth/me").json()["email"] == "marta-auth@test.com"
    assert client.patch("/users/me", json={"name": "Changed", "email": "marta-auth@test.com"}).status_code == 403
    csrf = client.get("/auth/csrf").json()["csrf_token"]
    updated = client.patch(
        "/users/me",
        json={"name": "Changed", "email": "marta-auth@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    client.post("/auth/logout", headers={"X-CSRF-Token": csrf})
    assert client.get("/auth/me").status_code == 401


def test_guest_checkout_is_available(client: TestClient, seed_data):
    response = client.post(
        "/orders/guest",
        json={"items": [{"product_id": seed_data["products"]["Alpha"].id, "quantity": 1}]},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] is None


def test_admin_can_preview_and_confirm_csv_import(client: TestClient):
    client.post("/auth/login", json={"email": "admin@test.com", "password": "Admin-password-123"})
    preview = client.post(
        "/admin/users/import/preview",
        files={"file": ("users.csv", b"name,email,password,role\nNew User,new-user@test.com,New-password-123,buyer\n", "text/csv")},
    )
    assert preview.status_code == 200
    rows = preview.json()["valid_rows"]
    csrf = client.get("/auth/csrf").json()["csrf_token"]
    confirmed = client.post("/admin/users/import/confirm", json=rows, headers={"X-CSRF-Token": csrf})
    assert confirmed.status_code == 201
    assert confirmed.json()[0]["email"] == "new-user@test.com"


def test_admin_product_category_import_export_and_bulk_operations(client: TestClient, seed_data):
    client.post("/auth/login", json={"email": "admin@test.com", "password": "Admin-password-123"})
    csrf = client.get("/auth/csrf").json()["csrf_token"]
    headers = {"X-CSRF-Token": csrf}

    category = client.post(
        "/categories/",
        json={"name": "Studio", "slug": "studio"},
        headers=headers,
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    created = client.post(
        "/products/",
        json={
            "name": "Camera",
            "sku": "CAM-001",
            "price": 120,
            "stock": 3,
            "category_id": category_id,
            "description": "Camera de estudio",
        },
        headers=headers,
    )
    assert created.status_code == 200
    product_id = created.json()["id"]

    updated = client.patch(
        f"/products/{product_id}",
        json={"price": 130, "stock": 5},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == 130

    bulk = client.post(
        "/products/bulk",
        json={"product_ids": [product_id], "stock_delta": -2},
        headers=headers,
    )
    assert bulk.status_code == 200
    assert client.get(f"/categories/{category_id}/products").json()["items"][0]["id"] == product_id

    preview = client.post(
        "/products/import/preview",
        files={"file": ("products.csv", b"name,sku,price,stock,category_slug\nMic,MIC-001,40,8,studio\n", "text/csv")},
    )
    assert preview.status_code == 200
    imported = client.post(
        "/products/import/confirm",
        json=preview.json()["valid_rows"],
        headers=headers,
    )
    assert imported.status_code == 201
    assert imported.json()["created"] == 1

    exported = client.get("/products/export?format=csv")
    assert exported.status_code == 200
    assert "CAM-001" in exported.text


def test_order_detail_status_and_historical_product_name(client: TestClient, seed_data):
    client.post("/auth/login", json={"email": "ana@test.com", "password": "Ana-password-123"})
    csrf = client.get("/auth/csrf").json()["csrf_token"]
    order_id = seed_data["order"].id
    detail = client.get(f"/orders/{order_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "confirmed"
    client.post("/auth/logout", headers={"X-CSRF-Token": csrf})

    client.post("/auth/login", json={"email": "admin@test.com", "password": "Admin-password-123"})
    csrf = client.get("/auth/csrf").json()["csrf_token"]
    changed = client.patch(
        f"/orders/{order_id}",
        json={"status": "processing"},
        headers={"X-CSRF-Token": csrf},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "processing"


def test_admin_cancellation_restores_inventory_once(client: TestClient, seed_data):
    client.post("/auth/login", json={"email": "admin@test.com", "password": "Admin-password-123"})
    csrf = client.get("/auth/csrf").json()["csrf_token"]
    laptop = seed_data["products"]["Laptop"]
    before = laptop.stock
    response = client.patch(
        f"/orders/{seed_data['order'].id}",
        json={"status": "cancelled", "cancellation_reason": "Customer request"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    catalog = {item["name"]: item for item in client.get("/products/").json()}
    assert catalog["Laptop"]["stock"] == before + 1
    repeated = client.patch(
        f"/orders/{seed_data['order'].id}",
        json={"status": "cancelled"},
        headers={"X-CSRF-Token": csrf},
    )
    assert repeated.status_code == 200
    assert {item["name"]: item for item in client.get("/products/").json()}["Laptop"]["stock"] == before + 1


def test_buyer_cannot_use_commercial_admin_endpoints(client: TestClient):
    assert client.get("/products/admin").status_code == 403
    assert client.get("/products/export").status_code == 403
    assert client.get("/orders/admin").status_code == 403
    assert client.post("/categories/", json={"name": "Blocked", "slug": "blocked"}).status_code == 403


def test_product_export_neutralizes_spreadsheet_formulas(client: TestClient):
    client.post("/auth/login", json={"email": "admin@test.com", "password": "Admin-password-123"})
    csrf = client.get("/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/products/",
        json={"name": "=HYPERLINK(\"https://example.test\")", "sku": "FORMULA-001", "price": 1, "stock": 1},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    exported = client.get("/products/export?format=csv")
    assert "'=HYPERLINK" in exported.text


def test_admin_creation_round_trip_and_public_registration_cannot_escalate(
    client: TestClient, seed_data
):
    registration = client.post(
        "/auth/register",
        json={
            "name": "Buyer",
            "email": "buyer-roundtrip@test.com",
            "password": "Buyer-password-123",
            "role": "admin",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["role"] == "buyer"

    client.post("/auth/login", json={"email": "admin@test.com", "password": "Admin-password-123"})
    csrf = client.get("/auth/csrf").json()["csrf_token"]
    headers = {"X-CSRF-Token": csrf}
    user = client.post(
        "/admin/users/",
        json={
            "name": "Admin Created",
            "email": "admin-created@test.com",
            "password": "Admin-created-123",
            "role": "buyer",
        },
        headers=headers,
    )
    assert user.status_code == 201
    assert user.json()["role"] == "buyer"

    product = client.post(
        "/products/",
        json={
            "name": "Round-trip product",
            "sku": "ROUND-001",
            "description": "Persisted product",
            "price": 75,
            "stock": 6,
        },
        headers=headers,
    )
    assert product.status_code == 200
    product_id = product.json()["id"]
    assert client.get("/products/").json()[-1]["id"] == product_id
    admin_products = client.get("/products/admin", headers=headers).json()["items"]
    assert next(item for item in admin_products if item["id"] == product_id)["sku"] == "ROUND-001"


def test_my_orders_requires_identity_and_never_uses_browser_user_id(client: TestClient, seed_data):
    client.post("/auth/logout", headers={"X-CSRF-Token": client.get("/auth/csrf").json()["csrf_token"]})
    assert client.get("/orders/mine").status_code == 401

    client.post("/auth/login", json={"email": "Ana@test.com", "password": "Ana-password-123"})
    response = client.get("/orders/mine")
    assert response.status_code == 200
    assert response.json()["items"][0]["user_id"] == seed_data["ana"].id
    assert client.get(f"/users/{seed_data['luis'].id}/orders").status_code == 403


def test_web_pages_use_real_authenticated_order_flow(client: TestClient):
    catalog = client.get("/")
    orders = client.get("/orders")
    orders_script = client.get("/static/orders.js")
    assert catalog.status_code == 200
    assert orders.status_code == 200
    assert orders_script.status_code == 200
    assert 'fetch("/orders/mine")' in orders_script.text
    assert "history-user-id" not in orders.text
