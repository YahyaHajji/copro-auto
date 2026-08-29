"use strict";

const CASABLANCA_TIME_ZONE = "Africa/Casablanca";
const state = {
  csrf: "",
  licenses: [],
  selectedId: null,
  selectedTrigger: null,
  metricFilter: "",
  panel: "licenses",
  activity: {
    page: 1, limit: 25, cursor: "", direction: "next", result: null, loading: false,
  },
  confirmResolve: null,
};
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== "") node.textContent = text;
  return node;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 4000);
}

function announce(message) { $("#live-status").textContent = message; }

function showNetworkError(message) {
  $("#network-message").textContent = `${message} Les dernières données affichées sont conservées.`;
  $("#network-banner").hidden = false;
}

function clearNetworkError() { $("#network-banner").hidden = true; }

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
    throw new Error(detail.message || "Une erreur est survenue.");
  }
  return data;
}

function formatDateTime(value) {
  if (!value) return "Non transmise";
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium", timeStyle: "short", timeZone: CASABLANCA_TIME_ZONE,
  }).format(new Date(value));
}

function formatRelative(value) {
  if (!value) return "";
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const relative = new Intl.RelativeTimeFormat("fr-FR", { numeric: "auto" });
  const absolute = Math.abs(seconds);
  if (absolute < 60) return relative.format(seconds, "second");
  if (absolute < 3600) return relative.format(Math.round(seconds / 60), "minute");
  if (absolute < 86400) return relative.format(Math.round(seconds / 3600), "hour");
  return relative.format(Math.round(seconds / 86400), "day");
}

function timeElement(value, includeRelative = false) {
  if (!value) return element("span", "muted", "Non transmise");
  const wrapper = element("span", "stacked-cell");
  const exact = element("time", "", formatDateTime(value));
  exact.dateTime = value;
  wrapper.append(exact);
  if (includeRelative) wrapper.append(element("small", "", formatRelative(value)));
  return wrapper;
}

function statusLabel(status) {
  return { active: "Active", revoked: "Révoquée", expired: "Expirée", deactivated: "Libéré" }[status] || status;
}

function planLabel(plan) { return plan === "office" ? "Bureau" : "Individuel"; }

function showLogin() {
  $("#login-view").hidden = false;
  $("#dashboard-view").hidden = true;
  closeDetail();
  $("#password").focus();
}

function showDashboard() {
  $("#login-view").hidden = true;
  $("#dashboard-view").hidden = false;
}

async function boot() {
  try {
    const session = await api("/session");
    if (session.authenticated) {
      state.csrf = session.csrf;
      showDashboard();
      restoreActivityFilters();
      await loadDashboard();
    } else showLogin();
  } catch (_) { showLogin(); }
}

async function loadDashboard() {
  clearNetworkError();
  try {
    const [summary, licenses] = await Promise.all([api("/summary"), api("/licenses")]);
    state.licenses = licenses.items;
    renderSummary(summary);
    renderLicenses();
    if (state.panel === "activity") await loadActivity();
  } catch (error) { showNetworkError(error.message); }
}

function renderSummary(summary) {
  $("#metric-valid").textContent = summary.valid_licenses;
  $("#metric-total").textContent = `sur ${summary.licenses} licences`;
  $("#metric-expiring").textContent = summary.expiring_soon;
  $("#metric-devices").textContent = summary.active_devices;
  $("#metric-capacity").textContent = `sur ${summary.seat_capacity} places`;
  $("#metric-online").textContent = summary.online_devices;
  $("#metric-outdated").textContent = summary.outdated_devices;
  $("#metric-current-version").textContent = `version recommandée ${summary.current_app_version || "non configurée"}`;
  updatePageTime(summary.updated_at);
}

function updatePageTime(value = new Date().toISOString()) {
  const target = $("#page-updated");
  target.replaceChildren(document.createTextNode("Mis à jour le "), timeElement(value), document.createTextNode(" · heure de Casablanca"));
}

