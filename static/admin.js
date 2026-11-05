(function () {
  const form = document.getElementById("admin-product-form");
  if (!form) return;
  const message = document.getElementById("admin-form-message");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button");
    button.disabled = true;
    message.className = "hidden";
    try {
      const payload = Object.fromEntries(new FormData(form).entries());
      payload.price = Number(payload.price);
      payload.stock = Number(payload.stock);
      const csrf = await fetch("/auth/csrf").then((response) => response.json());
      const response = await fetch("/products/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf.csrf_token },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "No se pudo crear el producto.");
      message.textContent = `Producto #${data.id} creado correctamente.`;
      message.className = "rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300";
      form.reset();
      window.setTimeout(() => window.location.reload(), 700);
    } catch (error) {
      message.textContent = error.message;
      message.className = "rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950/50 dark:text-rose-300";
      button.disabled = false;
    }
  });

  const usersBody = document.getElementById("admin-users-body");
  const userForm = document.getElementById("user-form");
  const userMessage = document.getElementById("user-form-message");
  const importForm = document.getElementById("import-form");
  const importMessage = document.getElementById("import-message");
  const csrf = async () => (await fetch("/auth/csrf")).json().then((data) => data.csrf_token);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[character]));
  const show = (element, text, ok) => {
    element.textContent = text;
    element.className = `rounded-xl px-3 py-2 text-sm ${ok ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`;
  };
  async function loadUsers() {
    const response = await fetch("/admin/users/?limit=50");
    if (!response.ok) return;
    const data = await response.json();
    usersBody.innerHTML = data.items.map((user) => `<tr><td>${escapeHtml(user.name)}<small>${escapeHtml(user.email)}</small></td><td>${escapeHtml(user.role)}</td><td>${user.is_active ? "Activo" : "Inactivo"}</td><td><button class="toggle-user text-indigo-500" data-id="${user.id}" data-active="${user.is_active}">${user.is_active ? "Desactivar" : "Reactivar"}</button></td></tr>`).join("");
  }
  async function loadProducts() {
    const search = encodeURIComponent(document.getElementById("admin-product-search").value);
    const response = await fetch(`/products/admin?search=${search}&include_archived=true&limit=50`);
    if (!response.ok) return;
    const data = await response.json();
    document.getElementById("admin-products-body").innerHTML = data.items.map((product) => `<tr><td><input class="product-select" type="checkbox" value="${product.id}"></td><td>${escapeHtml(product.name)}<small>${product.is_archived ? "Archivado" : "Activo"}</small></td><td>${escapeHtml(product.sku || "—")}</td><td>${Number(product.price).toFixed(2)} €</td><td>${product.stock}</td><td><button class="archive-product text-indigo-500" data-id="${product.id}" data-archived="${product.is_archived}">${product.is_archived ? "Restaurar" : "Archivar"}</button></td></tr>`).join("");
  }
  async function loadCategories() {
    const response = await fetch("/categories/?limit=100");
    if (!response.ok) return;
    const data = await response.json();
    document.getElementById("categories-list").innerHTML = data.items.map((category) => `<div class="list-row"><span>${escapeHtml(category.name)}</span><small>${escapeHtml(category.slug)}</small></div>`).join("");
  }
  async function loadOrders() {
    const search = encodeURIComponent(document.getElementById("admin-order-search").value);
    const status = encodeURIComponent(document.getElementById("admin-order-status").value);
    const response = await fetch(`/orders/admin?search=${search}&status=${status}&limit=50`);
    if (!response.ok) return;
    const data = await response.json();
    document.getElementById("admin-orders-body").innerHTML = data.items.map((order) => `<tr><td class="font-semibold">#${order.id}<small>${escapeHtml(order.created_at)}</small></td><td>${escapeHtml(order.user_id ? `Usuario #${order.user_id}` : "Visitante")}</td><td>${Number(order.total_price).toFixed(2)} €</td><td><select class="order-status rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-900" data-id="${order.id}">${["confirmed", "processing", "shipped", "completed", "cancelled"].map((item) => `<option ${item === order.status ? "selected" : ""}>${item}</option>`).join("")}</select></td><td>${order.is_archived ? "Archivada" : ""}</td></tr>`).join("");
  }
  userForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(userForm).entries());
    const response = await fetch("/admin/users/", { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrf() }, body: JSON.stringify(values) });
    const data = await response.json();
    if (!response.ok) { show(userMessage, data.detail || "No se pudo crear el usuario.", false); userMessage.classList.remove("hidden"); return; }
    show(userMessage, `Usuario #${data.id} creado.`, true); userMessage.classList.remove("hidden"); userForm.reset(); loadUsers();
  });
  usersBody.addEventListener("click", async (event) => {
    const button = event.target.closest(".toggle-user");
    if (!button) return;
    const response = await fetch(`/admin/users/${button.dataset.id}`, { method: "PATCH", headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrf() }, body: JSON.stringify({ is_active: button.dataset.active !== "true" }) });
    if (response.ok) loadUsers();
  });
  document.getElementById("admin-products-body").addEventListener("click", async (event) => {
    const button = event.target.closest(".archive-product");
    if (!button) return;
    const response = await fetch(`/products/${button.dataset.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrf() },
      body: JSON.stringify({ is_archived: button.dataset.archived !== "true" }),
    });
    if (response.ok) loadProducts();
  });
  document.getElementById("bulk-archive-products").addEventListener("click", async () => {
    const productIds = [...document.querySelectorAll(".product-select:checked")].map((item) => Number(item.value));
    if (!productIds.length) return;
    const response = await fetch("/products/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrf() },
      body: JSON.stringify({ product_ids: productIds, is_archived: true }),
    });
    if (response.ok) loadProducts();
  });
  document.getElementById("admin-orders-body").addEventListener("change", async (event) => {
    const select = event.target.closest(".order-status");
    if (!select) return;
    const response = await fetch(`/orders/${select.dataset.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrf() },
      body: JSON.stringify({ status: select.value }),
    });
    if (!response.ok) loadOrders();
  });
  document.getElementById("category-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/categories/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrf() },
      body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget).entries())),
    });
    const data = await response.json();
    show(document.getElementById("category-message"), response.ok ? "Categoría creada." : (data.detail || "No se pudo crear."), response.ok);
    document.getElementById("category-message").classList.remove("hidden");
    if (response.ok) { event.currentTarget.reset(); loadCategories(); }
  });
  document.getElementById("admin-product-search").addEventListener("input", loadProducts);
  document.getElementById("admin-order-search").addEventListener("input", loadOrders);
  document.getElementById("admin-order-status").addEventListener("change", loadOrders);
  importForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/admin/users/import/preview", { method: "POST", body: new FormData(importForm) });
    const data = await response.json();
    if (!response.ok || data.errors.length || data.duplicates.length) { show(importMessage, [...(data.errors || []), ...(data.duplicates || [])].join(" · ") || data.detail, false); importMessage.classList.remove("hidden"); return; }
    if (!window.confirm(`Se importarán ${data.valid_rows.length} usuarios. ¿Confirmar?`)) return;
    const confirmed = await fetch("/admin/users/import/confirm", { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrf() }, body: JSON.stringify(data.valid_rows) });
    const result = await confirmed.json();
    show(importMessage, confirmed.ok ? `${result.length} usuarios importados.` : (result.detail || "No se pudo importar."), confirmed.ok);
    importMessage.classList.remove("hidden");
    if (confirmed.ok) { importForm.reset(); loadUsers(); }
  });
  document.getElementById("product-import-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.getElementById("product-import-message");
    const preview = await fetch("/products/import/preview", { method: "POST", body: new FormData(event.currentTarget) });
    const data = await preview.json();
    if (!preview.ok || data.errors.length || data.duplicates.length) {
      show(message, [...(data.errors || []), ...(data.duplicates || [])].join(" · ") || data.detail, false);
      message.classList.remove("hidden");
      return;
    }
    if (!window.confirm(`Se procesarán ${data.valid_rows.length} productos. ¿Confirmar?`)) return;
    const confirmed = await fetch("/products/import/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrf() },
      body: JSON.stringify(data.valid_rows),
    });
    const result = await confirmed.json();
    show(message, confirmed.ok ? `${result.created} productos importados.` : (result.detail || "No se pudo importar."), confirmed.ok);
    message.classList.remove("hidden");
    if (confirmed.ok) { event.currentTarget.reset(); loadProducts(); }
  });
  loadUsers();
  loadProducts();
  loadCategories();
  loadOrders();
})();
