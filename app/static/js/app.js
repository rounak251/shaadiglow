// ShaadiGlow single-page app (vanilla JS modules, no build step).
import { t } from "./i18n.js";
import { productArt } from "./art.js";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const KEY = "sg.v1";
const ROLES = ["bride", "groom", "guest"];
const EVENTS = ["haldi", "mehendi", "sangeet", "wedding", "reception"];

let CFG = null;           // /api/config
let CATALOG = {};         // id -> product
let busy = false;

// ------------------------------------------------------------------ state
const fresh = () => ({
  lang: "en", role: "bride", persona: null, image_ref: null, images: {}, camera_kit: false,
  profile_id: (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2)),
  wedding_date: null, city: "mumbai", budget: "balanced", events: [...EVENTS], sensitive: false, pregnant: false,
  scanRes: null, plan: null, sim: null, shade: null, shadeSuggested: null, look: null, tryon: {}, cart: {},
  done: {}, consent: false, lookTab: "makeup", routineTab: "am",
});
let state = load();
function load() {
  try { return { ...fresh(), ...JSON.parse(localStorage.getItem(KEY) || "{}") }; } catch { return fresh(); }
}
function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* private mode */ } }
const T = (k, v) => t(state.lang, k, v);
const L = (o) => (o ? (typeof o === "string" ? o : o[state.lang] || o.en || "") : "");

// ------------------------------------------------------------------ api
async function api(path, opts = {}) {
  const init = { method: opts.method || (opts.body ? "POST" : "GET"), headers: {} };
  if (opts.body instanceof FormData) init.body = opts.body;
  else if (opts.body) { init.body = JSON.stringify(opts.body); init.headers["Content-Type"] = "application/json"; }
  const r = await fetch(path, init);
  if (opts.raw) return r;
  let data = null;
  try { data = await r.json(); } catch { data = null; }
  if (!r.ok) {
    const msg = (data && (data.message || (typeof data.detail === "string" ? data.detail : null))) || T("err_generic");
    const e = new Error(msg); e.status = r.status; e.data = data; throw e;
  }
  return data;
}

function toast(msg, err = false) {
  $$(".toast").forEach((n) => n.remove());
  const n = document.createElement("div");
  n.className = "toast" + (err ? " err" : "");
  n.textContent = msg;
  document.body.appendChild(n);
  setTimeout(() => n.remove(), 2600);
}

// ------------------------------------------------------------------ icons
const I = {
  logo: `<svg width="30" height="30" viewBox="0 0 40 40" aria-hidden="true"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#F2A007"/><stop offset="1" stop-color="#A3193F"/></linearGradient></defs>
    <circle cx="20" cy="20" r="18" fill="url(#lg)"/><g fill="#fff" opacity=".95">${[0, 45, 90, 135, 180, 225, 270, 315]
      .map((a) => `<ellipse cx="20" cy="9.5" rx="3.4" ry="6" transform="rotate(${a} 20 20)"/>`).join("")}</g>
    <circle cx="20" cy="20" r="5" fill="#A3193F"/></svg>`,
  info: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#7A1230" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></svg>`,
  report: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="10" r="6"/><path d="M8 20c1.5-1.5 6.5-1.5 8 0"/><path d="M10 9h.01M14 9h.01"/></svg>`,
  plan: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16M9 14l2 2 4-4"/></svg>`,
  looks: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 21V9l4-6 1 5h4l1 13"/><path d="M7 15h10"/></svg>`,
  shop: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 8h14l-1.2 11.2a2 2 0 0 1-2 1.8H8.2a2 2 0 0 1-2-1.8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>`,
  progress: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19h16M6 15l4-4 3 3 5-6"/><path d="M15 8h3v3"/></svg>`,
  camera: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7A1230" stroke-width="1.8"><rect x="3" y="7" width="18" height="13" rx="3"/><path d="M8 7l2-3h4l2 3"/><circle cx="12" cy="13.5" r="3.5"/></svg>`,
  upload: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7A1230" stroke-width="1.8"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/></svg>`,
  check: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 7"/></svg>`,
  bride: `<svg width="28" height="28" viewBox="0 0 32 32" fill="none" stroke="#A3193F" stroke-width="1.7"><circle cx="16" cy="13" r="6"/><path d="M6 28c1.5-6 18.5-6 20 0"/><path d="M9 11c0-6 14-6 14 0"/><circle cx="16" cy="5" r="1.6" fill="#F2A007" stroke="none"/></svg>`,
  groom: `<svg width="28" height="28" viewBox="0 0 32 32" fill="none" stroke="#A3193F" stroke-width="1.7"><circle cx="16" cy="14" r="6"/><path d="M6 28c1.5-6 18.5-6 20 0"/><path d="M9.5 10.5c2-5 11-5 13 0l-1-4h-11z" fill="#F2A007" stroke="#C77700"/></svg>`,
  guest: `<svg width="28" height="28" viewBox="0 0 32 32" fill="none" stroke="#A3193F" stroke-width="1.7"><circle cx="11" cy="13" r="4.5"/><circle cx="21" cy="13" r="4.5"/><path d="M3 27c1-5 15-5 16 0M13 27c1-5 15-5 16 0"/></svg>`,
  sun: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#C77700" stroke-width="1.8"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/></svg>`,
  nomakeup: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#A3193F" stroke-width="1.8"><circle cx="12" cy="12" r="8"/><path d="M6 6l12 12"/></svg>`,
  hair: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#A3193F" stroke-width="1.8"><circle cx="12" cy="14" r="6"/><path d="M5 11c1-7 13-7 14 0"/></svg>`,
  glasses: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#A3193F" stroke-width="1.8"><circle cx="7" cy="14" r="3.5"/><circle cx="17" cy="14" r="3.5"/><path d="M10.5 14h3M3 6l18 15"/></svg>`,
};

const toran = `<svg class="toran" viewBox="0 0 440 64" preserveAspectRatio="none" aria-hidden="true">
  <path d="M0 6 Q110 30 220 6 T440 6" stroke="#C9A04B" stroke-width="2" fill="none"/>
  ${Array.from({ length: 12 }, (_, i) => {
    const x = 18 + i * 37, y = 6 + 18 * Math.sin((i / 11) * Math.PI) * 0.0 + (i % 2 ? 4 : 0);
    const c = i % 3 === 0 ? "#F2A007" : i % 3 === 1 ? "#E8590C" : "#FFC53D";
    return `<g transform="translate(${x} ${y + 12})"><path d="M0 0 q-7 14 0 26 q7-12 0-26" fill="#2F7D3A" opacity=".85"/>
      <circle cx="0" cy="${24 + (i % 2) * 6}" r="7.5" fill="${c}"/><circle cx="0" cy="${24 + (i % 2) * 6}" r="3.2" fill="#fff" opacity=".35"/>
      <circle cx="0" cy="${38 + (i % 2) * 6}" r="5" fill="${c}"/></g>`;
  }).join("")}</svg>`;

const mandala = `<svg class="mandala" width="200" height="200" viewBox="0 0 200 200" aria-hidden="true"><g fill="none" stroke="#fff" stroke-width="2">
  ${Array.from({ length: 16 }, (_, i) => `<ellipse cx="100" cy="45" rx="14" ry="40" transform="rotate(${i * 22.5} 100 100)"/>`).join("")}
  <circle cx="100" cy="100" r="30"/><circle cx="100" cy="100" r="88"/></g></svg>`;