function activeLicenseFilters() {
  return {
    search: $("#license-search").value.trim().toLocaleLowerCase("fr"),
    status: $("#license-status-filter").value,
    type: $("#license-type-filter").value,
    expiry: $("#license-expiry-filter").value,
    activity: $("#license-activity-filter").value,
    sort: $("#license-sort").value,
  };
}

function resetLicenseFilters() {
  $("#license-search").value = "";
  $("#license-status-filter").value = "all";
  $("#license-type-filter").value = "all";
  $("#license-expiry-filter").value = "all";
  $("#license-activity-filter").value = "all";
  $("#license-sort").value = "created-desc";
  state.metricFilter = "";
  renderLicenses();
}

function renderLicenses() {
  const filters = activeLicenseFilters();
  let items = state.licenses.filter((item) => {
    const labels = (item.device_labels || []).join(" ").toLocaleLowerCase("fr");
    if (filters.search && !`${item.organization} ${labels}`.toLocaleLowerCase("fr").includes(filters.search)) return false;
    if (filters.status !== "all" && item.status !== filters.status) return false;
    if (filters.type === "trial" && !item.trial) return false;
    if (filters.type === "commercial" && item.trial) return false;
    if (filters.expiry === "30d" && !item.expiring_soon) return false;
    if (filters.expiry === "expired" && item.status !== "expired") return false;
    if (filters.activity === "online" && !item.online_devices) return false;
    if (filters.activity === "offline" && (!item.active_devices || item.online_devices)) return false;
    if (filters.activity === "outdated" && !item.outdated_devices) return false;
    if (state.metricFilter === "valid" && item.status !== "active") return false;
    if (state.metricFilter === "expiring" && !item.expiring_soon) return false;
    if (state.metricFilter === "occupied" && !item.active_devices) return false;
    if (state.metricFilter === "online" && !item.online_devices) return false;
    if (state.metricFilter === "outdated" && !item.outdated_devices) return false;
    return true;
  });
  const dateValue = (value) => value ? new Date(value).getTime() : 0;
  items.sort((a, b) => {
    if (filters.sort === "expiry-asc") return dateValue(a.commercial_expires_at) - dateValue(b.commercial_expires_at);
    if (filters.sort === "client-asc") return a.organization.localeCompare(b.organization, "fr", { sensitivity: "base" });
    if (filters.sort === "activity-desc") return dateValue(b.last_seen_at) - dateValue(a.last_seen_at);
    return dateValue(b.created_at) - dateValue(a.created_at);
  });
  const body = $("#licenses-body");
  body.replaceChildren();
  for (const item of items) body.append(licenseRow(item));
  $("#licenses-empty").hidden = items.length > 0;
  $("#license-result-count").textContent = `${items.length} résultat${items.length === 1 ? "" : "s"} sur ${state.licenses.length}`;
  const hasFilters = Boolean(filters.search || filters.status !== "all" || filters.type !== "all" || filters.expiry !== "all" || filters.activity !== "all" || state.metricFilter);
  $("#reset-license-filters").hidden = !hasFilters;
  $$("[data-metric-filter]").forEach((metric) => metric.classList.toggle("selected", metric.dataset.metricFilter === state.metricFilter));
}

