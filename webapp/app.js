// ==========================================================
// BILIG AI — Mini App frontend logikasi (vanilla JS, kutubxonasiz)
// ==========================================================

const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); }

const State = {
  me: null,
  role: null,
  activeChildId: null,   // "Bolaxona" rejimida tanlangan farzand ID
  activeChildName: null,
  currentTab: null,
  childrenCache: [],
};

// ---------------- API YORDAMCHISI ----------------
async function api(path, opts = {}) {
  const headers = { "X-Telegram-Init-Data": (tg && tg.initData) || "" };
  let url = path;

  if (!tg || !tg.initData) {
    // Telegram tashqarisida (oddiy brauzerda) sinash uchun DEV rejim
    let devId = localStorage.getItem("bilig_dev_id");
    if (!devId) {
      devId = prompt("DEV REJIM: test uchun Telegram user ID kiriting");
      if (devId) localStorage.setItem("bilig_dev_id", devId);
    }
    url += (path.includes("?") ? "&" : "?") + "dev_id=" + (devId || "0");
  }

  const fetchOpts = { method: opts.method || "GET", headers };
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

function haptic(type = "light") {
  if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(type);
}

function escapeHtml(s) {
  return (s || "").toString().replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function toast(msg, ms = 2600) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add("hidden"), ms);
}

// ---------------- EKRANLARNI ALMASHTIRISH ----------------
function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
  document.getElementById("app-shell").classList.add("hidden");
  if (id === "shell") {
    document.getElementById("app-shell").classList.remove("hidden");
  } else {
    document.getElementById(id).classList.remove("hidden");
  }
}

// ---------------- MODAL ----------------
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
document.getElementById("modal-overlay").addEventListener("click", e => {
  if (e.target.id === "modal-overlay") closeModal();
});

// ==========================================================
// BOSHLANG‘ICH YUKLASH (main.py dagi /start bilan bir xil vazifa)
// ==========================================================
async function boot() {
  try {
    const me = await api("/api/me");
    State.me = me;

    if (!me.exists || !me.approved) {
      showScreen("screen-closed");
      return;
    }

    if (!me.role) {
      showScreen("screen-role");
      return;
    }

    State.role = me.role;

    if (me.role === "child" && !me.linked_to_parent) {
      showScreen("screen-linkcode");
      return;
    }

    enterApp();
  } catch (e) {
    showScreen("screen-closed");
  }
}

document.querySelectorAll("[data-role]").forEach(btn => {
  btn.addEventListener("click", async () => {
    haptic();
    try {
      const res = await api("/api/register_role", { method: "POST", body: { role: btn.dataset.role } });
      State.role = res.role;
      if (res.role === "child") {
        showScreen("screen-linkcode");
      } else {
        toast(`Kodingiz: ${res.parent_code} — farzandingizga bering!`, 4000);
        enterApp();
      }
    } catch (e) {
      toast(e.error || "Xatolik yuz berdi");
    }
  });
});

document.getElementById("link-code-submit").addEventListener("click", async () => {
  const input = document.getElementById("link-code-input");
  const err = document.getElementById("link-code-error");
  err.textContent = "";
  try {
    await api("/api/link_parent", { method: "POST", body: { code: input.value.trim() } });
    toast("Tabriklaymiz! Ota-onangiz bilan bog‘landingiz 🎉");
    enterApp();
  } catch (e) {
    err.textContent = e.error || "Xatolik";
  }
});

// ==========================================================
// ILOVA QOBIG‘I (header + tabs)
// ==========================================================
async function enterApp() {
  showScreen("shell");
  await refreshHeader();
  setupTabsForRole();
}

async function refreshHeader() {
  const me = await api("/api/me");
  State.me = me;
  document.getElementById("header-avatar").textContent = me.role === "parent" ? "👨‍👩‍👦" : "🦸";
  document.getElementById("header-name").textContent = me.name || "Foydalanuvchi";
  document.getElementById("header-role").textContent = me.role === "parent" ? "Ota-ona kabineti" : "Qahramon";
  document.getElementById("header-coins").textContent = `🔅 ${me.coins ?? 0}`;
  document.getElementById("header-streak").textContent = `🔥 ${me.streak ?? 0}`;
}

const PARENT_TABS = [
  { id: "plans", label: "Rejalar", icon: "📚" },
  { id: "results", label: "Natijalar", icon: "📊" },
  { id: "store", label: "Do‘kon", icon: "🛒" },
  { id: "family", label: "Bolaxona", icon: "🧒" },
  { id: "contact", label: "Aloqa", icon: "📞" },
];
const CHILD_TABS = [
  { id: "read", label: "O‘qish", icon: "📖" },
  { id: "rewards", label: "Sovrinlar", icon: "🎁" },
  { id: "store", label: "Do‘kon", icon: "🛒" },
  { id: "rating", label: "Reyting", icon: "🏆" },
];

function setupTabsForRole() {
  const isChildView = State.role === "child" || State.activeChildId;
  const tabs = isChildView ? CHILD_TABS : PARENT_TABS;
  const nav = document.getElementById("app-tabs");
  nav.innerHTML = tabs.map(t => `
    <button class="tab-btn" data-action="open-tab" data-tab="${t.id}">
      <span class="tab-icon">${t.icon}</span><span>${t.label}</span>
    </button>`).join("");
  switchTab(tabs[0].id);

  const banner = document.getElementById("bolaxona-banner");
  if (State.activeChildId) {
    banner.classList.remove("hidden");
    document.getElementById("bolaxona-child-name").textContent = State.activeChildName || "";
  } else {
    banner.classList.add("hidden");
  }
}

