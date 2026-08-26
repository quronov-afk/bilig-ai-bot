// ==========================================================
// BILIG AI — Mini App frontend logikasi (vanilla JS)
// Yangi arxitektura: 4 ta doimiy tab — Bosh sahifa, Rejalar, Do‘kon, Reyting
// ==========================================================

const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); }

const State = {
  me: null,
  role: null,
  selectedChildId: null,   // Ota-ona tanlagan "faol farzand" konteksti (Bosh sahifa/Rejalar/Reyting uchun)
  activeChildId: null,     // "Bolaxona" rejimida to‘liq bola ekraniga o‘tilganda
  activeChildName: null,
  currentTab: "home",
  childrenCache: [],
  ratingMode: "global",
};

// ---------------- IKONALAR (Feather uslubi, emoji YO‘Q) ----------------
const ICON_PATHS = {
  home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  "book-open": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
  cart: '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>',
  award: '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  "plus-circle": '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
  camera: '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
  mic: '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  "chevron-right": '<polyline points="9 18 15 12 9 6"/>',
  "chevron-down": '<polyline points="6 9 12 15 18 9"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  flame: '<path d="M12 2c1 4-4 5-4 9a4 4 0 0 0 8 0c0-1-.5-2-1-3 1 0 2 1 2 3a5 5 0 0 1-10 0c0-5 5-6 5-9z"/>',
  coin: '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  "check-circle": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
  "arrow-right": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
  gift: '<polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>',
  "clipboard-list": '<path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="15" y2="16"/>',
  "volume-2": '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>',
  "message-circle": '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
  lock: '<rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
};
function icon(name, size, strokeWidth) {
  size = size || 20;
  strokeWidth = strokeWidth || 1.8;
  const paths = ICON_PATHS[name] || "";
  return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + strokeWidth + '" stroke-linecap="round" stroke-linejoin="round">' + paths + '</svg>';
}

// ---------------- API YORDAMCHISI ----------------
async function api(path, opts) {
  opts = opts || {};
  const headers = { "X-Telegram-Init-Data": (tg && tg.initData) || "" };
  let url = path;

  if (!tg || !tg.initData) {
    let devId = localStorage.getItem("bilig_dev_id");
    if (!devId) {
      devId = prompt("DEV REJIM: test uchun Telegram user ID kiriting");
      if (devId) localStorage.setItem("bilig_dev_id", devId);
    }
    url += (path.includes("?") ? "&" : "?") + "dev_id=" + (devId || "0");
  }

  const fetchOpts = { method: opts.method || "GET", headers: headers };
  if (opts.body instanceof FormData) {
    fetchOpts.body = opts.body;
  } else if (opts.body) {
    headers["Content-Type"] = "application/json";
    fetchOpts.body = JSON.stringify(opts.body);
  }

  const res = await fetch(url, fetchOpts);
  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) throw (data || { error: "Server xatoligi" });
  return data;
}

function haptic(type) { if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(type || "light"); }

function escapeHtml(s) {
  return (s || "").toString().replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}

function toast(msg, ms) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(function () { el.classList.add("hidden"); }, ms || 2600);
}

function showScreen(id) {
  document.querySelectorAll(".screen").forEach(function (s) { s.classList.add("hidden"); });
  document.getElementById("app-shell").classList.add("hidden");
  if (id === "shell") document.getElementById("app-shell").classList.remove("hidden");
  else document.getElementById(id).classList.remove("hidden");
}

function openModal(title, bodyHtml) {
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").innerHTML = bodyHtml;
  document.getElementById("modal-overlay").classList.remove("hidden");
}
function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
  document.getElementById("modal-body").innerHTML = "";
}
document.getElementById("modal-close").onclick = closeModal;
document.getElementById("modal-overlay").addEventListener("click", function (e) { if (e.target.id === "modal-overlay") closeModal(); });
document.getElementById("header-help-btn").addEventListener("click", openContactModal);

// ==========================================================
// BOSHLANG‘ICH YUKLASH
// ==========================================================
async function boot() {
  try {
    const me = await api("/api/me");
    State.me = me;
    if (!me.exists || !me.approved) { showScreen("screen-closed"); return; }
    if (!me.role) { showScreen("screen-role"); return; }
    State.role = me.role;
    if (me.role === "child" && !me.linked_to_parent) { showScreen("screen-linkcode"); return; }
    enterApp();
  } catch (e) { showScreen("screen-closed"); }
}

document.querySelectorAll("[data-role]").forEach(function (btn) {
  btn.addEventListener("click", async function () {
    haptic();
    try {
      const res = await api("/api/register_role", { method: "POST", body: { role: btn.dataset.role } });
      State.role = res.role;
      if (res.role === "child") showScreen("screen-linkcode");
      else { toast("Kodingiz: " + res.parent_code + " — farzandingizga bering", 4000); enterApp(); }
    } catch (e) { toast(e.error || "Xatolik yuz berdi"); }
  });
});

document.getElementById("link-code-submit").addEventListener("click", async function () {
  const input = document.getElementById("link-code-input");
  const err = document.getElementById("link-code-error");
  err.textContent = "";
  try {
    await api("/api/link_parent", { method: "POST", body: { code: input.value.trim() } });
    toast("Ota-onangiz bilan bog‘landingiz");
    enterApp();
  } catch (e) { err.textContent = e.error || "Xatolik"; }
});

// ==========================================================
// ILOVA QOBIG‘I
// ==========================================================
async function enterApp() {
  showScreen("shell");
  await refreshHeader();
  if (State.role === "parent") {
    try {
      const children = await api("/api/parent/children");
      State.childrenCache = children;
      if (children.length) State.selectedChildId = children[0].id;
    } catch (e) {}
  }
  setupTabsForRole();
}

async function refreshHeader() {
  const me = await api("/api/me");
  State.me = me;
  document.getElementById("header-avatar").textContent = (me.name || "?").charAt(0).toUpperCase();
  document.getElementById("header-name").textContent = me.name || "Foydalanuvchi";
  document.getElementById("header-role").textContent = me.role === "parent" ? "Ota-ona kabineti" : "O‘quvchi";
  document.getElementById("header-coins").innerHTML = icon("coin", 13, 2.2) + " " + (me.coins || 0);
  document.getElementById("header-streak").innerHTML = icon("flame", 13, 2.2) + " " + (me.streak || 0);
}

const TABS = [
  { id: "home", label: "Bosh sahifa", icon: "home" },
  { id: "plans", label: "Rejalar", icon: "book-open" },
  { id: "store", label: "Do‘kon", icon: "cart" },
  { id: "rating", label: "Reyting", icon: "award" },
];