function licenseRow(item) {
  const row = element("tr", `clickable${item.expiring_soon ? " attention" : ""}`);
  row.tabIndex = 0;
  row.setAttribute("aria-label", `Ouvrir la licence de ${item.organization}`);
  row.addEventListener("click", () => openDetail(item.id, row));
  row.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openDetail(item.id, row); }
  });
  const client = element("td", "client-cell");
  client.append(element("strong", "", item.organization), element("small", "", `${item.trial ? "Essai" : "Commerciale"} · ${planLabel(item.plan)}`));
  const licence = element("td", "", `•••• ${item.key_hint.slice(-4)}`);
  const status = element("td");
  status.append(element("span", `pill ${item.expiring_soon ? "warning" : item.status}`, item.expiring_soon ? "À renouveler" : statusLabel(item.status)));
  if (item.trial) status.append(" ", element("span", "pill trial", "Essai"));
  const seats = element("td", "stacked-cell");
  seats.append(element("strong", "", `${item.active_devices} / ${item.seat_limit}`));
  if (item.active_devices >= item.seat_limit) seats.append(element("small", "", "complet"));
  const activity = element("td");
  if (item.active_devices) {
    const line = element("div");
    line.append(element("span", `presence-dot${item.online_devices ? " online" : ""}`), document.createTextNode(item.online_devices ? `${item.online_devices} en ligne` : "Hors ligne"));
    activity.append(line, timeElement(item.last_seen_at));
  } else activity.append(element("span", "muted", "Aucun poste actif"));
  const expiry = element("td", "stacked-cell");
  expiry.append(timeElement(item.commercial_expires_at));
  if (item.expiring_soon) expiry.append(element("small", "warning-text", formatRelative(item.commercial_expires_at)));
  row.append(client, licence, status, seats, activity, expiry, element("td", "row-arrow", "›"));
  return row;
}

async function openDetail(id, trigger = null) {
  state.selectedId = id;
  state.selectedTrigger = trigger || state.selectedTrigger;
  try {
    const item = await api(`/licenses/${id}`);
    renderDetail(item);
    $("#drawer-backdrop").hidden = false;
    $("#detail-drawer").hidden = false;
    $("#close-detail").focus();
  } catch (error) { showToast(error.message); }
}

function renderDetail(item) {
  $("#detail-title").textContent = item.organization;
  $("#detail-subtitle").textContent = `Clé •••• ${item.key_hint.slice(-4)} · ${item.trial ? "Essai" : "Commerciale"}`;
  const content = $("#detail-content");
  content.replaceChildren();
  const summary = element("div", "detail-summary");
  summary.append(
    detailStat("Plan", planLabel(item.plan)),
    detailStat("Échéance", timeElement(item.commercial_expires_at), item.expiring_soon ? "warning" : ""),
    detailStat("Places", `${item.active_devices} utilisées sur ${item.seat_limit}`),
  );
  content.append(summary);
  const active = item.activations.filter((device) => device.status === "active");
  const released = item.activations.filter((device) => device.status !== "active");
  content.append(sectionHeading("Places actives", `${active.length} appareil${active.length === 1 ? "" : "s"}`));
  if (!active.length) content.append(element("p", "muted", "Aucun appareil n'utilise actuellement cette licence."));
  active.forEach((device) => content.append(deviceCard(device, item, true)));
  if (released.length) {
    const toggle = element("button", "released-toggle");
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", "false");
    toggle.append(element("span", "", "Historique des postes libérés"), element("span", "muted", `${released.length} appareil${released.length === 1 ? "" : "s"} ›`));
    const history = element("div", "released-list");
    history.hidden = true;
    released.forEach((device) => history.append(deviceCard(device, item, false)));
    toggle.addEventListener("click", () => {
      history.hidden = !history.hidden;
      toggle.setAttribute("aria-expanded", String(!history.hidden));
    });
    content.append(toggle, history);
  }
  content.append(sectionHeading("Actions sur la licence"));
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
    revoke.addEventListener("click", () => revokeSelected(item));
    actions.append(revoke);
  }
  content.append(actions);
}

function detailStat(label, value, variant = "") {
  const card = element("div", `detail-stat ${variant}`.trim());
  const strong = element("strong");
  strong.append(typeof value === "string" ? document.createTextNode(value) : value);
  card.append(element("small", "", label), strong);
  return card;
}

function sectionHeading(title, meta = "") {
  const heading = element("h3", "section-title");
  heading.append(element("span", "", title));
  if (meta) heading.append(element("span", "muted", meta));
  return heading;
}