function switchTab(tabId) {
  State.currentTab = tabId;
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tabId));
  const isChildView = State.role === "child" || State.activeChildId;
  const renderers = isChildView ? {
    read: renderChildRead, rewards: renderChildRewards, store: renderChildStore, rating: renderChildRating
  } : {
    plans: renderParentPlans, results: renderParentResults, store: renderParentStore,
    family: renderParentFamily, contact: renderParentContact
  };
  const fn = renderers[tabId];
  const main = document.getElementById("app-main");
  main.innerHTML = `<div class="empty-state"><div class="spinner"></div>Yuklanmoqda…</div>`;
  if (fn) fn().catch(e => { main.innerHTML = `<div class="empty-state">⚠️ ${e.error || "Xatolik yuz berdi"}</div>`; });
}

function asChildQuery() {
  return State.activeChildId ? `?as_child=${State.activeChildId}` : "";
}

// ==========================================================
// MARKAZIY KLIK BOSHQARUVCHISI (data-action)
// ==========================================================
document.addEventListener("click", async (e) => {
  const el = e.target.closest("[data-action]");
  if (!el) return;
  const a = el.dataset.action;
  haptic();

  try {
    switch (a) {
      case "open-tab": switchTab(el.dataset.tab); break;
      case "close-modal": closeModal(); break;

      // ---- Ota-ona: reja/kitob qo‘shish ustasi (wizard) ----
      case "open-add-plan": await Wizard.start(); break;
      case "wizard-pick-child": await Wizard.pickChild(Number(el.dataset.id)); break;
      case "wizard-pick-mode": await Wizard.pickMode(el.dataset.mode); break;
      case "wizard-continue-plan": await Wizard.continuePlan(); break;
      case "wizard-pick-method": await Wizard.pickMethod(el.dataset.method); break;
      case "wizard-pick-rec": await Wizard.addRecBook(Number(el.dataset.idx)); break;
      case "wizard-submit-text": await Wizard.submitTextBook(); break;
      case "wizard-add-more": await Wizard.pickMethod(null); break;
      case "wizard-finish": closeModal(); switchTab("plans"); break;

      // ---- Ota-ona: reja/kitob boshqaruvi ----
      case "delete-book":
        if (confirm("Kitobni o‘chirasizmi?")) {
          await api(`/api/parent/books/${el.dataset.id}`, { method: "DELETE" });
          toast("Kitob o‘chirildi");
          closeModal(); switchTab("plans");
        }
        break;
      case "open-generate-test": openGenerateTestModal(Number(el.dataset.id)); break;
      case "submit-generate-test": await submitGenerateTest(Number(el.dataset.id)); break;

      // ---- Ota-ona: natijalar ----
      case "select-result-child": renderParentResults(Number(el.dataset.id)); break;
      case "open-passport": await openPassportModal(Number(el.dataset.id)); break;
      case "adjust-coins": await adjustCoins(Number(el.dataset.id), Number(el.dataset.delta)); break;

      // ---- Ota-ona: do‘kon ----
      case "open-store-add": openStoreAddModal(); break;
      case "submit-store-add": await submitStoreAdd(); break;
      case "delete-store-item":
        await api(`/api/parent/store/${el.dataset.id}`, { method: "DELETE" });
        toast("Sovg‘a o‘chirildi"); switchTab("store");
        break;
      case "open-rate": openRateModal(); break;
      case "submit-rate": await submitRate(); break;

      // ---- Ota-ona: bolaxona ----
      case "enter-bolaxona":
        State.activeChildId = Number(el.dataset.id);
        State.activeChildName = el.dataset.name;
        setupTabsForRole();
        break;
      case "save-child-age": await saveChildAge(Number(el.dataset.id)); break;

      // ---- Ota-ona: aloqa ----
      case "submit-contact": await submitContact(); break;

      // ---- Bola: kitob o‘qish ----
      case "open-book": await openBookModal(Number(el.dataset.id)); break;
      case "open-page-photo": openPagePhotoModal(Number(el.dataset.id)); break;
      case "open-page-manual": openPageManualModal(Number(el.dataset.id)); break;
      case "submit-page-manual": await submitPageManual(Number(el.dataset.id)); break;
      case "open-voice": openVoiceModal(Number(el.dataset.id)); break;
      case "open-test": await openTestModal(Number(el.dataset.id), el.dataset.stage); break;
      case "select-test-opt": Test.select(el.dataset.qid, el.dataset.val); break;
      case "submit-test": await Test.submit(Number(el.dataset.book)); break;

      // ---- Bola: do‘kon ----
      case "buy-item": await buyItem(Number(el.dataset.id)); break;

      // ---- Bolaxona chiqish ----
      case "exit-bolaxona":
        State.activeChildId = null; State.activeChildName = null;
        setupTabsForRole();
        break;
    }
  } catch (err) {
    toast(err.error || err.message || "Xatolik yuz berdi");
  }
});

document.getElementById("bolaxona-exit").addEventListener("click", () => {
  State.activeChildId = null; State.activeChildName = null;
  setupTabsForRole();
});

// ==========================================================
// OTA-ONA: "📚 Faol rejalar" (+ kitob qo‘shish)
// ==========================================================
async function renderParentPlans() {
  const plans = await api("/api/parent/plans");
  const main = document.getElementById("app-main");

  let html = `<div class="section-title">📚 Mutolaa rejalari</div>
  <button class="btn btn-gold btn-block" data-action="open-add-plan">➕ Kitob / reja qo‘shish</button>`;

  if (!plans.length) {
    html += `<div class="empty-state"><div class="em-icon">📖</div>Hali faol reja yo‘q.<br>Yuqoridagi tugma orqali birinchi kitobni qo‘shing!</div>`;
  } else {
    plans.forEach(p => {
      html += `<div class="section-title" style="font-size:15px;margin-top:20px">🎯 ${escapeHtml(p.name)} ${p.prize ? `<span class="badge">🎁 ${escapeHtml(p.prize)}</span>` : ""}</div>`;
      p.books.forEach(b => {
        const pct = b.total_pages > 0 ? Math.min(100, Math.round((b.pages_read / b.total_pages) * 100)) : (b.pages_read > 0 ? 40 : 0);
        html += `
        <div class="card book-card">
          <div class="book-title">${escapeHtml(b.title)}</div>
          <div class="book-author">${escapeHtml(b.author || "")}</div>
          <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
          <div class="progress-label">${b.pages_read} ${b.total_pages ? "/ " + b.total_pages : ""} bet ${b.completed ? "· ✅ tugatilgan" : ""}</div>
          <div class="action-row">
            <button class="btn btn-outline" data-action="open-generate-test" data-id="${b.id}">🧠 AI test tuzish</button>
            <button class="btn btn-danger" data-action="delete-book" data-id="${b.id}">🗑 O‘chirish</button>
          </div>
        </div>`;
      });
    });
  }
  main.innerHTML = html;
}