function setupTabsForRole() {
  const nav = document.getElementById("app-tabs");
  nav.innerHTML = TABS.map(function (t) {
    return '<button class="tab-btn" data-action="open-tab" data-tab="' + t.id + '">' + icon(t.icon, 21, 1.7) + '<span>' + t.label + '</span></button>';
  }).join("");
  switchTab("home");

  const banner = document.getElementById("bolaxona-banner");
  if (State.activeChildId) {
    banner.classList.remove("hidden");
    document.getElementById("bolaxona-child-name").textContent = State.activeChildName || "";
  } else {
    banner.classList.add("hidden");
  }
}

function isChildView() { return State.role === "child" || !!State.activeChildId; }
function asChildQuery() {
  const cid = State.activeChildId || (State.role === "parent" ? State.selectedChildId : null);
  return cid ? "?as_child=" + cid : "";
}

function switchTab(tabId) {
  State.currentTab = tabId;
  document.querySelectorAll(".tab-btn").forEach(function (b) { b.classList.toggle("active", b.dataset.tab === tabId); });
  const renderers = isChildView()
    ? { home: renderChildHome, plans: renderChildPlans, store: renderStoreTab, rating: renderRatingTab }
    : { home: renderParentHome, plans: renderParentPlans, store: renderStoreTab, rating: renderRatingTab };
  const fn = renderers[tabId];
  const main = document.getElementById("app-main");
  main.innerHTML = '<div class="empty-state"><div class="spinner"></div>Yuklanmoqda…</div>';
  if (fn) fn().catch(function (e) { main.innerHTML = '<div class="empty-state">' + escapeHtml(e.error || "Xatolik yuz berdi") + '</div>'; });
}

// ==========================================================
// MARKAZIY KLIK BOSHQARUVCHISI
// ==========================================================
document.addEventListener("click", async function (e) {
  const el = e.target.closest("[data-action]");
  if (!el) return;
  const a = el.dataset.action;
  haptic();

  try {
    switch (a) {
      case "open-tab": switchTab(el.dataset.tab); break;
      case "close-modal": closeModal(); break;

      case "select-child": State.selectedChildId = Number(el.dataset.id); switchTab("home"); break;
      case "enter-bolaxona":
        State.activeChildId = Number(el.dataset.id);
        State.activeChildName = el.dataset.name;
        setupTabsForRole();
        break;
      case "exit-bolaxona":
        State.activeChildId = null; State.activeChildName = null;
        setupTabsForRole();
        break;

      case "open-add-plan": await Wizard.start(); break;
      case "wizard-pick-child": await Wizard.pickChild(Number(el.dataset.id)); break;
      case "wizard-pick-mode": await Wizard.pickMode(el.dataset.mode); break;
      case "wizard-continue-plan": await Wizard.continuePlan(); break;
      case "wizard-pick-method": await Wizard.pickMethod(el.dataset.method); break;
      case "wizard-pick-rec": await Wizard.addRecBook(Number(el.dataset.idx)); break;
      case "wizard-submit-text": await Wizard.submitTextBook(); break;
      case "wizard-add-more": await Wizard.pickMethod(null); break;
      case "wizard-finish": closeModal(); switchTab("plans"); break;

      case "delete-book":
        if (confirm("Kitobni o‘chirasizmi?")) {
          await api("/api/parent/books/" + el.dataset.id, { method: "DELETE" });
          toast("Kitob o‘chirildi"); closeModal(); switchTab("plans");
        }
        break;
      case "open-generate-test": openGenerateTestModal(Number(el.dataset.id)); break;
      case "submit-generate-test": await submitGenerateTest(Number(el.dataset.id)); break;

      case "adjust-coins": await adjustCoins(Number(el.dataset.id), Number(el.dataset.delta)); break;

      case "open-store-add": openStoreEditModal(null); break;
      case "open-store-edit": openStoreEditModal(el.dataset.id, el.dataset.name, el.dataset.price); break;
      case "submit-store-save": await submitStoreSave(el.dataset.id || null); break;
      case "delete-store-item":
        await api("/api/parent/store/" + el.dataset.id, { method: "DELETE" });
        toast("Mahsulot o‘chirildi"); closeModal(); switchTab("store");
        break;
      case "open-rate": openRateModal(); break;
      case "submit-rate": await submitRate(); break;

      case "save-child-age": await saveChildAge(Number(el.dataset.id)); break;

      case "open-contact": openContactModal(); break;
      case "submit-contact": await submitContact(); break;

      case "open-book": await openBookModal(Number(el.dataset.id)); break;
      case "open-page-photo": openPagePhotoModal(Number(el.dataset.id)); break;
      case "open-page-manual": openPageManualModal(Number(el.dataset.id)); break;
      case "submit-page-manual": await submitPageManual(Number(el.dataset.id)); break;
      case "open-voice": openVoiceModal(Number(el.dataset.id)); break;
      case "open-test": await openTestModal(Number(el.dataset.id), el.dataset.stage); break;
      case "select-test-opt": Test.select(el.dataset.qid, el.dataset.val); break;
      case "submit-test": await Test.submit(Number(el.dataset.book)); break;

      case "buy-item": await buyItem(Number(el.dataset.id)); break;

      case "set-rating-mode": State.ratingMode = el.dataset.mode; renderRatingTab(); break;
      case "go-plans-tab": switchTab("plans"); break;
    }
  } catch (err) {
    toast(err.error || err.message || "Xatolik yuz berdi");
  }
});

document.getElementById("bolaxona-exit").addEventListener("click", function () {
  State.activeChildId = null; State.activeChildName = null;
  setupTabsForRole();
});

