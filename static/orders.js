(function () {
  const body = document.getElementById("orders-body");
  const empty = document.getElementById("history-empty");
  const error = document.getElementById("history-error");
  const money = (value) => new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(value);
  const date = (value) => new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[character]));
  async function loadHistory() {
    error.classList.add("hidden");
    body.innerHTML = '<tr><td colspan="5" class="px-6 py-12 text-center text-slate-500">Cargando pedidos...</td></tr>';
    try {
      const response = await fetch("/orders/mine");
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 401) throw new Error("Inicia sesión para consultar tus pedidos.");
        throw new Error(data.detail || "No se pudo cargar el historial.");
      }
      body.innerHTML = data.items.map((order) => `<tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50"><td class="whitespace-nowrap px-6 py-5 font-medium">#${order.id}</td><td class="min-w-[220px] px-6 py-5 text-slate-500 dark:text-slate-400">${escapeHtml(order.items.map((item) => `${item.product_name || `Producto #${item.product_id}`} × ${item.quantity}`).join(", "))}</td><td class="whitespace-nowrap px-6 py-5 text-slate-500 dark:text-slate-400">${escapeHtml(date(order.created_at))}</td><td class="px-6 py-5"><span class="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">${escapeHtml(order.status)}</span></td><td class="whitespace-nowrap px-6 py-5 text-right font-semibold">${money(order.total_price)}</td></tr>`).join("");
      empty.classList.toggle("hidden", data.items.length !== 0);
    } catch (requestError) { body.innerHTML = ""; empty.classList.add("hidden"); error.textContent = requestError.message; error.classList.remove("hidden"); }
  }
  document.getElementById("refresh-orders").addEventListener("click", loadHistory);
  loadHistory();
})();