function openGenerateTestModal(bookId) {
  openModal("🧠 AI Savollar banki", `
    <p class="section-sub">Kitobning 5–10 ta sahifasini rasmga oling. AI ular asosida test tuzadi.</p>
    <input type="file" id="test-photos-input" accept="image/*" multiple style="margin-bottom:12px" />
    <div id="test-photos-count" class="section-sub"></div>
    <button class="btn btn-gold btn-block" data-action="submit-generate-test" data-id="${bookId}">✅ Testni tuzish</button>
  `);
  document.getElementById("test-photos-input").addEventListener("change", (e) => {
    document.getElementById("test-photos-count").textContent = `${e.target.files.length} ta rasm tanlandi`;
  });
}
async function submitGenerateTest(bookId) {
  const input = document.getElementById("test-photos-input");
  if (!input.files.length) { toast("Kamida 1 ta rasm tanlang"); return; }
  const fd = new FormData();
  [...input.files].forEach(f => fd.append("photos", f));
  openModal("⏳ Ishlanmoqda…", `<div class="empty-state"><div class="spinner"></div>Gemini AI sahifalarni tahlil qilmoqda…</div>`);
  const res = await api(`/api/parent/books/${bookId}/generate_test`, { method: "POST", body: fd });
  closeModal();
  toast(`✅ ${res.count} ta savol tuzildi!`);
}

// ==========================================================
// OTA-ONA: "📊 Farzandim natijalari"
// ==========================================================
async function renderParentResults(childId) {
  const children = await api("/api/parent/children");
  State.childrenCache = children;
  if (!children.length) {
    document.getElementById("app-main").innerHTML = `<div class="empty-state"><div class="em-icon">👦</div>Hali farzand ulanmagan.</div>`;
    return;
  }
  const cid = childId || children[0].id;
  const results = await api(`/api/parent/results/${cid}`);

  let chips = children.map(c => `
    <button class="btn ${c.id === cid ? "btn-primary" : "btn-secondary"}" style="padding:8px 14px;font-size:13px"
      data-action="select-result-child" data-id="${c.id}">${escapeHtml(c.name)}</button>
  `).join(" ");

  let booksHtml = results.books.map(b => `
    <div class="list-row">
      <div>
        <div style="font-weight:700;font-size:13.5px">${escapeHtml(b.title)}</div>
        <div class="card-meta">${b.pages_read}${b.total_pages ? "/" + b.total_pages : ""} bet</div>
      </div>
      <span class="badge ${b.completed ? "done" : ""}">${b.completed ? "✅ Tugallandi" : "📖 Jarayonda"}</span>
    </div>`).join("") || `<div class="card-meta">Hali kitob yo‘q</div>`;

  document.getElementById("app-main").innerHTML = `
    <div class="section-title">📊 Farzandim natijalari</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">${chips}</div>
    <div class="card" style="text-align:center">
      <div style="font-family:'Fraunces',serif;font-weight:600;font-size:19px">${escapeHtml(results.name)}</div>
      <div class="card-meta">${escapeHtml(results.rank)}</div>
    </div>
    <div class="stat-grid">
      <div class="stat-box"><div class="num">${results.coins}</div><div class="lbl">🔅 Bilig</div></div>
      <div class="stat-box"><div class="num">${results.streak}</div><div class="lbl">🔥 Streak</div></div>
      <div class="stat-box"><div class="num">${results.total_pages}</div><div class="lbl">📖 Bet</div></div>
    </div>
    <button class="btn btn-secondary btn-block" data-action="open-passport" data-id="${cid}">📜 Oylik Kitobxon Pasporti</button>
    <div class="section-title" style="font-size:15px">Kitoblar</div>
    <div class="card">${booksHtml}</div>
    <div class="section-title" style="font-size:15px">Bilig balansini boshqarish</div>
    <div class="action-row">
      <button class="btn btn-outline" data-action="adjust-coins" data-id="${cid}" data-delta="5">+5 🔅</button>
      <button class="btn btn-outline" data-action="adjust-coins" data-id="${cid}" data-delta="-5">-5 🔅</button>
    </div>
  `;
}