// ==========================================================
// TAB 1: BOSH SAHIFA — OTA-ONA
// ==========================================================
async function renderParentHome() {
  const main = document.getElementById("app-main");
  if (!State.childrenCache.length) {
    main.innerHTML = emptyState("users", "Hali farzand ulanmagan", "Ota-ona kodi: <b>" + (State.me.parent_code || "") + "</b> — shu kodni farzandingizga yuboring.");
    return;
  }
  if (!State.selectedChildId) State.selectedChildId = State.childrenCache[0].id;
  const childId = State.selectedChildId;
  const data = await api("/api/parent/home/" + childId);

  let chips = State.childrenCache.map(function (c) {
    return '<button class="chip ' + (c.id === childId ? "active" : "") + '" data-action="select-child" data-id="' + c.id + '">' + escapeHtml(c.name) + '</button>';
  }).join("");
  chips += '<button class="chip" data-action="enter-bolaxona" data-id="' + childId + '" data-name="' + escapeHtml(data.name) + '">' + icon("users", 15, 2) + ' Bolaxona</button>';

  let html = '<div class="chip-row">' + chips + '</div>';

  html += '<div class="hero-card" data-action="open-add-plan">' +
    '<div class="icon-circle">' + icon("plus-circle", 22, 1.8) + '</div>' +
    '<p class="eyebrow">Yangi maqsad</p>' +
    '<p class="hc-title">Kitob qo‘shish</p>' +
    '<div style="display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600;">Tezkor yoki marafon rejasi yaratish ' + icon("arrow-right", 15, 2) + '</div>' +
    '</div>';

  html += '<div class="stat-grid">' +
    '<div class="stat-box"><div class="num">' + data.streak + '</div><div class="lbl">Ketma-ket kun</div></div>' +
    '<div class="stat-box"><div class="num">' + data.coins + '</div><div class="lbl">Bilig</div></div>' +
    '<div class="stat-box" style="font-size:11px"><div class="num" style="font-size:13px">' + escapeHtml(data.rank) + '</div><div class="lbl">Daraja</div></div>' +
    '</div>';

  if (data.current_book) {
    const b = data.current_book;
    const pct = b.total_pages ? Math.min(100, Math.round(b.pages_read / b.total_pages * 100)) : 0;
    html += '<p class="eyebrow">Jarayondagi kitob</p>' +
      '<div class="card" data-action="go-plans-tab" style="cursor:pointer">' +
      '<p class="book-title" style="margin-bottom:6px">' + escapeHtml(b.title) + '</p>' +
      '<div class="progress-track"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
      '<div class="progress-label">' + b.pages_read + (b.total_pages ? "/" + b.total_pages : "") + ' bet</div>' +
      '</div>';
  }

  if (data.last_report && (data.last_report.summary || data.last_report.conversation_topic)) {
    html += '<p class="eyebrow">AI Ustoz xulosasi</p>' +
      '<div class="card"><div style="display:flex;gap:10px;align-items:flex-start;">' +
      '<div style="color:var(--brand);flex-shrink:0;margin-top:2px">' + icon("message-circle", 20, 1.8) + '</div>' +
      '<div><p style="margin:0 0 8px;font-size:13.5px;line-height:1.5">' + escapeHtml(data.last_report.summary || "") + '</p>' +
      (data.last_report.conversation_topic ? '<p style="margin:0;font-size:12.5px;color:var(--text-soft)"><b>Kechki suhbat mavzusi:</b> ' + escapeHtml(data.last_report.conversation_topic) + '</p>' : "") +
      '</div></div></div>';
  }

  main.innerHTML = html;
}

// ==========================================================
// TAB 1: BOSH SAHIFA — BOLA
// ==========================================================
async function renderChildHome() {
  const data = await api("/api/child/home" + asChildQuery());
  let html = '<div class="stat-grid">' +
    '<div class="stat-box"><div class="num">' + data.coins + '</div><div class="lbl">Bilig</div></div>' +
    '<div class="stat-box"><div class="num">' + data.streak + '</div><div class="lbl">Ketma-ket kun</div></div>' +
    '<div class="stat-box" style="font-size:11px"><div class="num" style="font-size:13px">' + escapeHtml(data.rank) + '</div><div class="lbl">Daraja</div></div>' +
    '</div>';

  if (data.current_book) {
    const b = data.current_book;
    const pct = b.total_pages ? Math.min(100, Math.round(b.pages_read / b.total_pages * 100)) : 0;
    html += '<div class="hero-card" data-action="open-book" data-id="' + b.id + '">' +
      '<div class="icon-circle">' + icon("book-open", 22, 1.8) + '</div>' +
      '<p class="eyebrow">O‘qishda davom eting</p>' +
      '<p class="hc-title">' + escapeHtml(b.title) + '</p>' +
      '<div class="progress-track" style="background:rgba(255,255,255,.25)"><div class="progress-fill" style="width:' + pct + '%;background:#fff"></div></div>' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;font-size:12.5px;">' +
      '<span>' + b.pages_read + (b.total_pages ? "/" + b.total_pages : "") + ' bet</span>' +
      '<span style="display:flex;align-items:center;gap:4px;font-weight:700">Davom etish ' + icon("arrow-right", 15, 2) + '</span>' +
      '</div></div>';
  } else {
    html += '<div class="hero-card" data-action="go-plans-tab">' +
      '<div class="icon-circle">' + icon("book-open", 22, 1.8) + '</div>' +
      '<p class="hc-title">Hozircha o‘qiladigan kitob yo‘q</p>' +
      '<div style="font-size:13px;font-weight:600;display:flex;align-items:center;gap:6px">Rejalarni ko‘rish ' + icon("arrow-right", 15, 2) + '</div>' +
      '</div>';
  }

  if (data.last_badge) {
    html += '<div class="card" style="display:flex;align-items:center;gap:10px;">' +
      '<div style="color:var(--gold-deep)">' + icon("award", 22, 1.8) + '</div>' +
      '<div><p style="margin:0;font-size:13px;font-weight:700">Yangi nishon</p><p style="margin:0;font-size:12.5px;color:var(--text-soft)">' + escapeHtml(data.last_badge) + '</p></div></div>';
  }

  document.getElementById("app-main").innerHTML = html;
}

function emptyState(iconName, title, sub) {
  return '<div class="empty-state"><div class="em-icon">' + icon(iconName, 38, 1.4) + '</div><p style="font-weight:700;color:var(--text);margin:0 0 4px">' + title + '</p><p style="margin:0">' + (sub || "") + '</p></div>';
}

// ==========================================================
// TAB 2: REJALAR — OTA-ONA
// ==========================================================
async function renderParentPlans() {
  const plans = await api("/api/parent/plans");
  const main = document.getElementById("app-main");
  let html = '<button class="btn btn-primary btn-block" data-action="open-add-plan" style="display:flex;align-items:center;justify-content:center;gap:6px">' + icon("plus", 17, 2) + ' Yangi kitob qo‘shish</button>';

  const active = [];
  const completed = [];
  plans.forEach(function (p) {
    p.books.forEach(function (b) {
      const item = Object.assign({}, b, { planName: p.name, prize: p.prize });
      (b.completed ? completed : active).push(item);
    });
  });

  if (!active.length && !completed.length) {
    html += emptyState("book-open", "Hali faol reja yo‘q", "Yuqoridagi tugma orqali birinchi kitobni qo‘shing.");
  } else {
    if (active.length) {
      html += '<p class="section-title">Faol kitoblar</p>';
      active.forEach(function (b) { html += bookCardHtml(b, true); });
    }
    if (completed.length) {
      html += '<p class="section-title">Tugallangan</p>';
      completed.forEach(function (b) { html += bookCardHtml(b, true); });
    }
  }
  main.innerHTML = html;
}

