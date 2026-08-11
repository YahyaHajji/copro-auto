"use strict";

const state = { csrf: "", licenses: [], selectedId: null };
const $ = (selector) => document.querySelector(selector);

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 3500);
}

async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  if (options.method && options.method !== "GET" && state.csrf) headers["X-CSRF-Token"] = state.csrf;
  const response = await fetch(`/admin/api${path}`, { credentials: "same-origin", ...options, headers });
  let data = {};
  try { data = await response.json(); } catch (_) { data = {}; }
  if (!response.ok) {
    if (response.status === 401 && path !== "/login") showLogin();
    const detail = data.detail || {};
    throw new Error(detail.message || "Une erreur inattendue est survenue.");
  }
  return data;
}

function showLogin() {
  state.csrf = "";
  $("#dashboard-view").hidden = true;
  $("#login-view").hidden = false;
  $("#password").focus();
}

function showDashboard() {
  $("#login-view").hidden = true;
  $("#dashboard-view").hidden = false;
}

async function boot() {
  try {
    const session = await api("/session");
    if (!session.authenticated) return showLogin();
    state.csrf = session.csrf;
    showDashboard();
    await loadDashboard();
  } catch (error) {
    showLogin();
    $("#login-error").textContent = error.message;
    $("#login-error").hidden = false;
  }
}

async function loadDashboard() {
  const [summary, licenses] = await Promise.all([api("/summary"), api("/licenses")]);
  $("#metric-total").textContent = summary.licenses;
  $("#metric-valid").textContent = summary.valid_licenses;
  $("#metric-trials").textContent = summary.trials;
  $("#metric-devices").textContent = summary.active_devices;
  state.licenses = licenses.items;
  renderLicenses();
}

function formatDate(value) {
  return value ? new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value)) : "—";
}

function statusLabel(status) {
  return { active: "Active", revoked: "Révoquée", expired: "Expirée", deactivated: "Libéré" }[status] || status;
}

function planLabel(plan) { return plan === "office" ? "Bureau" : "Individuel"; }

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderLicenses() {
  const body = $("#licenses-body");
  const query = $("#license-search").value.trim().toLocaleLowerCase("fr");
  const items = state.licenses.filter((item) => item.organization.toLocaleLowerCase("fr").includes(query));
  body.replaceChildren();
  for (const item of items) {
    const row = document.createElement("tr");
    row.tabIndex = 0;
    row.setAttribute("aria-label", `Ouvrir la licence de ${item.organization}`);
    row.addEventListener("click", () => openDetail(item.id));
    row.addEventListener("keydown", (event) => { if (event.key === "Enter") openDetail(item.id); });

    const client = element("td", "client-cell");
    client.append(element("strong", "", item.organization), element("small", "", item.trial ? "Essai" : "Licence régulière"));
    row.append(client);
    row.append(element("td", "", `•••• ${item.key_hint}`));
    row.append(element("td", "", planLabel(item.plan)));
    const status = element("td");
    status.append(element("span", `pill ${item.status}`, statusLabel(item.status)));
    row.append(status);
    row.append(element("td", "", `${item.active_devices} / ${item.seat_limit}`));
    row.append(element("td", "", formatDate(item.commercial_expires_at)));
    row.append(element("td", "row-arrow", "›"));
    body.append(row);
  }
  $("#licenses-empty").hidden = items.length !== 0;
}

async function openDetail(id) {
  try {
    const item = await api(`/licenses/${id}`);
    state.selectedId = id;
    $("#detail-title").textContent = item.organization;
    const content = $("#detail-content");
    content.replaceChildren();

    const summary = element("div", "detail-summary");
    for (const [label, value] of [
      ["Plan", planLabel(item.plan)],
      ["Statut", statusLabel(item.status)],
      ["Échéance", formatDate(item.commercial_expires_at)],
    ]) {
      const stat = element("div", "detail-stat");
      stat.append(element("small", "", label), element("strong", "", value));
      summary.append(stat);
    }
    content.append(summary, element("h3", "section-title", `Appareils (${item.active_devices}/${item.seat_limit})`));
    if (!item.activations.length) content.append(element("p", "muted", "Aucun appareil n'a encore activé cette licence."));
    for (const device of item.activations) {
      const row = element("div", "device-row");
      const info = element("div");
      info.append(element("strong", "", device.device_label));
      info.append(element("small", "", `${device.app_version || "Version inconnue"} · Dernier contact ${formatDate(device.last_seen_at)}`));
      row.append(info);
      if (device.status === "active") {
        const release = element("button", "button secondary", "Libérer");
        release.addEventListener("click", () => releaseDevice(device.id));
        row.append(release);
      } else row.append(element("span", "pill expired", "Libéré"));
      content.append(row);
    }
    const actions = element("div", "detail-actions");
    const renew = element("button", "button secondary", "Prolonger");
    renew.addEventListener("click", renewSelected);
    actions.append(renew);
    if (item.status === "revoked") {
      const reactivate = element("button", "button primary", "Réactiver");
      reactivate.addEventListener("click", reactivateSelected);
      actions.append(reactivate);
    } else {
      const revoke = element("button", "button danger", "Révoquer");
      revoke.addEventListener("click", revokeSelected);
      actions.append(revoke);
    }
    content.append(actions);
    $("#detail-dialog").showModal();
  } catch (error) { showToast(error.message); }
}