function platformLabel(device) {
  const name = [device.os_name, device.os_edition].filter(Boolean).join(" ");
  const version = device.os_version ? ` ${device.os_version}` : "";
  const build = device.os_build ? ` · build ${device.os_build}` : "";
  const architecture = device.architecture ? ` · ${device.architecture}` : "";
  return name ? `${name}${version}${build}${architecture}` : "Informations système non transmises";
}

function deviceCard(device, license, canRelease) {
  const card = element("article", "device-card");
  const head = element("div", "device-card-head");
  const title = element("div", "device-title");
  title.append(element("span", `presence-dot${device.connection_status === "online" ? " online" : ""}`), document.createTextNode(device.device_label));
  const badges = element("div", "device-badges");
  badges.append(element("span", `pill ${device.status}`, `● ${statusLabel(device.status)}`), element("span", `pill ${device.connection_status}`, `● ${device.connection_status === "online" ? "En ligne" : "Hors ligne"}`));
  head.append(title, badges);
  card.append(head, element("p", "device-platform", platformLabel(device)));
  const version = element("p", "device-version", `Copro Auto ${device.app_version || "Non transmise"}`);
  if (device.outdated) version.append(" ", element("span", "pill warning", `Mise à jour ${device.current_app_version}`));
  card.append(version);
  const details = element("div", "device-details");
  details.append(deviceDatum("Première activation", timeElement(device.created_at)), deviceDatum("Dernier contact", timeElementWithRelative(device.last_seen_at)), deviceDatum("Identifiant support", device.device_hint));
  if (device.deactivated_at) details.append(deviceDatum("Libéré", timeElement(device.deactivated_at)));
  card.append(details);
  if (canRelease) {
    const actions = element("div", "device-actions");
    const release = element("button", "button danger", "Libérer ce poste");
    release.addEventListener("click", () => releaseDevice(device, license));
    actions.append(release);
    card.append(actions);
  }
  return card;
}

function deviceDatum(label, value) {
  const datum = element("div");
  const valueNode = typeof value === "string" ? document.createTextNode(value || "Non transmise") : (value || element("span", "muted", "Non transmise"));
  const strong = element("strong");
  strong.append(valueNode);
  datum.append(element("small", "", label), strong);
  return datum;
}

function timeElementWithRelative(value) {
  const wrapper = timeElement(value);
  if (value) wrapper.append(document.createTextNode(` · ${formatRelative(value)}`));
  return wrapper;
}

function closeDetail() {
  if ($("#detail-drawer")) $("#detail-drawer").hidden = true;
  if ($("#drawer-backdrop")) $("#drawer-backdrop").hidden = true;
  const trigger = state.selectedTrigger;
  state.selectedId = null;
  state.selectedTrigger = null;
  if (trigger && document.contains(trigger)) trigger.focus();
}

async function refreshSelected() {
  await loadDashboard();
  if (state.selectedId) await openDetail(state.selectedId);
}

function confirmAction(title, message, actionLabel) {
  $("#confirm-title").textContent = title;
  $("#confirm-message").textContent = message;
  $("#confirm-submit").textContent = actionLabel;
  $("#confirm-dialog").showModal();
  $("#confirm-cancel").focus();
  return new Promise((resolve) => { state.confirmResolve = resolve; });
}

function finishConfirmation(result) {
  $("#confirm-dialog").close();
  const resolve = state.confirmResolve;
  state.confirmResolve = null;
  if (resolve) resolve(result);
}

