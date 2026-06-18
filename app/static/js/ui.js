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

function initPhoneLists() {
  document.querySelectorAll("[data-phone-list]").forEach((root) => {
    const rows = root.querySelector(".phone-rows");
    const addBtn = root.querySelector("[data-phone-add]");
    const listError = root.querySelector(".phone-list-error");
    const checkUrl = root.dataset.checkUrl;
    const excludeUserId = root.dataset.excludeUserId || "";
    if (!rows || !addBtn) return;

    const showListError = (message) => {
      if (!listError) return;
      if (message) {
        listError.textContent = message;
        listError.hidden = false;
      } else {
        listError.textContent = "";
        listError.hidden = true;
      }
    };

    const setRowError = (row, message) => {
      const input = row.querySelector(".phone-number-input");
      const errorEl = row.querySelector(".phone-field-error");
      if (!input || !errorEl) return;
      if (message) {
        input.classList.add("phone-input-invalid");
        errorEl.textContent = message;
        errorEl.hidden = false;
      } else {
        input.classList.remove("phone-input-invalid");
        errorEl.textContent = "";
        errorEl.hidden = true;
      }
    };

    const getFilledRows = () =>
      [...rows.querySelectorAll(".phone-row")].filter((row) => {
        const value = row.querySelector(".phone-number-input")?.value.trim();
        return Boolean(value);
      });

    const getPhoneKey = (row) => {
      const input = row.querySelector(".phone-number-input");
      return (input?.dataset.normalizedPhone || input?.value.trim() || "").toLowerCase();
    };

    const findDuplicateInForm = (key, currentRow) => {
      if (!key) return false;
      return getFilledRows().some((row) => row !== currentRow && getPhoneKey(row) === key.toLowerCase());
    };

    const checkPhoneRemote = async (phone) => {
      const params = new URLSearchParams({ phone });
      if (excludeUserId) params.set("exclude_user_id", excludeUserId);
      const res = await fetch(`${checkUrl}?${params.toString()}`);
      if (!res.ok) return { ok: false, message: "Could not verify phone number" };
      return res.json();
    };

    const validateRow = async (row, { quietEmpty = true } = {}) => {
      const input = row.querySelector(".phone-number-input");
      if (!input) return true;
      const value = input.value.trim();
      if (!value) {
        if (!quietEmpty) {
          setRowError(row, "Enter a phone number");
          return false;
        }
        setRowError(row, "");
        return true;
      }

      if (findDuplicateInForm(value, row)) {
        setRowError(row, "Duplicate phone in this form");
        return false;
      }

      try {
        const result = await checkPhoneRemote(value);
        if (!result.ok) {
          input.dataset.normalizedPhone = "";
          setRowError(row, result.message || "Phone number is not available");
          return false;
        }
        if (result.phone) {
          input.value = result.phone;
          input.dataset.normalizedPhone = result.phone;
        }
        const key = getPhoneKey(row);
        if (findDuplicateInForm(key, row)) {
          setRowError(row, "Duplicate phone in this form");
          return false;
        }
        setRowError(row, "");
        return true;
      } catch (_) {
        setRowError(row, "Could not verify phone number");
        return false;
      }
    };

    const reindexPrimary = () => {
      const rowList = [...rows.querySelectorAll(".phone-row")];
      rowList.forEach((row, index) => {
        const radio = row.querySelector('input[name="phone_primary"]');
        const label = row.querySelector(".phone-primary-label");
        const radioId = `phone_primary_${index}_${Math.random().toString(36).slice(2, 7)}`;
        if (radio) {
          radio.value = String(index);
          radio.id = radioId;
        }
        if (label && radio) label.setAttribute("for", radioId);
      });
      const radios = rows.querySelectorAll('input[name="phone_primary"]');
      if (radios.length && !rows.querySelector('input[name="phone_primary"]:checked')) {
        radios[0].checked = true;
      }
    };

    const bindRow = (row) => {
      const input = row.querySelector(".phone-number-input");
      const removeBtn = row.querySelector(".phone-remove");

      input?.addEventListener("blur", () => {
        validateRow(row).then((ok) => {
          if (ok) showListError("");
        });
      });

      input?.addEventListener("input", () => {
        input.dataset.normalizedPhone = "";
        setRowError(row, "");
        showListError("");
      });

      removeBtn?.addEventListener("click", () => {
        if (rows.children.length <= 1) {
          input.value = "";
          row.querySelector('input[name="phone_label"]').value = "";
          setRowError(row, "");
          showListError("");
          return;
        }
        row.remove();
        reindexPrimary();
        showListError("");
      });
    };

    const createRowHtml = (index) => {
      const radioId = `phone_primary_new_${index}_${Date.now()}`;
      return `
        <div class="phone-row">
          <div class="phone-field-wrap">
            <input type="text" class="phone-number-input" name="phone_number" placeholder="+995592159199" value="" autocomplete="off">
            <p class="phone-field-error" role="alert" hidden></p>
          </div>
          <div class="phone-field-wrap">
            <input type="text" name="phone_label" placeholder="Label (Personal, Family…)" value="">
          </div>
          <div class="phone-primary-control">
            <input type="radio" name="phone_primary" id="${radioId}" value="${index}">
            <label class="phone-primary-label" for="${radioId}">Primary</label>
          </div>
          <button type="button" class="btn btn-ghost btn-sm phone-remove" aria-label="Remove phone">&times;</button>
        </div>
      `;
    };

    rows.querySelectorAll(".phone-row").forEach(bindRow);
    reindexPrimary();

    addBtn.addEventListener("click", async () => {
      showListError("");
      const filled = getFilledRows();
      if (!filled.length) {
        showListError("Enter a phone number before adding another.");
        return;
      }
      let ok = true;
      for (const row of filled) {
        const rowOk = await validateRow(row, { quietEmpty: false });
        ok = ok && rowOk;
      }
      if (!ok) {
        showListError("Fix phone number issues before adding another.");
        return;
      }

      const index = rows.children.length;
      const wrapper = document.createElement("div");
      wrapper.innerHTML = createRowHtml(index).trim();
      const row = wrapper.firstElementChild;
      rows.appendChild(row);
      bindRow(row);
      reindexPrimary();
      row.querySelector(".phone-number-input")?.focus();
    });

    const form = root.closest("form");
    form?.addEventListener("submit", async (event) => {
      const filled = getFilledRows();
      if (!filled.length) return;
      for (const row of filled) {
        const rowOk = await validateRow(row, { quietEmpty: false });
        if (!rowOk) {
          event.preventDefault();
          showListError("Please fix phone number errors before saving.");
          return;
        }
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
  initPhoneLists();
});
