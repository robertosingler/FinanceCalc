(() => {
  "use strict";

  const CURRENT_USER = window.FC_USER || null;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const state = {
    rate_type: "effective",
    mode: "end",
    decimals: 3,
  };

  const fields = ["pv", "pmt", "fv", "rate", "n"];
  const inputs = Object.fromEntries(fields.map((f) => [f, $(`#in-${f}`)]));

  // ---------- Toast ----------
  let toastTimer = null;
  function toast(msg, isError = false) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.toggle("error", isError);
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
  }

  // ---------- Pill toggles (rate_type / mode / decimals) ----------
  $$(".pill-toggle[data-group]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const group = btn.dataset.group;
      const value = btn.dataset.value;
      $$(`.pill-toggle[data-group="${group}"]`).forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state[group] = group === "decimals" ? parseInt(value, 10) : value;
    });
  });

  // ---------- Theme ----------
  const root = document.documentElement;
  $("#btn-theme").addEventListener("click", () => {
    const isLight = root.getAttribute("data-theme") === "light";
    root.setAttribute("data-theme", isLight ? "dark" : "light");
    $("#btn-theme").textContent = isLight ? "🌙" : "☀️";
    localStorage.setItem("fc_theme", isLight ? "dark" : "light");
  });
  (() => {
    const saved = localStorage.getItem("fc_theme");
    if (saved === "light") {
      root.setAttribute("data-theme", "light");
      $("#btn-theme").textContent = "☀️";
    }
  })();

  // ---------- Helpers ----------
  function num(id) {
    const v = inputs[id].value.trim();
    if (v === "") return null;
    const n = parseFloat(v);
    return Number.isNaN(n) ? null : n;
  }

  function fmt(n, decimals = state.decimals) {
    if (n === null || n === undefined || Number.isNaN(n)) return "—";
    return Number(n).toLocaleString("es-AR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  function currentPayload(solveFor) {
    return {
      solve_for: solveFor,
      pv: num("pv"),
      pmt: num("pmt"),
      fv: num("fv"),
      rate: num("rate"),
      n: num("n"),
      freq: parseInt($("#sel-freq").value, 10),
      rate_type: state.rate_type,
      mode: state.mode,
      decimals: state.decimals,
    };
  }

  function updateSummary() {
    $("#sum-pv").textContent = fmt(num("pv"), 2);
    $("#sum-pmt").textContent = fmt(num("pmt"), 2);
    $("#sum-fv").textContent = fmt(num("fv"), 2);
    $("#sum-rate").textContent = num("rate") !== null ? `${fmt(num("rate"), 4)}%` : "—";
    $("#sum-n").textContent = num("n") !== null ? fmt(num("n"), 0) : "—";
  }

  // ---------- Solve ----------
  async function solve(field) {
    const payload = currentPayload(field);
    const btn = document.querySelector(`.solve-btn[data-solve="${field}"]`);
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = "…";

    try {
      const res = await fetch("/api/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!data.ok) {
        toast(data.error || "Error al calcular", true);
        return;
      }

      const value = data.result[field];
      inputs[field].value = value;

      const fieldEl = document.querySelector(`.field[data-field="${field}"]`);
      fieldEl.classList.remove("solved");
      void fieldEl.offsetWidth;
      fieldEl.classList.add("solved");

      $("#sum-periodic").textContent = `${fmt(data.result.periodic_rate_pct, 5)}%`;
      $("#result-value").textContent = `${field.toUpperCase()} = ${fmt(value, state.decimals)}`;
      updateSummary();
      // El backend ya guardo esta entrada en la base de datos si hay sesion.
      if (CURRENT_USER) renderHistory(); else pushHistoryLocal(field, value, payload);
    } catch (e) {
      toast("No se pudo conectar con el servidor", true);
    } finally {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }

  $$(".solve-btn").forEach((btn) => {
    btn.addEventListener("click", () => solve(btn.dataset.solve));
  });

  fields.forEach((f) => inputs[f].addEventListener("input", updateSummary));

  // ---------- Reset ----------
  $("#btn-reset").addEventListener("click", () => {
    fields.forEach((f) => (inputs[f].value = ""));
    $("#result-value").textContent = "—";
    updateSummary();
    $("#sum-periodic").textContent = "—";
    toast("Calculadora reiniciada");
  });

  // ---------- Example (matches the reference screenshot) ----------
  $("#btn-example").addEventListener("click", () => {
    inputs.pv.value = "250000";
    inputs.pmt.value = "-5080.228";
    inputs.fv.value = "";
    inputs.rate.value = "8.4";
    inputs.n.value = "60";
    $("#sel-freq").value = "12";
    document.querySelector('.pill-toggle[data-group="rate_type"][data-value="effective"]').click();
    document.querySelector('.pill-toggle[data-group="mode"][data-value="end"]').click();
    updateSummary();
    toast("Ejemplo cargado: préstamo a 60 meses");
  });

  // ---------- History (guest: localStorage / logueado: base de datos) ----------
  function loadHistoryLocal() {
    return JSON.parse(localStorage.getItem("fc_history") || "[]");
  }
  function saveHistoryListLocal(list) {
    localStorage.setItem("fc_history", JSON.stringify(list.slice(0, 30)));
  }
  function pushHistoryLocal(field, value, payload) {
    const list = loadHistoryLocal();
    list.unshift({
      id: Date.now(),
      field,
      value,
      payload,
      time: new Date().toLocaleString("es-AR"),
    });
    saveHistoryListLocal(list);
    renderHistory();
  }

  function renderHistoryItems(items, onDelete) {
    const wrap = $("#history-list");
    const empty = $("#history-empty");
    wrap.innerHTML = "";
    empty.style.display = items.length ? "none" : "block";
    items.forEach((item) => {
      const el = document.createElement("div");
      el.className = "list-item";
      el.innerHTML = `
        <button class="li-del" data-id="${item.id}">✕</button>
        <div class="li-top"><span>${item.field.toUpperCase()} = ${fmt(item.value, 2)}</span><span>${item.time}</span></div>
        <div class="li-detail">PV ${fmt(item.payload.pv,2)} · PMT ${fmt(item.payload.pmt,2)} · FV ${fmt(item.payload.fv,2)} · Rate ${item.payload.rate ?? "—"}% · N ${item.payload.n ?? "—"}</div>
      `;
      el.addEventListener("click", (e) => {
        if (e.target.closest(".li-del")) return;
        restorePayload(item.payload);
        toast("Cálculo restaurado del historial");
      });
      wrap.appendChild(el);
    });
    $$(".li-del", wrap).forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        onDelete(btn.dataset.id);
      });
    });
  }

  async function renderHistory() {
    if (!CURRENT_USER) {
      const list = loadHistoryLocal();
      renderHistoryItems(list, (id) => {
        saveHistoryListLocal(loadHistoryLocal().filter((i) => i.id !== parseInt(id, 10)));
        renderHistory();
      });
      return;
    }
    try {
      const res = await fetch("/api/history");
      const data = await res.json();
      if (!data.ok) return;
      const items = data.history.map((row) => ({
        id: row.id,
        field: row.solved_field,
        value: row[row.solved_field],
        payload: row,
        time: new Date(row.created_at).toLocaleString("es-AR"),
      }));
      renderHistoryItems(items, async (id) => {
        await fetch(`/api/history/${id}`, { method: "DELETE" });
        renderHistory();
      });
    } catch (e) {
      toast("No se pudo cargar el historial", true);
    }
  }

  function restorePayload(payload) {
    inputs.pv.value = payload.pv ?? "";
    inputs.pmt.value = payload.pmt ?? "";
    inputs.fv.value = payload.fv ?? "";
    inputs.rate.value = payload.rate ?? "";
    inputs.n.value = payload.n ?? "";
    $("#sel-freq").value = payload.freq ?? 12;
    document.querySelector(`.pill-toggle[data-group="rate_type"][data-value="${payload.rate_type}"]`)?.click();
    document.querySelector(`.pill-toggle[data-group="mode"][data-value="${payload.mode}"]`)?.click();
    updateSummary();
  }

  // ---------- Saved scenarios (guest: localStorage / logueado: base de datos) ----------
  function loadSavedLocal() {
    return JSON.parse(localStorage.getItem("fc_saved") || "[]");
  }

  function renderSavedItems(items, onDelete) {
    const wrap = $("#saved-list");
    const empty = $("#saved-empty");
    wrap.innerHTML = "";
    empty.style.display = items.length ? "none" : "block";
    items.forEach((item) => {
      const el = document.createElement("div");
      el.className = "list-item";
      el.innerHTML = `
        <button class="li-del" data-id="${item.id}">✕</button>
        <div class="li-top"><span>${item.name}</span><span>${item.time}</span></div>
        <div class="li-detail">PV ${fmt(item.payload.pv,2)} · PMT ${fmt(item.payload.pmt,2)} · FV ${fmt(item.payload.fv,2)} · Rate ${item.payload.rate ?? "—"}% · N ${item.payload.n ?? "—"}</div>
      `;
      el.addEventListener("click", (e) => {
        if (e.target.closest(".li-del")) return;
        restorePayload(item.payload);
        toast(`Escenario "${item.name}" cargado`);
      });
      wrap.appendChild(el);
    });
    $$(".li-del", wrap).forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        onDelete(btn.dataset.id);
      });
    });
  }

  async function renderSaved() {
    if (!CURRENT_USER) {
      const list = loadSavedLocal();
      renderSavedItems(list, (id) => {
        localStorage.setItem("fc_saved", JSON.stringify(loadSavedLocal().filter((i) => i.id !== parseInt(id, 10))));
        renderSaved();
      });
      return;
    }
    try {
      const res = await fetch("/api/saved");
      const data = await res.json();
      if (!data.ok) return;
      const items = data.saved.map((row) => ({
        id: row.id,
        name: row.name,
        payload: row,
        time: new Date(row.created_at).toLocaleString("es-AR"),
      }));
      renderSavedItems(items, async (id) => {
        await fetch(`/api/saved/${id}`, { method: "DELETE" });
        renderSaved();
      });
    } catch (e) {
      toast("No se pudo cargar los escenarios guardados", true);
    }
  }

  $("#btn-save").addEventListener("click", async () => {
    const name = prompt("Nombre para este escenario:", "Mi cálculo");
    if (!name) return;

    if (!CURRENT_USER) {
      const list = loadSavedLocal();
      list.unshift({
        id: Date.now(),
        name,
        payload: currentPayload(null),
        time: new Date().toLocaleString("es-AR"),
      });
      localStorage.setItem("fc_saved", JSON.stringify(list));
      renderSaved();
      toast("Escenario guardado en este navegador. Iniciá sesión para guardarlo permanentemente.");
      return;
    }

    try {
      const res = await fetch("/api/saved", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, ...currentPayload(null) }),
      });
      const data = await res.json();
      if (!data.ok) {
        toast(data.error || "No se pudo guardar", true);
        return;
      }
      renderSaved();
      toast("Escenario guardado");
    } catch (e) {
      toast("No se pudo conectar con el servidor", true);
    }
  });

  // ---------- Tabs ----------
  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".tab").forEach((t) => t.classList.remove("active"));
      $$(".tab-content").forEach((c) => c.classList.remove("active"));
      tab.classList.add("active");
      $(`#tab-${tab.dataset.tab}`).classList.add("active");
    });
  });

  // ---------- Modals ----------
  function openModal(overlay) { overlay.classList.add("open"); }
  function closeModal(overlay) { overlay.classList.remove("open"); }

  $$("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => btn.closest(".modal-overlay").classList.remove("open"));
  });
  [$("#modal-overlay"), $("#modal-overlay-help")].forEach((ov) => {
    ov.addEventListener("click", (e) => { if (e.target === ov) closeModal(ov); });
  });

  $("#btn-help").addEventListener("click", () => openModal($("#modal-overlay-help")));

  // ---------- Amortization ----------
  let lastAmortData = null;

  $("#btn-amort").addEventListener("click", async () => {
    const payload = currentPayload(null);
    if (payload.pv === null || payload.pmt === null || payload.rate === null || payload.n === null) {
      toast("Completá PV, PMT, RATE y N para generar la amortización", true);
      return;
    }
    try {
      const res = await fetch("/api/amortization", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!data.ok) {
        toast(data.error || "Error al generar amortización", true);
        return;
      }
      lastAmortData = data;
      renderAmortization(data);
      openModal($("#modal-overlay"));
    } catch (e) {
      toast("No se pudo conectar con el servidor", true);
    }
  });

  function renderAmortization(data) {
    $("#amort-summary").innerHTML = `
      <div class="as-item"><span>Total pagado</span><strong>${fmt(data.summary.total_paid, 2)}</strong></div>
      <div class="as-item"><span>Total interés</span><strong>${fmt(data.summary.total_interest, 2)}</strong></div>
      <div class="as-item"><span>Saldo final</span><strong>${fmt(data.summary.final_balance, 2)}</strong></div>
    `;
    const tbody = $("#amort-table tbody");
    tbody.innerHTML = data.schedule.map((row) => `
      <tr>
        <td>${row.period}</td>
        <td>${fmt(row.payment, 2)}</td>
        <td>${fmt(row.interest, 2)}</td>
        <td>${fmt(row.principal, 2)}</td>
        <td>${fmt(row.balance, 2)}</td>
      </tr>
    `).join("");
  }

  $("#btn-amort-csv").addEventListener("click", () => {
    if (!lastAmortData) return;
    const rows = [["Periodo", "Pago", "Interes", "Capital", "Saldo"]];
    lastAmortData.schedule.forEach((r) => rows.push([r.period, r.payment, r.interest, r.principal, r.balance]));
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "amortizacion.csv";
    a.click();
    URL.revokeObjectURL(url);
  });

  // ---------- Export (mailto, opens the user's own mail client) ----------
  $("#btn-export").addEventListener("click", () => {
    const subject = encodeURIComponent("Cálculo FinanceCalc");
    const body = encodeURIComponent(
      `PV: ${inputs.pv.value}\nPMT: ${inputs.pmt.value}\nFV: ${inputs.fv.value}\nRATE: ${inputs.rate.value}%\nN: ${inputs.n.value}\nCapitalización: ${$("#sel-freq").selectedOptions[0].textContent}\nTasa: ${state.rate_type}\nModo: ${state.mode}`
    );
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  });

  // ---------- Init ----------
  renderHistory();
  renderSaved();
  updateSummary();
})();