function bookCardHtml(b, isParent) {
  const pct = b.total_pages > 0 ? Math.min(100, Math.round((b.pages_read / b.total_pages) * 100)) : (b.pages_read > 0 ? 30 : 0);
  let testBadges = "";
  if (b.mid_test_1_done !== undefined) {
    testBadges = '<div class="badge-row">' +
      '<span class="badge ' + (b.mid_test_1_done ? "done" : "pending") + '">1-oraliq test</span>' +
      '<span class="badge ' + (b.mid_test_2_done ? "done" : "pending") + '">2-oraliq test</span>' +
      '<span class="badge ' + (b.final_test_done ? "done" : "pending") + '">Yakuniy test</span>' +
      '<span class="badge ' + (b.has_voice ? "done" : "pending") + '">Ovozli tahlil</span>' +
      '</div>';
  }
  return '<div class="card book-card" ' + (isParent ? "" : 'data-action="open-book" data-id="' + b.id + '"') + '>' +
    '<div class="book-cover">' + icon("image", 22, 1.5) + '</div>' +
    '<div class="book-info">' +
    '<p class="book-title">' + escapeHtml(b.title) + '</p>' +
    '<p class="book-author">' + escapeHtml(b.author || "") + '</p>' +
    '<div class="progress-track"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
    '<div class="progress-label">' + b.pages_read + (b.total_pages ? "/" + b.total_pages : "") + ' bet</div>' +
    testBadges +
    (isParent ? '<div class="action-row">' +
      '<button class="btn btn-outline" data-action="open-generate-test" data-id="' + b.id + '">Test tuzish</button>' +
      '<button class="btn btn-danger" data-action="delete-book" data-id="' + b.id + '">' + icon("trash", 14, 2) + '</button>' +
      '</div>' : "") +
    '</div></div>';
}

function openGenerateTestModal(bookId) {
  openModal("AI savollar banki",
    '<p class="section-sub">Kitobning 5-10 ta sahifasini rasmga oling. AI ular asosida test tuzadi.</p>' +
    '<input type="file" id="test-photos-input" accept="image/*" multiple style="margin-bottom:12px" />' +
    '<div id="test-photos-count" class="section-sub"></div>' +
    '<button class="btn btn-primary btn-block" data-action="submit-generate-test" data-id="' + bookId + '">Testni tuzish</button>'
  );
  document.getElementById("test-photos-input").addEventListener("change", function (e) {
    document.getElementById("test-photos-count").textContent = e.target.files.length + " ta rasm tanlandi";
  });
}
async function submitGenerateTest(bookId) {
  const input = document.getElementById("test-photos-input");
  if (!input.files.length) { toast("Kamida 1 ta rasm tanlang"); return; }
  const fd = new FormData();
  Array.prototype.forEach.call(input.files, function (f) { fd.append("photos", f); });
  openModal("Ishlanmoqda", '<div class="empty-state"><div class="spinner"></div>Sahifalar tahlil qilinmoqda…</div>');
  const res = await api("/api/parent/books/" + bookId + "/generate_test", { method: "POST", body: fd });
  closeModal();
  toast(res.count + " ta savol tuzildi");
}

// ==========================================================
// TAB 2: REJALAR — BOLA
// ==========================================================
async function renderChildPlans() {
  const plans = await api("/api/child/books" + asChildQuery());
  let html = "";
  const activeBooks = [];
  const completedBooks = [];
  plans.forEach(function (p) {
    p.books.forEach(function (b) { (b.completed ? completedBooks : activeBooks).push(b); });
  });

  if (!activeBooks.length && !completedBooks.length) {
    html = emptyState("book-open", "Hozircha kitob yo‘q", "Ota-onangiz tez orada kitob qo‘shadi.");
  } else {
    if (activeBooks.length) {
      html += '<p class="section-title">O‘qilayotgan kitoblar</p>';
      activeBooks.forEach(function (b) { html += bookCardHtml(b, false); });
    }
    if (completedBooks.length) {
      html += '<p class="section-title">Tugallangan</p>';
      completedBooks.forEach(function (b) { html += bookCardHtml(b, false); });
    }
  }
  document.getElementById("app-main").innerHTML = html;
}

async function openBookModal(bookId) {
  const b = await api("/api/child/book/" + bookId + asChildQuery());
  const pct = b.total_pages ? Math.min(100, Math.round(b.pages_read / b.total_pages * 100)) : 0;
  let testsHtml;
  if (b.has_test) {
    testsHtml = '<p class="eyebrow" style="margin-top:18px">Bilim testlari</p><div class="action-row">' +
      '<button class="btn ' + (b.mid_test_1_done ? "btn-secondary" : "btn-outline") + '" data-action="open-test" data-id="' + bookId + '" data-stage="mid_test_1">1-oraliq ' + (b.mid_test_1_done ? "(bajarilgan)" : "") + '</button>' +
      '<button class="btn ' + (b.mid_test_2_done ? "btn-secondary" : "btn-outline") + '" data-action="open-test" data-id="' + bookId + '" data-stage="mid_test_2">2-oraliq ' + (b.mid_test_2_done ? "(bajarilgan)" : "") + '</button>' +
      '<button class="btn ' + (b.final_test_done ? "btn-secondary" : "btn-outline") + '" data-action="open-test" data-id="' + bookId + '" data-stage="final_test">Yakuniy ' + (b.final_test_done ? "(bajarilgan)" : "") + '</button>' +
      '</div>';
  } else {
    testsHtml = '<p class="section-sub" style="margin-top:18px">Bu kitob uchun test hali tuzilmagan.</p>';
  }
  openModal(b.title,
    '<p class="section-sub" style="margin-top:-4px">' + escapeHtml(b.author || "") + '</p>' +
    '<div class="progress-track"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
    '<div class="progress-label">' + b.pages_read + (b.total_pages ? "/" + b.total_pages : "") + ' bet</div>' +
    '<p class="eyebrow" style="margin-top:18px">O‘qishni belgilash</p>' +
    '<div class="action-row">' +
    '<button class="btn btn-primary" data-action="open-page-photo" data-id="' + bookId + '">' + icon("camera", 16, 2) + ' Sahifa rasmi</button>' +
    '<button class="btn btn-outline" data-action="open-page-manual" data-id="' + bookId + '">' + icon("edit", 16, 2) + ' Qo‘lda kiritish</button>' +
    '</div>' +
    '<p class="eyebrow" style="margin-top:18px">Ovozli xulosa</p>' +
    '<button class="btn btn-secondary btn-block" data-action="open-voice" data-id="' + bookId + '">' + icon("mic", 16, 2) + ' Ovozli xulosa yuborish ' + (b.has_voice ? "(qayta yuborish)" : "") + '</button>' +
    testsHtml
  );
}