async function openPassportModal(childId) {
  const p = await api(`/api/parent/passport/${childId}`);
  openModal("📜 Oylik Kitobxon Pasporti", `
    <div class="big-seal-row"><div class="big-seal"><div class="seal seal-lg">🔅</div>
      <div class="num">${p.coins}</div><div class="lbl">${escapeHtml(p.rank)}</div></div></div>
    <div class="stat-grid">
      <div class="stat-box"><div class="num">${p.completed_books}</div><div class="lbl">Tugatilgan kitob</div></div>
      <div class="stat-box"><div class="num">${p.total_pages}</div><div class="lbl">Jami bet</div></div>
      <div class="stat-box"><div class="num">${p.streak}</div><div class="lbl">🔥 Streak</div></div>
    </div>
    <div class="section-title" style="font-size:15px">🧠 Ko‘nikmalar diagnostikasi</div>
    ${diagRow("Faktik xotira", p.factual_bar)}
    ${diagRow("Sabab-oqibat mantiqi", p.logic_bar)}
    ${diagRow("Asar xulosasi", p.conclusion_bar)}
    ${diagRow("Nutq ravonligi", p.fluency_bar)}
    <div class="section-sub" style="margin-top:10px">🏅 Nishonlar: ${escapeHtml(p.badges)}</div>
  `);
}
function diagRow(label, bar) {
  return `<div class="diag-row"><div class="diag-label"><span>${label}</span></div><div class="card-meta" style="font-family:'JetBrains Mono',monospace">${bar}</div></div>`;
}
async function adjustCoins(childId, delta) {
  await api(`/api/parent/coins/${childId}`, { method: "POST", body: { delta } });
  toast(delta > 0 ? "🔅 Bilig qo‘shildi" : "🔅 Bilig ayirildi");
  renderParentResults(childId);
}

// ==========================================================
// OTA-ONA: "🛒 Do‘kon"
// ==========================================================
async function renderParentStore() {
  const items = await api("/api/parent/store");
  const list = items.map(i => `
    <div class="list-row">
      <div><div style="font-weight:700">${escapeHtml(i.name)}</div><div class="card-meta">🔅 ${i.price}</div></div>
      <button class="btn-icon" data-action="delete-store-item" data-id="${i.id}">🗑</button>
    </div>`).join("") || `<div class="card-meta">Hali sovg‘a qo‘shilmagan</div>`;

  document.getElementById("app-main").innerHTML = `
    <div class="section-title">🛒 Sovg‘alar do‘koni</div>
    <p class="section-sub">Farzandingiz Bilig tangalarini shu sovg‘alarga almashtiradi.</p>
    <div class="grid-2">
      <button class="btn btn-gold" data-action="open-store-add">➕ Sovg‘a</button>
      <button class="btn btn-secondary" data-action="open-rate">🔅 Bilig kursi</button>
    </div>
    <div class="card" style="margin-top:14px">${list}</div>
  `;
}
function openStoreAddModal() {
  openModal("➕ Yangi sovg‘a", `
    <label class="field-label">Sovg‘a nomi</label>
    <input id="store-name" class="text-input" placeholder="Masalan: 1 soat multfilm" />
    <label class="field-label">Narxi (🔅 Bilig)</label>
    <input id="store-price" type="number" class="text-input" placeholder="20" />
    <button class="btn btn-gold btn-block" data-action="submit-store-add">Saqlash</button>
  `);
}
async function submitStoreAdd() {
  const name = document.getElementById("store-name").value.trim();
  const price = Number(document.getElementById("store-price").value);
  if (!name || !price) { toast("Nomi va narxini kiriting"); return; }
  await api("/api/parent/store", { method: "POST", body: { name, price } });
  closeModal(); toast("Sovg‘a qo‘shildi"); switchTab("store");
}
function openRateModal() {
  openModal("🔅 Bilig kursi", `
    <p class="section-sub">1 Bilig necha so‘mga teng bo‘lishini belgilang (ixtiyoriy).</p>
    <input id="rate-input" type="number" class="text-input" placeholder="500" />
    <button class="btn btn-gold btn-block" data-action="submit-rate">Saqlash</button>
  `);
}
async function submitRate() {
  const rate = Number(document.getElementById("rate-input").value || 0);
  await api("/api/parent/rate", { method: "POST", body: { rate } });
  closeModal(); toast("Bilig kursi saqlandi");
}

// ==========================================================
// OTA-ONA: "🧒 Bolaxona"
// ==========================================================
async function renderParentFamily() {
  const children = await api("/api/parent/children");
  State.childrenCache = children;
  const parentCode = State.me.parent_code || "";

  let html = `<div class="section-title">🧒 Bolaxona</div>
  <p class="section-sub">Farzand kodi: <b>${parentCode}</b> — shu kodni farzandingizga bering.</p>`;

  if (!children.length) {
    html += `<div class="empty-state"><div class="em-icon">👦</div>Hali farzand ulanmagan.</div>`;
  } else {
    children.forEach(c => {
      html += `
      <div class="card">
        <div class="card-row">
          <div><div class="card-title">👦👧 ${escapeHtml(c.name)}</div><div class="card-meta">Yoshi: ${c.age}</div></div>
          <button class="btn btn-gold" style="padding:9px 14px;font-size:13px" data-action="enter-bolaxona" data-id="${c.id}" data-name="${escapeHtml(c.name)}">Kirish →</button>
        </div>
        <div class="action-row">
          <input type="number" class="text-input" style="margin:8px 0 0;padding:9px" id="age-input-${c.id}" placeholder="Yoshini kiriting" value="${c.age}" />
          <button class="btn btn-outline" style="margin-top:8px" data-action="save-child-age" data-id="${c.id}">Saqlash</button>
        </div>
      </div>`;
    });
  }
  document.getElementById("app-main").innerHTML = html;
}
async function saveChildAge(childId) {
  const age = Number(document.getElementById(`age-input-${childId}`).value);
  await api(`/api/parent/children/${childId}/age`, { method: "POST", body: { age } });
  toast("Yoshi saqlandi ✅");
}

// ==========================================================
// OTA-ONA: "📞 Qayta aloqa"
// ==========================================================
async function renderParentContact() {
  document.getElementById("app-main").innerHTML = `
    <div class="section-title">📞 Qayta aloqa</div>
    <p class="section-sub">Savol, taklif yoki muammoingizni yozing — administratorga yuboriladi.</p>
    <textarea id="contact-text" class="text-input" placeholder="Xabaringizni shu yerga yozing…"></textarea>
    <button class="btn btn-gold btn-block" data-action="submit-contact">Yuborish</button>
  `;
}
async function submitContact() {
  const text = document.getElementById("contact-text").value.trim();
  if (!text) { toast("Xabar bo‘sh bo‘lmasin"); return; }
  await api("/api/parent/contact", { method: "POST", body: { text } });
  toast("✅ Xabaringiz yuborildi!");
  document.getElementById("contact-text").value = "";
}