// ------------------------------------------------------------------ helpers
const fmtINR = (n) => "₹" + Number(n).toLocaleString("en-IN");
const todayISO = () => (CFG && CFG.today) || new Date().toISOString().slice(0, 10);
const daysBetween = (a, b) => Math.round((Date.parse(b + "T00:00:00Z") - Date.parse(a + "T00:00:00Z")) / 86400000);
const addDays = (iso, n) => { const d = new Date(iso + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const fmtDate = (iso) => new Date(iso + "T00:00:00").toLocaleDateString(state.lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short" });
const bandColor = { focus: "var(--focus)", improve: "var(--improve)", good: "var(--good)", great: "var(--great)" };
const scan = () => state.scanRes && state.scanRes.scan;
const unitsLabel = (n) => (n === 1 ? T("unit_1") : T("units_n", { n }));
const unitsTag = (res) => !res ? "" : (res.cached || res.units_charged === 0) ? T("cached") : unitsLabel(res.units_charged);

function apiTag(res) {
  if (!res) return "";
  const name = res.api || "";
  return `<div class="apitag"><code>${esc(name)}</code><span>${esc(unitsTag(res))}</span>
    <button class="linkbtn" data-act="show-request" data-key="${esc(res.cache_key || "")}">API ↗</button></div>`;
}
const lastRes = {};   // cache_key -> response, for the API drawer

function remember(res) { if (res && res.cache_key) lastRes[res.cache_key] = res; return res; }

// ------------------------------------------------------------------ shell
const NAV = [["report", "tab_report", I.report], ["plan", "tab_plan", I.plan], ["looks", "tab_looks", I.looks],
  ["shop", "tab_shop", I.shop], ["progress", "tab_progress", I.progress]];

function shell(route, inner) {
  const live = CFG && CFG.mode === "live";
  const cartN = Object.values(state.cart).reduce((a, b) => a + b.qty, 0);
  const showNav = !!scan() && NAV.some(([r]) => r === route);
  document.body.dataset.lang = state.lang;
  document.documentElement.lang = state.lang === "hi" ? "hi" : "en";
  return `<div class="app ${showNav ? "" : "no-nav"}">
    <header class="topbar"><a class="brand" href="#/">${I.logo}<span>ShaadiGlow</span></a><div class="spacer"></div>
      <button class="pill ${live ? "live" : ""}" data-act="about" title="${live ? "Live YouCam API" : "No YouCam key on this server yet: demo fixtures"}">
        <span class="dot"></span>${T(live ? "live_mode" : "demo_mode")}</button>
      <button class="langbtn" data-act="lang" aria-label="language">${state.lang === "en" ? "हिं" : "EN"}</button>
      <button class="iconbtn" data-act="about" aria-label="about">${I.info}</button></header>
    <main id="main">${inner}</main>
    ${showNav ? `<nav class="nav">${NAV.map(([r, k, ic]) => `<a href="#/${r}" class="${r === route ? "on" : ""}">${ic}<span>${T(k)}${r === "shop" && cartN ? ` (${cartN})` : ""}</span></a>`).join("")}</nav>` : ""}
  </div><div id="YMK-module"></div>`;
}

const ROUTES = {};
function route() { return (location.hash.replace(/^#\/?/, "") || "").split("?")[0]; }
async function render() {
  const r = route();
  const view = ROUTES[r] || ROUTES[""];
  if (["report", "plan", "looks", "shop", "progress"].includes(r) && !scan()) { location.hash = "#/"; return; }
  const root = $("#root");
  root.innerHTML = shell(r, view.html());
  window.scrollTo(0, 0);
  if (view.mount) await view.mount();
}
window.addEventListener("hashchange", render);
const go = (r) => { location.hash = "#/" + r; };

// ------------------------------------------------------------------ welcome
ROUTES[""] = {
  html() {
    const personas = (CFG ? CFG.personas : []);
    return `<div class="hero">${toran}<div class="screen" style="padding-top:4px">
      <span class="kicker">शादी ग्लो · Shaadi Glow</span>
      <h1>${T("app_tag")}</h1><p class="lede">${T("hero_sub")}</p>
      <h3>${T("who")}</h3>
      <div class="roles">${ROLES.map((r) => `<button class="role ${state.role === r ? "on" : ""}" data-act="role" data-role="${r}">
        <span class="em">${I[r]}</span>${T("role_" + r)}</button>`).join("")}</div>
      <button class="btn primary block" data-act="start-selfie">${T("start_selfie")}</button>
      <div class="journey">${[["j_scan", "AI Skin Analysis"], ["j_plan", "D-60 → D-day"], ["j_try", "Makeup · Hair · Jewellery"], ["j_shop", "1 cart"]]
        .map(([k, sub], i) => `<div class="jstep"><span class="n">${i + 1}</span><b>${T(k)}</b><span class="tiny">${esc(sub)}</span></div>`).join("")}</div>
      <div class="section-title"><h2>${T("samples_title")}</h2><span class="pill">0 units</span></div>
      <div class="personas">${personas.map((p) => `<button class="persona" data-act="persona" data-id="${p.id}">
        <img src="${p.image}" alt="${esc(p.name)}" loading="lazy"><div class="grow"><b>${esc(p.name)}</b>
        <div class="small muted">${esc(L(p.blurb))}</div><div class="tiny">Photo: ${esc(p.credit)}</div></div>
        <span class="chip">${T(p.role)}</span></button>`).join("")}</div>
      <p class="tiny mt8">${T("samples_note")}</p>
      <div class="apis">${CFG ? Object.values(CFG.apis).map((a) => `<span>${esc(a.title)}</span>`).join("") : ""}</div>
    </div></div>`;
  },
};

// ------------------------------------------------------------------ setup
ROUTES.setup = {
  html() {
    if (!state.wedding_date) state.wedding_date = addDays(todayISO(), 58);
    const n = daysBetween(todayISO(), state.wedding_date);
    const tiers = CFG.budgets;
    return `<div class="screen"><span class="kicker">${T("role_" + state.role)}</span><h1>${T("setup_title")}</h1>
      <label class="field"><span>${T("wedding_date")}</span>
        <input class="input" type="date" id="wdate" value="${state.wedding_date}" min="${todayISO()}">
        <div class="small muted mt8" id="dcount">${n === 1 ? T("day_to_go") : T("days_to_go", { n })}</div></label>
      <label class="field"><span>${T("city")}</span><select class="input" id="city">
        ${CFG.cities.map((c) => `<option value="${c.id}" ${c.id === state.city ? "selected" : ""}>${esc(state.lang === "hi" ? c.hi : c.name)}</option>`).join("")}
      </select></label>
      <div class="field"><span>${T("budget")}</span><div class="tiers">
        ${Object.entries(tiers).map(([k, v]) => `<button class="tier ${state.budget === k ? "on" : ""}" data-act="tier" data-tier="${k}">
          <b>${v.label}</b><span class="small">${T("tier_" + k)}</span><div class="tiny">${T("up_to", { n: v.cap.toLocaleString("en-IN") })}</div></button>`).join("")}
      </div></div>
      <div class="field"><span>${T("events")}</span><div class="chips">
        ${EVENTS.map((e) => `<button class="chip ${state.events.includes(e) ? "on" : ""}" data-act="event" data-ev="${e}">${T("ev_" + e)}</button>`).join("")}
      </div></div>
      <div class="field"><span>${T("notes")}</span>
        <label class="toggle"><input type="checkbox" id="sens" ${state.sensitive ? "checked" : ""}><span>${T("sensitive")}</span></label>
        <label class="toggle"><input type="checkbox" id="preg" ${state.pregnant ? "checked" : ""}><span>${T("pregnant")}</span></label></div>
      <button class="btn primary block mt16" data-act="setup-next">${T("continue")}</button></div>`;
  },
  mount() {
    $("#wdate").addEventListener("change", (e) => {
      state.wedding_date = e.target.value; save();
      const n = daysBetween(todayISO(), state.wedding_date);
      $("#dcount").textContent = n === 1 ? T("day_to_go") : T("days_to_go", { n });
    });
    $("#city").addEventListener("change", (e) => { state.city = e.target.value; save(); });
    $("#sens").addEventListener("change", (e) => { state.sensitive = e.target.checked; save(); });
    $("#preg").addEventListener("change", (e) => { state.pregnant = e.target.checked; save(); });
  },
};

// ------------------------------------------------------------------ capture
let cropSrc = null;
ROUTES.capture = {
  html() {
    return `<div class="screen"><h1>${T("capture_title")}</h1>
      <div class="tips"><div class="tip"><div class="ic">${I.nomakeup}</div>${T("tip_nomakeup")}</div>
        <div class="tip"><div class="ic">${I.sun}</div>${T("tip_light")}</div>
        <div class="tip"><div class="ic">${I.hair}</div>${T("tip_hair")}</div>
        <div class="tip"><div class="ic">${I.glasses}</div>${T("tip_glasses")}</div></div>
      <label class="consent"><input type="checkbox" id="consent" ${state.consent ? "checked" : ""}><span>${T("consent")}</span></label>
      <div id="capture-body" class="mt16">
        <button class="bigopt" data-act="camkit"><span class="ic">${I.camera}</span><span><b>${T("camera_kit")}</b><span class="small muted">${T("camera_kit_sub")}</span></span></button>
        <button class="bigopt" data-act="pick"><span class="ic">${I.upload}</span><span><b>${T("upload")}</b><span class="small muted">${T("upload_sub")}</span></span></button>
        <input type="file" id="file" accept="image/jpeg,image/png" class="hidden">
        <p class="center mt16"><a href="#/" class="small">${T("or_sample")}</a></p>
      </div></div>`;
  },
  mount() {
    $("#consent").addEventListener("change", (e) => { state.consent = e.target.checked; save(); });
    $("#file").addEventListener("change", async (e) => {
      const f = e.target.files[0];
      if (!f) return;
      cropSrc = URL.createObjectURL(f);
      state.camera_kit = false;
      showCropper();
    });
  },
};

function needConsent() { if (!state.consent) { toast(T("consent_needed"), true); return true; } return false; }

function showCropper() {
  const body = $("#capture-body");
  body.innerHTML = `<h2>${T("crop_title")}</h2><div class="cropper" id="cropper"><img id="cimg" alt=""><div class="oval"></div></div>
    <p class="tiny center mt8">${T("crop_hint")}</p><input type="range" id="zoom" min="1" max="3" step="0.01" value="1">
    <button class="btn primary block mt12" data-act="use-photo">${T("use_photo")}</button>`;
  const img = $("#cimg"), box = $("#cropper");
  const st = { s: 1, x: 0, y: 0, base: 1 };
  img.onload = () => {
    const W = box.clientWidth, H = box.clientHeight;
    st.base = Math.max(W / img.naturalWidth, H / img.naturalHeight);
    st.x = (W - img.naturalWidth * st.base) / 2; st.y = (H - img.naturalHeight * st.base) / 2;
    apply();
  };
  img.src = cropSrc;
  const apply = () => {
    const W = box.clientWidth, H = box.clientHeight, sc = st.base * st.s;
    st.x = Math.min(0, Math.max(W - img.naturalWidth * sc, st.x));
    st.y = Math.min(0, Math.max(H - img.naturalHeight * sc, st.y));
    img.style.transform = `translate(${st.x}px, ${st.y}px) scale(${sc})`;
  };
  let drag = null;
  box.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, sx: st.x, sy: st.y }; box.setPointerCapture(e.pointerId); });
  box.addEventListener("pointermove", (e) => { if (!drag) return; st.x = drag.sx + e.clientX - drag.x; st.y = drag.sy + e.clientY - drag.y; apply(); });
  box.addEventListener("pointerup", () => { drag = null; });
  $("#zoom").addEventListener("input", (e) => {
    const W = box.clientWidth / 2, H = box.clientHeight / 2, old = st.base * st.s;
    st.s = parseFloat(e.target.value);
    const k = (st.base * st.s) / old;
    st.x = W - (W - st.x) * k; st.y = H - (H - st.y) * k; apply();
  });
  ROUTES.capture.crop = () => {
    const W = box.clientWidth, H = box.clientHeight, sc = st.base * st.s;
    const sx = -st.x / sc, sy = -st.y / sc, sw = W / sc, sh = H / sc;
    const draw = (x, y, w, h) => new Promise((res) => {
      const c = document.createElement("canvas"); c.width = 1080; c.height = 1440;
      c.getContext("2d").drawImage(img, x, y, w, h, 0, 0, 1080, 1440);
      c.toBlob(res, "image/jpeg", 0.92);
    });
    // portrait = 1.7x wider window around the same centre, kept inside the photo
    const pw = Math.min(img.naturalWidth, sw * 1.7), ph = Math.min(img.naturalHeight, pw * 4 / 3), pw2 = ph * 3 / 4;
    const cx = sx + sw / 2, cy = sy + sh * 0.45;
    const px = Math.min(Math.max(0, cx - pw2 / 2), img.naturalWidth - pw2), py = Math.min(Math.max(0, cy - ph * 0.38), img.naturalHeight - ph);
    return Promise.all([draw(sx, sy, sw, sh), draw(px, py, pw2, ph)]);
  };
}

async function usePhoto() {
  if (needConsent()) return;
  const [face, portrait] = await ROUTES.capture.crop();
  const fd = new FormData();
  fd.append("face", face, "face.jpg"); fd.append("portrait", portrait, "portrait.jpg");
  fd.append("source", state.camera_kit ? "camera_kit" : "upload");
  try {
    const r = await api("/api/photo", { body: fd });
    Object.assign(state, { image_ref: r.image_ref, images: r.urls, persona: null, scanRes: null, plan: null, sim: null, tryon: {}, shade: null });
    save(); go("scan");
  } catch (e) { toast(e.message, true); }
}

function openCameraKit() {
  if (needConsent()) return;
  const start = () => {
    window.YMK.init({ faceDetectionMode: "skincare", imageFormat: "base64", language: state.lang === "hi" ? "enu" : "enu" });
    window.YMK.openCameraKit();
  };
  if (window.YMK && window.YMK.init) { start(); return; }
  window.ymkAsyncInit = window.YMKAsyncInit = () => {
    window.YMK.addEventListener("faceDetectionCaptured", (r) => {
      const im = r.images && r.images[0];
      if (!im) return;
      cropSrc = typeof im.image === "string" ? im.image : URL.createObjectURL(im.image);
      state.camera_kit = true;
      try { window.YMK.close(); } catch { /* ignore */ }
      showCropper();
    });
    window.YMK.addEventListener("cameraFailed", () => { toast(T("upload_sub"), true); try { window.YMK.close(); } catch { } });
    start();
  };
  const s = document.createElement("script");
  s.src = "https://plugins-media.makeupar.com/v2.5-camera-kit/sdk.js";
  s.onerror = () => toast("Camera Kit could not load. Please upload a photo instead.", true);
  document.body.appendChild(s);
}

// ------------------------------------------------------------------ scanning
ROUTES.scan = {
  html() {
    const img = state.images.face || "";
    return `<div class="screen"><span class="kicker">${T("role_" + state.role)}</span><h1>${T("scanning")}</h1>
      <div class="scanner"><img src="${img}" alt=""><div class="grid"></div></div>
      <div class="steps card mt16">
        <div class="step" id="st1"><span class="b"></span>${T("step_upload")}<span class="tag">${T("step_upload_api")}</span></div>
        <div class="step" id="st2"><span class="b"></span>${T("step_scan")}<span class="tag" id="st2tag">AI Skin Analysis</span></div>
        <div class="step" id="st3"><span class="b"></span>${T("step_masks")}</div>
        <div class="step" id="st4"><span class="b"></span>${T("step_plan")}</div>
      </div></div>`;
  },
  async mount() {
    const on = (id) => $("#" + id) && $("#" + id).classList.add("on");
    const done = (id) => { const n = $("#" + id); if (n) { n.classList.remove("on"); n.classList.add("done"); n.querySelector(".b").innerHTML = I.check; } };
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    on("st1"); await wait(700); done("st1"); on("st2");
    try {
      const res = remember(await api("/api/scan", { body: { image_ref: state.image_ref, profile_id: state.profile_id, camera_kit: state.camera_kit } }));
      state.scanRes = res; state.sim = null; save();
      $("#st2tag") && ($("#st2tag").textContent = unitsTag(res));
      done("st2"); on("st3"); await wait(600); done("st3"); on("st4");
      await makePlan();
      await wait(450); done("st4"); await wait(350);
      go("report");
    } catch (e) {
      toast(e.message, true);
      setTimeout(() => go(state.persona ? "" : "capture"), 1600);
    }
  },
};

async function makePlan() {
  const body = { scan: scan(), wedding_date: state.wedding_date, city: state.city, budget: state.budget, role: state.role,
    sensitive: state.sensitive, pregnant: state.pregnant, events: state.events, today: todayISO() };
  state.plan = await api("/api/plan", { body }); save();
}

// ------------------------------------------------------------------ report
let maskOn = null;
ROUTES.report = {
  html() {
    const s = scan(), res = state.scanRes;
    const focus = s.concerns.filter((c) => c.ui < 75).slice(0, 3);
    const top = (focus.length ? focus : s.concerns.slice(0, 3));
    const best = [...s.concerns].sort((a, b) => b.ui - a.ui).slice(0, 2);
    const st = s.skin_type || {};
    const R = 50, C = 2 * Math.PI * R, pct = Math.max(0, Math.min(100, s.overall)) / 100;
    return `<div class="screen"><span class="kicker">${T("report_title")}</span>
      <div class="photo-card mt8" id="photo"><img src="${res.image || state.images.face}" alt="">
        <img class="mask" id="mask" alt="" style="opacity:0"><span class="badge" id="maskname">${T("show_mask")}</span></div>
      <div class="chips scroll mt12" id="maskchips"><button class="chip on" data-act="mask" data-id="">${T("mask_none")}</button>
        ${s.concerns.map((c) => `<button class="chip" data-act="mask" data-id="${c.id}"><span class="sw" style="background:${bandColor[c.band]}"></span>${esc(L(c.label))}</button>`).join("")}</div>
      <div class="card mt12"><div class="summary"><div class="ring"><svg width="112" height="112"><circle cx="56" cy="56" r="${R}" stroke="#F1E7DF" stroke-width="10" fill="none"/>
        <circle cx="56" cy="56" r="${R}" stroke="url(#rg)" stroke-width="10" fill="none" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - pct)}"/>
        <defs><linearGradient id="rg"><stop offset="0" stop-color="#F2A007"/><stop offset="1" stop-color="#A3193F"/></linearGradient></defs></svg>
        <div class="val"><b>${s.overall}</b><span>${T("skin_score")}</span></div></div>
        <div class="facts"><div class="fact"><span class="tiny">${T("skin_age")}</span><b>${s.skin_age ?? "–"}</b></div>
          <div class="fact"><span class="tiny">${T("skin_type")}</span><b>${esc(skinType(st.whole && st.whole.type))}</b></div>
          <div class="fact"><span class="tiny">${T("tzone")}</span><b>${esc(skinType(st.t_zone && st.t_zone.type))}</b></div>
          <div class="fact"><span class="tiny">${T("uzone")}</span><b>${esc(skinType(st.u_zone && st.u_zone.type))}</b></div></div></div>
        ${apiTag(res)}</div>
      <div class="section-title"><h2>${T("focus_title")}</h2></div>
      <div class="card">${top.map(concernRow).join("")}
        <div class="why mt12">${T("targets_line", { list: top.map((c) => L(c.label)).join(", ") })}</div></div>
      <div class="card" id="goal"><span class="kicker">AI Skin Simulation</span><h2 class="mt8">${T("goal_title")}</h2>
        <p class="small muted" style="margin-top:-4px">${T("goal_sub")}</p><div id="goalbody">${goalBody()}</div></div>
      <div class="section-title"><h2>${T("strengths")}</h2></div>
      <div class="card">${best.map(concernRow).join("")}</div>
      <details class="card mt12"><summary><b>${T("all_concerns")}</b></summary><div class="mt8">${s.concerns.map(concernRow).join("")}</div></details>
      <button class="btn primary block mt16" data-act="nav" data-to="plan">${T("see_plan")}</button>
      <p class="tiny center mt12">${esc(L(state.plan && state.plan.disclaimer))}</p></div>`;
  },
  mount() { maskOn = null; bindCompare(); },
};

function skinType(v) {
  if (!v) return "–";
  if (state.lang !== "hi") return v;
  const m = { Normal: "सामान्य", Oily: "तैलीय", Dry: "रूखी", Combination: "मिश्रित" };
  return v.split(" & ").map((x) => m[x] || x).join(" व ");
}

function concernRow(c) {
  return `<div class="concern"><div class="row between"><div class="grow"><div class="row"><span class="name">${esc(L(c.label))}</span>
    <span class="band ${c.band}">${T("band_" + c.band)}</span></div><div class="small muted">${esc(L(c.what))}</div></div>
    <span class="score">${c.ui}</span></div><div class="bar"><i style="width:${c.ui}%;background:${bandColor[c.band]}"></i></div></div>`;
}

function goalBody() {
  if (state.sim) {
    return `${compareView(state.sim.before, state.sim.url, T("before"), T("after"))}${apiTag(state.sim)}<p class="tiny mt8">${T("goal_note")}</p>`;
  }
  return `<button class="btn gold block" data-act="goal">${T("goal_btn")} · ${T("units_n", { n: 4 })}</button>`;
}

function compareView(before, after, lb, la, busyMsg = null) {
  return `<div class="compare" data-compare style="--split:50%"><img src="${before}" alt="">
    ${after ? `<img class="after" src="${after}" alt="">` : ""}<div class="handle"></div>
    <span class="lbl l">${esc(lb)}</span>${after ? `<span class="lbl r">${esc(la)}</span>` : ""}
    ${busyMsg ? `<div class="busy"><div><div class="spin"></div>${esc(busyMsg)}</div></div>` : ""}</div>`;
}

function bindCompare() {
  $$("[data-compare]").forEach((el) => {
    let down = false;
    const set = (x) => { const r = el.getBoundingClientRect(); el.style.setProperty("--split", Math.max(0, Math.min(100, ((x - r.left) / r.width) * 100)) + "%"); };
    el.addEventListener("pointerdown", (e) => { down = true; el.setPointerCapture(e.pointerId); set(e.clientX); });
    el.addEventListener("pointermove", (e) => { if (down) set(e.clientX); });
    el.addEventListener("pointerup", () => { down = false; });
  });
}

async function runGoal() {
  const s = scan();
  const focus = s.concerns.filter((c) => c.id !== "moisture").slice(0, 4).map((c) => c.id);
  $("#goalbody").innerHTML = compareView(state.scanRes.image || state.images.face, null, T("before"), T("after"), T("rendering"));
  try {
    state.sim = remember(await api("/api/simulate", { body: { image_ref: state.image_ref, focus, strength: 0.6, profile_id: state.profile_id } }));
    save();
  } catch (e) { toast(e.message, true); }
  $("#goalbody").innerHTML = goalBody(); bindCompare();
}

function showMask(id) {
  const s = scan(), m = $("#mask"), name = $("#maskname");
  $$("#maskchips .chip").forEach((c) => c.classList.toggle("on", c.dataset.id === (id || "")));
  if (!id) { m.style.opacity = 0; name.textContent = T("show_mask"); return; }
  const c = s.concerns.find((x) => x.id === id);
  if (!c || !c.mask) return;
  m.src = c.mask; m.style.opacity = 0.92;
  name.textContent = `${L(c.label)} · ${c.ui}/100`;
}

// ------------------------------------------------------------------ plan
ROUTES.plan = {
  html() {
    const p = state.plan;
    if (!p) return `<div class="screen"><div class="empty">…</div></div>`;
    const cl = p.climate.now;
    const n = p.days_left;
    const ph = p.phases.find((x) => x.id === p.current_phase) || p.phases[0];
    const tab = state.routineTab;
    const steps = !ph ? [] : (tab === "am" ? ph.am : tab === "pm" ? ph.pm : ph.weekly);
    const dk = todayISO(), doneMap = state.done[dk] || {};
    const allSteps = ph ? [...ph.am.map((s) => "am:" + s.product), ...ph.pm.map((s) => "pm:" + s.product)] : [];
    const nDone = allSteps.filter((k) => doneMap[k]).length;
    const upcoming = p.milestones.filter((m) => m.date >= dk).slice(0, 6);
    const over = p.total - p.budget.cap;
    const hum = { humid: "hum_humid", moderate: "hum_moderate", dry: "hum_dry" }[cl.humidity];
    return `<div class="screen">
      <div class="countdown">${mandala}<span class="kicker" style="color:#FFD36B">${T("plan_title")}</span>
        <div class="big">${n > 0 ? T("d_minus", { n }) : "D-day"}</div>
        <div class="sub">${fmtDate(p.wedding_date)} · ${esc(state.lang === "hi" ? cl.name_hi : cl.name)} · ${esc(T("role_" + p.role))}</div>
        <div class="climate">${climateRow(T("clim_now"), cl)}${climateRow(T("clim_wedding"), p.climate.wedding)}</div></div>
      <div class="phases">${p.phases.map((x) => `<div class="phase ${x.id === p.current_phase ? "now" : ""} ${x.end < dk ? "past" : ""}">
        <span class="tiny">${fmtDate(x.start)} – ${fmtDate(x.end)}</span><b>${esc(L(x.name))}</b>
        ${x.id === p.current_phase ? `<span class="band improve">${T("phase_now")}</span>` : ""}</div>`).join("")}</div>
      ${ph ? `<p class="small muted mt12" style="margin-bottom:0">${esc(L(ph.goal))}</p>` : ""}
      <div class="section-title"><h2>${T("today_routine")}</h2><span class="small muted">${T("done_today", { a: nDone, b: allSteps.length })} · ${T("streak", { n: streak() })}</span></div>
      <div class="seg mb8">${["am", "pm", "weekly"].map((k) => `<button class="${tab === k ? "on" : ""}" data-act="rtab" data-tab="${k}">${T(k)}</button>`).join("")}</div>
      <div class="card">${steps.length ? steps.map((s, i) => stepRow(s, tab, i, doneMap)).join("") : `<div class="empty small">–</div>`}
        ${ph && ph.notes.length ? `<div class="why mt8">${ph.notes.map((r) => `<p>• ${esc(L(r))}</p>`).join("")}</div>` : ""}</div>
      <div class="section-title"><h2>${T("coming_up")}</h2><button class="btn ghost sm" data-act="ics">${T("add_calendar")}</button></div>
      <div class="card">${upcoming.map((m) => `<div class="milestone"><div class="dd"><b>${m.d === 0 ? "D" : "D" + m.d}</b><span>${fmtDate(m.date)}</span></div>
        <div><span class="kind ${m.kind}"></span><span class="small" style="font-weight:600">${esc(L(m.title))}</span></div></div>`).join("")}</div>
      ${p.skipped.length ? `<div class="section-title"><h2>${T("skipped_title")}</h2></div><div class="card">
        ${p.skipped.map((s) => `<div class="concern"><b>${esc(L(s.name))}</b><div class="small muted">${esc(L(s.reason))}</div></div>`).join("")}</div>` : ""}
      <div class="section-title"><h2>${T("budget_card")}</h2><span class="small muted">${esc(p.budget.label)} · ${T("tier_" + p.budget.tier)}</span></div>
      <div class="card"><div class="row between"><b style="font-size:22px">${fmtINR(p.total)}</b>
        <span class="small ${over > 0 ? "" : "muted"}">${over > 0 ? T("over_budget", { n: over.toLocaleString("en-IN") }) : T("within_budget", { tier: p.budget.label })}</span></div>
        <div class="meter mt8 ${over > 0 ? "over" : ""}"><i style="width:${Math.min(100, (p.total / p.budget.cap) * 100)}%"></i></div>
        <div class="tiny mt8">${p.products.length} items · cap ${fmtINR(p.budget.cap)}</div>
        <button class="btn primary block mt12" data-act="shop-routine">${T("shop_routine")}</button></div>
      <details class="card mt12"><summary><b>${T("rules_title")}</b></summary><div class="why mt8">${p.rules.map((r) => `<p><b>${esc(r.id)}</b> ${esc(L(r))}</p>`).join("")}</div></details>
      <p class="tiny center mt12">${esc(L(p.disclaimer))}</p></div>`;
  },
};

const UVHI = { high: "ऊँचा", "very high": "बहुत ऊँचा", extreme: "अत्यधिक" };
function monthName(n) {
  return new Date(Date.UTC(2026, n - 1, 15)).toLocaleDateString(state.lang === "hi" ? "hi-IN" : "en-IN", { month: "short" });
}
function climateRow(label, c) {
  const air = c.skin_air === "dry" ? (c.temp === "cool" ? "air_cool" : "hum_dry") : c.skin_air === "humid" ? "hum_humid" : "hum_moderate";
  const uv = state.lang === "hi" ? (UVHI[c.uv] || c.uv) : c.uv;
  return `<div class="crow"><span class="cl">${esc(label)} · ${esc(monthName(c.month_num))}</span><span class="chip">${T(air)}</span>
    <span class="chip">${T("uv", { v: uv })}</span>${c.smog ? `<span class="chip">${T("smog")}</span>` : ""}</div>`;
}

function stepRow(s, tab, i, doneMap) {
  const p = CATALOG[s.product] || { art: {} };
  const key = tab + ":" + s.product;
  const on = !!doneMap[key];
  const why = s.why && s.why.length;
  return `<div class="routine-step"><div class="art">${productArt(p.art, 40)}</div><div class="grow">
    <div class="slot">${i + 1}. ${esc(L(s.label))}</div><div class="nm">${esc(s.name)}</div>
    ${s.note ? `<div class="small muted">${esc(L(s.note))}</div>` : ""}
    ${why ? `<button class="linkbtn" data-act="why" data-i="${tab}${i}">${T("why")}</button>
      <div class="why hidden" id="why-${tab}${i}">${s.why.map((r) => `<p>${esc(L(r))}</p>`).join("")}</div>` : ""}</div>
    ${tab !== "weekly" ? `<button class="check ${on ? "on" : ""}" data-act="tick" data-key="${esc(key)}" aria-label="done">${on ? I.check : ""}</button>` : ""}</div>`;
}

function streak() {
  let n = 0, d = todayISO();
  while (state.done[d] && Object.values(state.done[d]).some(Boolean)) { n++; d = addDays(d, -1); }
  return n;
}

async function downloadIcs() {
  const body = { scan: scan(), wedding_date: state.wedding_date, city: state.city, budget: state.budget, role: state.role,
    sensitive: state.sensitive, pregnant: state.pregnant, events: state.events, today: todayISO() };
  const r = await api(`/api/plan.ics?lang=${state.lang}`, { body, raw: true });
  const blob = await r.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "shaadiglow-plan.ics"; a.click();
}

// ------------------------------------------------------------------ looks
let LOOKS = [], TEMPLATES = null;
ROUTES.looks = {
  html() {
    const tabs = ["makeup", "hair", state.role === "groom" ? "beard" : "jewel"];
    if (!tabs.includes(state.lookTab)) state.lookTab = "makeup";
    return `<div class="screen"><span class="kicker">${T("looks_title")}</span>
      <div class="seg mt8">${tabs.map((k) => `<button class="${state.lookTab === k ? "on" : ""}" data-act="ltab" data-tab="${k}">${T("seg_" + k)}</button>`).join("")}</div>
      <div id="viewer" class="mt12"></div><div id="lookbody"></div></div>`;
  },
  async mount() {
    if (!LOOKS.length || LOOKS.role !== state.role) {
      LOOKS = (await api(`/api/looks?role=${state.role}`)).looks; LOOKS.role = state.role;
    }
    if (!state.shadeSuggested) {
      try {
        const sh = await api("/api/shade", { body: { image_ref: state.image_ref } });
        state.shadeSuggested = sh.product; state.shades = sh.shades; if (!state.shade) state.shade = sh.product; save();
      } catch { /* optional */ }
    }
    if (state.role === "groom" && !TEMPLATES) {
      try { TEMPLATES = (await api("/api/tryon/beard/templates")).templates; } catch { TEMPLATES = []; }
    }
    drawLooks();
  },
};

function variantFor(tab) { return tab === "makeup" ? "face" : tab === "beard" ? "beard" : "portrait"; }

function drawLooks(busyMsg = null) {
  const tab = state.lookTab;
  const cur = state.tryon[tab];
  const before = state.images[variantFor(tab)] || state.images.face;
  $("#viewer").innerHTML = compareView(before, cur && cur.url, T("before"), cur ? cur.title || "" : "", busyMsg) +
    (cur ? apiTag(cur) : `<p class="tiny mt8">${T("drag_compare")}</p>`);
  bindCompare();
  let body = "";
  if (tab === "makeup") {
    body = `<div class="section-title"><h2>${T("seg_makeup")}</h2></div><div class="lookcards">${LOOKS.map((lk) => `
      <button class="lookcard ${cur && cur.id === lk.id ? "on" : ""}" data-act="look" data-id="${lk.id}"><span class="ev">${T("ev_" + lk.event)}</span>
      <b>${esc(L(lk.name))}</b><div class="swatches">${lk.items.slice(0, 6).map((it) => `<i style="background:${swatch(it)}"></i>`).join("")}</div></button>`).join("")}</div>
      ${state.shades ? `<div class="section-title"><h3 style="margin:0">${T("shade")}</h3><span class="tiny">${esc((CATALOG[state.shade] || {}).name || "")}</span></div>
      <div class="shades">${state.shades.map((s) => `<button class="shade ${state.shade === s.id ? "on" : ""}" data-act="shade" data-id="${s.id}" title="${esc(s.name)}" style="background:${s.hex}">
        ${state.shadeSuggested === s.id ? `<span class="star">★</span>` : ""}</button>`).join("")}</div>` : ""}
      ${cur ? lookProducts(cur) : `<p class="small muted mt12">${esc(L((LOOKS[0] || {}).desc))}</p>`}`;
  } else if (tab === "hair") {
    const hair = Object.values(CATALOG).filter((p) => p.category === "Hair colour");
    body = `<div class="section-title"><h2>${T("seg_hair")}</h2></div><div class="tilegrid">${hair.map((p) => tile(p, cur)).join("")}</div>${cur ? lookProducts(cur) : ""}`;
  } else if (tab === "jewel") {
    const j = Object.values(CATALOG).filter((p) => p.category === "Jewellery");
    body = `<div class="section-title"><h2>${T("seg_jewel")}</h2></div><p class="tiny" style="margin-top:-6px">${T("jewel_note")}</p>
      <div class="tilegrid">${j.map((p) => tile(p, cur)).join("")}</div>${cur ? lookProducts(cur) : ""}`;
  } else if (tab === "beard") {
    body = `<div class="section-title"><h2>${T("seg_beard")}</h2><span class="tiny">AI Beard Style Generator</span></div>
      <div class="tilegrid">${(TEMPLATES || []).map((tp) => `<button class="tile ${cur && cur.id === tp.id ? "on" : ""}" data-act="beard" data-id="${esc(tp.id)}">
      <div class="img">${tp.thumb ? `<img src="${esc(tp.thumb)}" alt="">` : ""}</div><b>${esc(tp.title || tp.id)}</b><span class="tiny">2 units</span></button>`).join("")}</div>
      <div class="section-title"><h2>${T("in_look")}</h2></div><div class="card"><div class="products">${["gr_beardoil", "gr_beardwash", "gr_aftershave"].map((id) => productRow(CATALOG[id], "extra")).join("")}</div></div>`;
  }
  $("#lookbody").innerHTML = body;
}

function swatch(it) {
  const a = it.art || {};
  return a.color || (a.colors && a.colors[0]) || "#ddd";
}

function tile(p, cur) {
  return `<button class="tile ${cur && cur.id === p.id ? "on" : ""}" data-act="tryprod" data-id="${p.id}">
    <div class="img">${productArt(p.art, 72)}</div><b>${esc(p.name)}</b><span class="tiny">${fmtINR(p.price)} · 1 unit</span></button>`;
}

function lookProducts(cur) {
  const ids = cur.products || [];
  return `<div class="section-title"><h2>${T("in_look")}</h2>
    <button class="btn ghost sm" data-act="add-many" data-ids="${esc(ids.join(","))}">${T(ids.length > 1 ? "add_look" : "add_item")}</button></div>
    <div class="card"><div class="products">${ids.map((id) => productRow(CATALOG[id], "look")).join("")}</div>
    ${cur.desc ? `<p class="small muted mt8">${esc(L(cur.desc))}</p>` : ""}</div>`;
}

function productRow(p, src) {
  if (!p) return "";
  const inCart = !!state.cart[p.id];
  return `<div class="product"><div class="art">${productArt(p.art, 46)}</div><div class="grow"><div class="nm">${esc(p.name)}</div>
    <div class="tiny">${esc(p.size)}</div></div><div class="center"><div class="price">${fmtINR(p.price)}</div>
    <button class="linkbtn" data-act="add" data-id="${p.id}" data-src="${src}">${inCart ? "✓ " + T("added") : "+ " + T("add_item")}</button></div></div>`;
}

async function tryOn(kind, id) {
  if (busy) return;
  busy = true;
  drawLooks(T("rendering"));
  try {
    let res, title = "", extra = {};
    if (kind === "makeup") {
      const lk = LOOKS.find((x) => x.id === id);
      res = await api("/api/tryon/makeup", { body: { image_ref: state.image_ref, look_id: id, shade_id: state.shade, profile_id: state.profile_id } });
      title = L(lk.name); extra = { desc: lk.desc };
    } else if (kind === "hair" || kind === "jewel") {
      const path = kind === "hair" ? "/api/tryon/hair" : "/api/tryon/jewellery";
      res = await api(path, { body: { image_ref: state.image_ref, product_id: id, profile_id: state.profile_id } });
      title = CATALOG[id].name;
    } else if (kind === "beard") {
      res = await api("/api/tryon/beard", { body: { image_ref: state.image_ref, template_id: id, profile_id: state.profile_id } });
      title = ((TEMPLATES || []).find((x) => x.id === id) || {}).title || id;
    }
    state.tryon[kind] = { ...remember(res), id, title, ...extra };
    save();
  } catch (e) { toast(e.message, true); }
  busy = false;
  drawLooks();
}

// ------------------------------------------------------------------ cart
function addToCart(ids, src) {
  ids.forEach((id) => { if (!CATALOG[id]) return; const c = state.cart[id]; state.cart[id] = { qty: c ? c.qty : 1, src: c ? c.src : src }; });
  save();
  toast(`${ids.length > 1 ? ids.length + " items" : CATALOG[ids[0]].name} · ${T("added")}`);
}

ROUTES.shop = {
  html() {
    const items = Object.entries(state.cart).filter(([id]) => CATALOG[id]);
    const groups = { routine: [], look: [], extra: [] };
    items.forEach(([id, c]) => (groups[c.src] || groups.extra).push([id, c]));
    const sum = (arr) => arr.reduce((a, [id, c]) => a + CATALOG[id].price * c.qty, 0);
    const total = sum(items);
    const cap = state.plan ? state.plan.budget.cap : 0;
    const routineTotal = sum(groups.routine);
    const sec = (key, arr) => !arr.length ? "" : `<div class="section-title"><h2>${T(key)}</h2><span class="small muted">${fmtINR(sum(arr))}</span></div>
      <div class="card"><div class="products">${arr.map(([id, c]) => cartRow(CATALOG[id], c)).join("")}</div></div>`;
    return `<div class="screen"><span class="kicker">${T("shop_title")}</span><div class="notice mt8">ⓘ <span>${T("sample_store")}</span></div>
      ${items.length ? sec("sec_routine", groups.routine) + sec("sec_looks", groups.look) + sec("sec_extras", groups.extra)
        : `<div class="empty">${T("empty_cart")}<div class="mt12"><button class="btn ghost sm" data-act="shop-routine">${T("shop_routine")}</button></div></div>`}
      ${items.length ? `<div class="totals"><div class="card"><div class="row between"><span class="muted">${T("total")}</span><b style="font-size:22px">${fmtINR(total)}</b></div>
        ${cap && routineTotal ? `<div class="tiny mt8">${T("sec_routine")}: ${fmtINR(routineTotal)} / ${fmtINR(cap)} ${routineTotal <= cap ? "✓" : ""}</div>` : ""}
        <div class="row mt12"><button class="btn ghost sm grow" data-act="share">${T("share")}</button>
        <button class="btn primary sm grow" data-act="checkout">${T("checkout")}</button></div></div></div>` : ""}</div>`;
  },
};

function cartRow(p, c) {
  const why = (state.plan && state.plan.products.find((x) => x.id === p.id) || {}).for || [];
  return `<div class="product"><div class="art">${productArt(p.art, 46)}</div><div class="grow"><div class="nm">${esc(p.name)}</div>
    <div class="tiny">${esc(p.size)}</div>${why.map((w) => `<span class="for">${T("for_")} ${esc(L(w))}</span>`).join("")}</div>
    <div class="center"><div class="price">${fmtINR(p.price * c.qty)}</div><div class="qty mt8"><button data-act="qty" data-id="${p.id}" data-d="-1">−</button>
    <span>${c.qty}</span><button data-act="qty" data-id="${p.id}" data-d="1">+</button></div></div></div>`;
}

// ------------------------------------------------------------------ progress
let demoProg = null;
ROUTES.progress = {
  html() {
    const p = state.plan;
    const next = p && p.milestones.find((m) => m.kind === "scan" && m.date >= todayISO());
    return `<div class="screen"><span class="kicker">${T("progress_title")}</span>
      <div class="card mt8"><h2>${next ? T("next_rescan", { date: fmtDate(next.date) }) : T("rescan_now")}</h2>
        <p class="small muted" style="margin-top:-4px">${T("rescan_sub")}</p>
        <div class="row mt12"><button class="btn primary sm grow" data-act="rescan" ${state.persona ? "disabled" : ""}>${T("rescan_now")}</button>
        <button class="btn ghost sm grow" data-act="demo-progress">${T("example_progress")}</button></div></div>
      <div id="progbody">${demoProg ? progressView(demoProg) : ""}</div></div>`;
  },
  async mount() {
    if (!state.persona) {
      try {
        const prof = await api(`/api/profile/${state.profile_id}`);
        if (prof.compare) $("#progbody").innerHTML = progressView({ compare: prof.compare,
          baseline: { image: imgFor(prof.scans[0]), label: T("scan1") }, latest: { image: imgFor(prof.scans[prof.scans.length - 1]), label: T("rescan") } });
      } catch { /* none yet */ }
    }
  },
};
const imgFor = (s) => (s.image_ref.startsWith("persona:") ? `/static/personas/${s.image_ref.slice(8)}/face.jpg` : `/uploads/${s.image_ref.slice(7)}/face.jpg`);

function progressView(d) {
  const c = d.compare;
  return `<div class="section-title"><h2>${T("example_progress")}</h2></div>
    <div class="pair"><figure><img src="${d.baseline.image}" alt=""><figcaption>${esc(d.baseline.label || T("scan1"))}</figcaption></figure>
      <figure><img src="${d.latest.image}" alt=""><figcaption>${esc(d.latest.label || T("rescan"))}</figcaption></figure></div>
    <div class="card mt12"><div class="headline">${esc(L(c.headline))}</div>
      <div class="mt12">${c.rows.map((r) => `<div class="delta"><span><b>${esc(L(r.label))}</b><div class="tiny">${r.before} → ${r.after}</div></span>
        <span class="dchip ${r.verdict}">${r.delta > 0 ? "+" : ""}${r.delta}</span><span class="small muted">${T(r.verdict)}</span></div>`).join("")}</div>
      <p class="tiny mt8">${T("noise_note", { n: c.noise_band })}</p>
      ${d.latest && d.latest.api ? apiTag(d.latest) : ""}</div>`;
}

async function rescan() {
  const tracked = (await api(`/api/profile/${state.profile_id}`)).tracked || [];
  try {
    const res = await api("/api/scan", { body: { image_ref: state.image_ref, profile_id: state.profile_id, kind: "quick", concerns: tracked } });
    remember(res); toast(unitsTag(res)); render();
  } catch (e) { toast(e.message, true); }
}

// ------------------------------------------------------------------ sheets
function sheet(html) {
  const bg = document.createElement("div"); bg.className = "sheet-bg";
  const sh = document.createElement("div"); sh.className = "sheet"; sh.innerHTML = `<div class="grab"></div>${html}`;
  const close = () => { bg.remove(); sh.remove(); };
  bg.onclick = close; sh.addEventListener("click", (e) => { if (e.target.dataset.act === "close") close(); });
  document.body.append(bg, sh);
  return sh;
}

async function about() {
  let u = CFG.units;
  try { u = await api("/api/units"); } catch { /* keep */ }
  const live = CFG.mode === "live";
  sheet(`<h2>${T("about_title")}</h2>
    <div class="card"><div class="row between"><span class="muted">${T("mode")}</span><b>${live ? "Live · YouCam API" : "Demo · recorded fixtures"}</b></div>
      <div class="row between mt8"><span class="muted">${T("region")}</span><b>${esc(CFG.region)} · ${esc(CFG.api_host)}</b></div>
      <div class="row between mt8"><span class="muted">${T("units_used")}</span><b>${u.spent}</b></div>
      <div class="row between mt8"><span class="muted">${T("units_left")}</span><b>${u.remaining}</b></div>
      <div class="tiny mt8">Cache: ${u.cache.entries + u.cache.seed_entries} results stored · ${u.cache.hits} hits. Every call is keyed by image hash + parameters, so a repeat costs 0 units.</div></div>
    <div class="section-title"><h3 style="margin:0">YouCam APIs & unit cost</h3></div>
    <div class="card"><table class="costs">${CFG.costs.map((c) => `<tr><td>${esc(c.feature)}</td><td>${c.units}</td></tr>`).join("")}</table></div>
    <div class="section-title"><h3 style="margin:0">${T("privacy")}</h3></div>
    <div class="card small muted">Photos go to YouCam (Perfect Corp.) only to produce your results. "Delete" removes our copy and calls YouCam's Task Delete API for every task you created.
      <button class="btn ghost block mt12" data-act="delete-data">${T("delete_data")}</button></div>
    <div class="section-title"><h3 style="margin:0">${T("credits")}</h3></div>
    <div class="card tiny">Sample photos: Andre Styles, ARTO SURAJ, Himanshu Dewangan (Unsplash License). Fonts: Playfair Display, Plus Jakarta Sans, Mukta (SIL OFL).
      Products, prices and jewellery art are fictional samples. AI by YouCam APIs (Perfect Corp.). v${esc(CFG.version)}</div>
    <button class="btn primary block mt16" data-act="close">${T("close")}</button>`);
}

function showRequest(key) {
  const r = lastRes[key];
  if (!r) return;
  sheet(`<h2>${esc(r.api || "")}</h2><p class="small muted">task ${esc((r.task_id || "").slice(0, 18))}… · ${esc(r.mode)} · ${r.elapsed_s ?? 0}s · ${r.polls ?? 0} polls · ${esc(unitsTag(r))}</p>
    <div class="card"><h3>Request body</h3><pre class="tiny" style="white-space:pre-wrap;word-break:break-word;margin:0">${esc(JSON.stringify(r.request, null, 1))}</pre></div>
    <div class="card mt12"><h3>Call trace</h3><pre class="tiny" style="white-space:pre-wrap;word-break:break-word;margin:0">${esc((r.calls || []).join("\n"))}</pre></div>
    <button class="btn primary block mt16" data-act="close">${T("close")}</button>`);
}

// ------------------------------------------------------------------ events
document.addEventListener("click", async (e) => {
  const el = e.target.closest("[data-act]");
  if (!el) return;
  const a = el.dataset.act;
  if (a === "lang") { state.lang = state.lang === "en" ? "hi" : "en"; save(); render(); }
  else if (a === "about") about();
  else if (a === "role") { state.role = el.dataset.role; save(); $$(".role").forEach((b) => b.classList.toggle("on", b === el)); }
  else if (a === "start-selfie") { Object.assign(state, { persona: null, image_ref: null, scanRes: null, plan: null, tryon: {}, sim: null }); save(); go("setup"); }
  else if (a === "persona") {
    const p = CFG.personas.find((x) => x.id === el.dataset.id);
    Object.assign(state, { persona: p.id, role: p.role, city: p.city, image_ref: "persona:" + p.id, camera_kit: false,
      images: { face: `/static/personas/${p.id}/face.jpg`, portrait: `/static/personas/${p.id}/portrait.jpg`, beard: `/static/personas/${p.id}/beard.jpg` },
      wedding_date: addDays(todayISO(), p.wedding_in_days), scanRes: null, plan: null, sim: null, tryon: {}, shade: null, shadeSuggested: null,
      lookTab: "makeup", events: p.role === "guest" ? ["sangeet", "wedding", "reception"] : [...EVENTS] });
    save(); go("setup");
  }
  else if (a === "tier") { state.budget = el.dataset.tier; save(); $$(".tier").forEach((b) => b.classList.toggle("on", b === el)); }
  else if (a === "event") {
    const ev = el.dataset.ev;
    state.events = state.events.includes(ev) ? state.events.filter((x) => x !== ev) : [...state.events, ev];
    el.classList.toggle("on"); save();
  }
  else if (a === "setup-next") {
    if (state.scanRes && state.image_ref) { await makePlan(); go("plan"); return; }
    go(state.image_ref ? "scan" : "capture");
  }
  else if (a === "pick") { if (!needConsent()) $("#file").click(); }
  else if (a === "camkit") openCameraKit();
  else if (a === "use-photo") usePhoto();
  else if (a === "mask") showMask(el.dataset.id);
  else if (a === "goal") runGoal();
  else if (a === "nav") go(el.dataset.to);
  else if (a === "rtab") { state.routineTab = el.dataset.tab; save(); render(); }
  else if (a === "why") $("#why-" + el.dataset.i).classList.toggle("hidden");
  else if (a === "tick") {
    const d = todayISO(); state.done[d] = state.done[d] || {};
    state.done[d][el.dataset.key] = !state.done[d][el.dataset.key]; save(); render();
  }
  else if (a === "ics") downloadIcs().catch((err) => toast(err.message, true));
  else if (a === "shop-routine") { addToCart(state.plan.products.map((p) => p.id), "routine"); go("shop"); }
  else if (a === "ltab") { state.lookTab = el.dataset.tab; save(); $$(".seg button").forEach((b) => b.classList.toggle("on", b === el)); drawLooks(); }
  else if (a === "look") tryOn("makeup", el.dataset.id);
  else if (a === "shade") {
    state.shade = el.dataset.id; save();
    const cur = state.tryon.makeup;
    if (cur) tryOn("makeup", cur.id); else drawLooks();
  }
  else if (a === "tryprod") tryOn(state.lookTab, el.dataset.id);
  else if (a === "beard") tryOn("beard", el.dataset.id);
  else if (a === "add") { addToCart([el.dataset.id], el.dataset.src || "extra"); if (route() === "looks") drawLooks(); }
  else if (a === "add-many") { addToCart(el.dataset.ids.split(",").filter(Boolean), "look"); drawLooks(); }
  else if (a === "qty") {
    const id = el.dataset.id, c = state.cart[id];
    if (c) { c.qty += parseInt(el.dataset.d, 10); if (c.qty <= 0) delete state.cart[id]; save(); render(); }
  }
  else if (a === "share") {
    const lines = Object.entries(state.cart).map(([id, c]) => `• ${CATALOG[id].name} x${c.qty} (${fmtINR(CATALOG[id].price * c.qty)})`);
    const txt = `My ShaadiGlow wedding kit (sample store):\n${lines.join("\n")}`;
    window.open("https://wa.me/?text=" + encodeURIComponent(txt), "_blank", "noopener");
  }
  else if (a === "checkout") {
    sheet(`<div class="center"><div style="font-size:48px">🎉</div><h2>${T("order_done")}</h2><p class="small muted">${T("order_sub")}</p></div>
      <button class="btn primary block mt16" data-act="close">${T("close")}</button>`);
  }
  else if (a === "demo-progress") {
    el.disabled = true;
    try { demoProg = await api("/api/demo/progress/arjun"); remember(demoProg.latest); $("#progbody").innerHTML = progressView(demoProg); }
    catch (err) { toast(err.message, true); }
    el.disabled = false;
  }
  else if (a === "rescan") rescan();
  else if (a === "show-request") showRequest(el.dataset.key);
  else if (a === "delete-data") {
    try {
      const r = await api(`/api/profile/${state.profile_id}/delete`, { method: "POST" });
      const lang = state.lang;
      state = { ...fresh(), lang }; save();
      toast(T("deleted", { n: r.youcam_tasks_deleted }));
      $$(".sheet,.sheet-bg").forEach((n) => n.remove()); go("");
    } catch (err) { toast(err.message, true); }
  }
});

// ------------------------------------------------------------------ boot
(async function boot() {
  try {
    CFG = await api("/api/config");
    const cat = await api("/api/catalog");
    cat.products.forEach((p) => { CATALOG[p.id] = p; });
  } catch (e) {
    $("#root").innerHTML = `<div class="app"><div class="screen"><h1>ShaadiGlow</h1><p>${esc(e.message)}</p></div></div>`;
    return;
  }
  render();
})();