async function releaseDevice(device, license) {
  const approved = await confirmAction("Libérer ce poste ?", `${device.device_label} sera libéré de la licence de ${license.organization}. L'utilisateur devra réactiver la licence sur cet ordinateur.`, "Libérer le poste");
  if (!approved) return;
  try { await api(`/activations/${device.id}/release`, { method: "POST" }); await refreshSelected(); showToast("Poste libéré."); }
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

async function revokeSelected(item) {
  const approved = await confirmAction("Révoquer cette licence ?", `La licence de ${item.organization} sera révoquée. Ses appareils ne pourront plus renouveler leur accès.`, "Révoquer la licence");
  if (!approved) return;
  try { await api(`/licenses/${state.selectedId}/revoke`, { method: "POST" }); await refreshSelected(); showToast("Licence révoquée."); }
  catch (error) { showToast(error.message); }
}

async function reactivateSelected() {
  try { await api(`/licenses/${state.selectedId}/reactivate`, { method: "POST" }); await refreshSelected(); showToast("Licence réactivée."); }
  catch (error) { showToast(error.message); }
}

function activityQuery({ withCursor = true } = {}) {
  const params = new URLSearchParams({
    limit: String(state.activity.limit),
    search: $("#activity-search").value.trim(),
    period: $("#activity-period").value,
    category: $("#activity-category").value,
    origin: $("#activity-origin").value,
    include_refresh: String($("#activity-refresh-filter").checked),
  });
  if ($("#activity-period").value === "custom") {
    if ($("#activity-start").value) params.set("start_date", $("#activity-start").value);
    if ($("#activity-end").value) params.set("end_date", $("#activity-end").value);
  }
  if (withCursor && state.activity.cursor) {
    params.set("cursor", state.activity.cursor);
    params.set("direction", state.activity.direction);
  }
  return params;
}

function syncActivityUrl() {
  const params = activityQuery({ withCursor: false });
  params.set("panel", "activity");
  history.replaceState(null, "", `${location.pathname}?${params.toString()}`);
}

function restoreActivityFilters() {
  const params = new URLSearchParams(location.search);
  if (params.get("panel") !== "activity") return;
  const mapping = {
    search: "#activity-search", period: "#activity-period", category: "#activity-category", origin: "#activity-origin",
  };
  for (const [key, selector] of Object.entries(mapping)) if (params.has(key)) $(selector).value = params.get(key);
  if (params.has("include_refresh")) $("#activity-refresh-filter").checked = params.get("include_refresh") === "true";
  if (params.has("limit") && [25, 50, 100].includes(Number(params.get("limit")))) {
    state.activity.limit = Number(params.get("limit"));
    $("#activity-page-size").value = String(state.activity.limit);
  }
  if (params.has("start_date")) $("#activity-start").value = params.get("start_date");
  if (params.has("end_date")) $("#activity-end").value = params.get("end_date");
  $("#custom-period").hidden = $("#activity-period").value !== "custom";
  switchPanel("activity", false);
}

function resetActivityPaging() {
  state.activity.page = 1;
  state.activity.cursor = "";
  state.activity.direction = "next";
}

function resetActivityFilters() {
  $("#activity-search").value = "";
  $("#activity-period").value = "30d";
  $("#activity-category").value = "all";
  $("#activity-origin").value = "all";
  $("#activity-refresh-filter").checked = false;
  $("#activity-start").value = "";
  $("#activity-end").value = "";
  $("#custom-period").hidden = true;
  resetActivityPaging();
  loadActivity();
}

async function loadActivity() {
  if (state.activity.loading) return;
  state.activity.loading = true;
  $("#activity-body").replaceChildren(activityLoadingRow());
  try {
    const result = await api(`/audit?${activityQuery().toString()}`);
    state.activity.result = result;
    renderActivity(result);
    syncActivityUrl();
    clearNetworkError();
    updatePageTime();
  } catch (error) {
    showNetworkError(error.message);
    $("#activity-body").replaceChildren();
  } finally { state.activity.loading = false; }
}

function activityLoadingRow() {
  const row = element("tr");
  const cell = element("td", "muted", "Chargement de l'activité…");
  cell.colSpan = 6;
  row.append(cell);
  return row;
}

function groupRefreshEvents(items) {
  const grouped = [];
  for (const item of items) {
    const previous = grouped[grouped.length - 1];
    const close = previous && previous.event_type === "refresh" && item.event_type === "refresh" && previous.device_label === item.device_label && Math.abs(new Date(previous.created_at) - new Date(item.created_at)) <= 15 * 60 * 1000;
    if (close) {
      previous.groupItems = previous.groupItems || [previous];
      previous.groupItems.push(item);
    } else grouped.push({ ...item });
  }
  return grouped;
}

function renderActivity(result) {
  const body = $("#activity-body");
  body.replaceChildren();
  const items = groupRefreshEvents(result.items);
  for (const item of items) body.append(activityRow(item));
  $("#activity-empty").hidden = items.length > 0;
  $("#activity-events").textContent = result.summary.events;
  $("#activity-activations").textContent = result.summary.activations;
  $("#activity-admin").textContent = result.summary.admin_actions;
  $("#activity-released").textContent = result.summary.released_devices;
  const start = result.total ? (state.activity.page - 1) * state.activity.limit + 1 : 0;
  const end = Math.min(start + result.items.length - 1, result.total);
  $("#activity-range").textContent = result.total ? `${start}–${end} sur ${result.total} événements` : "0 événement";
  $("#activity-page").textContent = `Page ${state.activity.page}`;
  $("#activity-previous").disabled = !result.previous_cursor;
  $("#activity-next").disabled = !result.next_cursor;
  const hasFilters = $("#activity-search").value || $("#activity-period").value !== "30d" || $("#activity-category").value !== "all" || $("#activity-origin").value !== "all" || $("#activity-refresh-filter").checked;
  $("#reset-activity-filters").hidden = !hasFilters;
  announce(`Événements ${start} à ${end} chargés`);
}

function activityRow(item) {
  const row = element("tr", item.license_id ? "clickable" : "");
  if (item.license_id) {
    row.tabIndex = 0;
    row.setAttribute("aria-label", `Ouvrir ${item.organization || "la licence associée"}`);
    row.addEventListener("click", () => openDetail(item.license_id, row));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openDetail(item.license_id, row); }
    });
  }
  const when = element("td");
  when.append(timeElement(item.created_at, true));
  const eventCell = element("td", "activity-event");
  const main = element("div", "event-main");
  const meta = eventPresentation(item);
  main.append(element("span", `event-icon ${meta.variant}`, meta.icon));
  const copy = element("div", "stacked-cell");
  copy.append(element("strong", "", meta.title), element("small", "", meta.description));
  if (item.groupItems?.length > 1) {
    const toggle = element("button", "refresh-group", `${item.groupItems.length} vérifications regroupées · afficher`);
    const list = element("div", "muted");
    list.hidden = true;
    list.textContent = item.groupItems.map((entry) => formatDateTime(entry.created_at)).join(" · ");
    toggle.addEventListener("click", (event) => { event.stopPropagation(); list.hidden = !list.hidden; toggle.textContent = `${item.groupItems.length} vérifications regroupées · ${list.hidden ? "afficher" : "masquer"}`; });
    copy.append(toggle, list);
  }
  main.append(copy);
  eventCell.append(main);
  row.append(when, eventCell, element("td", item.organization ? "" : "muted", item.organization || "—"), element("td", item.device_label ? "" : "muted", item.device_label || "—"));
  const origin = element("td");
  origin.append(element("span", `pill ${item.origin}`, item.origin === "application" ? "Application" : "Administrateur"));
  row.append(origin, element("td", "row-arrow", item.license_id ? "›" : ""));
  return row;
}