function openPagePhotoModal(bookId) {
  openModal("Sahifa rasmi",
    '<p class="section-sub">O‘qib bo‘lgan sahifangizni, sahifa raqami ko‘rinadigan qilib suratga oling.</p>' +
    '<div class="upload-zone" id="page-upload-zone">' + icon("camera", 22, 1.6) + '<div style="margin-top:8px">Rasm tanlash uchun bosing</div></div>' +
    '<input type="file" id="page-photo-input" accept="image/*" capture="environment" class="hidden" />'
  );
  const zone = document.getElementById("page-upload-zone");
  const input = document.getElementById("page-photo-input");
  zone.onclick = function () { input.click(); };
  input.onchange = async function () {
    if (!input.files.length) return;
    zone.innerHTML = '<div class="spinner"></div>Tekshirilmoqda…';
    zone.classList.add("has-file");
    const fd = new FormData();
    fd.append("photo", input.files[0]);
    try {
      const res = await api("/api/child/book/" + bookId + "/page_photo" + asChildQuery(), { method: "POST", body: fd });
      if (!res.ok) { toast(res.message || "Qaytadan urinib ko‘ring"); closeModal(); return; }
      showPageResult(res);
    } catch (e) { toast(e.error || "Xatolik"); closeModal(); }
  };
}

function openPageManualModal(bookId) {
  openModal("Sahifa raqami",
    '<label class="field-label">Qaysi sahifagacha o‘qidingiz?</label>' +
    '<input id="manual-page-input" type="number" class="text-input" placeholder="Masalan: 45" />' +
    '<button class="btn btn-primary btn-block" data-action="submit-page-manual" data-id="' + bookId + '">Yuborish</button>'
  );
}
async function submitPageManual(bookId) {
  const page = Number(document.getElementById("manual-page-input").value);
  if (!page) { toast("Sahifa raqamini kiriting"); return; }
  const res = await api("/api/child/book/" + bookId + "/page_manual" + asChildQuery(), { method: "POST", body: { page_number: page } });
  if (!res.ok) { toast(res.message); return; }
  showPageResult(res);
}
function showPageResult(res) {
  openModal("Ajoyib natija",
    '<div class="stat-grid">' +
    '<div class="stat-box"><div class="num">+' + res.earned_bilig + '</div><div class="lbl">Bilig</div></div>' +
    '<div class="stat-box"><div class="num">' + res.new_page + '</div><div class="lbl">Sahifa</div></div>' +
    '<div class="stat-box"><div class="num">' + res.streak + '</div><div class="lbl">Ketma-ket kun</div></div>' +
    '</div>' +
    (res.shield_used ? '<p class="section-sub">Streak qalqoni ishlatildi — ketma-ketlik saqlanib qoldi.</p>' : "") +
    '<button class="btn btn-primary btn-block" data-action="close-modal">Yopish</button>'
  );
  refreshHeader();
  if (State.currentTab === "plans") renderChildPlans();
  if (State.currentTab === "home") renderChildHome();
}

let mediaRecorder = null, audioChunks = [], recordSeconds = 0, recordTimer = null;

function openVoiceModal(bookId) {
  openModal("Ovozli xulosa",
    '<p class="section-sub">Kitob haqida 1-2 daqiqa gapirib bering: nima haqida edi, sizga nima yoqdi?</p>' +
    '<div style="text-align:center;padding:16px 0">' +
    '<button id="rec-btn" class="icon-btn" style="width:76px;height:76px;border-radius:50%;background:var(--brand);color:#fff;margin:0 auto">' + icon("mic", 28, 1.7) + '</button>' +
    '<div id="rec-time" class="card-meta" style="margin-top:10px;color:var(--text-soft);font-size:13px">Yozishni boshlash uchun bosing</div>' +
    '</div>' +
    '<div id="voice-actions" class="hidden">' +
    '<button class="btn btn-primary btn-block" id="voice-send-btn">Yuborish</button>' +
    '<button class="btn btn-outline btn-block" id="voice-retry-btn">Qaytadan yozish</button>' +
    '</div>' +
    '<input type="file" id="voice-file-input" accept="audio/*" class="hidden" />' +
    '<p class="section-sub" style="margin-top:10px">Mikrofon ishlamasa, <span style="text-decoration:underline;cursor:pointer" id="voice-upload-alt">audio fayl yuklang</span>.</p>'
  );

  let recordedBlob = null;
  const recBtn = document.getElementById("rec-btn");
  const timeEl = document.getElementById("rec-time");
  const actions = document.getElementById("voice-actions");

  recBtn.onclick = async function () {
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = []; recordSeconds = 0;
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = function (e) { audioChunks.push(e.data); };
        mediaRecorder.onstop = function () {
          recordedBlob = new Blob(audioChunks, { type: "audio/webm" });
          stream.getTracks().forEach(function (t) { t.stop(); });
          actions.classList.remove("hidden");
          timeEl.textContent = "Yozib olindi — endi yuboring";
        };
        mediaRecorder.start();
        recBtn.innerHTML = icon("x", 26, 2);
        recordTimer = setInterval(function () { recordSeconds++; timeEl.textContent = "Yozilmoqda… " + recordSeconds + "s"; }, 1000);
      } catch (e) { toast("Mikrofonga ruxsat berilmadi. Fayl yuklang."); }
    } else {
      mediaRecorder.stop();
      clearInterval(recordTimer);
      recBtn.innerHTML = icon("mic", 28, 1.7);
    }
  };

  document.getElementById("voice-retry-btn").onclick = function () {
    recordedBlob = null; actions.classList.add("hidden"); timeEl.textContent = "Yozishni boshlash uchun bosing";
  };
  document.getElementById("voice-upload-alt").onclick = function () { document.getElementById("voice-file-input").click(); };
  document.getElementById("voice-file-input").onchange = function (e) {
    if (e.target.files.length) { recordedBlob = e.target.files[0]; actions.classList.remove("hidden"); timeEl.textContent = "Fayl tanlandi"; }
  };

  document.getElementById("voice-send-btn").onclick = async function () {
    if (!recordedBlob) { toast("Avval ovoz yozing yoki fayl tanlang"); return; }
    openModal("AI Ustoz tinglamoqda", '<div class="empty-state"><div class="spinner"></div>Ovozli xulosa tahlil qilinmoqda…</div>');
    const fd = new FormData();
    fd.append("audio", recordedBlob, "summary.webm");
    try {
      const res = await api("/api/child/book/" + bookId + "/voice" + asChildQuery(), { method: "POST", body: fd });
      openModal("AI Ustoz fikri",
        '<div class="stat-grid" style="grid-template-columns:1fr">' +
        '<div class="stat-box"><div class="num">+' + res.bonus_bilig + '</div><div class="lbl">bonus Bilig</div></div>' +
        '</div>' +
        '<div class="card">' + escapeHtml(res.feedback) + '</div>' +
        (res.give_badge ? '<p class="section-sub">Yangi nishon qo‘lga kiritdingiz.</p>' : "") +
        '<button class="btn btn-primary btn-block" data-action="close-modal">Ajoyib</button>'
      );
      refreshHeader();
    } catch (e) { toast(e.error || "Xatolik yuz berdi"); closeModal(); }
  };
}