// ==========================================================
// BOLA: "📖 Kitob o‘qish"
// ==========================================================
async function renderChildRead() {
  const plans = await api(`/api/child/books${asChildQuery()}`);
  let html = `<div class="section-title">📖 Mening kitoblarim</div>`;

  const activeBooks = plans.flatMap(p => p.books.filter(b => !b.completed));
  if (!activeBooks.length) {
    html += `<div class="empty-state"><div class="em-icon">🦸</div>Senda hozircha o‘qilishi kerak bo‘lgan kitob yo‘q. 😊</div>`;
  } else {
    plans.forEach(p => {
      const books = p.books.filter(b => !b.completed);
      if (!books.length) return;
      html += `<div class="section-title" style="font-size:15px">🎯 ${escapeHtml(p.name)}</div>`;
      books.forEach(b => {
        const pct = b.total_pages > 0 ? Math.min(100, Math.round((b.pages_read / b.total_pages) * 100)) : 0;
        html += `
        <div class="card book-card" data-action="open-book" data-id="${b.id}" style="cursor:pointer">
          <div class="book-title">📘 ${escapeHtml(b.title)}</div>
          <div class="book-author">${escapeHtml(b.author || "")}</div>
          <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
          <div class="progress-label">${b.pages_read}${b.total_pages ? "/" + b.total_pages : ""} bet o‘qildi</div>
        </div>`;
      });
    });
  }
  document.getElementById("app-main").innerHTML = html;
}

async function openBookModal(bookId) {
  const b = await api(`/api/child/book/${bookId}`);
  openModal(`📘 ${b.title}`, `
    <p class="card-meta">${escapeHtml(b.author || "")}</p>
    <div class="progress-track"><div class="progress-fill" style="width:${b.total_pages ? Math.min(100, Math.round(b.pages_read/b.total_pages*100)) : 0}%"></div></div>
    <div class="progress-label">${b.pages_read}${b.total_pages ? "/" + b.total_pages : ""} bet</div>

    <div class="section-title" style="font-size:14px">O‘qishni belgilash</div>
    <div class="action-row">
      <button class="btn btn-gold" data-action="open-page-photo" data-id="${bookId}">📸 Sahifa rasmini yuborish</button>
      <button class="btn btn-outline" data-action="open-page-manual" data-id="${bookId}">✏️ Qo‘lda kiritish</button>
    </div>

    <div class="section-title" style="font-size:14px">Ovozli xulosa (bonus Bilig!)</div>
    <button class="btn btn-secondary btn-block" data-action="open-voice" data-id="${bookId}">🎙 Ovozli xulosa yuborish</button>

    ${b.has_test ? `
    <div class="section-title" style="font-size:14px">Bilim testlari</div>
    <div class="action-row">
      <button class="btn ${b.mid_test_1_done ? "btn-secondary" : "btn-outline"}" data-action="open-test" data-id="${bookId}" data-stage="mid_test_1">1-oraliq test ${b.mid_test_1_done ? "✅" : ""}</button>
      <button class="btn ${b.mid_test_2_done ? "btn-secondary" : "btn-outline"}" data-action="open-test" data-id="${bookId}" data-stage="mid_test_2">2-oraliq test ${b.mid_test_2_done ? "✅" : ""}</button>
      <button class="btn ${b.final_test_done ? "btn-secondary" : "btn-outline"}" data-action="open-test" data-id="${bookId}" data-stage="final_test">Yakuniy test ${b.final_test_done ? "✅" : ""}</button>
    </div>` : `<p class="section-sub">Bu kitob uchun test hali tuzilmagan.</p>`}
  `);
}

function openPagePhotoModal(bookId) {
  openModal("📸 Sahifa rasmi", `
    <p class="section-sub">O‘qib bo‘lgan sahifangizni ochiq holda, sahifa raqami ko‘rinadigan qilib suratga oling.</p>
    <div class="upload-zone" id="page-upload-zone">📷 Rasm tanlash uchun bosing</div>
    <input type="file" id="page-photo-input" accept="image/*" capture="environment" class="hidden" />
  `);
  const zone = document.getElementById("page-upload-zone");
  const input = document.getElementById("page-photo-input");
  zone.onclick = () => input.click();
  input.onchange = async () => {
    if (!input.files.length) return;
    zone.textContent = "⏳ AI sahifani tekshirmoqda…";
    zone.classList.add("has-file");
    const fd = new FormData();
    fd.append("photo", input.files[0]);
    try {
      const res = await api(`/api/child/book/${bookId}/page_photo${asChildQuery()}`, { method: "POST", body: fd });
      if (!res.ok) { toast(res.message || "Qaytadan urinib ko‘ring"); closeModal(); return; }
      showPageResult(res);
    } catch (e) { toast(e.error || "Xatolik"); closeModal(); }
  };
}