function eventPresentation(item) {
  const days = item.details?.days;
  return {
    license_created: { title: "Licence créée", description: "Nouvel accès créé", icon: "+", variant: "" },
    activate: { title: "Appareil activé", description: "Nouvelle place de licence occupée", icon: "✓", variant: "" },
    refresh: { title: "Licence vérifiée", description: "Contact automatique avec le serveur", icon: "↻", variant: "" },
    deactivate: { title: "Appareil désactivé", description: "Place libérée depuis l'application", icon: "×", variant: "danger" },
    admin_license_renewed: { title: `Licence prolongée${days ? ` de ${days} jours` : ""}`, description: "Échéance commerciale mise à jour", icon: "+", variant: "warning" },
    admin_license_revoked: { title: "Licence révoquée", description: "Renouvellements en ligne interrompus", icon: "!", variant: "danger" },
    admin_license_reactivated: { title: "Licence réactivée", description: "Renouvellements en ligne rétablis", icon: "✓", variant: "" },
    admin_activation_released: { title: "Poste libéré", description: "La place peut être utilisée sur un autre ordinateur", icon: "×", variant: "danger" },
    admin_audit_exported: { title: "Journal exporté", description: "Export CSV de l'activité filtrée", icon: "⇩", variant: "" },
  }[item.event_type] || { title: item.event_type, description: "Événement administratif", icon: "•", variant: "" };
}

