(function () {
  const root = document.documentElement;
  const savedTheme = localStorage.getItem("northstar-theme");
  if (savedTheme === "dark" || (!savedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches)) root.classList.add("dark");
  const button = document.getElementById("theme-toggle");
  const icon = document.getElementById("theme-icon");
  const updateIcon = () => { if (icon) icon.textContent = root.classList.contains("dark") ? "☼" : "◐"; };
  updateIcon();
  button?.addEventListener("click", () => {
    root.classList.toggle("dark");
    localStorage.setItem("northstar-theme", root.classList.contains("dark") ? "dark" : "light");
    updateIcon();
  });
  window.showToast = (message) => {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove("translate-y-4", "opacity-0");
    window.setTimeout(() => toast.classList.add("translate-y-4", "opacity-0"), 2600);
  };
})();