function openPageManualModal(bookId) {
  openModal("✏️ Sahifa raqami", `
    <label class="field-label">Qaysi sahifagacha o‘qidingiz?</label>
    <input id="manual-page-input" type="number" class="text-input" placeholder="Masalan: 45" />
    <button class="btn btn-gold btn-block" data-action="submit-page-manual" data-id="${bookId}">Yuborish</button>
  `);
}
async function submitPageManual(bookId) {
  const page = Number(document.getElementById("manual-page-input").value);
  if (!page) { toast("Sahifa raqamini kiriting"); return; }
  const res = await api(`/api/child/book/${bookId}/page_manual${asChildQuery()}`, { method: "POST", body: { page_number: page } });
  if (!res.ok) { toast(res.message); return; }
  showPageResult(res);
}
function showPageResult(res) {
  openModal("🎉 Ajoyib!", `
    <div class="big-seal-row"><div class="big-seal">
      <div class="seal seal-lg">🔅</div>
      <div class="num">+${res.earned_bilig}</div><div class="lbl">Bilig qo‘lga kiritdingiz!</div>
    </div></div>
    <div class="stat-grid">
      <div class="stat-box"><div class="num">${res.new_page}</div><div class="lbl">Sahifa</div></div>
      <div class="stat-box"><div class="num">${res.streak}</div><div class="lbl">🔥 Streak</div></div>
      <div class="stat-box"><div class="num">${res.balance}</div><div class="lbl">🔅 Balans</div></div>
    </div>
    ${res.shield_used ? `<p class="section-sub">🛡 Olov qalqoni ishlatildi — streak saqlanib qoldi!</p>` : ""}
    <button class="btn btn-primary btn-block" data-action="close-modal">Yopish</button>
  `);
  refreshHeader();
  if (State.currentTab === "read") renderChildRead();
}

// ---- Ovozli xulosa (mikrofon orqali yozib olish) ----
let mediaRecorder = null, audioChunks = [], recordSeconds = 0, recordTimer = null;

function openVoiceModal(bookId) {
  openModal("🎙 Ovozli xulosa", `
    <p class="section-sub">Kitob haqida 1-2 daqiqa gapirib bering: nima haqida edi, sizga nima yoqdi?</p>
    <div style="text-align:center;padding:16px 0">
      <button id="rec-btn" class="btn btn-gold" style="border-radius:50%;width:84px;height:84px;font-size:28px">🎙</button>
      <div id="rec-time" class="card-meta" style="margin-top:10px">Yozishni boshlash uchun bosing</div>
    </div>
    <div id="voice-actions" class="hidden">
      <button class="btn btn-primary btn-block" id="voice-send-btn">✅ Yuborish</button>
      <button class="btn btn-outline btn-block" id="voice-retry-btn">🔁 Qaytadan yozish</button>
    </div>
    <input type="file" id="voice-file-input" accept="audio/*" class="hidden" />
    <p class="section-sub" style="margin-top:10px">Mikrofon ishlamasa, <span style="text-decoration:underline;cursor:pointer" id="voice-upload-alt">audio fayl yuklang</span>.</p>
  `);

  let recordedBlob = null;
  const recBtn = document.getElementById("rec-btn");
  const timeEl = document.getElementById("rec-time");
  const actions = document.getElementById("voice-actions");

  recBtn.onclick = async () => {
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = []; recordSeconds = 0;
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = () => {
          recordedBlob = new Blob(audioChunks, { type: "audio/webm" });
          stream.getTracks().forEach(t => t.stop());
          actions.classList.remove("hidden");
          timeEl.textContent = "Yozib olindi ✅ Endi yuboring";
        };
        mediaRecorder.start();
        recBtn.textContent = "⏹";
        recordTimer = setInterval(() => { recordSeconds++; timeEl.textContent = `⏺ Yozilmoqda… ${recordSeconds}s`; }, 1000);
      } catch (e) {
        toast("Mikrofonga ruxsat berilmadi. Fayl yuklang.");
      }
    } else {
      mediaRecorder.stop();
      clearInterval(recordTimer);
      recBtn.textContent = "🎙";
    }
  };

  document.getElementById("voice-retry-btn").onclick = () => {
    recordedBlob = null; actions.classList.add("hidden"); timeEl.textContent = "Yozishni boshlash uchun bosing";
  };

  document.getElementById("voice-upload-alt").onclick = () => document.getElementById("voice-file-input").click();
  document.getElementById("voice-file-input").onchange = (e) => {
    if (e.target.files.length) { recordedBlob = e.target.files[0]; actions.classList.remove("hidden"); timeEl.textContent = "Fayl tanlandi ✅"; }
  };

  document.getElementById("voice-send-btn").onclick = async () => {
    if (!recordedBlob) { toast("Avval ovoz yozing yoki fayl tanlang"); return; }
    openModal("⏳ AI Ustoz tinglamoqda…", `<div class="empty-state"><div class="spinner"></div>Ovozli xulosangiz tahlil qilinmoqda…</div>`);
    const fd = new FormData();
    fd.append("audio", recordedBlob, "summary.webm");
    try {
      const res = await api(`/api/child/book/${bookId}/voice${asChildQuery()}`, { method: "POST", body: fd });
      openModal("🎉 AI Ustoz fikri", `
        <div class="big-seal-row"><div class="big-seal"><div class="seal seal-lg">🔅</div>
          <div class="num">+${res.bonus_bilig}</div><div class="lbl">bonus Bilig!</div></div></div>
        <div class="card">${escapeHtml(res.feedback)}</div>
        ${res.give_badge ? `<p class="section-sub">🏅 Yangi nishon qo‘lga kiritdingiz!</p>` : ""}
        <button class="btn btn-primary btn-block" data-action="close-modal">Ajoyib!</button>
      `);
      refreshHeader();
    } catch (e) { toast(e.error || "Xatolik yuz berdi"); closeModal(); }
  };
}

// ---- Test topshirish ----
const Test = {
  bookId: null, stage: null, questions: [], answers: {},
  select(qid, val) {
    this.answers[qid] = val;
    document.querySelectorAll(`[data-qid="${qid}"]`).forEach(b => b.classList.toggle("selected", b.dataset.val === val));
  },
  async submit(bookId) {
    const res = await api(`/api/child/book/${bookId}/test/submit${asChildQuery()}`, {
      method: "POST", body: { stage: this.stage, answers: this.answers }
    });
    openModal("📝 Natija", `
      <div class="big-seal-row"><div class="big-seal">
        <div class="seal seal-lg">${res.percent >= 60 ? "🏆" : "💪"}</div>
        <div class="num">${res.correct}/${res.total}</div><div class="lbl">${res.percent}% to‘g‘ri</div>
      </div></div>
      <p class="section-sub" style="text-align:center">+${res.earned_bilig} 🔅 Bilig qo‘lga kiritdingiz!</p>
      <button class="btn btn-primary btn-block" data-action="close-modal">Yopish</button>
    `);
    refreshHeader();
  }
};