async function exportActivity() {
  const button = $("#export-audit-button");
  button.disabled = true;
  const params = activityQuery({ withCursor: false });
  params.delete("limit");
  try {
    const response = await fetch(`/admin/api/audit/export?${params.toString()}`, {
      method: "POST", credentials: "same-origin", headers: { "X-CSRF-Token": state.csrf },
    });
    if (!response.ok) {
      let data = {};
      try { data = await response.json(); } catch (_) { data = {}; }
      throw new Error(data.detail?.message || "Export impossible.");
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const filename = disposition.match(/filename="([^"]+)"/)?.[1] || "copro-auto-activite.csv";
    const url = URL.createObjectURL(blob);
    const link = element("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showToast("Journal CSV exporté.");
    await loadActivity();
  } catch (error) { showToast(error.message); }
  finally { button.disabled = false; }
}

function switchPanel(panel, load = true) {
  state.panel = panel;
  const activity = panel === "activity";
  $("#licenses-panel").hidden = activity;
  $("#activity-panel").hidden = !activity;
  $("#new-license-button").hidden = activity;
  $("#export-audit-button").hidden = !activity;
  $("#page-title").textContent = activity ? "Activité" : "Licences";
  $("#page-eyebrow").textContent = activity ? "JOURNAL DE SÉCURITÉ ET DE GESTION" : "GESTION CENTRALISÉE";
  $$(".nav-item").forEach((item) => {
    const selected = item.dataset.panel === panel;
    item.classList.toggle("active", selected);
    if (selected) item.setAttribute("aria-current", "page"); else item.removeAttribute("aria-current");
  });
  if (activity && load) loadActivity();
  if (!activity) history.replaceState(null, "", location.pathname);
}

function scheduleLicenseRender() {
  clearTimeout(scheduleLicenseRender.timer);
  scheduleLicenseRender.timer = setTimeout(renderLicenses, 120);
}

function scheduleActivityReload() {
  clearTimeout(scheduleActivityReload.timer);
  scheduleActivityReload.timer = setTimeout(() => { resetActivityPaging(); loadActivity(); }, 250);
}

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = $("#login-error");
  const button = event.currentTarget.querySelector("button[type=submit]");
  error.hidden = true; button.disabled = true;
  try {
    const result = await api("/login", { method: "POST", body: JSON.stringify({ password: $("#password").value }) });
    state.csrf = result.csrf; $("#password").value = ""; showDashboard(); await loadDashboard();
  } catch (exception) { error.textContent = exception.message; error.hidden = false; }
  finally { button.disabled = false; }
});
$("#logout-button").addEventListener("click", async () => { try { await api("/logout", { method: "POST" }); } finally { showLogin(); } });
$("#refresh-button").addEventListener("click", () => state.panel === "activity" ? loadActivity() : loadDashboard());
$("#retry-button").addEventListener("click", () => state.panel === "activity" ? loadActivity() : loadDashboard());
$("#new-license-button").addEventListener("click", () => $("#create-dialog").showModal());
$("#cancel-create").addEventListener("click", () => $("#create-dialog").close());
$("#close-create").addEventListener("click", () => $("#create-dialog").close());
$("#create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget; const data = new FormData(form); const button = $("#create-submit"); const error = $("#create-error");
  error.hidden = true; button.disabled = true;
  try {
    const result = await api("/licenses", { method: "POST", body: JSON.stringify({ organization: data.get("organization"), plan: data.get("plan"), seats: Number(data.get("seats")), days: Number(data.get("days")), trial: data.get("trial") === "on" }) });
    $("#create-dialog").close(); $("#created-key").textContent = result.license_key; $("#key-dialog").showModal(); form.reset(); form.elements.seats.value = 2; form.elements.days.value = 30; form.elements.trial.checked = true; await loadDashboard();
  } catch (exception) { error.textContent = exception.message; error.hidden = false; }
  finally { button.disabled = false; }
});
$("#copy-key").addEventListener("click", async () => { await navigator.clipboard.writeText($("#created-key").textContent); showToast("Clé copiée."); });
$("#close-key").addEventListener("click", () => { $("#created-key").textContent = ""; $("#key-dialog").close(); });
$("#close-detail").addEventListener("click", closeDetail);
$("#drawer-backdrop").addEventListener("click", closeDetail);
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !$("#detail-drawer").hidden) closeDetail(); });
$("#confirm-cancel").addEventListener("click", () => finishConfirmation(false));
$("#confirm-submit").addEventListener("click", () => finishConfirmation(true));
$("#confirm-dialog").addEventListener("cancel", (event) => { event.preventDefault(); finishConfirmation(false); });
$$("[data-metric-filter]").forEach((metric) => metric.addEventListener("click", () => { state.metricFilter = state.metricFilter === metric.dataset.metricFilter ? "" : metric.dataset.metricFilter; renderLicenses(); }));
$("#license-search").addEventListener("input", scheduleLicenseRender);
["#license-status-filter", "#license-type-filter", "#license-expiry-filter", "#license-activity-filter", "#license-sort"].forEach((selector) => $(selector).addEventListener("change", renderLicenses));
$("#reset-license-filters").addEventListener("click", resetLicenseFilters);
$("#empty-reset-button").addEventListener("click", resetLicenseFilters);
$$(".nav-item").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.panel)));
$("#activity-search").addEventListener("input", scheduleActivityReload);
["#activity-category", "#activity-origin", "#activity-refresh-filter"].forEach((selector) => $(selector).addEventListener("change", () => { resetActivityPaging(); loadActivity(); }));
$("#activity-period").addEventListener("change", () => { const custom = $("#activity-period").value === "custom"; $("#custom-period").hidden = !custom; if (!custom) { resetActivityPaging(); loadActivity(); } });
$("#apply-custom-period").addEventListener("click", () => { if (!$("#activity-start").value || !$("#activity-end").value) return showToast("Choisissez les deux dates."); resetActivityPaging(); loadActivity(); });
$("#reset-activity-filters").addEventListener("click", resetActivityFilters);
$("#activity-empty-reset").addEventListener("click", resetActivityFilters);
$("#activity-page-size").addEventListener("change", () => { state.activity.limit = Number($("#activity-page-size").value); resetActivityPaging(); loadActivity(); });
$("#activity-next").addEventListener("click", () => { if (!state.activity.result?.next_cursor) return; state.activity.cursor = state.activity.result.next_cursor; state.activity.direction = "next"; state.activity.page += 1; loadActivity().then(() => $("#activity-results-title").focus()); });
$("#activity-previous").addEventListener("click", () => { if (!state.activity.result?.previous_cursor) return; state.activity.cursor = state.activity.result.previous_cursor; state.activity.direction = "previous"; state.activity.page = Math.max(1, state.activity.page - 1); loadActivity().then(() => $("#activity-results-title").focus()); });
$("#export-audit-button").addEventListener("click", exportActivity);

boot();
