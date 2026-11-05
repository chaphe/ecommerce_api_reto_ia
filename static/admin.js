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
      const response = await fetch("/products/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
})();