async function openTestModal(bookId, stage) {
  const questions = await api(`/api/child/book/${bookId}/test${asChildQuery()}`);
  Test.bookId = bookId; Test.stage = stage; Test.questions = questions; Test.answers = {};

  const stageLabel = { mid_test_1: "1-oraliq test", mid_test_2: "2-oraliq test", final_test: "Yakuniy test" }[stage];
  let html = `<p class="section-sub">${questions.length} ta savol. Har biriga bittadan javob tanlang.</p>`;
  questions.forEach(q => {
    html += `<div class="card"><div class="card-title" style="margin-bottom:8px">${escapeHtml(q.question)}</div>`;
    (q.options || []).forEach(opt => {
      html += `<button class="option-btn" data-action="select-test-opt" data-qid="${q.id}" data-val="${escapeHtml(opt)}">${escapeHtml(opt)}</button>`;
    });
    html += `</div>`;
  });
  html += `<button class="btn btn-gold btn-block" data-action="submit-test" data-book="${bookId}">✅ Testni yakunlash</button>`;
  openModal(stageLabel, html);
}

// ==========================================================
// BOLA: "🎁 Sovrinlarim"
// ==========================================================
async function renderChildRewards() {
  const r = await api(`/api/child/rewards${asChildQuery()}`);
  const badges = r.badges.length ? r.badges.map(b => `<span class="badge done">🏅 ${escapeHtml(b)}</span>`).join(" ") : `<span class="card-meta">Hali nishonlar yo‘q — o‘qishda davom eting!</span>`;
  document.getElementById("app-main").innerHTML = `
    <div class="section-title">🎁 Sovrinlarim</div>
    <div class="big-seal-row"><div class="big-seal"><div class="seal seal-lg">🔅</div>
      <div class="num">${r.coins}</div><div class="lbl">Jami Bilig</div></div></div>
    <div class="stat-grid">
      <div class="stat-box"><div class="num">${r.streak}</div><div class="lbl">🔥 Streak</div></div>
      <div class="stat-box" style="grid-column:span 2"><div class="num" style="font-size:13px">${escapeHtml(r.rank)}</div><div class="lbl">Darajam</div></div>
    </div>
    <div class="section-title" style="font-size:15px">🏅 Nishonlarim</div>
    <div class="card">${badges}</div>
  `;
}

// ==========================================================
// BOLA: "🛒 Do‘kon"
// ==========================================================
async function renderChildStore() {
  const data = await api(`/api/child/store${asChildQuery()}`);
  const list = data.items.map(i => `
    <div class="list-row">
      <div><div style="font-weight:700">${escapeHtml(i.name)}</div><div class="card-meta">🔅 ${i.price}</div></div>
      <button class="btn ${i.affordable ? "btn-gold" : "btn-secondary"}" style="padding:8px 14px;font-size:12.5px" data-action="buy-item" data-id="${i.id}" ${i.affordable ? "" : "disabled"}>
        ${i.affordable ? "Sotib olish" : "Yetarli emas"}
      </button>
    </div>`).join("") || `<div class="card-meta">Ota-onangiz hali sovg‘a qo‘shmagan</div>`;

  document.getElementById("app-main").innerHTML = `
    <div class="section-title">🛒 Do‘kon</div>
    <div class="pill pill-gold" style="width:fit-content;margin-bottom:12px">🔅 Balans: ${data.balance}</div>
    <div class="card">${list}</div>
  `;
}
async function buyItem(itemId) {
  const res = await api(`/api/child/store/${itemId}/buy${asChildQuery()}`, { method: "POST" });
  if (!res.ok) { toast(res.message); return; }
  toast("🎉 Sovg‘a sotib olindi! Ota-onangizga xabar berildi.");
  refreshHeader(); renderChildStore();
}

// ==========================================================
// BOLA: "🏆 Reyting"
// ==========================================================
async function renderChildRating() {
  const data = await api(`/api/child/rating${asChildQuery()}`);
  const rows = data.list.map((r, i) => `
    <div class="list-row ${r.is_me ? "me-row" : ""}">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="rank-chip ${i === 0 ? "top1" : ""}">${i + 1}</div>
        <div><div style="font-weight:700;font-size:13.5px">${escapeHtml(r.name)}${r.is_me ? " (Siz)" : ""}</div><div class="card-meta">${escapeHtml(r.rank)}</div></div>
      </div>
      <div class="pill pill-leaf">${r.xp} XP</div>
    </div>`).join("");

  document.getElementById("app-main").innerHTML = `
    <div class="section-title">🏆 Reyting</div>
    <p class="section-sub">${data.scope === "oila" ? "Oilangiz o‘quvchilari orasida" : "Barcha o‘quvchilar orasida TOP-10"}</p>
    <div class="card">${rows || '<div class="card-meta">Reyting hali bo\'sh</div>'}</div>
  `;
}