const Test = {
  bookId: null, stage: null, questions: [], answers: {},
  select: function (qid, val) {
    this.answers[qid] = val;
    document.querySelectorAll('[data-qid="' + qid + '"]').forEach(function (b) { b.classList.toggle("selected", b.dataset.val === val); });
  },
  submit: async function (bookId) {
    const res = await api("/api/child/book/" + bookId + "/test/submit" + asChildQuery(), {
      method: "POST", body: { stage: this.stage, answers: this.answers }
    });
    openModal("Natija",
      '<div class="stat-grid">' +
      '<div class="stat-box"><div class="num">' + res.correct + '/' + res.total + '</div><div class="lbl">To‘g‘ri javob</div></div>' +
      '<div class="stat-box"><div class="num">' + res.percent + '%</div><div class="lbl">Natija</div></div>' +
      '<div class="stat-box"><div class="num">+' + res.earned_bilig + '</div><div class="lbl">Bilig</div></div>' +
      '</div>' +
      '<button class="btn btn-primary btn-block" data-action="close-modal">Yopish</button>'
    );
    refreshHeader();
  }
};

async function openTestModal(bookId, stage) {
  const questions = await api("/api/child/book/" + bookId + "/test" + asChildQuery());
  Test.bookId = bookId; Test.stage = stage; Test.questions = questions; Test.answers = {};
  const stageLabel = { mid_test_1: "1-oraliq test", mid_test_2: "2-oraliq test", final_test: "Yakuniy test" }[stage];
  let html = '<p class="section-sub">' + questions.length + ' ta savol. Har biriga bittadan javob tanlang.</p>';
  questions.forEach(function (q) {
    html += '<div class="card"><p style="font-weight:700;font-size:14px;margin:0 0 10px">' + escapeHtml(q.question) + '</p>';
    (q.options || []).forEach(function (opt) {
      html += '<button class="option-btn" data-action="select-test-opt" data-qid="' + q.id + '" data-val="' + escapeHtml(opt) + '">' + escapeHtml(opt) + '</button>';
    });
    html += '</div>';
  });
  html += '<button class="btn btn-primary btn-block" data-action="submit-test" data-book="' + bookId + '">Testni yakunlash</button>';
  openModal(stageLabel, html);
}

// ==========================================================
// TAB 3: DO‘KON (ota-ona ham, bola ham shu yerda)
// ==========================================================
async function renderStoreTab() {
  const main = document.getElementById("app-main");
  if (isChildView()) {
    const data = await api("/api/child/store" + asChildQuery());
    let html = '<div class="pill pill-gold" style="width:fit-content;margin-bottom:14px">' + icon("coin", 13, 2.2) + ' Balans: ' + data.balance + '</div>';
    if (!data.items.length) {
      html += emptyState("gift", "Hali sovg‘a yo‘q", "Ota-onangiz tez orada do‘konga mahsulot qo‘shadi.");
    } else {
      html += '<div class="store-grid">' + data.items.map(function (i) {
        return '<div class="store-item">' +
          '<div class="store-icon">' + icon("gift", 22, 1.6) + '</div>' +
          '<p class="store-name">' + escapeHtml(i.name) + '</p>' +
          '<p class="store-price">' + icon("coin", 13, 2.2) + ' ' + i.price + '</p>' +
          '<button class="btn ' + (i.affordable ? "btn-primary" : "btn-secondary") + ' btn-block" style="padding:8px;font-size:12.5px" data-action="buy-item" data-id="' + i.id + '" ' + (i.affordable ? "" : "disabled") + '>' +
          (i.affordable ? "Xarid qilish" : "Yetarli emas") + '</button></div>';
      }).join("") + '</div>';
    }
    main.innerHTML = html;
  } else {
    const items = await api("/api/parent/store");
    let html = '<div class="grid-2" style="margin-bottom:16px">' +
      '<button class="btn btn-primary" data-action="open-store-add" style="display:flex;align-items:center;justify-content:center;gap:6px">' + icon("plus", 16, 2) + ' Mahsulot</button>' +
      '<button class="btn btn-outline" data-action="open-rate">Bilig kursi</button></div>';
    if (!items.length) {
      html += emptyState("gift", "Hali mahsulot yo‘q", "Yuqoridagi tugma orqali birinchi sovg‘ani qo‘shing.");
    } else {
      html += '<div class="store-grid">' + items.map(function (i) {
        return '<div class="store-item" data-action="open-store-edit" data-id="' + i.id + '" data-name="' + escapeHtml(i.name) + '" data-price="' + i.price + '" style="cursor:pointer">' +
          '<div class="store-icon">' + icon("gift", 22, 1.6) + '</div>' +
          '<p class="store-name">' + escapeHtml(i.name) + '</p>' +
          '<p class="store-price">' + icon("coin", 13, 2.2) + ' ' + i.price + '</p>' +
          '<span class="badge">' + icon("edit", 12, 2) + ' Tahrirlash</span></div>';
      }).join("") + '</div>';
    }
    main.innerHTML = html;
  }
}

