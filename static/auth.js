(function () {
  const form = document.getElementById("auth-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = document.getElementById("auth-error");
    error.classList.add("hidden");
    const payload = Object.fromEntries(new FormData(form).entries());
    try {
      const response = await fetch(window.AUTH_MODE === "register" ? "/auth/register" : "/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "No se pudo completar la operación.");
      window.location.href = data.role === "admin" ? "/admin" : "/orders";
    } catch (requestError) {
      error.textContent = requestError.message;
      error.classList.remove("hidden");
    }
  });
})();