// ==========================================================
// OTA-ONA: KITOB QO‘SHISH USTASI (Wizard)
// ==========================================================
const Wizard = {
  children: [], childId: null, childAge: 10, mode: "quick",
  planId: null, planName: "", prizeText: "", recBooks: [],

  async start() {
    const children = await api("/api/parent/children");
    if (!children.length) {
      openModal("⚠️ Diqqat", `<p>Sizga hali hech qaysi farzand ulanmagan. Farzandingiz kod orqali ulansin: <br><b>${State.me.parent_code}</b></p>`);
      return;
    }
    this.children = children;
    if (children.length === 1) {
      this.childId = children[0].id; this.childAge = children[0].age || 10;
      this.renderMode();
    } else {
      this.renderChildPick();
    }
  },
  renderChildPick() {
    const opts = this.children.map(c => `<button class="option-btn" data-action="wizard-pick-child" data-id="${c.id}">👦👧 ${escapeHtml(c.name)}</button>`).join("");
    openModal("Qaysi farzand uchun?", opts);
  },
  async pickChild(id) {
    this.childId = id; this.childAge = (this.children.find(c => c.id === id) || {}).age || 10;
    this.renderMode();
  },
  renderMode() {
    openModal("Reja turi", `
      <button class="option-btn" data-action="wizard-pick-mode" data-mode="quick">⚡️ Tezkor mutolaa (bitta kitob)</button>
      <button class="option-btn" data-action="wizard-pick-mode" data-mode="marathon">🎯 Mutolaa marafoni (bir nechta kitob)</button>
    `);
  },
  pickMode(mode) {
    this.mode = mode;
    openModal("Rejani nomlang", `
      <label class="field-label">Reja nomi</label>
      <input id="wiz-plan-name" class="text-input" placeholder="Masalan: Yozgi mutolaa" value="${mode === "quick" ? "Tezkor mutolaa" : "Mutolaa marafoni"}" />
      <label class="field-label">Marra sovrini (ixtiyoriy)</label>
      <input id="wiz-plan-prize" class="text-input" placeholder="Masalan: Velosiped" />
      <button class="btn btn-gold btn-block" data-action="wizard-continue-plan">Davom etish</button>
    `);
  },
  async continuePlan() {
    this.planName = document.getElementById("wiz-plan-name").value.trim() || "Mutolaa rejasi";
    this.prizeText = document.getElementById("wiz-plan-prize").value.trim();
    const res = await api("/api/parent/plans", { method: "POST", body: { child_id: this.childId, name: this.planName, prize: this.prizeText } });
    this.planId = res.plan_id;
    this.pickMethod(null);
  },
  pickMethod(method) {
    if (!method) {
      openModal("Kitobni qanday qo‘shamiz?", `
        <button class="option-btn" data-action="wizard-pick-method" data-method="rec">👶 Tavsiya etilgan kitoblardan</button>
        <button class="option-btn" data-action="wizard-pick-method" data-method="text">✍️ Nomini yozib qo‘shish</button>
        <button class="option-btn" data-action="wizard-pick-method" data-method="photo">📸 Muqovani rasmga olish</button>
      `);
      return;
    }
    this.showMethod(method);
  },
  async showMethod(method) {
    if (method === "rec") {
      const books = await api(`/api/parent/recommended_books?age=${this.childAge}`);
      this.recBooks = books;
      const opts = books.map((b, i) => `<button class="option-btn" data-action="wizard-pick-rec" data-idx="${i}">${escapeHtml(b)}</button>`).join("");
      openModal(`Tavsiyalar (${this.childAge} yosh)`, `<div style="max-height:60vh;overflow-y:auto">${opts || '<p class="card-meta">Tavsiya topilmadi</p>'}</div>`);
    } else if (method === "text") {
      openModal("✍️ Kitob nomi", `
        <label class="field-label">Kitob nomi (va muallif, ixtiyoriy)</label>
        <input id="wiz-book-text" class="text-input" placeholder="Masalan: Shum bola. G'.G‘ulom" />
        <label class="field-label">Jami sahifa soni (ixtiyoriy)</label>
        <input id="wiz-book-pages" type="number" class="text-input" placeholder="120" />
        <button class="btn btn-gold btn-block" data-action="wizard-submit-text">Qo‘shish</button>
      `);
    } else if (method === "photo") {
      openModal("📸 Muqova rasmi", `
        <div class="upload-zone" id="wiz-photo-zone">📷 Kitob muqovasini rasmga oling</div>
        <input type="file" id="wiz-photo-input" accept="image/*" capture="environment" class="hidden" />
      `);
      const zone = document.getElementById("wiz-photo-zone");
      const input = document.getElementById("wiz-photo-input");
      zone.onclick = () => input.click();
      input.onchange = async () => {
        if (!input.files.length) return;
        zone.textContent = "⏳ AI muqovani o‘qimoqda…";
        const fd = new FormData(); fd.append("photo", input.files[0]);
        const res = await api(`/api/parent/plans/${this.planId}/books/photo`, { method: "POST", body: fd });
        toast(`✅ "${res.title}" qo‘shildi!`);
        this.afterBookAdded();
      };
    }
  },
  async addRecBook(idx) {
    const text = this.recBooks[idx];
    const res = await api(`/api/parent/plans/${this.planId}/books`, { method: "POST", body: { text } });
    toast(`✅ "${res.title}" qo‘shildi!`);
    this.afterBookAdded();
  },
  async submitTextBook() {
    const text = document.getElementById("wiz-book-text").value.trim();
    const pages = Number(document.getElementById("wiz-book-pages").value || 0);
    if (!text) { toast("Kitob nomini kiriting"); return; }
    const res = await api(`/api/parent/plans/${this.planId}/books`, { method: "POST", body: { text, total_pages: pages } });
    toast(`✅ "${res.title}" qo‘shildi!`);
    this.afterBookAdded();
  },
  afterBookAdded() {
    if (this.mode === "marathon") {
      openModal("✅ Kitob qo‘shildi", `
        <button class="btn btn-gold btn-block" data-action="wizard-add-more">➕ Yana kitob qo‘shish</button>
        <button class="btn btn-primary btn-block" data-action="wizard-finish">✅ Marafonni yakunlash</button>
      `);
    } else {
      closeModal(); switchTab("plans");
    }
  }
};

// ---------------- ISHGA TUSHIRISH ----------------
boot();