function openStoreEditModal(id, name, price) {
  const isEdit = !!id;
  openModal(isEdit ? "Mahsulotni tahrirlash" : "Yangi mahsulot",
    '<label class="field-label">Mahsulot nomi</label>' +
    '<input id="store-name" class="text-input" placeholder="Masalan: 1 soat multfilm" value="' + escapeHtml(name || "") + '" />' +
    '<label class="field-label">Narxi (Bilig)</label>' +
    '<input id="store-price" type="number" class="text-input" placeholder="20" value="' + (price || "") + '" />' +
    '<button class="btn btn-primary btn-block" data-action="submit-store-save" data-id="' + (id || "") + '">Saqlash</button>' +
    (isEdit ? '<button class="btn btn-danger btn-block" data-action="delete-store-item" data-id="' + id + '">' + icon("trash", 15, 2) + ' O‘chirish</button>' : "")
  );
}
async function submitStoreSave(id) {
  const name = document.getElementById("store-name").value.trim();
  const price = Number(document.getElementById("store-price").value);
  if (!name || !price) { toast("Nomi va narxini kiriting"); return; }
  if (id) { await api("/api/parent/store/" + id, { method: "DELETE" }); }
  await api("/api/parent/store", { method: "POST", body: { name: name, price: price } });
  closeModal(); toast("Saqlandi"); switchTab("store");
}
function openRateModal() {
  openModal("Bilig kursi",
    '<p class="section-sub">1 Bilig necha so‘mga teng bo‘lishini belgilang (ixtiyoriy).</p>' +
    '<input id="rate-input" type="number" class="text-input" placeholder="500" />' +
    '<button class="btn btn-primary btn-block" data-action="submit-rate">Saqlash</button>'
  );
}
async function submitRate() {
  const rate = Number(document.getElementById("rate-input").value || 0);
  await api("/api/parent/rate", { method: "POST", body: { rate: rate } });
  closeModal(); toast("Bilig kursi saqlandi");
}
async function buyItem(itemId) {
  const res = await api("/api/child/store/" + itemId + "/buy" + asChildQuery(), { method: "POST" });
  if (!res.ok) { toast(res.message); return; }
  toast("Sotib olindi — ota-onangizga xabar berildi");
  refreshHeader(); renderStoreTab();
}

// ==========================================================
// TAB 4: REYTING VA DIAGNOSTIKA
// ==========================================================
async function renderRatingTab() {
  const main = document.getElementById("app-main");
  main.innerHTML =
    '<div class="segmented">' +
    '<button class="' + (State.ratingMode === "global" ? "active" : "") + '" data-action="set-rating-mode" data-mode="global">Global reyting</button>' +
    '<button class="' + (State.ratingMode === "passport" ? "active" : "") + '" data-action="set-rating-mode" data-mode="passport">Shaxsiy pasport</button>' +
    '</div>' +
    '<div id="rating-content"><div class="empty-state"><div class="spinner"></div>Yuklanmoqda…</div></div>';
  const content = document.getElementById("rating-content");
  if (State.ratingMode === "global") {
    const data = await api("/api/child/rating" + asChildQuery());
    const rows = data.list.map(function (r, i) {
      return '<div class="list-row ' + (r.is_me ? "me-row" : "") + '">' +
        '<div style="display:flex;align-items:center;gap:10px;min-width:0">' +
        '<div class="rank-chip ' + (i === 0 ? "top1" : "") + '">' + (i + 1) + '</div>' +
        '<div style="min-width:0"><p style="margin:0;font-weight:700;font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + escapeHtml(r.name) + (r.is_me ? " (Siz)" : "") + '</p><p style="margin:0;font-size:11.5px;color:var(--text-faint)">' + escapeHtml(r.rank) + '</p></div>' +
        '</div><div class="pill pill-leaf">' + r.xp + ' XP</div></div>';
    }).join("");
    content.innerHTML = '<p class="section-sub">' + (data.scope === "oila" ? "Oilangiz o‘quvchilari orasida" : "Barcha o‘quvchilar orasida TOP-10") + '</p>' +
      '<div class="card">' + (rows || emptyState("award", "Reyting hali bo‘sh", "")) + '</div>';
  } else {
    const p = await api("/api/child/passport" + asChildQuery());
    content.innerHTML =
      '<div class="stat-grid">' +
      '<div class="stat-box"><div class="num">' + p.completed_books + '</div><div class="lbl">Tugallangan kitob</div></div>' +
      '<div class="stat-box"><div class="num">' + p.total_pages + '</div><div class="lbl">Jami bet</div></div>' +
      '<div class="stat-box"><div class="num">' + p.streak + '</div><div class="lbl">Ketma-ket kun</div></div>' +
      '</div>' +
      '<p class="eyebrow">Ko‘nikmalar diagnostikasi</p>' +
      '<div class="card">' +
      diagRow("Faktik xotira", p.factual_bar) +
      diagRow("Sabab-oqibat mantiqi", p.logic_bar) +
      diagRow("Asar xulosasi", p.conclusion_bar) +
      diagRow("Nutq ravonligi", p.fluency_bar) +
      '</div>' +
      '<p class="eyebrow">Nishonlar kolleksiyasi</p>' +
      '<div class="card">' + escapeHtml(p.badges || "Hali nishonlar yo‘q") + '</div>';
  }
}
function diagRow(label, bar) {
  return '<div class="diag-row"><div class="diag-label"><span>' + label + '</span><span>' + bar + '</span></div></div>';
}

// ==========================================================
// YORDAMCHI MODALLAR
// ==========================================================
async function adjustCoins(childId, delta) {
  await api("/api/parent/coins/" + childId, { method: "POST", body: { delta: delta } });
  toast(delta > 0 ? "Bilig qo‘shildi" : "Bilig ayirildi");
  renderParentHome();
}
async function saveChildAge(childId) {
  const age = Number(document.getElementById("age-input-" + childId).value);
  await api("/api/parent/children/" + childId + "/age", { method: "POST", body: { age: age } });
  toast("Yoshi saqlandi");
}
function openContactModal() {
  openModal("Yordam va aloqa",
    '<p class="section-sub">Savol, taklif yoki muammoingizni yozing — administratorga yuboriladi.</p>' +
    '<textarea id="contact-text" class="text-input" placeholder="Xabaringizni shu yerga yozing…"></textarea>' +
    '<button class="btn btn-primary btn-block" data-action="submit-contact">Yuborish</button>'
  );
}
async function submitContact() {
  const text = document.getElementById("contact-text").value.trim();
  if (!text) { toast("Xabar bo‘sh bo‘lmasin"); return; }
  await api("/api/parent/contact", { method: "POST", body: { text: text } });
  toast("Xabaringiz yuborildi");
  closeModal();
}

