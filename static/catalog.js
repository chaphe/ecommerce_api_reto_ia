(function () {
  const config = window.STORE_CONFIG || { discountThreshold: 100, discountRate: 0.1 };
  const money = (value) => new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(value);
  const cart = new Map(JSON.parse(localStorage.getItem("northstar-cart") || "[]").map((item) => [item.id, item]));
  const drawer = document.getElementById("cart-drawer");
  const modal = document.getElementById("checkout-modal");
  const cartItems = document.getElementById("cart-items");
  const count = document.getElementById("cart-count");
  const subtotal = document.getElementById("cart-subtotal");
  const discount = document.getElementById("cart-discount");
  const total = document.getElementById("cart-total");
  const checkout = document.getElementById("checkout-button");
  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[character]));

  function renderCart() {
    const items = [...cart.values()];
    const quantity = items.reduce((sum, item) => sum + item.quantity, 0);
    const raw = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const savings = items.reduce((sum, item) => sum + (item.price > config.discountThreshold ? item.price * config.discountRate * item.quantity : 0), 0);
    count.textContent = quantity;
    document.getElementById("cart-subtitle").textContent = `${quantity} producto${quantity === 1 ? "" : "s"}`;
    subtotal.textContent = money(raw);
    discount.textContent = `-${money(savings)}`;
    total.textContent = money(raw - savings);
    checkout.disabled = !items.length;
    localStorage.setItem("northstar-cart", JSON.stringify(items));
    cartItems.innerHTML = items.length ? items.map((item) => `<div class="flex items-center gap-3 rounded-xl bg-slate-50 p-3 dark:bg-slate-800"><div class="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-indigo-100 font-semibold text-indigo-500 dark:bg-indigo-950">${escapeHtml(item.name[0].toUpperCase())}</div><div class="min-w-0 flex-1"><p class="truncate text-sm font-medium">${escapeHtml(item.name)}</p><p class="text-xs text-slate-500">${money(item.price)} · ${item.quantity} ud.</p></div><div class="flex items-center gap-1"><button class="cart-quantity rounded-md px-2 py-1 text-slate-500 hover:bg-white dark:hover:bg-slate-700" data-id="${item.id}" data-change="-1">−</button><span class="w-4 text-center text-sm">${item.quantity}</span><button class="cart-quantity rounded-md px-2 py-1 text-slate-500 hover:bg-white dark:hover:bg-slate-700" data-id="${item.id}" data-change="1">+</button></div></div>`).join("") : '<div class="flex h-full flex-col items-center justify-center text-center text-slate-500"><span class="text-4xl">∅</span><p class="mt-3 text-sm">Tu carrito está vacío.</p></div>';
  }
  function open(element) { element.classList.remove("hidden"); element.classList.add("flex"); element.setAttribute("aria-hidden", "false"); }
  function close(element) { element.classList.add("hidden"); element.classList.remove("flex"); element.setAttribute("aria-hidden", "true"); }
  document.querySelectorAll(".add-to-cart").forEach((button) => button.addEventListener("click", () => {
    const item = { id: Number(button.dataset.id), name: button.dataset.name, price: Number(button.dataset.price), stock: Number(button.dataset.stock), quantity: 0 };
    const existing = cart.get(item.id) || item;
    if (existing.quantity < existing.stock) existing.quantity += 1;
    cart.set(item.id, existing);
    renderCart();
    window.showToast(`${item.name} añadido al carrito`);
  }));
  cartItems.addEventListener("click", (event) => {
    const button = event.target.closest(".cart-quantity");
    if (!button) return;
    const item = cart.get(Number(button.dataset.id));
    item.quantity += Number(button.dataset.change);
    if (item.quantity <= 0) cart.delete(item.id);
    if (item.quantity > item.stock) item.quantity = item.stock;
    renderCart();
  });
  document.getElementById("open-cart").addEventListener("click", () => open(drawer));
  document.getElementById("close-cart").addEventListener("click", () => close(drawer));
  document.getElementById("cart-backdrop").addEventListener("click", () => close(drawer));
  checkout.addEventListener("click", () => { close(drawer); open(modal); });
  document.getElementById("close-checkout").addEventListener("click", () => close(modal));
  document.getElementById("checkout-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = document.getElementById("checkout-error");
    error.classList.add("hidden");
    const payload = { items: [...cart.values()].map((item) => ({ product_id: item.id, quantity: item.quantity })) };
    try {
      const response = await fetch("/orders/guest", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "No se pudo procesar la orden.");
      cart.clear(); renderCart(); close(modal); window.showToast(`Orden #${data.id} confirmada`);
      window.setTimeout(() => window.location.href = "/", 1200);
    } catch (requestError) { error.textContent = requestError.message; error.classList.remove("hidden"); }
  });
  function filterProducts() {
    const term = document.getElementById("product-search").value.toLowerCase().trim();
    const category = document.getElementById("category-filter").value;
    const price = document.getElementById("price-filter").value;
    let visible = 0;
    document.querySelectorAll(".product-card").forEach((card) => {
      const amount = Number(card.dataset.price);
      const matchesPrice = price === "all" || (price === "under-50" && amount < 50) || (price === "50-100" && amount >= 50 && amount <= 100) || (price === "over-100" && amount > 100);
      const matches = card.dataset.name.includes(term) && (category === "all" || card.dataset.category === category) && matchesPrice;
      card.classList.toggle("hidden", !matches); if (matches) visible += 1;
    });
    document.getElementById("empty-results").classList.toggle("hidden", visible !== 0);
    document.getElementById("results-count").textContent = `${visible} producto${visible === 1 ? "" : "s"} encontrado${visible === 1 ? "" : "s"}`;
  }
  ["product-search", "category-filter", "price-filter"].forEach((id) => document.getElementById(id).addEventListener("input", filterProducts));
  document.getElementById("clear-filters").addEventListener("click", () => {
    document.getElementById("product-search").value = "";
    document.getElementById("category-filter").value = "all";
    document.getElementById("price-filter").value = "all";
    filterProducts();
  });
  document.getElementById("checkout-form").addEventListener("submit", () => {
    document.getElementById("confirm-checkout").disabled = true;
    document.getElementById("confirm-checkout").textContent = "Procesando…";
  });
  renderCart();
})();
