(async function () {
  const form = document.getElementById("profile-form");
  const message = document.getElementById("profile-message");
  const response = await fetch("/auth/me");
  if (!response.ok) { window.location.href = "/login"; return; }
  const user = await response.json();
  document.getElementById("profile-name").value = user.name;
  document.getElementById("profile-email").value = user.email;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const csrf = await fetch("/auth/csrf").then((item) => item.json());
    const update = await fetch("/users/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf.csrf_token },
      body: JSON.stringify(Object.fromEntries(new FormData(form).entries())),
    });
    const data = await update.json();
    message.textContent = update.ok ? "Perfil actualizado." : (data.detail || "No se pudo actualizar.");
    message.className = update.ok
      ? "rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
      : "rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700";
  });
  document.getElementById("logout-button").addEventListener("click", async () => {
    const csrf = await fetch("/auth/csrf").then((item) => item.json());
    await fetch("/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf.csrf_token } });
    window.location.href = "/";
  });
})();