// ==========================================================
// OTA-ONA: KITOB QO‘SHISH USTASI (Wizard)
// ==========================================================
const Wizard = {
  children: [], childId: null, childAge: 10, mode: "quick",
  planId: null, planName: "", prizeText: "", recBooks: [],

  start: async function () {
    const children = State.childrenCache.length ? State.childrenCache : await api("/api/parent/children");
    if (!children.length) {
      openModal("Diqqat", "<p>Sizga hali hech qaysi farzand ulanmagan. Farzandingiz kod orqali ulansin: <br><b>" + State.me.parent_code + "</b></p>");
      return;
    }
    this.children = children;
    this.childId = State.selectedChildId || children[0].id;
    const found = children.filter(function (c) { return c.id === this.childId; }, this)[0];
    this.childAge = (found && found.age) || 10;
    this.renderMode();
  },
  renderMode: function () {
    openModal("Reja turi",
      '<button class="option-btn" data-action="wizard-pick-mode" data-mode="quick">' + icon("book-open", 18, 1.8) + ' Tezkor mutolaa (bitta kitob)</button>' +
      '<button class="option-btn" data-action="wizard-pick-mode" data-mode="marathon">' + icon("award", 18, 1.8) + ' Mutolaa marafoni (bir nechta kitob)</button>'
    );
  },
  pickMode: function (mode) {
    this.mode = mode;
    openModal("Rejani nomlang",
      '<label class="field-label">Reja nomi</label>' +
      '<input id="wiz-plan-name" class="text-input" placeholder="Masalan: Yozgi mutolaa" value="' + (mode === "quick" ? "Tezkor mutolaa" : "Mutolaa marafoni") + '" />' +
      '<label class="field-label">Marra sovrini (ixtiyoriy)</label>' +
      '<input id="wiz-plan-prize" class="text-input" placeholder="Masalan: Velosiped" />' +
      '<button class="btn btn-primary btn-block" data-action="wizard-continue-plan">Davom etish</button>'
    );
  },
  continuePlan: async function () {
    this.planName = document.getElementById("wiz-plan-name").value.trim() || "Mutolaa rejasi";
    this.prizeText = document.getElementById("wiz-plan-prize").value.trim();
    const res = await api("/api/parent/plans", { method: "POST", body: { child_id: this.childId, name: this.planName, prize: this.prizeText } });
    this.planId = res.plan_id;
    this.pickMethod(null);
  },
  pickMethod: function (method) {
    if (!method) {
      openModal("Kitobni qanday qo‘shamiz?",
        '<button class="option-btn" data-action="wizard-pick-method" data-method="rec">Tavsiya etilgan kitoblardan</button>' +
        '<button class="option-btn" data-action="wizard-pick-method" data-method="text">Nomini yozib qo‘shish</button>' +
        '<button class="option-btn" data-action="wizard-pick-method" data-method="photo">Muqovani rasmga olish</button>'
      );
      return;
    }
    this.showMethod(method);
  },
  showMethod: async function (method) {
    const self = this;
    if (method === "rec") {
      const books = await api("/api/parent/recommended_books?age=" + this.childAge);
      this.recBooks = books;
      const opts = books.map(function (b, i) {
        return '<button class="option-btn" data-action="wizard-pick-rec" data-idx="' + i + '">' + escapeHtml(b) + '</button>';
      }).join("");
      openModal("Tavsiyalar (" + this.childAge + " yosh)", '<div style="max-height:60vh;overflow-y:auto">' + (opts || '<p class="section-sub">Tavsiya topilmadi</p>') + '</div>');
    } else if (method === "text") {
      openModal("Kitob nomi",
        '<label class="field-label">Kitob nomi (va muallif, ixtiyoriy)</label>' +
        '<input id="wiz-book-text" class="text-input" placeholder="Masalan: Shum bola. G‘afur G‘ulom" />' +
        '<label class="field-label">Jami sahifa soni (ixtiyoriy)</label>' +
        '<input id="wiz-book-pages" type="number" class="text-input" placeholder="120" />' +
        '<button class="btn btn-primary btn-block" data-action="wizard-submit-text">Qo‘shish</button>'
      );
    } else if (method === "photo") {
      openModal("Muqova rasmi",
        '<div class="upload-zone" id="wiz-photo-zone">' + icon("camera", 22, 1.6) + '<div style="margin-top:8px">Kitob muqovasini rasmga oling</div></div>' +
        '<input type="file" id="wiz-photo-input" accept="image/*" capture="environment" class="hidden" />'
      );
      const zone = document.getElementById("wiz-photo-zone");
      const input = document.getElementById("wiz-photo-input");
      zone.onclick = function () { input.click(); };
      input.onchange = async function () {
        if (!input.files.length) return;
        zone.innerHTML = '<div class="spinner"></div>Tahlil qilinmoqda…';
        const fd = new FormData(); fd.append("photo", input.files[0]);
        const res = await api("/api/parent/plans/" + self.planId + "/books/photo", { method: "POST", body: fd });
        toast('"' + res.title + '" qo‘shildi');
        self.afterBookAdded();
      };
    }
  },
  addRecBook: async function (idx) {
    const text = this.recBooks[idx];
    const res = await api("/api/parent/plans/" + this.planId + "/books", { method: "POST", body: { text: text } });
    toast('"' + res.title + '" qo‘shildi');
    this.afterBookAdded();
  },
  submitTextBook: async function () {
    const text = document.getElementById("wiz-book-text").value.trim();
    const pages = Number(document.getElementById("wiz-book-pages").value || 0);
    if (!text) { toast("Kitob nomini kiriting"); return; }
    const res = await api("/api/parent/plans/" + this.planId + "/books", { method: "POST", body: { text: text, total_pages: pages } });
    toast('"' + res.title + '" qo‘shildi');
    this.afterBookAdded();
  },
  afterBookAdded: function () {
    if (this.mode === "marathon") {
      openModal("Kitob qo‘shildi",
        '<button class="btn btn-primary btn-block" data-action="wizard-add-more">Yana kitob qo‘shish</button>' +
        '<button class="btn btn-secondary btn-block" data-action="wizard-finish">Marafonni yakunlash</button>'
      );
    } else {
      closeModal(); switchTab("plans");
    }
  }
};

// ---------------- ISHGA TUSHIRISH ----------------
boot();