async function refreshSelected() {
  await loadDashboard();
  if (state.selectedId) {
    $("#detail-dialog").close();
    await openDetail(state.selectedId);
  }
}

async function releaseDevice(id) {
  if (!confirm("Libérer ce poste ? L'utilisateur devra réactiver la licence sur cet ordinateur.")) return;
  try { await api(`/activations/${id}/release`, { method: "POST" }); await refreshSelected(); showToast("Poste libéré."); }
  catch (error) { showToast(error.message); }
}

async function renewSelected() {
  const input = prompt("Nombre de jours à ajouter :", "30");
  if (input === null) return;
  const days = Number(input);
  if (!Number.isInteger(days) || days < 1 || days > 3650) return showToast("Saisissez un nombre de jours valide.");
  try { await api(`/licenses/${state.selectedId}/renew`, { method: "POST", body: JSON.stringify({ days }) }); await refreshSelected(); showToast("Licence prolongée."); }
  catch (error) { showToast(error.message); }
}

async function revokeSelected() {
  if (!confirm("Révoquer cette licence ? Les appareils ne pourront plus renouveler leur accès.")) return;
  try { await api(`/licenses/${state.selectedId}/revoke`, { method: "POST" }); await refreshSelected(); showToast("Licence révoquée."); }
  catch (error) { showToast(error.message); }
}

async function reactivateSelected() {
  try { await api(`/licenses/${state.selectedId}/reactivate`, { method: "POST" }); await refreshSelected(); showToast("Licence réactivée."); }
  catch (error) { showToast(error.message); }
}

async function loadAudit() {
  try {
    const result = await api("/audit");
    const list = $("#audit-list");
    list.replaceChildren();
    const labels = {
      license_created: "Licence créée", activate: "Appareil activé", refresh: "Licence vérifiée",
      deactivate: "Appareil désactivé", admin_license_renewed: "Licence prolongée",
      admin_license_revoked: "Licence révoquée", admin_license_reactivated: "Licence réactivée",
      admin_activation_released: "Poste libéré",
    };
    for (const event of result.items) {
      const row = element("div", "timeline-item");
      row.append(element("span", "timeline-dot"), element("span", "", labels[event.event_type] || event.event_type));
      const time = element("time", "", formatDate(event.created_at));
      time.dateTime = event.created_at;
      row.append(time);
      list.append(row);
    }
    if (!result.items.length) list.append(element("p", "muted", "Aucune activité enregistrée."));
  } catch (error) { showToast(error.message); }
}

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = $("#login-error");
  const button = event.currentTarget.querySelector("button[type=submit]");
  error.hidden = true; button.disabled = true;
  try {
    const result = await api("/login", { method: "POST", body: JSON.stringify({ password: $("#password").value }) });
    state.csrf = result.csrf;
    $("#password").value = "";
    showDashboard();
    await loadDashboard();
  } catch (exception) { error.textContent = exception.message; error.hidden = false; }
  finally { button.disabled = false; }
});

$("#logout-button").addEventListener("click", async () => {
  try { await api("/logout", { method: "POST" }); } finally { showLogin(); }
});
$("#new-license-button").addEventListener("click", () => $("#create-dialog").showModal());
$("#cancel-create").addEventListener("click", () => $("#create-dialog").close());
$("#close-create").addEventListener("click", () => $("#create-dialog").close());
$("#create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const button = $("#create-submit");
  const error = $("#create-error");
  error.hidden = true; button.disabled = true;
  try {
    const result = await api("/licenses", { method: "POST", body: JSON.stringify({
      organization: data.get("organization"), plan: data.get("plan"), seats: Number(data.get("seats")),
      days: Number(data.get("days")), trial: data.get("trial") === "on",
    }) });
    $("#create-dialog").close();
    $("#created-key").textContent = result.license_key;
    $("#key-dialog").showModal();
    form.reset();
    form.elements.seats.value = 2; form.elements.days.value = 30; form.elements.trial.checked = true;
    await loadDashboard();
  } catch (exception) { error.textContent = exception.message; error.hidden = false; }
  finally { button.disabled = false; }
});
$("#copy-key").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("#created-key").textContent);
  showToast("Clé copiée.");
});
$("#close-key").addEventListener("click", () => { $("#created-key").textContent = ""; $("#key-dialog").close(); });
$("#close-detail").addEventListener("click", () => $("#detail-dialog").close());
$("#license-search").addEventListener("input", renderLicenses);
document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", async () => {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item === button));
  const activity = button.dataset.panel === "activity";
  $("#licenses-panel").hidden = activity; $("#activity-panel").hidden = !activity;
  $("#new-license-button").hidden = activity; $("#page-title").textContent = activity ? "Activité" : "Licences";
  if (activity) await loadAudit();
}));

boot();
