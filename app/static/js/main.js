/** Client-side helpers — minimal for now */

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-flash]").forEach((el) => {
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.4s";
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });
});
