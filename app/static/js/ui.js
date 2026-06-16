/** UI components: combobox search, flash dismiss, mobile nav */

function debounce(fn, ms = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

function initFlashMessages() {
  document.querySelectorAll("[data-flash]").forEach((el) => {
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.35s";
      setTimeout(() => el.remove(), 350);
    }, 5000);
  });
}

function initMobileNav() {
  const toggle = document.querySelector("[data-nav-toggle]");
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.querySelector(".sidebar-overlay");
  if (!toggle || !sidebar) return;

  const close = () => {
    sidebar.classList.remove("open");
    overlay?.classList.remove("open");
  };

  toggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay?.classList.toggle("open");
  });
  overlay?.addEventListener("click", close);
}

function initComboboxes() {
  document.querySelectorAll("[data-combobox]").forEach((root) => {
    const source = root.dataset.source;
    const input = root.querySelector(".combobox-input");
    const hidden = root.querySelector(`input[name="${root.dataset.name}"]`);
    const dropdown = root.querySelector(".combobox-dropdown");
    const clearBtn = root.querySelector(".combobox-clear");
    let activeIndex = -1;
    let items = [];

    const showClear = () => {
      if (clearBtn) clearBtn.hidden = !hidden.value;
    };

    const setValue = (item) => {
      if (!item) return;
      hidden.value = item.id;
      input.value = item.label + (item.sub ? ` · ${item.sub}` : "");
      dropdown.hidden = true;
      showClear();
    };

    if (root.dataset.initialValue && root.dataset.initialLabel) {
      input.value = root.dataset.initialLabel;
      showClear();
    }

    const render = (results) => {
      items = results;
      activeIndex = -1;
      dropdown.innerHTML = "";
      if (!results.length) {
        dropdown.innerHTML = '<li class="combobox-empty">No results found</li>';
        dropdown.hidden = false;
        return;
      }
      results.forEach((item, idx) => {
        const li = document.createElement("li");
        li.className = "combobox-option";
        li.role = "option";
        li.innerHTML = `<div class="combobox-option-label">${escapeHtml(item.label)}</div>` +
          (item.sub ? `<div class="combobox-option-sub">${escapeHtml(item.sub)}</div>` : "");
        li.addEventListener("mousedown", (e) => {
          e.preventDefault();
          setValue(item);
        });
        dropdown.appendChild(li);
      });
      dropdown.hidden = false;
    };

    const fetchResults = debounce(async (q) => {
      try {
        const res = await fetch(`${source}?q=${encodeURIComponent(q)}&limit=20`);
        if (!res.ok) return;
        render(await res.json());
      } catch (_) {
        /* ignore */
      }
    }, 220);

    input.addEventListener("input", () => {
      hidden.value = "";
      showClear();
      fetchResults(input.value.trim());
    });

    input.addEventListener("focus", () => {
      fetchResults(input.value.trim());
    });

    input.addEventListener("keydown", (e) => {
      const options = dropdown.querySelectorAll(".combobox-option");
      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeIndex = Math.min(activeIndex + 1, options.length - 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
      } else if (e.key === "Enter" && activeIndex >= 0) {
        e.preventDefault();
        setValue(items[activeIndex]);
        return;
      } else if (e.key === "Escape") {
        dropdown.hidden = true;
        return;
      } else {
        return;
      }
      options.forEach((el, i) => el.classList.toggle("active", i === activeIndex));
    });

    clearBtn?.addEventListener("click", () => {
      hidden.value = "";
      input.value = "";
      dropdown.hidden = true;
      showClear();
      input.focus();
    });

    document.addEventListener("click", (e) => {
      if (!root.contains(e.target)) dropdown.hidden = true;
    });
  });
}

function initTransactionDialogs() {
  const openDialog = (id) => {
    if (!id) return;
    const dialog = document.getElementById(id);
    if (!dialog || typeof dialog.showModal !== "function") return;
    dialog.showModal();
    document.body.classList.add("modal-open");
  };

  const closeDialog = (dialog) => {
    if (!dialog) return;
    dialog.close();
    document.body.classList.remove("modal-open");
  };

  document.querySelectorAll("[data-open-bank-details]").forEach((el) => {
    const dialogId = el.dataset.openBankDetails;
    const open = () => openDialog(dialogId);

    if (el.matches("button")) {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        open();
      });
    }

    if (el.matches("tr")) {
      el.addEventListener("dblclick", open);
    }
  });

  document.querySelectorAll(".txn-dialog").forEach((dialog) => {
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog) closeDialog(dialog);
    });

    dialog.querySelectorAll("[data-close-dialog]").forEach((btn) => {
      btn.addEventListener("click", () => closeDialog(dialog));
    });

    dialog.addEventListener("close", () => {
      if (!document.querySelector(".txn-dialog[open]")) {
        document.body.classList.remove("modal-open");
      }
    });
  });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

document.addEventListener("DOMContentLoaded", () => {
  initFlashMessages();
  initMobileNav();
  initComboboxes();
  initTransactionDialogs();
});
