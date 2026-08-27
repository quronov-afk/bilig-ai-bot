// ==========================================================
// BILIG AI — Mini App frontend logikasi (vanilla JS)
// Yangi arxitektura: 4 ta doimiy tab — Bosh sahifa, Rejalar, Do‘kon, Reyting
// ==========================================================

const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); }

// ==========================================================
// BEZAK YETIB KELDIMI — O‘ZINI TEKSHIRISH
// ----------------------------------------------------------
// Telefondagi Telegram ba'zan uslub faylini yuklay olmay qoladi
// (tarmoq uzilishi yoki eski nusxa keshda qolib ketishi sabab).
// Natijada ilova butunlay bezaksiz ochilardi: hamma ekran birdaniga
// ko‘rinib, harflar katta-katta bo‘lib ketardi.
// Endi ilova buni o‘zi sezadi va faylni yangi manzil bilan qayta so‘raydi.
// ==========================================================
function stylesheetLoaded() {
  const sheets = document.styleSheets;
  for (let i = 0; i < sheets.length; i++) {
    const href = sheets[i].href || "";
    if (href.indexOf("style.css") < 0) continue;
    try {
      // Fayl o‘rniga HTML kelgan bo‘lsa, qoidalar deyarli bo‘lmaydi
      if (sheets[i].cssRules && sheets[i].cssRules.length > 20) return true;
    } catch (e) {
      return true;      // boshqa manbadan kelgan — o‘qib bo‘lmaydi, lekin yuklangan
    }
  }
  return false;
}

// Bezak tayyor — ilovani ko‘rsatamiz, yuklanish ekranini olib tashlaymiz.
function revealApp() {
  document.documentElement.classList.add("css-ok");
}

// Har urinish orasida tobora uzoqroq kutamiz. Mobil tarmoq uzuq-yuluq
// bo‘lganda birinchi urinish yiqilib, keyingisi o‘tib ketishi mumkin —
// shuning uchun darrov taslim bo‘lmaymiz.
const STYLE_RETRY_MS = [600, 1500, 3000];

function ensureStylesLoaded(attempt) {
  attempt = attempt || 0;
  if (stylesheetLoaded()) { revealApp(); return; }
  if (attempt >= STYLE_RETRY_MS.length) {
    // Bezakni umuman keltira olmadik. Ilovani baribir ochamiz — chala
    // ko‘rinishda bo‘lsa ham, umuman ochilmagandan yaxshiroq.
    revealApp();
    return;
  }
  const fresh = document.createElement("link");
  fresh.rel = "stylesheet";
  fresh.href = "style.css?v=" + ASSET_V + "&r=" + Date.now();
  const again = function () {
    setTimeout(function () { ensureStylesLoaded(attempt + 1); }, STYLE_RETRY_MS[attempt]);
  };
  fresh.onload = function () { setTimeout(function () { ensureStylesLoaded(attempt + 1); }, 150); };
  fresh.onerror = again;
  document.head.appendChild(fresh);
}

// Bezak allaqachon kelgan bo‘lsa — darrov ochamiz (kutib o‘tirmaymiz).
if (stylesheetLoaded()) revealApp();
// Kelmagan bo‘lsa, hamma narsa yuklangach qayta so‘rab ko‘ramiz.
window.addEventListener("load", function () { ensureStylesLoaded(0); });
// Xavfsizlik: 8 soniyadan keyin baribir ko‘rsatamiz. Bezaksiz bo‘lsa ham,
// ilova umuman ochilmay qolgandan ko‘ra shunisi yaxshiroq.
setTimeout(revealApp, 8000);

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
  // --- Sof chiziqli (to‘ldirishsiz) ---
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  "chevron-right": '<polyline points="9 18 15 12 9 6"/>',
  "chevron-down": '<polyline points="6 9 12 15 18 9"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  "arrow-right": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  clock: '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',

  // --- Duotone: [ichki to‘ldirish, ustki chiziq] ---
  home: [
    '<path d="M3.8 10.3 12 3.6l8.2 6.7v8.9a2 2 0 0 1-2 2H5.8a2 2 0 0 1-2-2z"/>',
    '<path d="M3.8 10.3 12 3.6l8.2 6.7v8.9a2 2 0 0 1-2 2H5.8a2 2 0 0 1-2-2z"/><path d="M9.4 21.2v-5.6a2.6 2.6 0 0 1 5.2 0v5.6"/>'],
  "book-open": [
    '<path d="M12 6.6C10.4 5.1 8.4 4.4 4.9 4.4H3.4v13.1h1.5c3.5 0 5.5.7 7.1 2.2 1.6-1.5 3.6-2.2 7.1-2.2h1.5V4.4h-1.5c-3.5 0-5.5.7-7.1 2.2z"/>',
    '<path d="M12 6.6C10.4 5.1 8.4 4.4 4.9 4.4H3.4v13.1h1.5c3.5 0 5.5.7 7.1 2.2 1.6-1.5 3.6-2.2 7.1-2.2h1.5V4.4h-1.5c-3.5 0-5.5.7-7.1 2.2z"/><path d="M12 6.6v13.1"/>'],
  cart: [
    '<path d="M6.6 7.4h14.1l-1.85 7.6a2.2 2.2 0 0 1-2.14 1.68H9.6a2.2 2.2 0 0 1-2.14-1.68z"/>',
    '<path d="M6.6 7.4h14.1l-1.85 7.6a2.2 2.2 0 0 1-2.14 1.68H9.6a2.2 2.2 0 0 1-2.14-1.68z"/><path d="M2.6 3.2h1.9a1 1 0 0 1 .97.76L6.6 7.4"/><circle cx="10.2" cy="20.2" r="1.5"/><circle cx="17" cy="20.2" r="1.5"/>'],
  award: [
    '<circle cx="12" cy="14.6" r="6.2"/>',
    '<circle cx="12" cy="14.6" r="6.2"/><path d="M8.4 9.2 6.2 2.8h11.6l-2.2 6.4"/><path d="M12 11.9l1.05 2.13 2.35.34-1.7 1.66.4 2.34L12 17.26l-2.1 1.11.4-2.34-1.7-1.66 2.35-.34z"/>'],
  "plus-circle": [
    '<circle cx="12" cy="12" r="8.8"/>',
    '<circle cx="12" cy="12" r="8.8"/><path d="M12 8.3v7.4"/><path d="M8.3 12h7.4"/>'],
  camera: [
    '<path d="M2.8 8.6h4.1l1.9-2.9h6.4l1.9 2.9h4.1v10.2a2 2 0 0 1-2 2H4.8a2 2 0 0 1-2-2z"/>',
    '<path d="M2.8 8.6h4.1l1.9-2.9h6.4l1.9 2.9h4.1v10.2a2 2 0 0 1-2 2H4.8a2 2 0 0 1-2-2z"/><circle cx="12" cy="13.7" r="3.7"/>'],
  mic: [
    '<rect x="9.5" y="2.3" width="5" height="10.4" rx="2.5"/>',
    '<rect x="9.5" y="2.3" width="5" height="10.4" rx="2.5"/><path d="M5.9 10.9v1.1a6.1 6.1 0 0 0 12.2 0v-1.1"/><path d="M12 18.1v3.4"/><path d="M8.7 21.5h6.6"/>'],
  edit: [
    '<path d="M13.6 4.9 19.1 10.4 9.9 19.6l-5.5.9.9-5.5z"/>',
    '<path d="M13.6 4.9a2.2 2.2 0 0 1 3.1 0l2.4 2.4a2.2 2.2 0 0 1 0 3.1L9.9 19.6l-5.5.9.9-5.5z"/><path d="M12.4 6.1 17.9 11.6"/>'],
  trash: [
    '<path d="M5.6 7.4h12.8l-.92 12a2 2 0 0 1-2 1.85H8.52a2 2 0 0 1-2-1.85z"/>',
    '<path d="M5.6 7.4h12.8l-.92 12a2 2 0 0 1-2 1.85H8.52a2 2 0 0 1-2-1.85z"/><path d="M3.4 7.4h17.2"/><path d="M9.3 7.4V5.9a1.7 1.7 0 0 1 1.7-1.7h2a1.7 1.7 0 0 1 1.7 1.7v1.5"/><path d="M10.4 11.6v5.4"/><path d="M13.6 11.6v5.4"/>'],
  help: [
    '<circle cx="12" cy="12" r="8.8"/>',
    '<circle cx="12" cy="12" r="8.8"/><path d="M9.6 9.6a2.5 2.5 0 1 1 3.3 2.4c-.6.2-.9.8-.9 1.4v.4"/><path d="M12 17.2h.01"/>'],
  flame: [
    '<path d="M12 21.2a5.6 5.6 0 0 0 5.6-5.6c0-4.3-3.4-6.1-4.4-12.8-2.1 2.4-3.3 4.6-3.3 6.6 0 1.1.3 1.9.7 2.7-1.1-.4-1.9-1.2-2.4-2.2-1.2 1.6-1.8 3.4-1.8 5.7a5.6 5.6 0 0 0 5.6 5.6z"/>',
    '<path d="M12 21.2a5.6 5.6 0 0 0 5.6-5.6c0-4.3-3.4-6.1-4.4-12.8-2.1 2.4-3.3 4.6-3.3 6.6 0 1.1.3 1.9.7 2.7-1.1-.4-1.9-1.2-2.4-2.2-1.2 1.6-1.8 3.4-1.8 5.7a5.6 5.6 0 0 0 5.6 5.6z"/><path d="M12 21.2a2.7 2.7 0 0 0 2.7-2.7c0-1.6-1.3-2.5-2.7-4.4-1.4 1.9-2.7 2.8-2.7 4.4a2.7 2.7 0 0 0 2.7 2.7z"/>'],
  coin: [
    '<circle cx="12" cy="12" r="8.6"/>',
    '<circle cx="12" cy="12" r="8.6"/><path d="M10.1 7.7v8.6"/><path d="M10.1 7.7h3.15a2.15 2.15 0 0 1 0 4.3H10.1"/><path d="M10.1 12h3.5a2.15 2.15 0 0 1 0 4.3H10.1"/>'],
  users: [
    '<circle cx="8.6" cy="8" r="3.6"/>',
    '<circle cx="8.6" cy="8" r="3.6"/><path d="M2.8 19.8a5.8 5.8 0 0 1 11.6 0"/><circle cx="17.6" cy="9.6" r="2.6"/><path d="M17.4 14.8a4.6 4.6 0 0 1 3.8 4.5"/>'],
  "check-circle": [
    '<circle cx="12" cy="12" r="8.8"/>',
    '<circle cx="12" cy="12" r="8.8"/><path d="M8.2 12.2l2.6 2.6 5-5.2"/>'],
  gift: [
    '<path d="M3.6 10.6h16.8v9a2 2 0 0 1-2 2H5.6a2 2 0 0 1-2-2z"/>',
    '<path d="M3.6 10.6h16.8v9a2 2 0 0 1-2 2H5.6a2 2 0 0 1-2-2z"/><rect x="2.6" y="6.6" width="18.8" height="4" rx="1.4"/><path d="M12 6.6v15"/><path d="M12 6.6S11 2.4 8.4 2.4a2.1 2.1 0 0 0 0 4.2z"/><path d="M12 6.6s1-4.2 3.6-4.2a2.1 2.1 0 0 1 0 4.2z"/>'],
  // Kubok — reyting
  "trophy": [
    '<path d="M7 4h10v5a5 5 0 0 1-10 0z"/>',
    '<path d="M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4.6v1.4A3.4 3.4 0 0 0 8 10.8"/><path d="M17 6h2.4v1.4A3.4 3.4 0 0 1 16 10.8"/><path d="M12 14v3.4"/><path d="M8.4 20.5h7.2"/><path d="M9.8 20.5c.2-1.9.9-3.1 2.2-3.1s2 1.2 2.2 3.1"/>'],
  // Ustunli diagramma — shaxsiy natija
  "chart": [
    '<rect x="4" y="12.5" width="3.6" height="7.2" rx="1.3"/><rect x="10.2" y="8" width="3.6" height="11.7" rx="1.3"/><rect x="16.4" y="4.6" width="3.6" height="15.1" rx="1.3"/>',
    '<rect x="4" y="12.5" width="3.6" height="7.2" rx="1.3"/><rect x="10.2" y="8" width="3.6" height="11.7" rx="1.3"/><rect x="16.4" y="4.6" width="3.6" height="15.1" rx="1.3"/>'],
  // Qidiruv
  "search": [
    '<circle cx="10.8" cy="10.8" r="7"/>',
    '<circle cx="10.8" cy="10.8" r="7"/><path d="M16 16l4.4 4.4"/>'],
  // Nusxalash — ikkita ustma-ust yumaloq burchakli varaq
  "copy": [
    '<rect x="8.6" y="8.6" width="12" height="12" rx="3"/>',
    '<rect x="8.6" y="8.6" width="12" height="12" rx="3"/><path d="M15.4 5.6a2.6 2.6 0 0 0-2.2-2.2H6.6a3 3 0 0 0-3 3v6.6a2.6 2.6 0 0 0 2.2 2.2"/>'],
  "clipboard-list": [
    '<rect x="4.4" y="4.7" width="15.2" height="16.6" rx="2.5"/>',
    '<rect x="4.4" y="4.7" width="15.2" height="16.6" rx="2.5"/><rect x="8.6" y="2.5" width="6.8" height="4.2" rx="1.5"/><path d="M8.7 12.1h6.6"/><path d="M8.7 16.3h4.4"/>'],
  "message-circle": [
    '<path d="M12 3.4c-4.85 0-8.8 3.35-8.8 7.5 0 2.35 1.28 4.45 3.27 5.82L5.4 21.1l4.66-2.2c.63.1 1.27.15 1.94.15 4.85 0 8.8-3.35 8.8-7.5S16.85 3.4 12 3.4z"/>',
    '<path d="M12 3.4c-4.85 0-8.8 3.35-8.8 7.5 0 2.35 1.28 4.45 3.27 5.82L5.4 21.1l4.66-2.2c.63.1 1.27.15 1.94.15 4.85 0 8.8-3.35 8.8-7.5S16.85 3.4 12 3.4z"/>'],
  image: [
    '<rect x="3.2" y="4.2" width="17.6" height="15.6" rx="2.6"/>',
    '<rect x="3.2" y="4.2" width="17.6" height="15.6" rx="2.6"/><circle cx="8.6" cy="9.4" r="1.8"/><path d="M3.4 16.6l4.3-4.1a2 2 0 0 1 2.7-.05l4.2 3.8"/><path d="M13.4 14.6l2.2-2a2 2 0 0 1 2.7.03l2.4 2.2"/>'],
  lock: [
    '<rect x="4.3" y="10.3" width="15.4" height="10.6" rx="2.5"/>',
    '<rect x="4.3" y="10.3" width="15.4" height="10.6" rx="2.5"/><path d="M7.9 10.3V7.7a4.1 4.1 0 0 1 8.2 0v2.6"/><path d="M12 14.4v2.5"/>'],
  user: [
    '<circle cx="12" cy="7.9" r="3.9"/>',
    '<circle cx="12" cy="7.9" r="3.9"/><path d="M4.4 20.6a7.6 7.6 0 0 1 15.2 0"/>'],
  shield: [
    '<path d="M12 2.7 19.5 5.5v6.1c0 4.5-3.05 8.05-7.5 9.55-4.45-1.5-7.5-5.05-7.5-9.55V5.5z"/>',
    '<path d="M12 2.7 19.5 5.5v6.1c0 4.5-3.05 8.05-7.5 9.55-4.45-1.5-7.5-5.05-7.5-9.55V5.5z"/><path d="M9.1 11.8l2.15 2.15 3.95-4.1"/>'],
  star: [
    '<path d="M12 2.9c.35 0 .67.2.83.52l2.42 4.9 5.41.79c.75.11 1.05 1.03.5 1.56l-3.91 3.81.92 5.39c.13.75-.65 1.32-1.32.96L12 18.29l-4.85 2.55c-.67.36-1.45-.21-1.32-.96l.92-5.39-3.91-3.81c-.55-.53-.25-1.45.5-1.56l5.41-.79 2.42-4.9c.16-.32.48-.52.83-.52z"/>',
    '<path d="M12 2.9c.35 0 .67.2.83.52l2.42 4.9 5.41.79c.75.11 1.05 1.03.5 1.56l-3.91 3.81.92 5.39c.13.75-.65 1.32-1.32.96L12 18.29l-4.85 2.55c-.67.36-1.45-.21-1.32-.96l.92-5.39-3.91-3.81c-.55-.53-.25-1.45.5-1.56l5.41-.79 2.42-4.9c.16-.32.48-.52.83-.52z"/>'],
};

// Kitob qo‘shish kartochkasi bezagi — o‘qiyotgan boyo‘g‘li maskoti
const HERO_MASCOT = '<img class="hero-mascot" src="/mascots/mascot-boyogli-oqish-cutout.webp" alt="">';

// ---------------- KITOB MUQOVALARI ----------------
// covers/index.json — kitob nomi bo‘yicha muqova faylini topish jadvali.
let COVER_INDEX = null;

// Muqovalar ro‘yxati o‘zgarganda shu raqamni oshiring — shunda telefon
// eski nusxani emas, yangisini yuklaydi (index.html dagi ?v= bilan bir xil).
const ASSET_V = "14";

function loadCoverIndex() {
  return fetch("/covers/index.json?v=" + ASSET_V)
    .then(function (r) { return r.ok ? r.json() : {}; })
    .then(function (d) { COVER_INDEX = d; })
    .catch(function () { COVER_INDEX = {}; });
}

// Solishtirish uchun nomni soddalashtirish (apostrof — ajratuvchi).
function coverKey(s) {
  return (s || "").toLowerCase()
    .replace(/[ʻʼ‘’'`´]/g, " ")
    .normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function coverFile(title, author) {
  if (!COVER_INDEX) return null;
  const t = coverKey(title);
  const exact = COVER_INDEX[coverKey(title + " " + (author || ""))] || COVER_INDEX[t];
  if (exact) return exact;
  if (t.length < 8) return null;

  // Nom to‘liq mos kelmasligi mumkin: kitob «Galaktikada bir kun» deb
  // yozilgan, muqova esa «Galaktikada bir kun 1-2-3» nomi bilan saqlangan.
  // Shuning uchun boshi mos keladigan eng qisqa nomni qidiramiz.
  let best = null, bestLen = Infinity;
  for (const key in COVER_INDEX) {
    const longer = key.length > t.length && key.indexOf(t + " ") === 0;
    const shorter = t.length > key.length && key.length >= 8 && t.indexOf(key + " ") === 0;
    if ((longer || shorter) && key.length < bestLen) {
      best = COVER_INDEX[key];
      bestLen = key.length;
    }
  }
  return best;
}

// Muqova rasmi; topilmasa — nomning birinchi harfi rangli fonda.
function coverHtml(title, author, cls, custom) {
  // Ota-ona muqovani o‘zi rasmga olgan bo‘lsa — o‘shani ko‘rsatamiz.
  if (custom && custom.indexOf("up:") === 0) {
    return '<div class="' + cls + '"><img src="/uploads/cv/' + custom.slice(3) +
      '" alt="" loading="lazy"></div>';
  }
  const file = coverFile(title, author);
  if (file) {
    return '<div class="' + cls + '"><img src="/covers/' + file + '?v=' + ASSET_V + '" alt="" loading="lazy"></div>';
  }
  const letter = (title || "?").trim().charAt(0).toUpperCase();
  const hue = Math.abs(coverKey(title).split("").reduce(function (a, c) {
    return c.charCodeAt(0) + ((a << 5) - a);
  }, 0)) % 360;
  return '<div class="' + cls + ' cover-blank" style="--h:' + hue + 'deg"><span>' + escapeHtml(letter) + '</span></div>';
}

// ---------------- 10 TA BOLALAR AVATARI (cho‘chqa yo‘q) ----------------
const AVATARS = {
  fox: { label: "Tulki", bg: "#F2A65A", inner:
    '<path d="M 20 25 Q 20.84 12.51 35 12 Q 38 28 28 34 Z" fill="#D97F3D"/><path d="M 80 25 Q 79.16 12.51 65 12 Q 62 28 72 34 Z" fill="#D97F3D"/><path d="M 50 40 Q 25 45 25 68 Q 37 82 50 76 Q 63 82 75 68 Q 75 45 50 40 Z" fill="#FFF3E0"/><circle cx="40" cy="55" r="5" fill="#2B2B2B"/><circle cx="60" cy="55" r="5" fill="#2B2B2B"/><path d="M 46 66 L 54 66 L 50 72 Z" fill="#2B2B2B"/>' },
  bear: { label: "Ayiqcha", bg: "#C89B6B", inner:
    '<circle cx="25.45" cy="27.2" r="14" fill="#C89B6B"/><circle cx="74.55" cy="27.2" r="14" fill="#C89B6B"/><circle cx="22" cy="24" r="6" fill="#A97C4F"/><circle cx="78" cy="24" r="6" fill="#A97C4F"/><ellipse cx="50" cy="62" rx="26" ry="20" fill="#F5E6D3"/><circle cx="40" cy="52" r="5" fill="#2B2B2B"/><circle cx="60" cy="52" r="5" fill="#2B2B2B"/><ellipse cx="50" cy="62" rx="6" ry="4" fill="#2B2B2B"/>' },
  penguin: { label: "Pingvin", bg: "#2D3142", inner:
    '<path d="M 50 30 Q 28 35 28 60 Q 28 82 50 85 Q 72 82 72 60 Q 72 35 50 30 Z" fill="#FFFFFF"/><circle cx="42" cy="50" r="4" fill="#2B2B2B"/><circle cx="58" cy="50" r="4" fill="#2B2B2B"/><path d="M 44 58 L 56 58 L 50 68 Z" fill="#F2A65A"/>' },
  rabbit: { label: "Quyoncha", bg: "#F7C6D9", inner:
    '<ellipse cx="40.64" cy="26.28" rx="9" ry="22" fill="#F7C6D9"/><ellipse cx="59.36" cy="26.28" rx="9" ry="22" fill="#F7C6D9"/><ellipse cx="37.12" cy="19.08" rx="4" ry="14" fill="#F49AC1"/><ellipse cx="62.88" cy="19.08" rx="4" ry="14" fill="#F49AC1"/><ellipse cx="50" cy="62" rx="24" ry="20" fill="#FFFFFF"/><circle cx="41" cy="55" r="5" fill="#2B2B2B"/><circle cx="59" cy="55" r="5" fill="#2B2B2B"/><circle cx="50" cy="65" r="4" fill="#F49AC1"/>' },
  cat: { label: "Mushukcha", bg: "#D9A679", inner:
    '<path d="M 25 25 L 20.84 12.51 L 40 20 Z" fill="#D9A679"/><path d="M 75 25 L 79.16 12.51 L 60 20 Z" fill="#D9A679"/><path d="M 25 22 L 21.5 12 L 36 20 Z" fill="#F4C9A0"/><path d="M 75 22 L 78.5 12 L 64 20 Z" fill="#F4C9A0"/><ellipse cx="40" cy="56" rx="6" ry="8" fill="#2B2B2B"/><ellipse cx="60" cy="56" rx="6" ry="8" fill="#2B2B2B"/><path d="M 46 66 L 54 66 L 50 70 Z" fill="#F49AC1"/><line x1="10" y1="60" x2="35" y2="63" stroke="#2B2B2B" stroke-width="1.5"/><line x1="10" y1="68" x2="35" y2="68" stroke="#2B2B2B" stroke-width="1.5"/><line x1="90" y1="60" x2="65" y2="63" stroke="#2B2B2B" stroke-width="1.5"/><line x1="90" y1="68" x2="65" y2="68" stroke="#2B2B2B" stroke-width="1.5"/>' },
  owl: { label: "Boyo‘g‘li", bg: "#C08A56", inner:
    '<path d="M 30 18 L 25.3 9.43 L 38 14 Z" fill="#C08A56"/><path d="M 70 18 L 74.7 9.43 L 62 14 Z" fill="#C08A56"/><circle cx="38" cy="50" r="18" fill="#FFFFFF"/><circle cx="62" cy="50" r="18" fill="#FFFFFF"/><circle cx="38" cy="50" r="8" fill="#2B2B2B"/><circle cx="62" cy="50" r="8" fill="#2B2B2B"/><path d="M 46 62 L 54 62 L 50 70 Z" fill="#F2A65A"/>' },
  panda: { label: "Panda", bg: "#FFFFFF", inner:
    '<circle cx="25.45" cy="27.2" r="14" fill="#2B2B2B"/><circle cx="74.55" cy="27.2" r="14" fill="#2B2B2B"/><ellipse cx="38" cy="54" rx="13" ry="16" fill="#2B2B2B"/><ellipse cx="62" cy="54" rx="13" ry="16" fill="#2B2B2B"/><circle cx="38" cy="55" r="5" fill="#FFFFFF"/><circle cx="62" cy="55" r="5" fill="#FFFFFF"/><ellipse cx="50" cy="70" rx="6" ry="4" fill="#2B2B2B"/>' },
  lion: { label: "Sherbola", bg: "#F2C14E", inner:
    '<circle cx="16" cy="50" r="9" fill="#D9A441"/><circle cx="84" cy="50" r="9" fill="#D9A441"/><circle cx="24" cy="26" r="9" fill="#D9A441"/><circle cx="76" cy="26" r="9" fill="#D9A441"/><circle cx="24" cy="74" r="9" fill="#D9A441"/><circle cx="76" cy="74" r="9" fill="#D9A441"/><ellipse cx="50" cy="58" rx="28" ry="24" fill="#F2C14E"/><ellipse cx="50" cy="64" rx="18" ry="14" fill="#FCE8B8"/><circle cx="41" cy="55" r="5" fill="#2B2B2B"/><circle cx="59" cy="55" r="5" fill="#2B2B2B"/><path d="M 46 66 L 54 66 L 50 71 Z" fill="#2B2B2B"/>' },
  elephant: { label: "Fil", bg: "#B7C4CE", inner:
    '<ellipse cx="22.54" cy="48.47" rx="14" ry="20" fill="#A3B4C0"/><ellipse cx="77.46" cy="48.47" rx="14" ry="20" fill="#A3B4C0"/><ellipse cx="50" cy="48" rx="34" ry="30" fill="#B7C4CE"/><circle cx="40" cy="45" r="4" fill="#2B2B2B"/><circle cx="60" cy="45" r="4" fill="#2B2B2B"/><path d="M 46 60 Q 46 78 38 82" fill="none" stroke="#A3B4C0" stroke-width="9" stroke-linecap="round"/>' },
  dog: { label: "Kuchukcha", bg: "#C9A27E", inner:
    '<path d="M 18 25 Q 8 55 26 62 Q 34 40 30 22 Z" fill="#A87C55"/><path d="M 82 25 Q 92 55 74 62 Q 66 40 70 22 Z" fill="#A87C55"/><ellipse cx="50" cy="60" rx="26" ry="22" fill="#C9A27E"/><ellipse cx="50" cy="68" rx="14" ry="10" fill="#F4E3D0"/><circle cx="40" cy="54" r="5" fill="#2B2B2B"/><circle cx="60" cy="54" r="5" fill="#2B2B2B"/><ellipse cx="50" cy="65" rx="5" ry="4" fill="#2B2B2B"/>' }
};
const AVATAR_ORDER = ["fox", "bear", "penguin", "rabbit", "cat", "owl", "panda", "lion", "elephant", "dog"];

function avatarMarkup(avatarId, size) {
  // Foydalanuvchi o‘z rasmini qo‘ygan bo‘lsa — o‘shani ko‘rsatamiz.
  if (avatarId && avatarId.indexOf("up:") === 0) {
    return '<img class="avatar-photo" src="/uploads/av/' + avatarId.slice(3) +
      '" width="' + size + '" height="' + size + '" alt="">';
  }
  const a = AVATARS[avatarId] || AVATARS.fox;
  return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="' + a.bg + '"/>' + a.inner + '</svg>';
}


// ==========================================================
// RASMNI KESISH OYNASI
// ----------------------------------------------------------
// Foydalanuvchi rasmni surib va kattalashtirib joylashtiradi.
// Natija telefonning O‘ZIDA kichraytirilib WebP ga o‘tkaziladi —
// serverga 8-20 KB lik tayyor fayl boradi, disk deyarli band bo‘lmaydi.
// ==========================================================
const CROP_SHAPES = {
  // maxBytes — serverdagi chegaradan bir oz past. Ilova rasmni shu hajmga
  // TUSHGUNCHA o‘zi siqadi; foydalanuvchidan hech narsa talab qilinmaydi.
  avatar: { w: 264, h: 264, outW: 192, outH: 192, round: true,  quality: 0.72,
            maxBytes: 38 * 1024,
            title: "Rasmni joyla", hint: "Yuzing doira ichida qolsin" },
  cover:  { w: 240, h: 360, outW: 320, outH: 480, round: false, quality: 0.70,
            maxBytes: 76 * 1024,
            title: "Muqovani joyla", hint: "Kitob muqovasi ramka ichida qolsin" }
};

let Crop = null;

function openCropper(file, shapeName, onSave, opts) {
  const cfg = Object.assign({}, CROP_SHAPES[shapeName] || CROP_SHAPES.avatar, opts || {});
  const reader = new FileReader();
  reader.onload = function (e) {
    const img = new Image();
    img.onload = function () { startCropper(img, cfg, onSave); };
    img.onerror = function () { toast("Rasmni ocholmadim"); };
    img.src = e.target.result;
  };
  reader.onerror = function () { toast("Faylni o‘qib bo‘lmadi"); };
  reader.readAsDataURL(file);
}

function startCropper(img, cfg, onSave) {
  cfg = Object.assign({}, cfg);
  openModal(cfg.title,
    '<p class="section-sub">' + cfg.hint + '</p>' +
    '<div class="crop-stage" style="width:' + cfg.w + 'px;height:' + cfg.h + 'px">' +
      '<canvas id="crop-cv" width="' + cfg.w + '" height="' + cfg.h + '"></canvas>' +
      '<div class="crop-mask' + (cfg.round ? " is-round" : "") + '"></div>' +
    '</div>' +
    '<div class="crop-zoom">' +
      '<span class="crop-zoom-lbl">kichik</span>' +
      '<input id="crop-zoom" type="range" min="100" max="300" value="100">' +
      '<span class="crop-zoom-lbl">katta</span>' +
    '</div>' +
    '<button class="btn btn-primary btn-block" data-action="crop-save">Saqlash</button>' +
    (cfg.skip ? '<button class="btn btn-block" data-action="crop-skip" style="margin-top:8px">Keyinroq</button>' : "")
  );

  const cv = document.getElementById("crop-cv");
  const fit = Math.max(cfg.w / img.width, cfg.h / img.height);
  Crop = { img: img, cfg: cfg, cv: cv, ctx: cv.getContext("2d"),
           fit: fit, zoom: 1, x: 0, y: 0, onSave: onSave };
  clampCrop();
  drawCrop();

  const zoomEl = document.getElementById("crop-zoom");
  zoomEl.oninput = function () {
    Crop.zoom = Number(this.value) / 100;
    clampCrop(); drawCrop();
  };

  // Surish — sichqoncha ham, barmoq ham
  let dragging = false, lastX = 0, lastY = 0;
  function down(e) {
    dragging = true;
    const t = e.touches ? e.touches[0] : e;
    lastX = t.clientX; lastY = t.clientY;
  }
  function move(e) {
    if (!dragging) return;
    const t = e.touches ? e.touches[0] : e;
    Crop.x += t.clientX - lastX;
    Crop.y += t.clientY - lastY;
    lastX = t.clientX; lastY = t.clientY;
    clampCrop(); drawCrop();
    e.preventDefault();
  }
  function up() { dragging = false; }
  cv.addEventListener("mousedown", down);
  cv.addEventListener("touchstart", down, { passive: true });
  window.addEventListener("mousemove", move);
  cv.addEventListener("touchmove", move, { passive: false });
  window.addEventListener("mouseup", up);
  cv.addEventListener("touchend", up);
}

// Rasm ramkadan kichik bo‘lib, chetida bo‘shliq qolmasin
function clampCrop() {
  const c = Crop, sc = c.fit * c.zoom;
  const w = c.img.width * sc, h = c.img.height * sc;
  const maxX = Math.max(0, (w - c.cfg.w) / 2);
  const maxY = Math.max(0, (h - c.cfg.h) / 2);
  c.x = Math.max(-maxX, Math.min(maxX, c.x));
  c.y = Math.max(-maxY, Math.min(maxY, c.y));
}

function drawCrop() {
  const c = Crop, sc = c.fit * c.zoom;
  const w = c.img.width * sc, h = c.img.height * sc;
  c.ctx.clearRect(0, 0, c.cfg.w, c.cfg.h);
  c.ctx.drawImage(c.img, (c.cfg.w - w) / 2 + c.x, (c.cfg.h - h) / 2 + c.y, w, h);
}

// Canvas'ni belgilangan hajmga TUSHGUNCHA siqadi.
// ----------------------------------------------------------
// Ilgari faqat bitta urinish bor edi: WEBP, bitta sifat darajasi. Ammo
// ba'zi telefonlar (ayniqsa eski iPhone) WEBP ni umuman yasay olmaydi —
// brauzer jimgina PNG qaytaradi, u esa bir necha barobar og‘ir. Natijada
// server «Rasm juda katta» deb rad etardi va aybdor foydalanuvchi bo‘lib
// qolardi. Endi ilova o‘zi bir necha usulni ketma-ket sinab ko‘radi.
function canvasToBlob(canvas, type, quality) {
  return new Promise(function (res) { canvas.toBlob(res, type, quality); });
}

async function encodeUnderLimit(canvas, maxBytes, startQuality) {
  const ladder = [
    ["image/webp", startQuality], ["image/webp", 0.6], ["image/webp", 0.45],
    ["image/jpeg", startQuality], ["image/jpeg", 0.6], ["image/jpeg", 0.45], ["image/jpeg", 0.32]
  ];
  let best = null;
  for (let i = 0; i < ladder.length; i++) {
    const blob = await canvasToBlob(canvas, ladder[i][0], ladder[i][1]);
    if (!blob) continue;
    // Brauzer so‘ralgan turni qo‘llamasa, o‘zi bilganini qaytaradi (odatda PNG).
    // Bunday javobni o‘tkazib yuboramiz — keyingi usul sinaladi.
    if (blob.type !== ladder[i][0]) { if (!best || blob.size < best.size) best = blob; continue; }
    if (blob.size <= maxBytes) return blob;
    if (!best || blob.size < best.size) best = blob;
  }
  // Sifatni pasaytirish yetmadi — o‘lchamni kichraytirib qayta urinamiz.
  if (best && best.size > maxBytes && canvas.width > 96) {
    const small = document.createElement("canvas");
    small.width = Math.round(canvas.width * 0.75);
    small.height = Math.round(canvas.height * 0.75);
    const sx = small.getContext("2d");
    sx.imageSmoothingQuality = "high";
    sx.drawImage(canvas, 0, 0, small.width, small.height);
    return encodeUnderLimit(small, maxBytes, startQuality);
  }
  return best;
}

async function saveCrop() {
  if (!Crop || Crop.busy) return;
  const c = Crop, cfg = c.cfg;
  c.busy = true;
  const btn = document.querySelector('[data-action="crop-save"]');
  if (btn) { btn.disabled = true; btn.textContent = "Tayyorlanmoqda…"; }

  const k = cfg.outW / cfg.w;                 // ekrandagi o‘lchamdan haqiqiy o‘lchamga
  const out = document.createElement("canvas");
  out.width = cfg.outW; out.height = cfg.outH;
  const ox = out.getContext("2d");
  ox.imageSmoothingQuality = "high";
  const sc = c.fit * c.zoom * k;
  const w = c.img.width * sc, h = c.img.height * sc;
  ox.drawImage(c.img, (cfg.outW - w) / 2 + c.x * k, (cfg.outH - h) / 2 + c.y * k, w, h);

  let blob = null;
  try {
    blob = await encodeUnderLimit(out, cfg.maxBytes || 38 * 1024, cfg.quality);
  } catch (e) { blob = null; }

  // Tugma yana ishlasin: yuklash muvaffaqiyatsiz bo‘lsa, foydalanuvchi
  // qayta bosa oladi. Ilgari bu yerda Crop = null qilinardi va oyna
  // «o‘lik» holatga tushib qolardi — tugma bosilsa hech narsa bo‘lmasdi.
  c.busy = false;
  if (btn) { btn.disabled = false; btn.textContent = "Saqlash"; }

  if (!blob) { toast("Rasmni tayyorlab bo‘lmadi. Boshqa rasm tanlang."); return; }
  c.onSave(blob);
}

// Rasm tanlash oynasini ochadi va kesish oynasiga uzatadi
async function uploadAvatarBlob(blob, childId) {
  const fd = new FormData();
  fd.append("photo", blob, "avatar.webp");
  const q = childId ? ("?child_id=" + childId) : "";
  return api("/api/upload/avatar" + q, { method: "POST", body: fd });
}

function pickImage(shapeName, onSave, opts) {
  const inp = document.createElement("input");
  inp.type = "file";
  inp.accept = "image/*";
  inp.onchange = function () {
    if (!inp.files || !inp.files.length) return;
    openCropper(inp.files[0], shapeName, onSave, opts);
  };
  inp.click();
}

function icon(name, size, strokeWidth) {
  size = size || 20;
  strokeWidth = strokeWidth || 1.8;
  const p = ICON_PATHS[name] || "";
  // Duotone ikonalar massiv: [to‘ldirish, chiziq]. Oddiylari — oddiy satr.
  const fill = Array.isArray(p) ? p[0] : "";
  const line = Array.isArray(p) ? p[1] : p;
  return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none">' +
    (fill ? '<g fill="currentColor" opacity=".17">' + fill + '</g>' : "") +
    '<g stroke="currentColor" stroke-width="' + strokeWidth +
    '" stroke-linecap="round" stroke-linejoin="round">' + line + '</g>' +
    '</svg>';
}

// ---------------- API YORDAMCHISI ----------------
async function api(path, opts) {
  opts = opts || {};
  const headers = { "X-Telegram-Init-Data": (tg && tg.initData) || "" };
  let url = path;

  if (!tg || !tg.initData) {
    // Kompyuterda sinash uchun: manzil satriga ?dev_id=1001 qo‘shilsa,
    // hech narsa so‘ramasdan o‘sha foydalanuvchi nomidan ochiladi.
    const fromUrl = new URLSearchParams(location.search).get("dev_id");
    if (fromUrl) localStorage.setItem("bilig_dev_id", fromUrl);
    let devId = localStorage.getItem("bilig_dev_id");
    if (!devId) {
      devId = prompt("DEV REJIM: test uchun foydalanuvchi ID kiriting");
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

// ==========================================================
// RASMNI YUBORISHDAN OLDIN TAYYORLASH
// ==========================================================
// Telefon kamerasi 4000 nuqtali, 4-6 MB rasm oladi. AI rasmni kvadratchalarga
// bo‘lib hisoblaydi — katta rasm bir necha barobar qimmat va sekin yuklanadi.
// Shuning uchun har bir vazifaga aynan yetadigan o‘lcham tanlanadi:
//   page  — faqat bet raqami o‘qiladi          (eng tez-tez chaqiriladi)
//   text  — sahifadagi butun matn o‘qiladi     (sifat kerak)
//   cover — nom va muallif, muqova bezakli      (sifat kerak)
const IMG_PRESETS = {
  page:  { max: 1280, quality: 0.82 },
  text:  { max: 1600, quality: 0.88 },
  cover: { max: 1400, quality: 0.90 }
};

// Rasm qanchalik o‘tkir ekanini o‘lchaydi. Kichik son = xira rasm.
// (Qo‘shni nuqtalar orasidagi farq qancha keskin bo‘lsa, rasm shuncha o‘tkir.)
function measureSharpness(canvas) {
  try {
    const w = 240;
    const h = Math.max(1, Math.round(canvas.height * (w / canvas.width)));
    const small = document.createElement("canvas");
    small.width = w; small.height = h;
    small.getContext("2d").drawImage(canvas, 0, 0, w, h);
    const d = small.getContext("2d").getImageData(0, 0, w, h).data;
    const gray = new Float32Array(w * h);
    for (let i = 0; i < w * h; i++) {
      gray[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2];
    }
    let sum = 0, sum2 = 0, n = 0;
    for (let y = 1; y < h - 1; y++) {
      for (let x = 1; x < w - 1; x++) {
        const i = y * w + x;
        const lap = gray[i - 1] + gray[i + 1] + gray[i - w] + gray[i + w] - 4 * gray[i];
        sum += lap; sum2 += lap * lap; n++;
      }
    }
    if (!n) return 999;
    const mean = sum / n;
    return sum2 / n - mean * mean;
  } catch (e) { return 999; }
}

// Xira deb hisoblanadigan chegara. Ataylab past qo‘yilgan — faqat chindan ham
// o‘qib bo‘lmaydigan rasmlar ushlansin, oddiy rasm bekorga rad etilmasin.
const SHARPNESS_MIN = 5;

// Faylni kichraytirib, JPEG holida qaytaradi. Nimadir ishlamasa —
// asl faylni qaytaradi, ya'ni foydalanuvchi hech qachon to‘xtab qolmaydi.
function prepareImage(file, presetName) {
  const preset = IMG_PRESETS[presetName] || IMG_PRESETS.page;
  return new Promise(function (resolve) {
    if (!file || !file.type || file.type.indexOf("image/") !== 0) {
      resolve({ blob: file, sharpness: 999, resized: false });
      return;
    }
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = function () {
      try {
        const scale = Math.min(1, preset.max / Math.max(img.width, img.height));
        const w = Math.round(img.width * scale);
        const h = Math.round(img.height * scale);
        const canvas = document.createElement("canvas");
        canvas.width = w; canvas.height = h;
        const ctx = canvas.getContext("2d");
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(img, 0, 0, w, h);
        const sharp = measureSharpness(canvas);
        canvas.toBlob(function (blob) {
          URL.revokeObjectURL(url);
          resolve({ blob: blob || file, sharpness: sharp, resized: scale < 1 });
        }, "image/jpeg", preset.quality);
      } catch (e) {
        URL.revokeObjectURL(url);
        resolve({ blob: file, sharpness: 999, resized: false });
      }
    };
    img.onerror = function () {
      URL.revokeObjectURL(url);
      resolve({ blob: file, sharpness: 999, resized: false });
    };
    img.src = url;
  });
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

function openModal(title, bodyHtml, extraClass) {
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").innerHTML = bodyHtml;
  const box = document.querySelector("#modal-overlay .modal-box");
  box.className = "modal-box" + (extraClass ? " " + extraClass : "");
  box.scrollTop = 0;
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
    if (me.role === "child" && me.needs_profile) { showScreen("screen-child-profile"); initAvatarGrid(); return; }
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
    const res = await api("/api/link_parent", { method: "POST", body: { code: input.value.trim() } });
    if (res && res.profile_ready) {
      // Ota-ona profilni allaqachon to‘ldirib qo‘ygan — qayta so‘ramaymiz
      await boot();
      return;
    }
    showScreen("screen-child-profile");
    initAvatarGrid();
  } catch (e) { err.textContent = e.error || "Xatolik"; }
});

// ---------------- Bola profili: avatar + ism + yosh ----------------
let selectedProfileAvatar = "fox";

// «Mening rasmim» kartochkasi — hamma avatar ro‘yxatining oxirida turadi
function uploadTileHtml(current) {
  const mine = current && current.indexOf("up:") === 0;
  return '<button class="avatar-option' + (mine ? " selected" : "") + '" data-avatar="__upload" data-action="pick-edit-avatar">' +
    '<span class="avatar-circle">' +
      (mine ? avatarMarkup(current, 54)
            : '<span class="avatar-add">' + icon("plus", 22, 2.2) + '</span>') +
    '</span><span>' + (mine ? "Mening rasmim" : "Rasm qo‘shish") + '</span></button>';
}

function paintAvatarGrid() {
  const grid = document.getElementById("avatar-grid");
  if (!grid) return;
  grid.innerHTML = AVATAR_ORDER.map(function (id) {
    const a = AVATARS[id];
    return '<button class="avatar-option' + (id === selectedProfileAvatar ? " selected" : "") + '" data-avatar="' + id + '">' +
      '<span class="avatar-circle">' + avatarMarkup(id, 54) + '</span><span>' + a.label + '</span></button>';
  }).join("") + uploadTileHtml(selectedProfileAvatar);
}
function initAvatarGrid() {
  selectedProfileAvatar = "fox";
  const grid = document.getElementById("avatar-grid");
  paintAvatarGrid();
  grid.addEventListener("click", async function (e) {
    const btn = e.target.closest(".avatar-option");
    if (!btn) return;
    haptic();
    if (btn.dataset.avatar === "__upload") {
      pickImage("avatar", async function (blob) {
        try {
          const res = await uploadAvatarBlob(blob, null);
          selectedProfileAvatar = res.avatar_id;
          closeModal(); paintAvatarGrid();
        } catch (err) { toast(err.error || "Rasmni saqlab bo‘lmadi"); }
      });
      return;
    }
    selectedProfileAvatar = btn.dataset.avatar;
    paintAvatarGrid();
  });
}
document.getElementById("profile-submit").addEventListener("click", async function () {
  const name = document.getElementById("profile-name-input").value.trim();
  const age = document.getElementById("profile-age-input").value;
  const err = document.getElementById("profile-error");
  err.textContent = "";
  try {
    await api("/api/child/profile", { method: "POST", body: { name: name, age: age, avatar_id: selectedProfileAvatar } });
    toast("Xush kelibsiz, " + name + "!");
    enterApp();
  } catch (e) { err.textContent = e.error || "Xatolik"; }
});

// ==========================================================
// ILOVA QOBIG‘I
// ==========================================================
async function enterApp() {
  showScreen("shell");
  if (!COVER_INDEX) await loadCoverIndex();
  loadBadgeMeta();
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
  const avatarEl = document.getElementById("header-avatar");
  const nameEl = document.getElementById("header-name");
  const roleEl = document.getElementById("header-role");
  if (State.activeChildId) {
    // Bolaxona rejimida ota-ona farzand nomidan ishlaydi — sarlavha ham
    // shuni ko‘rsatishi kerak, aks holda qayerda turgani chalkashadi.
    nameEl.textContent = State.activeChildName || me.name || "Farzand";
    roleEl.textContent = "Bolaxona rejimi";
  } else {
    nameEl.textContent = me.name || "Foydalanuvchi";
    roleEl.textContent = me.role === "parent" ? "Ota-ona kabineti" : "O‘quvchi";
  }

  const statsBox = document.getElementById("header-stats");
  if (isChildView()) {
    let avatarId = me.avatar_id || "fox";
    if (State.activeChildId) {
      const child = State.childrenCache.filter(function (c) { return c.id === State.activeChildId; })[0];
      if (child) avatarId = child.avatar_id;
    }
    avatarEl.innerHTML = avatarMarkup(avatarId, 40);
    // Bilig va streak sarlavhada takrorlanmaydi — ular statistika blokida bor
    statsBox.innerHTML = "";
  } else {
    avatarEl.textContent = (me.name || "?").charAt(0).toUpperCase();
    statsBox.innerHTML = "";
  }
}

const TABS_PARENT = [
  { id: "home", label: "Bosh sahifa", icon: "home" },
  { id: "plans", label: "Rejalar", icon: "book-open" },
  { id: "store", label: "Do‘kon", icon: "cart" },
  { id: "bolaxona", label: "Bolaxona", icon: "users" },
];
const TABS_CHILD = [
  { id: "home", label: "Bosh sahifa", icon: "home" },
  { id: "plans", label: "Rejalar", icon: "book-open" },
  { id: "store", label: "Do‘kon", icon: "cart" },
  { id: "rating", label: "Reyting", icon: "award" },
];
const TABS_PARENT_ACTING = [
  { id: "home", label: "Bosh sahifa", icon: "home" },
  { id: "plans", label: "Rejalar", icon: "book-open" },
  { id: "store", label: "Do‘kon", icon: "cart" },
  { id: "ota-ona", label: "Ota-ona", icon: "users", action: "exit-bolaxona" },
];

async function setupTabsForRole() {
  const nav = document.getElementById("app-tabs");
  const tabs = State.role === "child" ? TABS_CHILD : (State.activeChildId ? TABS_PARENT_ACTING : TABS_PARENT);
  nav.innerHTML = tabs.map(function (t) {
    const action = t.action || "open-tab";
    const tabAttr = t.action ? "" : ' data-tab="' + t.id + '"';
    return '<button class="tab-btn" data-action="' + action + '"' + tabAttr + '>' + icon(t.icon, 21, 1.7) + '<span>' + t.label + '</span></button>';
  }).join("");
  await refreshHeader();
  switchTab("home");

  const banner = document.getElementById("bolaxona-banner");
  renderHeaderNav();
  if (State.activeChildId) {
    banner.classList.remove("hidden");
    document.getElementById("bolaxona-child-name").textContent = State.activeChildName || "";
    const exitBtn = document.getElementById("bolaxona-exit");
    if (exitBtn) exitBtn.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }
}

// Sarlavhadagi uchta tugma: reyting, shaxsiy natija va nishonlar.
// Har biri bir bosishda kerakli bo‘limni ochadi.
const HEADER_NAV = [
  { mode: "global", icon: "trophy", label: "Reyting" },
  { mode: "passport", icon: "chart", label: "Natija" },
  { mode: "badges", icon: "award", label: "Nishonlar" },
];

function renderHeaderNav() {
  const box = document.getElementById("header-nav");
  if (!box) return;
  // Bola rejimida ham, ota-ona kabinetida ham kerak
  box.innerHTML = HEADER_NAV.map(function (n) {
    const on = State.currentTab === "rating" && State.ratingMode === n.mode;
    return '<button class="icon-btn' + (on ? " is-on" : "") + '" data-action="open-rating" data-mode="' + n.mode + '" aria-label="' + n.label + '" title="' + n.label + '">' +
      icon(n.icon, 18, 1.8) + '</button>';
  }).join("");
}

function openRatingFromHeader() {
  document.querySelectorAll(".tab-btn").forEach(function (b) { b.classList.remove("active"); });
  State.currentTab = "rating";
  const main = document.getElementById("app-main");
  main.innerHTML = '<div class="empty-state"><div class="spinner"></div>Yuklanmoqda…</div>';
  renderRatingTab().catch(function (e) { main.innerHTML = '<div class="empty-state">' + escapeHtml(e.error || "Xatolik yuz berdi") + '</div>'; });
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
    : { home: renderParentHome, plans: renderParentPlans, store: renderStoreTab, bolaxona: renderBolaxonaTab };
  const fn = renderers[tabId];
  const main = document.getElementById("app-main");
  main.innerHTML = '<div class="empty-state"><div class="spinner"></div>Yuklanmoqda…</div>';
  if (fn) fn().catch(function (e) { main.innerHTML = '<div class="empty-state">' + escapeHtml(e.error || "Xatolik yuz berdi") + '</div>'; });
}

// ==========================================================
// MARKAZIY KLIK BOSHQARUVCHISI
// ==========================================================
// Bir vaqtda faqat bitta amal bajariladi. Bo‘lmasa foydalanuvchi javobni
// kutolmay qayta-qayta bosadi va buyruqlar birdaniga takrorlanib ketadi.
let actionBusy = false;

// Tabrik ekrani tugmasi va maskot lentasi — markaziy dispatcherdan tashqarida,
// chunki ular ilova qobig‘idan ustun turadi.
document.addEventListener("DOMContentLoaded", function () {
  const celBtn = document.getElementById("cel-btn");
  if (celBtn) celBtn.onclick = function () { haptic(); celNext(); };
  const mt = document.getElementById("mtoast");
  if (mt) mt.onclick = hideMascotToast;
});

document.addEventListener("click", async function (e) {
  const el = e.target.closest("[data-action]");
  if (!el) return;
  if (actionBusy) return;            // avvalgi amal tugamagan — bu bosishni e'tiborsiz qoldiramiz
  const a = el.dataset.action;
  haptic();

  actionBusy = true;
  // Amal tez tugasa, "kutish" belgisi umuman ko‘rinmaydi (150 ms dan keyin chiqadi)
  const busyTimer = setTimeout(function () { el.classList.add("is-busy"); }, 150);
  // Xavfsizlik: biror amal osilib qolsa ham ilova qotib qolmaydi
  const release = setTimeout(function () { actionBusy = false; }, 12000);

  try {
    switch (a) {
      case "open-tab": switchTab(el.dataset.tab); break;
      case "close-modal": closeModal(); break;
      case "show-unseen-badges": await showUnseenBadges(el); break;

      case "open-child-detail": State.selectedChildId = Number(el.dataset.id); await renderChildDetailPage(State.selectedChildId); break;
      case "back-to-home":
        document.getElementById("app-main").innerHTML = '<div class="empty-state"><div class="spinner"></div>Yuklanmoqda…</div>';
        await renderParentHome();
        break;
      case "enter-bolaxona":
        State.activeChildId = Number(el.dataset.id);
        State.activeChildName = el.dataset.name;
        closeModal();                 // kitob oynasidan kirilgan bo‘lsa ham yopiladi
        setupTabsForRole();
        break;
      case "exit-bolaxona":
        State.activeChildId = null; State.activeChildName = null;
        setupTabsForRole();
        break;

      case "open-add-plan": await Wizard.start(); break;
      case "wizard-pick-mode": await Wizard.pickMode(el.dataset.mode); break;
      case "wizard-continue-plan": await Wizard.continuePlan(); break;
      case "wizard-pick-method": await Wizard.pickMethod(el.dataset.method); break;
      case "wizard-pick-rec": await Wizard.addRecBook(Number(el.dataset.idx)); break;
      case "cat-age": Catalog.setAge(el.dataset.key); break;
      case "cat-pick": await Catalog.pick(Number(el.dataset.idx)); break;
      case "wizard-submit-text": await Wizard.submitTextBook(); break;
      case "wizard-save-cover": await Wizard.saveCoverBook(); break;
      case "wizard-add-more": await Wizard.pickMethod(null); break;
      case "wizard-finish": closeModal(); switchTab("plans"); break;

      case "delete-book":
        if (confirm("Kitobni o‘chirasizmi?")) {
          await api("/api/parent/books/" + el.dataset.id, { method: "DELETE" });
          toast("Kitob o‘chirildi"); closeModal(); switchTab("plans");
        }
        break;
      case "open-generate-test": openGenerateTestModal(Number(el.dataset.id)); break;
      case "shot-add": TestShots.add(); break;
      case "shot-del": TestShots.remove(Number(el.dataset.i)); break;
      case "shot-submit": await TestShots.submit(); break;

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

      case "edit-child": openEditChildModal(el.dataset.id, el.dataset.name, el.dataset.age, el.dataset.avatar); break;
      case "pick-edit-avatar":
        if (el.dataset.avatar === "__upload") {
          // DIQQAT: ilgari bu yerda «#avatar-grid mavjudmi?» deb tekshirilardi.
          // Lekin u index.html da DOIM turadi (bola profili ekrani yashirin
          // bo‘lsa ham) — shuning uchun «Rasm qo‘shish» katakchasi HECH QACHON
          // ishlamasdi. To‘g‘risi: bosilgan tugma AYNAN o‘sha tarmoq ichidami?
          if (el.closest("#avatar-grid")) break;   // bola profili ekrani o‘zi hal qiladi
          pickImage("avatar", async function (blob) {
            try {
              const res = await uploadAvatarBlob(blob, editChildId);
              editChildAvatar = res.avatar_id;
              closeModal();
              toast("Rasm saqlandi");
              await refreshHeader();
              renderParentHome();
            } catch (err) { toast(err.error || "Rasmni saqlab bo‘lmadi"); }
          });
          break;
        }
        editChildAvatar = el.dataset.avatar;
        document.querySelectorAll("#edit-avatar-grid .avatar-option").forEach(function (b) {
          b.classList.toggle("selected", b.dataset.avatar === editChildAvatar);
        });
        break;
      case "crop-save": await saveCrop(); break;
      case "crop-skip": {
        const skip = Crop && Crop.cfg && Crop.cfg.onSkip;
        Crop = null; closeModal();
        if (skip) skip();
        break;
      }
      case "submit-edit-child": await submitEditChild(el.dataset.id); break;
      case "pick-new-avatar":
        newChildAvatar = el.dataset.avatar;
        document.querySelectorAll("#new-avatar-grid .avatar-option").forEach(function (b) {
          b.classList.toggle("selected", b.dataset.avatar === newChildAvatar);
        });
        break;

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

      case "go-plans-tab": switchTab("plans"); break;
      case "go-book": await goToBook(Number(el.dataset.id)); break;
      case "set-active-child":
        State.selectedChildId = Number(el.dataset.id);
        await renderParentHome();
        break;
      case "open-add-child": openAddChildModal(); break;
      case "submit-add-child": await submitAddChild(); break;
      case "pick-new-avatar":
        newChildAvatar = el.dataset.avatar;
        document.querySelectorAll("#new-avatar-grid .avatar-option").forEach(function (b) {
          b.classList.toggle("selected", b.dataset.avatar === newChildAvatar);
        });
        break;
      case "copy-code": await copyCode(el.dataset.code); break;
      case "open-badges":
        State.ratingMode = "badges";     // to‘g‘ridan-to‘g‘ri nishonlar sahifasi
        openRatingFromHeader();
        break;
      case "open-result":
        State.ratingMode = "passport";
        openRatingFromHeader();
        break;
      case "cal-move":
        State.calShift = (State.calShift || 0) + Number(el.dataset.step);
        renderRatingTab();
        break;
      case "open-rating":
        State.calShift = 0;
        State.ratingMode = el.dataset.mode;
        openRatingFromHeader();
        break;
      case "switch-child":
        State.selectedChildId = Number(el.dataset.id);
        await refreshHeader();
        if (State.currentTab === "rating") { renderRatingTab(); }
        else { switchTab(State.currentTab || "home"); }
        break;
      case "demo-fill": await demoFill(Number(el.dataset.id), el.dataset.name); break;
      case "demo-clear": await demoClear(Number(el.dataset.id), el.dataset.name); break;
    }
  } catch (err) {
    toast(err.error || err.message || "Xatolik yuz berdi");
  } finally {
    clearTimeout(busyTimer);
    clearTimeout(release);
    el.classList.remove("is-busy");
    actionBusy = false;
  }
});

// ==========================================================
// TAB 1: BOSH SAHIFA — OTA-ONA
// ==========================================================
async function renderParentHome() {
  const main = document.getElementById("app-main");
  if (!State.childrenCache.length) {
    main.innerHTML = emptyState("users", "Hali farzand qo‘shilmagan", "Farzandingizni shu yerdan qo‘shing — alohida telefon shart emas.") +
      '<button class="btn btn-primary btn-block" data-action="open-add-child" style="display:flex;align-items:center;justify-content:center;gap:6px">' + icon("plus", 17, 2) + ' Farzand qo‘shish</button>';
    return;
  }
  // Faol farzand — ota-ona o‘zi tanlaydi. Tanlanmagan bo‘lsa, birinchisi olinadi.
  let primary = State.childrenCache.filter(function (c) { return c.id === State.selectedChildId; })[0];
  if (!primary) { primary = State.childrenCache[0]; State.selectedChildId = primary.id; }
  const primaryData = await api("/api/parent/home/" + primary.id);

  // ---- 1. Farzandlar karuseli ----
  // Kartochka bosilsa — o‘sha farzand faol bo‘ladi (butun bosh sahifa, Rejalar
  // va Do‘kon shunga qarab ko‘rsatiladi). Faol kartochkadagi belgi esa
  // uning batafsil sahifasini ochadi.
  const chips = State.childrenCache.map(function (c) {
    const isActive = c.id === primary.id;
    return '<button class="kid-chip ' + (isActive ? "is-active" : "") + '" data-action="set-active-child" data-id="' + c.id + '">' +
      '<span class="kid-av">' + avatarMarkup(c.avatar_id || "fox", 52) + '</span>' +
      '<span class="kid-name">' + escapeHtml(c.name) + '</span>' +
      (isActive ? '<span class="kid-flag">Faol</span>' +
        '<span class="kid-more" data-action="open-child-detail" data-id="' + c.id + '" title="Batafsil">' + icon("chevron-right", 13, 2.4) + '</span>' : "") +
      '</button>';
  }).join("") +
    '<button class="kid-chip kid-add" data-action="open-add-child">' +
    '<span class="kid-av kid-plus">' + icon("plus", 22, 2) + '</span>' +
    '<span class="kid-name">Farzand qo‘shish</span>' +
    '</button>';

  let html = '<p class="sec-label">Farzandlar</p>' +
    '<div class="kid-row">' + chips + '</div>';

  // ---- 2. Kitob qo‘shish ----
  html += '<div class="hero-card" data-action="open-add-plan">' +
    HERO_MASCOT +
    '<div class="icon-circle">' + icon("plus-circle", 22, 1.8) + '</div>' +
    '<p class="hc-title">Kitob qo‘shish</p>' +
    '<div style="display:flex;align-items:center;gap:6px;font-size:15px;font-weight:600;">Tezkor yoki marafon rejasi yaratish ' + icon("arrow-right", 15, 2) + '</div>' +
    '</div>';

  // ---- 3. So‘nggi natijalar (ilgari bu joyda 3 ta statistika qutisi turardi) ----
  html += '<p class="sec-label">So‘nggi natijalar</p>' +
    '<div class="res-card is-tappable" data-action="open-result">' +
    '<div class="res-who"><span class="av">' + avatarMarkup(primary.avatar_id || "fox", 48) + '</span>' +
    '<span>' + escapeHtml(primary.name) + '</span></div>' +
    '<div class="res-list">' +
    resRow("flame", "ic-flame", "Uzluksiz mutolaa", primaryData.streak + " kun") +
    resRow("book-open", "ic-brand", "Jami o‘qilgan", (primaryData.total_pages || 0) + " bet") +
    resRow("coin", "ic-coin", "To‘plangan Bilig", primaryData.coins + " ta") +
    resRow("star", "ic-rank", "Yangi nishon", primaryData.last_badge ? stripEmoji(primaryData.last_badge) : "hali yo‘q") +
    resRow("mic", "ic-audio", "AI audio bahosi", primaryData.last_audio_score ? primaryData.last_audio_score + "/5" : "hali yo‘q") +
    '</div></div>';

  // ---- 4. O‘qiyotgan kitobi ----
  html += '<p class="sec-label">O‘qiyotgan kitobi</p>' + nowReadingCard(primaryData.current_book);

  // ---- 5. AI ustoz xulosasi ----
  // Ota-ona uchun: kechqurun farzand bilan suhbatlashishga tayyor ko‘rsatma
  html += aiReportBlockHtml(primaryData.last_report);


  // ---- 6. Nishonlar ----
  html += badgesBlockHtml(primaryData.badges);

  // ---- 7. Kitoblar javoni (yon tarafga siljitiladi) ----
  const shelf = primaryData.shelf_books || primaryData.active_books || [];
  html += '<p class="sec-label">Kitoblar javoni' +
    (shelf.length > 3 ? ' <span class="sw" data-action="go-plans-tab">' + icon("chevron-right", 12, 2.4) + '</span>' : "") + '</p>' +
    shelfHtml(shelf, "Javon hozircha bo‘sh — yuqoridan kitob qo‘shing.");

  main.innerHTML = html;
}

// Kitoblar javoni — rejadagi kitoblar muqovalari bilan
function shelfHtml(books, emptyText) {
  const shelf = books || [];
  if (!shelf.length) {
    return '<div class="card"><p class="section-sub" style="margin:0">' + emptyText + '</p></div>';
  }
  return '<div class="shelf">' + shelf.map(function (b) {
    const pr = bookProgress(b);
    const done = !!b.completed;
    return '<article class="shelf-card' + (done ? " is-done" : "") + '" data-action="go-book" data-id="' + b.id + '">' +
      '<span class="shelf-wrap">' + coverHtml(b.title, b.author, "shelf-cover", b.cover_file) +
      (done ? '<span class="shelf-check">' + icon("check-circle", 17, 2.2) + '</span>' : "") +
      '</span>' +
      '<p class="shelf-title">' + escapeHtml(b.title) + '</p>' +
      (done ? "" : (pr.known ? '<div class="shelf-bar"><i style="width:' + pr.pct + '%"></i></div>' : "")) +
      '<span class="shelf-pct' + (done ? " is-done" : "") + '">' +
      (done ? 'Tugatildi' : (pr.known ? pr.pct + '% o‘qildi' : pr.label)) + '</span>' +
      '</article>';
  }).join("") + '</div>';
}

// AI ustoz xulosasi — ota-ona uchun: mazmun va kechki suhbat mavzusi
function aiReportBlockHtml(report) {
  if (!report || (!report.summary && !report.conversation_topic)) {
    return '<p class="sec-label">AI ustoz xulosasi</p>' +
      '<div class="card"><p class="section-sub" style="margin:0">Farzandingiz ovozli xulosa yuborgach, AI ustoz tahlili shu yerda chiqadi.</p></div>';
  }
  return '<p class="sec-label">AI ustoz xulosasi</p>' +
    '<div class="card ai-card">' +
    '<div class="ai-top"><span class="ai-ic">' + icon("message-circle", 19, 1.9) + '</span>' +
    (report.summary ? '<p class="ai-text">' + escapeHtml(report.summary) + '</p>' : '') +
    '</div>' +
    (report.conversation_topic
      ? '<div class="ai-topic"><b>Kechki suhbat mavzusi</b>' +
        '<p>' + escapeHtml(report.conversation_topic) + '</p></div>'
      : '') +
    '</div>';
}

// Nishonlar bloki — 4 tasi ko‘rsatiladi: avval olinganlari (yangisi
// birinchi), keyin olinmaganlari xira holatda. Shunda blok hech qachon
// bo‘sh turmaydi va bola nimaga intilishini ko‘radi.
function badgesBlockHtml(badgesStr, limit) {
  const earned = earnedBadgeSet(badgesStr);
  const have = BADGE_LIST.filter(function (b) { return earned[b[1].toLowerCase()]; });
  const rest = BADGE_LIST.filter(function (b) { return !earned[b[1].toLowerCase()]; });
  const max = limit || 4;
  const shown = have.slice().reverse().concat(rest).slice(0, max);

  return '<p class="sec-label">Nishonlar</p>' +
    '<div class="badge-strip" data-action="open-badges">' +
    shown.map(function (b) {
      const got = !!earned[b[1].toLowerCase()];
      return '<span class="bs-item' + (got ? "" : " is-locked") + '">' +
        badgeArt(b[0]) +
        '<b>' + escapeHtml(b[1]) + '</b></span>';
    }).join("") +
    '<span class="bs-more"><b>' + have.length + '</b><br>/' + BADGE_LIST.length + '</span>' +
    '</div>';
}

// Kitob yo‘lini hisoblash. Jami sahifa soni noma'lum bo‘lsa (masalan katalogdan
// tez qo‘shilgan kitob), soxta foiz o‘rniga faqat o‘qilgan betlar ko‘rsatiladi.
function bookProgress(b) {
  const total = Number(b.total_pages) || 0;
  const read = Number(b.pages_read) || 0;
  if (!total) {
    return { known: false, pct: 0, label: read + ' bet o‘qildi' };
  }
  const pct = Math.min(100, Math.round(read / total * 100));
  return { known: true, pct: pct, label: read + '/' + total + ' bet' };
}

// Oxirgi 7 kun: o‘qilgan kunlar to‘ldirilgan doira bilan belgilanadi
function weekStripHtml(week) {
  if (!week || !week.length) return "";
  const done = week.filter(function (d) { return d.read; }).length;
  return '<div class="week-strip">' +
    '<div class="week-days">' + week.map(function (d) {
      return '<span class="wd' + (d.read ? " is-read" : "") + (d.today ? " is-today" : "") + '">' +
        '<i>' + (d.read ? icon("check-circle", 15, 2.2) : "") + '</i>' +
        '<b>' + d.label + '</b></span>';
    }).join("") + '</div>' +
    '<span class="week-note">Shu haftada <b>' + done + '</b>/7 kun o‘qildi</span>' +
    '</div>';
}

// Unvon matnidagi emojini olib tashlash (ilovada emoji ishlatilmaydi)
function stripEmoji(s) {
  return (s || "").replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/gu, "").trim();
}

function resRow(iconName, cls, label, value) {
  return '<div class="res-row"><span class="' + cls + '">' + icon(iconName, 15, 2) + '</span>' +
    '<span class="rl">' + label + '</span><b>' + escapeHtml(String(value)) + '</b></div>';
}

function nowReadingCard(b) {
  if (!b) {
    return '<div class="card"><p class="section-sub" style="margin:0">Hozircha o‘qilayotgan kitob yo‘q.</p></div>';
  }
  const pr = bookProgress(b);
  return '<div class="now-card" data-action="go-book" data-id="' + b.id + '">' +
    '<div class="now-top">' +
    coverHtml(b.title, b.author, "now-cover", b.cover_file) +
    '<div class="now-info">' +
    '<p class="now-title">' + escapeHtml(b.title) + '</p>' +
    '<p class="now-author">' + escapeHtml(b.author || "") + '</p>' +
    (pr.known ? '<div class="progress-track"><div class="progress-fill" style="width:' + pr.pct + '%"></div></div>' : "") +
    '<div class="now-meta"><b>' + b.pages_read + '</b>' + (pr.known ? '/' + b.total_pages + ' bet <span class="dot">·</span> <b>' + pr.pct + '%</b>' : ' bet o‘qildi') + '</div>' +
    '</div></div>' +
    '<div class="now-foot">' +
    '<div><span class="ic-rank">' + icon("award", 15, 2) + '</span> <b>' + (b.tests_done || 0) + '</b> ta test</div>' +
    '<div><span class="ic-audio">' + icon("mic", 15, 2) + '</span> <b>' + (b.audio_count || 0) + '</b> ta audio xulosa</div>' +
    '</div></div>';
}

function bookCardOrEmpty(b, emptyText) {
  if (!b) return '<div class="card"><p class="section-sub" style="margin:0">' + emptyText + '</p></div>';
  const pr = bookProgress(b);
  return '<div class="card book-card" data-action="go-book" data-id="' + b.id + '" style="cursor:pointer">' +
    coverHtml(b.title, b.author, "book-cover", b.cover_file) +
    '<div class="book-info">' +
    '<p class="book-title">' + escapeHtml(b.title) + '</p>' +
    '<p class="book-author">' + escapeHtml(b.author || "") + '</p>' +
    (pr.known ? '<div class="progress-track"><div class="progress-fill" style="width:' + pr.pct + '%"></div></div>' : "") +
    '<div class="progress-label">' + pr.label + '</div>' +
    '</div></div>';
}

async function renderChildDetailPage(childId) {
  const main = document.getElementById("app-main");
  main.innerHTML = '<div class="empty-state"><div class="spinner"></div>Yuklanmoqda…</div>';
  const data = await api("/api/parent/home/" + childId);
  const c = State.childrenCache.filter(function (x) { return x.id === childId; })[0] || {};

  let html = '<div class="detail-topbar">' +
    '<button class="back-link" data-action="back-to-home">' + icon("arrow-left", 16, 2) + ' Orqaga</button>' +
    '</div>';

  html += '<div class="child-detail-header">' +
    '<span class="avatar-circle" style="width:64px;height:64px">' + avatarMarkup(c.avatar_id || "fox", 64) + '</span>' +
    '<p class="child-detail-name">' + escapeHtml(data.name || c.name || "") + '</p>' +
    '</div>';

  html += '<div class="stat-grid">' +
    '<div class="stat-box"><div class="num">' + data.streak + '</div><div class="lbl">Ketma-ket kun</div></div>' +
    '<div class="stat-box"><div class="num">' + data.coins + '</div><div class="lbl">Bilig</div></div>' +
    '<div class="stat-box" style="font-size:13px"><div class="num" style="font-size:15px">' + escapeHtml(stripEmoji(data.rank)) + '</div><div class="lbl">Daraja</div></div>' +
    '</div>';

  html += '<p class="eyebrow">O‘qiyotgan kitoblari</p>';
  if (data.active_books && data.active_books.length) {
    data.active_books.forEach(function (b) {
      html += bookCardOrEmpty(b, "");
    });
  } else {
    html += '<div class="card"><p class="section-sub" style="margin:0">Hozircha o‘qilayotgan kitob yo‘q.</p></div>';
  }

  html += '<p class="eyebrow">So‘nggi faoliyat</p>';
  if (data.recent_activity && data.recent_activity.length) {
    html += '<div class="card">' + data.recent_activity.map(function (a) {
      return '<div class="activity-row">' +
        '<div class="activity-dot">' + icon("book-open", 15, 2) + '</div>' +
        '<div style="min-width:0"><p style="margin:0;font-size:15px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + escapeHtml(a.title) + '</p>' +
        '<p style="margin:0;font-size:13.5px;color:var(--text-faint)">+' + a.pages_added + ' bet o‘qidi · ' + escapeHtml((a.created_at || "").slice(0, 16).replace("T", " ")) + '</p></div>' +
        '</div>';
    }).join("") + '</div>';
  } else {
    html += '<div class="card"><p class="section-sub" style="margin:0">Hali faoliyat qayd etilmagan.</p></div>';
  }

  if (data.last_report && (data.last_report.summary || data.last_report.conversation_topic)) {
    html += '<p class="eyebrow">AI Ustoz xulosasi</p>' +
      '<div class="card"><div style="display:flex;gap:10px;align-items:flex-start;">' +
      '<div style="color:var(--brand);flex-shrink:0;margin-top:2px">' + icon("message-circle", 20, 1.8) + '</div>' +
      '<div><p style="margin:0 0 8px;font-size:15.5px;line-height:1.5">' + escapeHtml(data.last_report.summary || "") + '</p>' +
      (data.last_report.conversation_topic ? '<p style="margin:0;font-size:14.5px;color:var(--text-soft)"><b>Kechki suhbat mavzusi:</b> ' + escapeHtml(data.last_report.conversation_topic) + '</p>' : "") +
      '</div></div></div>';
  }

  main.innerHTML = html;
}

// ==========================================================
// TAB 1: BOSH SAHIFA — BOLA
// ==========================================================
async function renderChildHome() {
  const data = await api("/api/child/home" + asChildQuery());

  // ---- 0. Kutib olish — bola ko‘rmagan nishonlar bo‘lsa ----
  let html = welcomeHtml(data.name, data.unseen_badges);

  // ---- 1. O‘qilayotgan kitob ----
  if (data.current_book) {
    const b = data.current_book;
    const pr = bookProgress(b);
    html += '<article class="reading-card" data-action="open-book" data-id="' + b.id + '">' +
      '<p class="rc-eyebrow">O‘qishda davom eting</p>' +
      '<div class="rc-top">' +
      coverHtml(b.title, b.author, "rc-cover", b.cover_file) +
      '<div class="rc-info">' +
      '<p class="rc-title">' + escapeHtml(b.title) + '</p>' +
      '<p class="rc-author">' + escapeHtml(b.author || "") + '</p>' +
      (pr.known
        ? '<div class="rc-bar"><i style="width:' + pr.pct + '%"></i></div>' +
          '<p class="rc-meta"><b>' + b.pages_read + '</b> / ' + b.total_pages + ' bet' +
          '<span class="rc-pct">' + pr.pct + '%</span></p>'
        : '<p class="rc-meta"><b>' + b.pages_read + '</b> bet o‘qildi</p>') +
      '</div></div>' +
      '<div class="rc-foot">' +
      '<span class="rc-stat">' + icon("award", 15, 2) + '<b>' + (b.tests_done || 0) + '</b> ta test</span>' +
      '<span class="rc-stat">' + icon("mic", 15, 2) + '<b>' + (b.audio_count || 0) + '</b> ta audio</span>' +
      '<span class="rc-go">Davom etish ' + icon("arrow-right", 15, 2.2) + '</span>' +
      '</div></article>';
  } else {
    html += '<div class="hero-card" data-action="go-plans-tab">' +
      '<div class="icon-circle">' + icon("book-open", 22, 1.8) + '</div>' +
      '<p class="hc-title">Hozircha o‘qiladigan kitob yo‘q</p>' +
      '<div style="font-size:15px;font-weight:600;display:flex;align-items:center;gap:6px">Rejalarni ko‘rish ' + icon("arrow-right", 15, 2) + '</div>' +
      '</div>';
  }

  // ---- 2. So‘nggi natijalar (ilgari bu joyda 3 ta statistika qutisi turardi) ----
  html += '<p class="sec-label">So‘nggi natijalar</p>' +
    '<div class="res-card is-tappable" data-action="open-result"><div class="res-list">' +
    resRow("book-open", "ic-brand", "Jami o‘qilgan", (data.total_pages || 0) + " bet") +
    resRow("check-circle", "ic-leaf", "Tugatilgan kitob", (data.completed_books || 0) + " ta") +
    resRow("coin", "ic-coin", "To‘plangan Bilig", data.coins + " ta") +
    resRow("star", "ic-rank", "Yangi nishon", data.last_badge ? stripEmoji(data.last_badge) : "hali yo‘q") +
    resRow("mic", "ic-audio", "AI audio bahosi", data.last_audio_score ? data.last_audio_score + "/5" : "hali yo‘q") +
    '</div></div>';

  // ---- 3. Haftalik chiziq (oxirgi 7 kun) ----
  html += weekStripHtml(data.week);

  // ---- 4. AI ustoz xulosasi (bolaning o‘ziga) ----
  html += childNoteHtml(data.child_note);

  // ---- 5. Nishonlar ----
  html += badgesBlockHtml(data.badges);

  // ---- 6. Kitoblarim (3 tasi; qolgani Rejalar bo‘limida) ----
  const books = data.shelf_books || data.active_books || [];
  html += '<p class="sec-label">Kitoblarim' +
    (books.length > 3 ? ' <span class="sw" data-action="go-plans-tab">' + icon("chevron-right", 12, 2.4) + '</span>' : "") + '</p>' +
    shelfHtml(books.slice(0, 3), "Hozircha kitob yo‘q — Rejalar bo‘limiga qarang.");

  document.getElementById("app-main").innerHTML = html;
}

// AI ustozning bolaga aytgan iliq xabari — sodda va samimiy
function childNoteHtml(note) {
  if (!note) {
    return '<p class="sec-label">AI ustoz</p>' +
      '<div class="card"><p class="section-sub" style="margin:0">Kitob haqida ovozli xulosa yuborsang, AI ustoz senga maslahat beradi.</p></div>';
  }
  return '<p class="sec-label">AI ustoz</p>' +
    '<div class="card ai-card ai-child">' +
    '<div class="ai-top"><span class="ai-ic">' + icon("message-circle", 19, 1.9) + '</span>' +
    '<p class="ai-text">' + escapeHtml(note) + '</p></div></div>';
}

// ==========================================================
// TANLOV KARTOCHKASI
// ----------------------------------------------------------
// Butun ilovadagi barcha tanlov ro‘yxatlari shu bitta funksiya orqali
// chiziladi. Shuning uchun kelajakda ko‘rinishni o‘zgartirish uchun
// faqat shu yerni tahrirlash yetarli.
//   ic     — ikona nomi (ICON_PATHS dan)
//   title  — tugma nomi
//   desc   — SODDA IZOH: foydalanuvchi nega buni bosishi kerak
//   action — data-action qiymati
//   data   — qo‘shimcha data-* atributlari, masalan {mode: "quick"}
//   tone   — ikona rangi: "" (ko‘k) | "gold" | "success" | "soft"
//   tag    — o‘ng yuqorida kichik yorliq, masalan "Tavsiya"
// ==========================================================
function choiceCard(cfg) {
  let attrs = "";
  const data = cfg.data || {};
  Object.keys(data).forEach(function (k) {
    attrs += ' data-' + k + '="' + escapeHtml(String(data[k])) + '"';
  });
  return '<button class="choice-card' + (cfg.tone ? " tone-" + cfg.tone : "") + '"' +
    ' data-action="' + cfg.action + '"' + attrs + '>' +
    '<span class="choice-ic">' + icon(cfg.ic, 22, 1.9) + '</span>' +
    '<span class="choice-tx">' +
      '<span class="choice-t">' + cfg.title +
        (cfg.tag ? '<span class="choice-tag">' + cfg.tag + '</span>' : "") +
      '</span>' +
      (cfg.desc ? '<span class="choice-d">' + cfg.desc + '</span>' : "") +
    '</span>' +
    '<span class="choice-go">' + icon("chevron-right", 18, 2.2) + '</span>' +
    '</button>';
}

function emptyState(iconName, title, sub) {
  return '<div class="empty-state"><div class="em-icon">' + icon(iconName, 38, 1.4) + '</div><p style="font-weight:700;color:var(--text);margin:0 0 4px">' + title + '</p><p style="margin:0">' + (sub || "") + '</p></div>';
}

// ==========================================================
// TAB: BOLAXONA (faqat ota-ona) — farzandni tanlab, uning ekraniga kirish
// ==========================================================
// Farzandning shaxsiy ID raqami har doim ko‘rinib turadi — u alohida
// telefondan kirmoqchi bo‘lganda aynan shu kod kerak bo‘ladi.
function childCodeLine(c) {
  if (c.linked) {
    return '<p class="kid-id kid-id-done">O‘z telefonidan ulangan</p>';
  }
  if (!c.child_code) return "";
  return '<p class="kid-id" data-action="copy-code" data-code="' + escapeHtml(c.child_code) + '">ID: <b>' +
    escapeHtml(c.child_code) + '</b> ' + icon("copy", 12, 2) + '</p>';
}

async function renderBolaxonaTab() {
  const main = document.getElementById("app-main");
  if (!State.childrenCache.length) {
    main.innerHTML = emptyState("users", "Hali farzand qo‘shilmagan", "Bosh sahifadagi «Farzand qo‘shish» orqali qo‘shing.");
    return;
  }
  main.innerHTML = '<p class="section-sub">Farzandingiz ekraniga kirib, kitob o‘qish, testlar va do‘kondan foydalanishni ular nomidan bajarishingiz mumkin.</p>' +
    State.childrenCache.map(function (c) {
      return '<div class="card" style="display:flex;align-items:center;justify-content:space-between;gap:10px">' +
        '<div style="display:flex;align-items:center;gap:10px"><span class="avatar-circle" style="width:44px;height:44px;display:block;box-shadow:none;border-radius:50%;overflow:hidden">' + avatarMarkup(c.avatar_id || "fox", 44) + '</span>' +
        '<div><p style="margin:0;font-weight:700;font-size:16px">' + escapeHtml(c.name) + '</p>' +
        '<p style="margin:0;font-size:14px;color:var(--text-faint)">Yoshi: ' + c.age + '</p>' +
        childCodeLine(c) + '</div></div>' +
        '<div class="kid-actions">' +
        '<button class="btn btn-outline btn-icon" title="Tahrirlash" data-action="edit-child" data-id="' + c.id + '" data-name="' + escapeHtml(c.name) + '" data-age="' + (c.age || "") + '" data-avatar="' + (c.avatar_id || "fox") + '">' + icon("edit", 15, 2) + '</button>' +
        '<button class="btn btn-primary" style="padding:9px 16px;font-size:15px" data-action="enter-bolaxona" data-id="' + c.id + '" data-name="' + escapeHtml(c.name) + '">Kirish</button>' +
        '</div></div>';
    }).join("") + demoPanelHtml();
}

// Namoyish paneli — faqat loyiha egasiga ko‘rinadi.
// Investorlarga ilovani to‘la ko‘rsatish uchun bitta farzand profilini
// haqiqiyga o‘xshash natijalar bilan to‘ldiradi.
function demoPanelHtml() {
  if (!State.me || !State.me.is_admin) return "";
  const rows = State.childrenCache.map(function (c) {
    return '<div class="demo-row"><span>' + escapeHtml(c.name) + '</span>' +
      '<span class="demo-btns">' +
      '<button class="btn btn-outline" data-action="demo-fill" data-id="' + c.id + '" data-name="' + escapeHtml(c.name) + '">To‘ldirish</button>' +
      '<button class="btn btn-outline" data-action="demo-clear" data-id="' + c.id + '" data-name="' + escapeHtml(c.name) + '">Tozalash</button>' +
      '</span></div>';
  }).join("");
  return '<p class="section-title">Namoyish ma\'lumoti</p>' +
    '<div class="card demo-card">' +
    '<p class="section-sub" style="margin:0 0 10px">Faqat sizga ko‘rinadi. Tanlangan farzand profili namoyish uchun to‘liq natijalar bilan to‘ldiriladi.</p>' +
    rows + '</div>';
}

async function demoFill(childId, name) {
  if (!confirm(name + " profili namoyish ma'lumoti bilan to‘ldiriladi.\n\nDIQQAT: uning hozirgi kitoblari va natijalari o‘chib ketadi. Davom etamizmi?")) return;
  const res = await api("/api/admin/demo", { method: "POST", body: { child_id: childId, action: "fill" } });
  toast(res.books + " ta kitob, " + res.reports + " ta AI tahlil qo‘shildi");
  State.childrenCache = await api("/api/parent/children");
  switchTab("home");
}

async function demoClear(childId, name) {
  if (!confirm(name + " ning BARCHA kitoblari va natijalari o‘chiriladi. Davom etamizmi?")) return;
  await api("/api/admin/demo", { method: "POST", body: { child_id: childId, action: "clear" } });
  toast("Tozalandi");
  switchTab("bolaxona");
}

// ==========================================================
// TAB 2: REJALAR — OTA-ONA
// ==========================================================
async function renderParentPlans() {
  // Faqat tanlangan (faol) farzandning rejalari ko‘rsatiladi
  const q = State.selectedChildId ? "?child_id=" + State.selectedChildId : "";
  const plans = await api("/api/parent/plans" + q);
  const main = document.getElementById("app-main");
  let html = childSwitcherHtml() +
    '<button class="btn btn-primary btn-block" data-action="open-add-plan" style="display:flex;align-items:center;justify-content:center;gap:6px">' + icon("plus", 17, 2) + ' Yangi kitob qo‘shish</button>';

  // Bir martalik kitoblar va marafonlar aralashib ketmasligi kerak —
  // ular butunlay boshqa narsa: biri bitta kitob, ikkinchisi uzoq musobaqa.
  const singleActive = [];
  const singleDone = [];
  const marathons = [];
  plans.forEach(function (p) {
    if (p.type === "marathon") { marathons.push(p); return; }
    p.books.forEach(function (b) { (b.completed ? singleDone : singleActive).push(b); });
  });

  if (!singleActive.length && !singleDone.length && !marathons.length) {
    html += emptyState("book-open", "Hali reja yo‘q", "Yuqoridagi tugma orqali birinchi kitobni qo‘shing.");
    main.innerHTML = html;
    return;
  }

  if (singleActive.length) {
    html += '<p class="section-title">Alohida kitoblar</p>';
    singleActive.forEach(function (b) { html += bookCardHtml(b, true); });
  }

  if (marathons.length) {
    html += '<p class="section-title">Marafonlar</p>';
    marathons.forEach(function (p) { html += marathonCardHtml(p); });
  }

  if (singleDone.length) {
    html += '<p class="section-title">Tugallangan</p>';
    singleDone.forEach(function (b) { html += bookCardHtml(b, true); });
  }

  main.innerHTML = html;
}

// Marafon — bitta yaxlit karta: nomi, sovrini, umumiy yo‘li va ichidagi kitoblar
function marathonCardHtml(p) {
  const total = p.books.length;
  const done = p.books.filter(function (b) { return b.completed; }).length;
  const pct = total ? Math.round(done / total * 100) : 0;
  return '<section class="marathon">' +
    '<div class="mr-head">' +
    '<div class="mr-ic">' + icon("award", 18, 1.9) + '</div>' +
    '<div style="min-width:0;flex:1">' +
    '<p class="mr-name">' + escapeHtml(p.name) + '</p>' +
    (p.prize ? '<p class="mr-prize">Marra sovrini: <b>' + escapeHtml(p.prize) + '</b></p>' : '') +
    '</div>' +
    '<span class="mr-count">' + done + '/' + total + '</span>' +
    '</div>' +
    '<div class="progress-track"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
    '<div class="mr-books">' +
    (total ? p.books.map(function (b) { return bookCardHtml(b, true); }).join("")
           : '<p class="section-sub" style="margin:8px 0 0">Bu marafonga hali kitob qo‘shilmagan.</p>') +
    '</div></section>';
}

function bookCardHtml(b, isParent) {
  const pr = bookProgress(b);
  let testBadges = "";
  if (b.test_final_only) {
    // Testi o‘qish davomida yig‘ilgan — oraliq bosqichlar yo‘q,
    // shuning uchun ularni belgilarda ham ko‘rsatmaymiz.
    testBadges = '<div class="badge-row">' +
      '<span class="badge ' + (b.final_test_done ? "done" : "pending") + '">Yakuniy test</span>' +
      '<span class="badge ' + (b.has_voice ? "done" : "pending") + '">Ovozli tahlil</span>' +
      '</div>';
  } else if (b.mid_test_1_done !== undefined) {
    testBadges = '<div class="badge-row">' +
      '<span class="badge ' + (b.mid_test_1_done ? "done" : "pending") + '">1-oraliq test</span>' +
      '<span class="badge ' + (b.mid_test_2_done ? "done" : "pending") + '">2-oraliq test</span>' +
      '<span class="badge ' + (b.final_test_done ? "done" : "pending") + '">Yakuniy test</span>' +
      '<span class="badge ' + (b.has_voice ? "done" : "pending") + '">Ovozli tahlil</span>' +
      '</div>';
  }
  return '<div class="card book-card" id="book-card-' + b.id + '" ' + (isParent ? "" : 'data-action="open-book" data-id="' + b.id + '"') + '>' +
    coverHtml(b.title, b.author, "book-cover", b.cover_file) +
    '<div class="book-info">' +
    '<p class="book-title">' + escapeHtml(b.title) + '</p>' +
    '<p class="book-author">' + escapeHtml(b.author || "") + '</p>' +
    (pr.known ? '<div class="progress-track"><div class="progress-fill" style="width:' + pr.pct + '%"></div></div>' : "") +
    '<div class="progress-label">' + pr.label + '</div>' +
    testBadges +
    (isParent ? '<div class="action-row">' +
      '<button class="btn btn-outline" data-action="open-generate-test" data-id="' + b.id + '">Test tuzish</button>' +
      '<button class="btn btn-danger" data-action="delete-book" data-id="' + b.id + '">' + icon("trash", 14, 2) + '</button>' +
      '</div>' : "") +
    '</div></div>';
}

// ==========================================================
// AI SAVOLLAR BANKI — KO‘P SAHIFALI RASM JAVONI
// ----------------------------------------------------------
// Ilgari bu yerda oddiy <input type="file" multiple> turardi. Telefonda
// kamera bilan rasm bittalab olinadi, va har yangi rasm avvalgisining
// O‘RNINI EGALLARDI — shuning uchun 5-10 ta sahifa hech qachon
// yig‘ilmasdi. Endi rasmlar javonga QO‘SHILIB boradi: har birining
// kichik ko‘rinishi chiqadi, keraksizini o‘chirish mumkin, va nechta
// sahifa yig‘ilgani chiziqda ko‘rinib turadi.
// ==========================================================
const TEST_SHOTS_MIN = 3;    // shundan kam bo‘lsa test sifatsiz chiqadi
const TEST_SHOTS_GOOD = 5;   // "yetarli" chizig‘i
const TEST_SHOTS_MAX = 12;   // bundan ortig‘i AI ga ortiqcha yuk

const TestShots = {
  bookId: null,
  items: [],      // { blob, url }

  open: function (bookId) {
    this.bookId = bookId;
    this.items.forEach(function (it) { URL.revokeObjectURL(it.url); });
    this.items = [];
    openModal("Kitob testini tuzish",
      '<p class="section-sub" style="margin-top:-4px">Farzandingiz kitobni tushunganini tekshiradigan savollar kerak. ' +
      'Kitobning ichidan ' + TEST_SHOTS_GOOD + '-10 ta sahifani suratga oling — AI o‘qib chiqib, savollarni o‘zi tuzadi.</p>' +
      '<div id="shot-body"></div>' +
      '<input type="file" id="shot-input" accept="image/*" multiple class="hidden" />'
    );
    const input = document.getElementById("shot-input");
    const self = this;
    input.addEventListener("change", async function () {
      const files = Array.prototype.slice.call(input.files || []);
      input.value = "";                       // bir xil rasmni qayta tanlash mumkin bo‘lsin
      for (let i = 0; i < files.length; i++) {
        if (self.items.length >= TEST_SHOTS_MAX) { toast("Ko‘pi bilan " + TEST_SHOTS_MAX + " ta sahifa"); break; }
        const prepared = await prepareImage(files[i], "text");
        self.items.push({ blob: prepared.blob, url: URL.createObjectURL(prepared.blob) });
        self.paint();
      }
    });
    this.paint();
  },

  paint: function () {
    const body = document.getElementById("shot-body");
    if (!body) return;
    const n = this.items.length;
    const cells = this.items.map(function (it, i) {
      return '<div class="shot-cell"><img src="' + it.url + '" alt="">' +
        '<button class="shot-del" data-action="shot-del" data-i="' + i + '">' + icon("x", 12, 2.6) + '</button></div>';
    }).join("");
    // Hali bitta ham rasm yo‘q — katta, aniq ko‘rinadigan tugma chiqadi.
    if (n === 0) {
      body.innerHTML =
        '<button class="shot-empty" data-action="shot-add">' + icon("camera", 26, 1.7) +
          '<span>Birinchi sahifani suratga olish</span>' +
          '<span style="font-size:13.5px;font-weight:500;color:var(--text-soft)">Har safar bittadan qo‘shaveresiz</span>' +
        '</button>' +
        '<p class="shot-hint">Kamida ' + TEST_SHOTS_MIN + ' ta sahifa kerak. ' + TEST_SHOTS_GOOD + ' ta bo‘lsa savollar aniqroq chiqadi.</p>' +
        '<button class="btn btn-primary btn-block" data-action="shot-submit" disabled>Testni tuzish</button>';
      return;
    }
    const addTile = n >= TEST_SHOTS_MAX ? "" :
      '<button class="shot-add" data-action="shot-add">' + icon("plus", 20, 2) + '</button>';
    const pct = Math.min(100, Math.round(n / TEST_SHOTS_GOOD * 100));
    let hint, okClass = "";
    if (n < TEST_SHOTS_MIN) hint = n + " ta sahifa — hali kam. Kamida " + TEST_SHOTS_MIN + " ta kerak.";
    else if (n < TEST_SHOTS_GOOD) hint = n + " ta sahifa — bo‘ladi, lekin " + TEST_SHOTS_GOOD + " ta bo‘lsa savollar aniqroq chiqadi.";
    else { hint = n + " ta sahifa — yetarli. Testni tuzsak bo‘ladi."; okClass = " is-ok"; }
    body.innerHTML =
      '<div class="shot-tray">' + cells + addTile + '</div>' +
      '<div class="shot-meter"><i style="width:' + pct + '%"></i></div>' +
      '<p class="shot-hint' + okClass + '">' + hint + '</p>' +
      '<button class="btn btn-primary btn-block" data-action="shot-submit"' + (n < TEST_SHOTS_MIN ? " disabled" : "") + '>' +
        'Testni tuzish (' + n + ' ta sahifa)</button>';
  },

  add: function () { document.getElementById("shot-input").click(); },

  remove: function (i) {
    const it = this.items[i];
    if (it) URL.revokeObjectURL(it.url);
    this.items.splice(i, 1);
    this.paint();
  },

  // Kutish oynasi. AI ishi uzoq davom etadi, shuning uchun foydalanuvchi
  // nima bo‘layotganini ko‘rib tursin.
  waitBox: function (text, sub) {
    openModal("Test tuzilmoqda",
      '<div class="empty-state" style="padding:26px 0">' +
        '<div class="spinner"></div>' +
        '<p style="font-weight:700;color:var(--text);margin:12px 0 4px">' + text + '</p>' +
        '<p style="margin:0">' + (sub || "") + '</p>' +
      '</div>');
  },

  fail: function (msg) {
    // Foydalanuvchi kutmasdan oynani yopgan bo‘lsa, daqiqalardan keyin
    // uni qaytadan ochib yubormaymiz — qisqa lenta bilan xabar beramiz.
    if (document.getElementById("modal-overlay").classList.contains("hidden")) {
      toast("Test tuzilmadi: " + msg);
      return;
    }
    openModal("Test tuzilmadi",
      '<p class="section-sub" style="margin-top:-4px">' + escapeHtml(msg) + '</p>' +
      '<p class="section-sub">Sahifalaringiz saqlanib qoldi — «Qayta urinish» ni bossangiz, ' +
      'ularni boshqatdan suratga olish shart emas.</p>' +
      '<button class="btn btn-primary btn-block" data-action="shot-submit">Qayta urinish</button>' +
      '<button class="btn btn-outline btn-block" data-action="close-modal">Yopish</button>');
  },

  submit: async function () {
    if (this.items.length < TEST_SHOTS_MIN) { toast("Kamida " + TEST_SHOTS_MIN + " ta sahifa kerak"); return; }
    const bookId = this.bookId;
    const fd = new FormData();
    this.items.forEach(function (it, i) { fd.append("photos", it.blob, "page" + (i + 1) + ".jpg"); });

    this.waitBox("Sahifalar yuborilmoqda…", "Internet sekin bo‘lsa biroz kutishga to‘g‘ri keladi.");
    let started;
    try {
      started = await api("/api/parent/books/" + bookId + "/generate_test", { method: "POST", body: fd });
    } catch (e) {
      this.fail(e.error || "Sahifalarni serverga yuborib bo‘lmadi. Internet aloqasini tekshiring.");
      return;
    }

    // Kitob umumiy bankda bor ekan — AI umuman chaqirilmadi, test darrov tayyor.
    if (started.from_bank) {
      this.done("Bu kitobning testi tayyor edi — " + started.count + " ta savol qo‘shildi");
      return;
    }

    // AI ishlayapti. Endi telefon aloqani ushlab turmaydi — vaqti-vaqti
    // bilan «tayyor bo‘ldimi?» deb so‘rab turadi. Shuning uchun ish
    // qanchalik uzoq davom etsa ham, aloqa uzilmaydi.
    this.waitBox("AI sahifalarni o‘qiyapti…", "Bu odatda yarim daqiqadan bir daqiqagacha davom etadi.");
    const self = this;
    const until = Date.now() + 4 * 60 * 1000;      // ko‘pi bilan 4 daqiqa kutamiz
    while (Date.now() < until) {
      await new Promise(function (r) { setTimeout(r, 2500); });
      let st;
      try {
        st = await api("/api/parent/test_job/" + started.job_id);
      } catch (e) {
        continue;                                   // aloqa uzildi — keyingi urinishda so‘raymiz
      }
      if (st.status === "tayyor") { self.done(st.count + " ta savol tuzildi"); return; }
      if (st.status === "xato") { self.fail(st.error || "AI savollarni tuza olmadi."); return; }
    }
    this.fail("Kutish vaqti tugadi. Sahifalar soni kamroq bo‘lsa, tezroq bo‘lishi mumkin.");
  },

  done: function (msg) {
    this.items.forEach(function (it) { URL.revokeObjectURL(it.url); });
    this.items = [];
    closeModal();
    toast(msg);
  }
};

function openGenerateTestModal(bookId) { TestShots.open(bookId); }

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
  const head =
    '<p class="section-sub" style="margin-top:-4px">' + escapeHtml(b.author || "") + '</p>' +
    '<div class="progress-track"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
    '<div class="progress-label">' + b.pages_read + (b.total_pages ? "/" + b.total_pages : "") + ' bet</div>';

  // Ota-ona o‘z kabinetida turgan bo‘lsa, unga BOLANING tugmalari
  // ko‘rsatilmaydi: sahifani rasmga olish, ovozli xulosa va testlar —
  // bularni farzandning o‘zi bajaradi. Ota-ona esa kuzatadi va boshqaradi.
  if (!isChildView()) { openParentBookModal(bookId, b, head); return; }

  let testsHtml;
  if (b.has_test && b.test_final_only) {
    // Test o‘qish davomida yig‘ilgan yozuvlardan tuzilgan. U kitobning
    // hamma joyini qamramaydi, shuning uchun oraliq testlar berilmaydi —
    // bola kitobni tugatdim deganda bitta yakuniy test topshiradi.
    testsHtml = '<p class="eyebrow" style="margin-top:18px">Kitobni tugatding?</p>' +
      (b.final_test_done
        ? '<div class="card" style="text-align:center;font-weight:700;color:var(--success-deep)">' +
            'Yakuniy test topshirilgan</div>'
        : choiceCard({
            ic: "award", tone: "gold", action: "open-test",
            data: { id: bookId, stage: "final_test" },
            title: "Kitobni yakunladim",
            desc: "Oxirigacha o‘qib bo‘lgan bo‘lsang, yakuniy testni topshir va kitobni yopamiz."
          }));
  } else if (b.has_test) {
    testsHtml = '<p class="eyebrow" style="margin-top:18px">Bilim testlari</p><div class="action-row">' +
      '<button class="btn ' + (b.mid_test_1_done ? "btn-secondary" : "btn-outline") + '" data-action="open-test" data-id="' + bookId + '" data-stage="mid_test_1">1-oraliq ' + (b.mid_test_1_done ? "(bajarilgan)" : "") + '</button>' +
      '<button class="btn ' + (b.mid_test_2_done ? "btn-secondary" : "btn-outline") + '" data-action="open-test" data-id="' + bookId + '" data-stage="mid_test_2">2-oraliq ' + (b.mid_test_2_done ? "(bajarilgan)" : "") + '</button>' +
      '<button class="btn ' + (b.final_test_done ? "btn-secondary" : "btn-outline") + '" data-action="open-test" data-id="' + bookId + '" data-stage="final_test">Yakuniy ' + (b.final_test_done ? "(bajarilgan)" : "") + '</button>' +
      '</div>';
  } else {
    testsHtml = '<p class="section-sub" style="margin-top:18px">Bu kitob uchun test hali tuzilmagan.</p>';
  }
  openModal(b.title,
    head +
    '<p class="eyebrow" style="margin-top:18px">Qayergacha o‘qiding?</p>' +
    choiceCard({
      ic: "camera", action: "open-page-photo", data: { id: bookId }, tag: "Tez",
      title: "Sahifani rasmga olish",
      desc: "To‘xtagan betingni suratga ol — bet raqamini o‘zi o‘qiydi va Bilig beradi."
    }) +
    choiceCard({
      ic: "edit", tone: "soft", action: "open-page-manual", data: { id: bookId },
      title: "Bet raqamini o‘zim yozaman",
      desc: "Rasm chiqmasa yoki yorug‘lik yetmasa — raqamni qo‘lda kiritasan."
    }) +
    '<p class="eyebrow" style="margin-top:18px">Kitob haqida gapirib ber</p>' +
    choiceCard({
      ic: "mic", tone: "success", action: "open-voice", data: { id: bookId },
      title: b.has_voice ? "Ovozli xulosani qayta yuborish" : "Ovozli xulosa yuborish",
      desc: "Kitobni o‘z so‘zing bilan so‘zlab ber. AI Ustoz tinglaydi va maslahat beradi."
    }) +
    testsHtml
  );
}

// ==========================================================
// OTA-ONA KO‘RADIGAN KITOB OYNASI
// ----------------------------------------------------------
// Ota-onaning ishi boshqa: u o‘qimaydi, kuzatadi va tayyorlaydi.
// Farzand nomidan biror amal qilish kerak bo‘lsa, Bolaxonaga o‘tadi.
// ==========================================================
function statusRow(label, done, doneText, pendingText) {
  return '<div class="stat-line">' +
    '<span class="sl-ic ' + (done ? "is-done" : "") + '">' + icon(done ? "check" : "clock", 15, 2.2) + '</span>' +
    '<span class="sl-name">' + label + '</span>' +
    '<span class="sl-val' + (done ? " is-done" : "") + '">' + (done ? doneText : pendingText) + '</span>' +
    '</div>';
}

function openParentBookModal(bookId, b, head) {
  const child = State.childrenCache.filter(function (c) { return c.id === State.selectedChildId; })[0];
  const childName = child ? child.name : "Farzandingiz";

  let testLines;
  if (!b.has_test) {
    testLines = statusRow("Bilim testi", false, "", "hali tuzilmagan");
  } else if (b.test_final_only) {
    testLines = statusRow("Yakuniy test", b.final_test_done, "topshirilgan", "kutilmoqda");
  } else {
    testLines =
      statusRow("1-oraliq test", b.mid_test_1_done, "topshirilgan", "kutilmoqda") +
      statusRow("2-oraliq test", b.mid_test_2_done, "topshirilgan", "kutilmoqda") +
      statusRow("Yakuniy test", b.final_test_done, "topshirilgan", "kutilmoqda");
  }

  openModal(b.title,
    head +
    '<p class="eyebrow" style="margin-top:18px">' + escapeHtml(childName) + ' nima qildi</p>' +
    '<div class="card" style="padding:12px 14px">' +
      statusRow("O‘qigan sahifalar", b.pages_read > 0,
                b.pages_read + " bet", "hali boshlamagan") +
      statusRow("Ovozli xulosa", b.has_voice, "yuborgan", "yuborilmagan") +
      testLines +
    '</div>' +

    '<p class="eyebrow" style="margin-top:18px">Siz nima qilishingiz mumkin</p>' +
    (b.has_test
      ? choiceCard({
          ic: "help", tone: "soft", action: "open-generate-test", data: { id: bookId },
          title: "Testni qaytadan tuzish",
          desc: "Savollar mos kelmasa, kitob sahifalarini suratga olib yangisini tuzasiz."
        })
      : choiceCard({
          ic: "help", action: "open-generate-test", data: { id: bookId }, tag: "Tavsiya",
          title: "Test tuzish",
          desc: "Kitobning 5-10 ta sahifasini suratga oling — AI savollarni o‘zi tuzadi."
        })) +
    choiceCard({
      ic: "users", tone: "gold", action: "enter-bolaxona",
      data: { id: State.selectedChildId, name: childName },
      title: "Bolaxonaga kirish",
      desc: escapeHtml(childName) + " nomidan sahifa belgilash yoki ovozli xulosa yuborish."
    }) +
    choiceCard({
      ic: "trash", tone: "soft", action: "delete-book", data: { id: bookId },
      title: "Kitobni o‘chirish",
      desc: "Kitob rejadan olib tashlanadi. O‘qilgan sahifalar tarixi saqlanib qoladi."
    })
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
    zone.innerHTML = '<div class="spinner"></div>Rasm tayyorlanmoqda…';
    zone.classList.add("has-file");
    const prepared = await prepareImage(input.files[0], "page");
    if (prepared.sharpness < SHARPNESS_MIN) {
      showBlurWarning(zone, function () { sendPagePhoto(bookId, prepared.blob, zone); });
      return;
    }
    sendPagePhoto(bookId, prepared.blob, zone);
  };
}

// Xira rasm haqida ogohlantirish. Majburlamaymiz — bola baribir yuborishi mumkin.
function showBlurWarning(zone, onSendAnyway) {
  zone.classList.remove("has-file");
  zone.innerHTML =
    '<div style="font-weight:700;margin-bottom:4px">Rasm xira chiqdi</div>' +
    '<div style="font-size:14.5px;color:var(--text-soft);margin-bottom:10px">Bet raqami o‘qilmasligi mumkin. Yorug‘roq joyda, telefonni qimirlatmay qayta oling.</div>' +
    '<div style="display:flex;gap:8px;justify-content:center">' +
    '<button class="btn btn-primary" id="blur-retake" style="padding:8px 14px;font-size:15px">Qaytadan olish</button>' +
    '<button class="btn btn-outline" id="blur-anyway" style="padding:8px 14px;font-size:15px">Baribir yuborish</button>' +
    '</div>';
  document.getElementById("blur-anyway").onclick = function (ev) {
    ev.stopPropagation();
    zone.innerHTML = '<div class="spinner"></div>Tekshirilmoqda…';
    zone.classList.add("has-file");
    onSendAnyway();
  };
  // "Qaytadan olish" tugmasi bosilganda zone'ning o‘z bosilishi ishlaydi
  // (ya'ni kamera qaytadan ochiladi) — qo‘shimcha kod kerak emas.
}

async function sendPagePhoto(bookId, blob, zone) {
  zone.innerHTML = '<div class="spinner"></div>Tekshirilmoqda…';
  zone.classList.add("has-file");
  const fd = new FormData();
  fd.append("photo", blob, "page.jpg");
  try {
    const res = await api("/api/child/book/" + bookId + "/page_photo" + asChildQuery(), { method: "POST", body: fd });
    if (!res.ok) { toast(res.message || "Qaytadan urinib ko‘ring"); closeModal(); return; }
    showPageResult(res);
  } catch (e) { toast(e.error || "Xatolik"); closeModal(); }
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
  // Nishon olingan bo‘lsa — avval to‘liq ekran tabrik, keyin natija oynasi.
  if (res.new_badges && res.new_badges.length) {
    celebrate(res.new_badges, function () { showPageResultModal(res); });
    return;
  }
  // Nishon yo‘q, lekin lahza arziydi — maskot lentasi chiqadi.
  if (res.streak_up) {
    mascotToast("sherbola-galaba", res.streak + "-kun ketma-ket!",
                "Bir kun ham qoldirmading. Zo‘rsan.");
  } else if (res.earned_bilig >= 5) {
    mascotToast("qorbars-tanga", "+" + res.earned_bilig + " Bilig!",
                "Xazinang o‘syapti — jami " + res.balance + " ta.");
  }
  showPageResultModal(res);
}
function showPageResultModal(res) {
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

// ==========================================================
// AUDIONI AI TUSHUNADIGAN FORMATGA O‘GIRISH
// ----------------------------------------------------------
// Brauzer ovozni o‘z formatida yozadi: Chrome/Android — WEBM,
// iPhone — MP4. AI esa bu formatlarni qabul qilmaydi va so‘rovni bir
// zumda rad etadi. Shuning uchun telefonning o‘zida WAV ga o‘giramiz —
// bu format hamma joyda ishlaydi.
// Ovoz 16 kHz, bir kanalga tushiriladi: nutq uchun shu yetarli va
// fayl bir necha barobar yengil bo‘ladi.
// ==========================================================
const VOICE_SAMPLE_RATE = 16000;
const VOICE_MAX_SECONDS = 150;      // 2,5 daqiqa — bundan uzog‘i shart emas

function encodeWav(samples, rate) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buf);
  const str = function (pos, s) { for (let i = 0; i < s.length; i++) view.setUint8(pos + i, s.charCodeAt(i)); };
  str(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  str(8, "WAVEfmt ");
  view.setUint32(16, 16, true);          // fmt bo‘limi uzunligi
  view.setUint16(20, 1, true);           // PCM
  view.setUint16(22, 1, true);           // bir kanal
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);          // 16 bit
  str(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let p = 44;
  for (let i = 0; i < samples.length; i++) {
    let v = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(p, v < 0 ? v * 0x8000 : v * 0x7FFF, true);
    p += 2;
  }
  return new Blob([buf], { type: "audio/wav" });
}

async function audioToWav(blob) {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return blob;                       // eski brauzer — borini yuboramiz
  const bytes = await blob.arrayBuffer();
  const ctx = new Ctx();
  let decoded;
  try {
    decoded = await new Promise(function (res, rej) {
      const p = ctx.decodeAudioData(bytes.slice(0), res, rej);
      if (p && p.then) p.then(res, rej);       // yangi brauzerlarda Promise qaytadi
    });
  } catch (e) {
    try { ctx.close(); } catch (e2) {}
    return blob;                               // ocholmadik — borini yuboramiz
  }
  // Kanallarni qo‘shib, bitta kanalga tushiramiz
  const chans = [];
  for (let c = 0; c < decoded.numberOfChannels; c++) chans.push(decoded.getChannelData(c));
  const mono = new Float32Array(decoded.length);
  for (let i = 0; i < decoded.length; i++) {
    let sum = 0;
    for (let c = 0; c < chans.length; c++) sum += chans[c][i];
    mono[i] = sum / chans.length;
  }
  // 16 kHz ga tushiramiz
  const ratio = decoded.sampleRate / VOICE_SAMPLE_RATE;
  let out = mono;
  if (ratio > 1) {
    const n = Math.floor(mono.length / ratio);
    out = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      // Oraliqdagi qiymatlar o‘rtachasi — shovqin kamayadi
      const from = Math.floor(i * ratio), to = Math.min(mono.length, Math.floor((i + 1) * ratio));
      let sum = 0, k = 0;
      for (let j = from; j < to; j++) { sum += mono[j]; k++; }
      out[i] = k ? sum / k : 0;
    }
  }
  try { ctx.close(); } catch (e) {}
  return encodeWav(out, ratio > 1 ? VOICE_SAMPLE_RATE : decoded.sampleRate);
}

function openVoiceModal(bookId) {
  openModal("Ovozli xulosa",
    '<p class="section-sub">Kitob haqida 1-2 daqiqa gapirib bering: nima haqida edi, sizga nima yoqdi?</p>' +
    '<div style="text-align:center;padding:16px 0">' +
    '<button id="rec-btn" class="icon-btn" style="width:76px;height:76px;border-radius:50%;background:var(--brand);color:#fff;margin:0 auto">' + icon("mic", 28, 1.7) + '</button>' +
    '<div id="rec-time" class="card-meta" style="margin-top:10px;color:var(--text-soft);font-size:15px">Yozishni boshlash uchun bosing</div>' +
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
        recordTimer = setInterval(function () {
          recordSeconds++;
          timeEl.textContent = "Yozilmoqda… " + recordSeconds + "s";
          // Juda uzun yozuv faylni og‘irlashtiradi va sekin internetda
          // yuborilmaydi. 2,5 daqiqada o‘zi to‘xtaydi — bu yetarli.
          if (recordSeconds >= VOICE_MAX_SECONDS) {
            mediaRecorder.stop();
            clearInterval(recordTimer);
            recBtn.innerHTML = icon("mic", 28, 1.7);
            toast("Yozuv " + Math.round(VOICE_MAX_SECONDS / 60) + " daqiqada to‘xtadi — bu yetarli");
          }
        }, 1000);
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
    openModal("AI Ustoz tinglamoqda",
      '<div class="empty-state" style="padding:26px 0"><div class="spinner"></div>' +
      '<p style="font-weight:700;color:var(--text);margin:12px 0 4px">Ovoz tayyorlanmoqda…</p></div>');
    // Telefonning o‘z formati (WEBM/MP4) AI ga to‘g‘ri kelmaydi — WAV ga o‘giramiz.
    let sendBlob = recordedBlob;
    try { sendBlob = await audioToWav(recordedBlob); } catch (e) { sendBlob = recordedBlob; }
    if (!sendBlob || !sendBlob.size) { toast("Ovoz yozilmadi. Qaytadan urinib ko‘ring."); closeModal(); return; }
    openModal("AI Ustoz tinglamoqda",
      '<div class="empty-state" style="padding:26px 0"><div class="spinner"></div>' +
      '<p style="font-weight:700;color:var(--text);margin:12px 0 4px">AI Ustoz tinglayapti…</p>' +
      '<p style="margin:0">Bu yarim daqiqacha davom etadi.</p></div>');
    const fd = new FormData();
    const ext = (sendBlob.type || "").indexOf("wav") >= 0 ? "wav" : "webm";
    fd.append("audio", sendBlob, "summary." + ext);
    try {
      const res = await api("/api/child/book/" + bookId + "/voice" + asChildQuery(), { method: "POST", body: fd });
      if (res.bonus_bilig >= 4) {
        mascotToast("olmaxon-2", "AI ustoz seni tingladi",
                    "+" + res.bonus_bilig + " bonus Bilig — nutqing ravon edi.");
      }
      const showVoice = function () { openModal("AI Ustoz fikri",
        '<div class="stat-grid" style="grid-template-columns:1fr">' +
        '<div class="stat-box"><div class="num">+' + res.bonus_bilig + '</div><div class="lbl">bonus Bilig</div></div>' +
        '</div>' +
        '<div class="card">' + escapeHtml(res.feedback) + '</div>' +
        '<button class="btn btn-primary btn-block" data-action="close-modal">Ajoyib</button>'
      ); };
      if (res.new_badges && res.new_badges.length) celebrate(res.new_badges, showVoice);
      else showVoice();
      refreshHeader();
    } catch (e) {
      // Sababni YASHIRMAYMIZ — «xatolik» degan bo‘sh gap hech kimga yordam bermaydi.
      closeModal();
      const reason = e.error || e.message || "Server javob bermadi. Internet aloqasini tekshiring.";
      openModal("Ovozli xulosa yuborilmadi",
        '<p class="section-sub" style="margin-top:-4px;color:var(--text);font-weight:600">' +
          'AI ovozni tahlil qila olmadi.</p>' +
        '<p class="section-sub" style="font-size:13.5px">' + escapeHtml(reason) + '</p>' +
        '<button class="btn btn-primary btn-block" data-action="open-voice" data-id="' + bookId + '">Qaytadan urinish</button>' +
        '<button class="btn btn-outline btn-block" data-action="close-modal">Yopish</button>');
    }
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
    mascotToast("qaldirgoch-tekshiruv", res.correct + "/" + res.total + " to‘g‘ri javob",
                res.percent >= 80 ? "Kitobni chindan tushunibsan." : "Yaxshi urinish — davom et.");
    const showRes = function () { openModal("Natija",
      '<div class="stat-grid">' +
      '<div class="stat-box"><div class="num">' + res.correct + '/' + res.total + '</div><div class="lbl">To‘g‘ri javob</div></div>' +
      '<div class="stat-box"><div class="num">' + res.percent + '%</div><div class="lbl">Natija</div></div>' +
      '<div class="stat-box"><div class="num">+' + res.earned_bilig + '</div><div class="lbl">Bilig</div></div>' +
      '</div>' +
      '<button class="btn btn-primary btn-block" data-action="close-modal">Yopish</button>'
    ); };
    if (res.new_badges && res.new_badges.length) celebrate(res.new_badges, showRes);
    else showRes();
    refreshHeader();
  }
};

async function openTestModal(bookId, stage) {
  const questions = await api("/api/child/book/" + bookId + "/test" + asChildQuery());
  Test.bookId = bookId; Test.stage = stage; Test.questions = questions; Test.answers = {};
  const stageLabel = { mid_test_1: "1-oraliq test", mid_test_2: "2-oraliq test", final_test: "Yakuniy test" }[stage];
  let html = '<p class="section-sub">' + questions.length + ' ta savol. Har biriga bittadan javob tanlang.</p>';
  questions.forEach(function (q) {
    html += '<div class="card"><p style="font-weight:700;font-size:16px;margin:0 0 10px">' + escapeHtml(q.question) + '</p>';
    (q.options || []).forEach(function (opt, oi) {
      html += '<button class="option-btn" data-action="select-test-opt" data-qid="' + q.id + '" data-val="' + escapeHtml(opt) + '">' +
        '<span class="opt-letter">' + "ABCDEF".charAt(oi) + '</span>' +
        '<span class="opt-text">' + escapeHtml(opt) + '</span></button>';
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
      html += '<div class="store-grid">' + data.items.map(function (i, idx) {
        return '<div class="store-item">' +
          '<div class="store-media tint-' + (idx % 4) + '"><div class="store-icon-lg">' + icon("gift", 22, 1.6) + '</div></div>' +
          '<div class="store-body">' +
          '<p class="store-name">' + escapeHtml(i.name) + '</p>' +
          '<div class="store-footer" style="margin-bottom:10px"><span class="store-price-chip">' + icon("coin", 12, 2.2) + ' ' + i.price + '</span></div>' +
          '<button class="btn ' + (i.affordable ? "btn-primary" : "btn-secondary") + ' btn-block" style="padding:8px;font-size:14.5px" data-action="buy-item" data-id="' + i.id + '" ' + (i.affordable ? "" : "disabled") + '>' +
          (i.affordable ? "Xarid qilish" : "Yetarli emas") + '</button>' +
          '</div></div>';
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
      html += '<div class="store-grid">' + items.map(function (i, idx) {
        return '<div class="store-item">' +
          '<div class="store-media tint-' + (idx % 4) + '">' +
          '<div class="store-icon-lg">' + icon("gift", 22, 1.6) + '</div>' +
          '<button class="store-edit-fab" data-action="open-store-edit" data-id="' + i.id + '" data-name="' + escapeHtml(i.name) + '" data-price="' + i.price + '" aria-label="Tahrirlash">' + icon("edit", 13, 2) + '</button>' +
          '</div>' +
          '<div class="store-body">' +
          '<p class="store-name">' + escapeHtml(i.name) + '</p>' +
          '<div class="store-footer"><span class="store-price-chip">' + icon("coin", 12, 2.2) + ' ' + i.price + '</span>' +
          '<button class="btn btn-outline" style="padding:6px 10px;font-size:14px" data-action="open-store-edit" data-id="' + i.id + '" data-name="' + escapeHtml(i.name) + '" data-price="' + i.price + '">Tahrirlash</button></div>' +
          '</div></div>';
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
  mascotToast("quyoncha-sovga", "Sovg‘ang buyurtma qilindi",
              "Ota-onangga xabar yubordik.");
  refreshHeader(); renderStoreTab();
}

// ==========================================================
// TAB 4: REYTING VA DIAGNOSTIKA
// ==========================================================
// Farzandni sahifadan chiqmasdan almashtirish. Ota-onada bir nechta
// farzand bo‘lsa, har bir bo‘limda ismlar qatori turadi — bosh sahifaga
// qaytib, keyin qayta kirish shart emas.
function childSwitcherHtml() {
  if (State.role !== "parent" || State.activeChildId) return "";
  const kids = State.childrenCache || [];
  if (kids.length < 2) return "";
  return '<div class="kid-switch">' + kids.map(function (c) {
    const on = c.id === State.selectedChildId;
    return '<button class="ks-btn' + (on ? " is-on" : "") + '" data-action="switch-child" data-id="' + c.id + '">' +
      '<span class="ks-av">' + avatarMarkup(c.avatar_id || "fox", 26) + '</span>' +
      escapeHtml(c.name) + '</button>';
  }).join("") + '</div>';
}

async function renderRatingTab() {
  const main = document.getElementById("app-main");
  const titles = { global: "Global reyting", passport: "Shaxsiy natija", badges: "Nishonlar" };
  const mode = State.ratingMode || "global";
  main.innerHTML =
    childSwitcherHtml() +
    '<p class="sec-label">' + titles[mode] + '</p>' +
    '<div id="rating-content"><div class="empty-state"><div class="spinner"></div>Yuklanmoqda…</div></div>';
  renderHeaderNav();
  const content = document.getElementById("rating-content");

  if (mode === "global") {
    const data = await api("/api/child/rating" + asChildQuery());
    const rows = data.list.map(function (r, i) {
      return '<div class="list-row ' + (r.is_me ? "me-row" : "") + '">' +
        '<div style="display:flex;align-items:center;gap:10px;min-width:0">' +
        '<div class="rank-chip ' + (i === 0 ? "top1" : "") + '">' + (i + 1) + '</div>' +
        '<div style="min-width:0"><p style="margin:0;font-weight:700;font-size:15.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + escapeHtml(r.name) + (r.is_me ? " (Siz)" : "") + '</p><p style="margin:0;font-size:13.5px;color:var(--text-faint)">' + escapeHtml(stripEmoji(r.rank)) + '</p></div>' +
        '</div><div class="pill pill-leaf">' + r.xp + ' XP</div></div>';
    }).join("");
    content.innerHTML = '<p class="section-sub">' + (data.scope === "oila" ? "Oilangiz o‘quvchilari orasida" : "Barcha o‘quvchilar orasida TOP-10") + '</p>' +
      '<div class="card">' + (rows || emptyState("award", "Reyting hali bo‘sh", "")) + '</div>';
    return;
  }

  const shift = State.calShift || 0;
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() + shift);
  const q = asChildQuery();
  const p = await api("/api/child/passport" + q + (q ? "&" : "?") +
    "year=" + d.getFullYear() + "&month=" + (d.getMonth() + 1));

  if (mode === "badges") {
    content.innerHTML = badgeGridHtml(p.badges);
    return;
  }

  let out =
    '<div class="stat-grid">' +
    '<div class="stat-box"><div class="num">' + p.completed_books + '</div><div class="lbl">Tugallangan kitob</div></div>' +
    '<div class="stat-box"><div class="num">' + p.total_pages + '</div><div class="lbl">Jami bet</div></div>' +
    '<div class="stat-box"><div class="num">' + p.streak + '</div><div class="lbl">Ketma-ket kun</div></div>' +
    '</div>' +
    calendarHtml(p.calendar) +
    booksStatHtml(p.books) +
    testStatHtml(p.tests);

  // Ko‘nikmalar diagnostikasi — faqat ota-onaga.
  // Bolaga foizli baho ko‘rsatish pedagogik jihatdan zararli: u o‘zini
  // baholanayotgandek his qiladi va stressga tushadi. Bolaga rag‘bat kerak.
  if (!isChildView()) {
    out += '<p class="eyebrow">Ko‘nikmalar diagnostikasi</p>' +
      '<div class="card">' +
      diagRow("Faktik xotira", p.factual_bar) +
      diagRow("Sabab-oqibat mantiqi", p.logic_bar) +
      diagRow("Asar xulosasi", p.conclusion_bar) +
      diagRow("Nutq ravonligi", p.fluency_bar) +
      '</div>';
  } else {
    out += strengthHtml(p.strength, p.next_rank);
  }
  content.innerHTML = out;
}

// ---------- Mutolaa taqvimi ----------
const WEEKDAY_LETTERS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];

function calendarHtml(c) {
  if (!c) return "";
  const read = {};
  (c.read_days || []).forEach(function (d) { read[d] = true; });

  let cells = "";
  for (let i = 0; i < c.first_weekday; i++) cells += '<span class="cal-cell is-empty"></span>';
  for (let d = 1; d <= c.days_in_month; d++) {
    const cls = (read[d] ? " is-read" : "") + (d === c.today ? " is-today" : "");
    cells += '<span class="cal-cell' + cls + '">' + d + '</span>';
  }

  return '<p class="eyebrow">Mutolaa taqvimi</p>' +
    '<div class="card cal-card">' +
    '<div class="cal-head">' +
    '<button class="cal-nav" data-action="cal-move" data-step="-1" aria-label="Oldingi oy">' + icon("chevron-right", 15, 2.4) + '</button>' +
    '<b>' + escapeHtml(c.month_name) + ' ' + c.year + '</b>' +
    '<button class="cal-nav" data-action="cal-move" data-step="1" aria-label="Keyingi oy">' + icon("chevron-right", 15, 2.4) + '</button>' +
    '</div>' +
    '<div class="cal-grid cal-names">' + WEEKDAY_LETTERS.map(function (w) {
      return '<span class="cal-name">' + w + '</span>';
    }).join("") + '</div>' +
    '<div class="cal-grid">' + cells + '</div>' +
    '<p class="cal-note">Shu oyda <b>' + c.read_count + '</b> kun o‘qildi' +
    (c.longest > 1 ? ' · eng uzun <b>' + c.longest + '</b> kun ketma-ket' : '') + '</p>' +
    '</div>';
}

// ---------- Kitoblar bo‘yicha ----------
function booksStatHtml(books) {
  const list = books || [];
  if (!list.length) return "";
  return '<p class="eyebrow">Kitoblar bo‘yicha</p>' +
    '<div class="card">' + list.map(function (b) {
      const pr = bookProgress(b);
      const done = !!b.completed;
      return '<div class="bstat">' +
        '<div class="bstat-top">' +
        '<span class="bstat-title">' + escapeHtml(b.title) + '</span>' +
        '<span class="bstat-num' + (done ? " is-done" : "") + '">' +
        (done ? b.pages_read + ' bet ' + icon("check-circle", 13, 2.4) : pr.label) + '</span>' +
        '</div>' +
        '<div class="bstat-bar"><i class="' + (done ? "is-done" : "") + '" style="width:' + (done ? 100 : pr.pct) + '%"></i></div>' +
        '</div>';
    }).join("") + '</div>';
}

// ---------- Testlar ----------
function testStatHtml(t) {
  if (!t || !t.count) {
    return '<p class="eyebrow">Testlar</p>' +
      '<div class="card"><p class="section-sub" style="margin:0">Hali test ishlanmagan.</p></div>';
  }
  const known = t.total > 0;
  const pct = known ? Math.round(t.correct / t.total * 100) : t.avg_pct;
  return '<p class="eyebrow">Testlar</p>' +
    '<div class="card">' +
    '<p class="tst-head"><b>' + t.count + '</b> ta test ishlandi' +
    '<span class="tst-pct">' + pct + '%</span></p>' +
    '<div class="tst-bar"><i style="width:' + pct + '%"></i></div>' +
    (known
      ? '<p class="tst-legend"><span class="ok">' + t.correct + ' to‘g‘ri</span>' +
        '<span class="bad">' + t.wrong + ' xato</span></p>'
      : '<p class="tst-legend"><span class="ok">O‘rtacha natija</span></p>') +
    (t.best ? '<p class="tst-best">Eng yaxshi: <b>' + escapeHtml(t.best.title) + '</b> — ' + t.best.pct + '%</p>' : '') +
    '</div>';
}

// ---------- Bolaga: kuchli tomoni va keyingi maqsad ----------
function strengthHtml(strength, next) {
  if (!strength && !next) return "";
  let inner = "";
  if (strength) {
    inner += '<div class="str-row">' +
      '<span class="str-ic">' + icon("star", 20, 1.9) + '</span>' +
      '<p><b>' + escapeHtml(strength.label) + '</b> — ' + escapeHtml(strength.text) + '!</p>' +
      '</div>';
  }
  if (next) {
    inner += '<div class="str-goal">Keyingi maqsad: <b>' + escapeHtml(next.title) + '</b> darajasigacha ' +
      next.pages_left + ' bet' +
      '<span class="str-bar"><i style="width:' + next.progress + '%"></i></span></div>';
  }
  return '<p class="eyebrow">Sening kuchli tomoning</p>' +
    '<div class="card str-card">' + inner + '</div>';
}

// Barcha nishonlar: [fayl nomi, nomi, berilish sharti].
// Chizmalar webapp/badges/ papkasida, manbasi tools/badges/ da.
const BADGE_LIST = [
  ["birinchi-qadam", "Birinchi qadam", "Ilk 5 sahifa o‘qilganda"],
  ["kitobxon-sayyoh", "Kitobxon sayyoh", "100 bet o‘qilganda"],
  ["kitoblar-sultoni", "Kitoblar sultoni", "500 bet o‘qilganda"],
  ["ming-betlik-dovon", "Ming bir sahifa", "1 000 bet o‘qilganda"],
  ["kitoblar-ummoni", "Kitob ummoni", "5 000 bet o‘qilganda"],
  ["olovli-qanot", "Olovli qanot", "3 kun uzluksiz o‘qilganda"],
  ["yengilmas-qahramon", "Tengsiz qahramon", "7 kun uzluksiz o‘qilganda"],
  ["mutolaa-afsonasi", "Mutolaa afsonasi", "30 kun uzluksiz o‘qilganda"],
  ["olmos-iroda", "Olmos iroda", "100 kun uzluksiz o‘qilganda"],
  ["yil-qahramoni", "Yil qahramoni", "365 kun uzluksiz o‘qilganda"],
  ["qalqon", "Qalqon", "Olov qalqonidan keyin darhol qaytganda"],
  ["marra-golibi", "Marra g‘olibi", "Ilk kitob yakunlanganda"],
  ["tezkor-mutolaa", "Tezkor mutolaa", "Kitob 3 kun ichida tugatilganda"],
  ["kichik-kutubxonachi", "Yosh kutubxonachi", "10 ta kitob tugatilganda"],
  ["mutolaa-akademigi", "Mutolaa akademigi", "25 ta kitob tugatilganda"],
  ["bilim-notigi", "Ilm notig‘i", "Audio xulosada 5 Bilig olinganda"],
  ["tafakkur", "Tafakkur", "Mustaqil fikr yuqori baholanganda"],
  ["buyuk-suxandon", "Buyuk suxandon", "10 ta kitob bo‘yicha a'lo xulosa"],
  ["oltin-qalam", "Oltin qalam", "Go‘zal adabiy so‘zlar bilan bayon etganda"],
  ["zukko-kitobxon", "Zukko kitobxon", "Testda 100% to‘g‘ri javob"],
  ["mantiq-ustasi", "Mantiq ustasi", "Jami 50 ta to‘g‘ri javob"],
  ["bilim-akademiyasi", "Bilimdon", "10 ta test ketma-ket 100%"],
  ["tonggi-qaldirgoch", "Tonggi qaldirg‘och", "06:00–09:00 oralig‘ida o‘qilganda"],
  ["qutb-yulduzi", "Qutb yulduzi", "Uxlashdan oldin o‘qilganda"],
  ["maroqli", "Maroqli", "Dam olish kunlari o‘qilganda"],
  ["oila-iftixori", "Oila iftixori", "Ota-ona bilan suhbat a'lo o‘tganda"],
  ["chaqmoq-kitobxon", "Chaqmoq kitobxon", "Bir o‘tirishda 30+ bet o‘qilganda"],
  ["ezgulik-elchisi", "Ezgulik elchisi", "Qahramon fazilatlari bo‘yicha xulosa"],
  ["xazinabon", "Xazinabon", "2000 Bilig to‘planganda"]
];

const BADGE_BY_NAME = {};
BADGE_LIST.forEach(function (b) { BADGE_BY_NAME[b[1].toLowerCase()] = b; });

function badgeFile(name) {
  const b = BADGE_BY_NAME[stripEmoji(name || "").trim().toLowerCase()];
  return b ? b[0] : null;
}

// Bolada bor nishonlar ro‘yxati (nomlar bo‘yicha)
function earnedBadgeSet(badgesStr) {
  const set = {};
  (badgesStr || "").split(",").forEach(function (n) {
    const k = stripEmoji(n).trim().toLowerCase();
    if (k && !/yo.q/i.test(k)) set[k] = true;
  });
  return set;
}


// ==========================================================
// NISHONLASH LAHZALARI
// ----------------------------------------------------------
// Uch daraja:
//   1. mascotToast() — kichik lenta, maskot bilan. Kamdan-kam chiqadi.
//   2. celebrate()   — to‘liq ekran tabrik. Faqat nishon uchun.
//   3. kutib olish   — bola ko‘rmagan nishonlarni tipratikan yetkazadi
//                      (renderChildHome ichida).
// Ranglar nishonning o‘z rang oilasidan olinadi (badges/index.json),
// maskotning rangi esa fonga yumshoq yorug‘lik qo‘shadi.
// ==========================================================
let BADGE_META = {}, MASCOT_ACCENT = {};

function loadBadgeMeta() {
  return Promise.all([
    fetch("/badges/index.json?v=" + ASSET_V).then(function (r) { return r.ok ? r.json() : {}; }),
    fetch("/mascots/trim/index.json?v=" + ASSET_V).then(function (r) { return r.ok ? r.json() : {}; })
  ]).then(function (res) {
    BADGE_META = res[0] || {}; MASCOT_ACCENT = res[1] || {};
  }).catch(function () { BADGE_META = {}; MASCOT_ACCENT = {}; });
}

function badgeMetaByName(name) {
  const key = stripEmoji(name || "").trim().toLowerCase();
  for (const slug in BADGE_META) {
    if ((BADGE_META[slug].name || "").toLowerCase() === key) {
      return Object.assign({ slug: slug }, BADGE_META[slug]);
    }
  }
  return null;
}

// ---------- ranglar ----------
function hex2rgb(h) {
  h = (h || "#4E8EF7").replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function rgb2hex(a) {
  return "#" + a.map(function (v) { return ("0" + Math.round(v).toString(16)).slice(-2); }).join("");
}
function mixColor(a, b, t) {
  const x = hex2rgb(a), y = hex2rgb(b);
  return rgb2hex(x.map(function (v, i) { return v + (y[i] - v) * t; }));
}
function lighten(h, t) { return mixColor(h, "#FFFFFF", t); }
function rgbaOf(h, a) { return "rgba(" + hex2rgb(h).join(",") + "," + a + ")"; }

// Fonni nishon rangi + maskot rangidan quradi. Konfetti ranglarini qaytaradi.
function applyCelTheme(meta, mascotAccent) {
  const cel = document.getElementById("cel");
  const rim = meta.rim || "#4E8EF7";
  const deep = meta.rim_dark || "#2F63D6";
  const glow = rgbaOf(mascotAccent || rim, .30);
  cel.style.background =
    "radial-gradient(58% 40% at 74% 78%," + glow + " 0%,transparent 64%)," +
    "radial-gradient(115% 80% at 50% 34%," + mixColor(deep, "#0B1226", .40) + " 0%," +
    mixColor(deep, "#0B1226", .74) + " 55%," + mixColor(deep, "#05080F", .88) + " 100%)";
  cel.style.setProperty("--ray", rgbaOf(lighten(rim, .5), .24));
  cel.style.setProperty("--eyebrow", lighten(rim, .38));
  cel.style.setProperty("--btn", "linear-gradient(180deg," + lighten(rim, .55) + "," + rim + ")");
  return [rim, lighten(meta.orn || rim, .35), "#F5C243", "#FFFFFF", mascotAccent || rim];
}

// ---------- 2-daraja: to‘liq ekran tabrik ----------
let celQueue = [], celIdx = 0, celDone = null;

function celebrate(names, onDone) {
  const list = (names || []).filter(Boolean);
  if (!list.length) { if (onDone) onDone(); return; }
  celQueue = list; celIdx = 0; celDone = onDone || null;
  celShow();
}

function celShow() {
  const cel = document.getElementById("cel");
  const name = celQueue[celIdx];
  const meta = badgeMetaByName(name) ||
    { slug: "", name: name, msg: "", rim: "#4E8EF7", rim_dark: "#2F63D6", orn: "#2F63D6" };
  const colors = applyCelTheme(meta, MASCOT_ACCENT["mascot-sherbola-galaba"]);
  const img = document.getElementById("cel-img");
  if (meta.slug) { img.src = "/badges/" + meta.slug + ".svg?v=" + ASSET_V; img.style.display = "block"; }
  else { img.style.display = "none"; }
  document.getElementById("cel-name").textContent = meta.name || name;
  document.getElementById("cel-msg").textContent = meta.msg || meta.cond || "";
  document.getElementById("cel-count").textContent =
    celQueue.length > 1 ? (celIdx + 1) + " / " + celQueue.length : "";
  document.getElementById("cel-btn").textContent =
    (celIdx < celQueue.length - 1) ? "Keyingisi" : "Ajoyib!";
  cel.classList.remove("on"); void cel.offsetWidth; cel.classList.add("on");
  haptic("heavy");
  celConfetti(colors);
}

function celNext() {
  celIdx++;
  if (celIdx < celQueue.length) { celShow(); return; }
  document.getElementById("cel").classList.remove("on");
  const cb = celDone; celDone = null;
  if (cb) cb();
}

// ---------- konfetti ----------
let celParts = [], celRaf = null, celColors = ["#F5C243", "#4E8EF7", "#10B981", "#FFFFFF"];

function celConfetti(palette) {
  if (palette && palette.length) celColors = palette;
  const cv = document.getElementById("cel-conf");
  cv.width = cv.offsetWidth; cv.height = cv.offsetHeight;
  celParts = [];
  for (let i = 0; i < 130; i++) {
    celParts.push({
      x: cv.width * (.15 + Math.random() * .7),
      y: cv.height * .42 + (Math.random() - .5) * 30,
      vx: (Math.random() - .5) * 11, vy: -6 - Math.random() * 7,
      w: 5 + Math.random() * 6, h: 8 + Math.random() * 8,
      rot: Math.random() * 6.3, vr: (Math.random() - .5) * .3,
      c: celColors[(Math.random() * celColors.length) | 0], life: 1
    });
  }
  if (celRaf) cancelAnimationFrame(celRaf);
  celTick();
}

function celTick() {
  const cv = document.getElementById("cel-conf"), cx = cv.getContext("2d");
  cx.clearRect(0, 0, cv.width, cv.height);
  let alive = 0;
  celParts.forEach(function (p) {
    p.vy += .28; p.vx *= .992; p.x += p.vx; p.y += p.vy; p.rot += p.vr;
    if (p.y > cv.height * .55) p.life -= .012;
    if (p.life <= 0) return;
    alive++;
    cx.save(); cx.globalAlpha = Math.max(0, p.life);
    cx.translate(p.x, p.y); cx.rotate(p.rot);
    cx.fillStyle = p.c; cx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h); cx.restore();
  });
  celRaf = alive ? requestAnimationFrame(celTick) : null;
}

// ---------- 1-daraja: maskot lentasi ----------
// Qadri saqlanishi uchun kamdan-kam chiqariladi — har bir sahifa uchun emas.
let mtTimer = null;

function mascotToast(mascot, title, sub, color) {
  const el = document.getElementById("mtoast");
  if (!el) return;
  document.getElementById("mtoast-img").src = "/mascots/trim/mascot-" + mascot + ".webp?v=" + ASSET_V;
  document.getElementById("mtoast-title").textContent = title;
  document.getElementById("mtoast-sub").textContent = sub || "";
  const bar = document.getElementById("mtoast-bar");
  bar.style.background = color || MASCOT_ACCENT["mascot-" + mascot] || "var(--gold)";
  bar.style.transition = "none"; bar.style.width = "100%";
  el.classList.add("on");
  haptic("light");
  requestAnimationFrame(function () {
    bar.style.transition = "width 3.4s linear"; bar.style.width = "0%";
  });
  clearTimeout(mtTimer);
  mtTimer = setTimeout(function () { el.classList.remove("on"); }, 3400);
}

function hideMascotToast() {
  clearTimeout(mtTimer);
  const el = document.getElementById("mtoast");
  if (el) el.classList.remove("on");
}

// ---------- 3-daraja: kutib olish kartochkasi ----------
function welcomeHtml(name, unseen) {
  if (!unseen || !unseen.length) return "";
  const word = unseen.length > 1 ? unseen.length + " ta nishon" : "«" + stripEmoji(unseen[0]) + "» nishoni";
  return '<div class="welc" data-action="show-unseen-badges">' +
    '<div class="t"><b>Xush kelibsan, ' + escapeHtml(name || "") + '!</b>' +
    '<span>Sen ko‘rmagan holda ' + escapeHtml(word) + ' qo‘lga kiritilgan.</span>' +
    '<span class="go">Ko‘rish →</span></div>' +
    '<div class="m"><img src="/mascots/trim/mascot-tipratikan-salom.webp?v=' + ASSET_V + '" alt=""></div>' +
    '</div>';
}

// Kutib olish kartochkasi bosilganda — ko‘rilmagan nishonlarni tabriklaymiz
async function showUnseenBadges(el) {
  const card = el.closest(".welc");
  const data = await api("/api/child/home" + asChildQuery());
  const names = data.unseen_badges || [];
  try { await api("/api/child/badges/seen" + asChildQuery(), { method: "POST" }); } catch (e) {}
  if (card) card.remove();
  celebrate(names, function () { if (State.currentTab === "home") renderChildHome(); });
}

function badgeArt(slug, size) {
  return '<img src="/badges/' + slug + '.svg?v=' + ASSET_V + '" alt="" loading="lazy">';
}

// To‘liq kolleksiya — olinmagan nishonlar xira va rangsiz turadi,
// shunda bola nimaga intilishini ko‘radi.
function badgeGridHtml(badgesStr) {
  const earned = earnedBadgeSet(badgesStr);
  const have = BADGE_LIST.filter(function (b) { return earned[b[1].toLowerCase()]; });
  const rest = BADGE_LIST.filter(function (b) { return !earned[b[1].toLowerCase()]; });
  const all = have.concat(rest);
  return '<p class="badge-count"><b>' + have.length + '</b> / ' + BADGE_LIST.length + ' nishon to‘plandi</p>' +
    '<div class="badge-grid">' + all.map(function (b) {
      const got = !!earned[b[1].toLowerCase()];
      return '<div class="badge-tile' + (got ? "" : " is-locked") + '" title="' + escapeHtml(b[2]) + '">' +
        '<div class="badge-icon has-art">' + badgeArt(b[0]) + '</div>' +
        '<p>' + escapeHtml(b[1]) + '</p>' +
        '<span class="badge-cond">' + escapeHtml(got ? "Olingan" : b[2]) + '</span>' +
        '</div>';
    }).join("") + '</div>';
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
let editChildAvatar = "fox", editChildId = null;
function openEditChildModal(id, name, age, avatarId) {
  editChildAvatar = avatarId || "fox";
  editChildId = id;
  const avatarsHtml = AVATAR_ORDER.map(function (aid) {
    const a = AVATARS[aid];
    return '<button class="avatar-option' + (aid === editChildAvatar ? " selected" : "") + '" data-action="pick-edit-avatar" data-avatar="' + aid + '">' +
      '<span class="avatar-circle">' + avatarMarkup(aid, 54) + '</span><span>' + a.label + '</span></button>';
  }).join("") + uploadTileHtml(editChildAvatar);
  openModal("Farzand ma'lumotlarini tahrirlash",
    '<div class="avatar-grid" id="edit-avatar-grid" style="padding:0 0 8px">' + avatarsHtml + '</div>' +
    '<label class="field-label">Ismi</label>' +
    '<input id="edit-child-name" class="text-input" value="' + escapeHtml(name || "") + '" />' +
    '<label class="field-label">Yoshi</label>' +
    '<input id="edit-child-age" type="number" class="text-input" value="' + (age || "") + '" />' +
    '<button class="btn btn-primary btn-block" data-action="submit-edit-child" data-id="' + id + '">Saqlash</button>'
  );
}
async function submitEditChild(id) {
  const name = document.getElementById("edit-child-name").value.trim();
  const age = Number(document.getElementById("edit-child-age").value);
  if (!name) { toast("Ismni kiriting"); return; }
  await api("/api/parent/children/" + id + "/profile", { method: "POST", body: { name: name, age: age, avatar_id: editChildAvatar } });
  closeModal();
  toast("Ma'lumotlar saqlandi");
  State.childrenCache = await api("/api/parent/children");
  renderChildDetailPage(Number(id));
}
// ==========================================================
// FARZAND QO‘SHISH
// ----------------------------------------------------------
// Uyda bitta telefon bo‘lishi mumkin — shuning uchun farzandning
// alohida Telegram hisobi shart emas. Ota-ona uni shu yerda o‘zi
// yaratadi, keyin farzandga 8 xonali ID beriladi.
// ==========================================================
let newChildAvatar = "fox";
function openAddChildModal() {
  newChildAvatar = "fox";
  const avatarsHtml = AVATAR_ORDER.map(function (aid) {
    const a = AVATARS[aid];
    return '<button class="avatar-option' + (aid === newChildAvatar ? " selected" : "") + '" data-action="pick-new-avatar" data-avatar="' + aid + '">' +
      '<span class="avatar-circle">' + avatarMarkup(aid, 54) + '</span><span>' + a.label + '</span></button>';
  }).join("");
  openModal("Farzand qo‘shish",
    '<p class="section-sub" style="margin-top:-4px">Farzandingizning alohida telefoni bo‘lishi shart emas — hammasini shu yerdan boshqarasiz. ' +
    'Keyin xohlasa, unga beriladigan ID orqali o‘z telefonidan kiradi.</p>' +
    '<label class="field-label">Qaysi hayvoncha unga yoqadi?</label>' +
    '<div class="avatar-grid" id="new-avatar-grid" style="padding:0 0 8px">' + avatarsHtml + '</div>' +
    '<label class="field-label">Ismi</label>' +
    '<input id="new-child-name" class="text-input" placeholder="Masalan: Ibrohim" />' +
    '<label class="field-label">Yoshi</label>' +
    '<input id="new-child-age" type="number" class="text-input" placeholder="Masalan: 9" />' +
    '<p class="section-sub" style="margin:8px 0 12px">Yoshi kitob tavsiyalari uchun kerak — katalog aynan shu yoshga mos kitoblarni ko‘rsatadi.</p>' +
    '<button class="btn btn-primary btn-block" data-action="submit-add-child">Qo‘shish</button>'
  );
}

async function submitAddChild() {
  const name = document.getElementById("new-child-name").value.trim();
  const age = Number(document.getElementById("new-child-age").value);
  if (!name) { toast("Ismini kiriting"); return; }
  if (!age || age < 3 || age > 17) { toast("Yoshini to‘g‘ri kiriting (3-17)"); return; }
  const res = await api("/api/parent/children", {
    method: "POST",
    body: { name: name, age: age, avatar_id: newChildAvatar }
  });
  closeModal();
  State.childrenCache = await api("/api/parent/children");
  State.selectedChildId = res.id;
  toast(name + " qo‘shildi");
  switchTab("home");
}

// Farzandning ID raqamini nusxalash — u o‘z telefonidan kirganda shu kod kerak.
async function copyCode(code) {
  let ok = false;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(code);
      ok = true;
    }
  } catch (e) { ok = false; }
  if (!ok) {
    // Eski telefonlarda clipboard API ishlamaydi — zaxira yo‘l.
    try {
      const ta = document.createElement("textarea");
      ta.value = code;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      ok = document.execCommand("copy");
      document.body.removeChild(ta);
    } catch (e) { ok = false; }
  }
  toast(ok ? "Kod nusxalandi: " + code : "Kod: " + code);
}

// Bosh sahifadagi kitob kartochkasi bosilganda kitob oynasi ochiladi:
// bet belgilash, ovozli xulosa va testlar shu yerda.
async function goToBook(bookId) {
  await openBookModal(bookId);
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
    openModal("Qanday reja tuzamiz?",
      '<p class="section-sub" style="margin-top:-4px">Reja — farzandingiz o‘qiydigan kitoblar ro‘yxati.</p>' +
      choiceCard({
        ic: "book-open", action: "wizard-pick-mode", data: { mode: "quick" }, tag: "Oddiy",
        title: "Bitta kitob",
        desc: "Faqat bitta kitob qo‘shasiz. Nom ham, sovrin ham so‘ralmaydi — bir bosishda tayyor."
      }) +
      choiceCard({
        ic: "award", tone: "gold", action: "wizard-pick-mode", data: { mode: "marathon" },
        title: "Mutolaa marafoni",
        desc: "Bir nechta kitobdan iborat uzoq safar. Nom qo‘yasiz va marra sovrinini va'da qilasiz."
      })
    );
  },
  pickMode: async function (mode) {
    this.mode = mode;
    // Tezkor mutolaada nom ham, sovrin ham so‘ralmaydi — ota-ona shunchaki
    // kitob tanlaydi. Nom va sovrin faqat marafonda ma'noga ega.
    if (mode === "quick") {
      this.planName = "Tezkor mutolaa";
      this.prizeText = "";
      await this.createPlan();
      this.pickMethod(null);
      return;
    }
    openModal("Marafonni nomlang",
      '<label class="field-label">Marafon nomi</label>' +
      '<input id="wiz-plan-name" class="text-input" placeholder="Masalan: Yozgi mutolaa" value="Mutolaa marafoni" />' +
      '<label class="field-label">Marra sovrini (ixtiyoriy)</label>' +
      '<input id="wiz-plan-prize" class="text-input" placeholder="Masalan: Velosiped" />' +
      '<button class="btn btn-primary btn-block" data-action="wizard-continue-plan">Davom etish</button>'
    );
  },
  createPlan: async function () {
    const res = await api("/api/parent/plans", {
      method: "POST",
      body: { child_id: this.childId, name: this.planName, prize: this.prizeText, type: this.mode }
    });
    this.planId = res.plan_id;
  },
  continuePlan: async function () {
    this.planName = document.getElementById("wiz-plan-name").value.trim() || "Mutolaa marafoni";
    this.prizeText = document.getElementById("wiz-plan-prize").value.trim();
    await this.createPlan();
    this.pickMethod(null);
  },
  pickMethod: function (method) {
    if (!method) {
      openModal("Kitobni qanday qo‘shamiz?",
        '<p class="section-sub" style="margin-top:-4px">Uchta yo‘l bor. Eng ishonchlisi — katalog.</p>' +
        choiceCard({
          ic: "book-open", action: "wizard-pick-method", data: { method: "rec" }, tag: "Tavsiya",
          title: "Katalogdan tanlash",
          desc: "167 ta kitob, muqovasi bilan. Testi ham tayyor — rasm yuklash shart emas."
        }) +
        choiceCard({
          ic: "edit", tone: "soft", action: "wizard-pick-method", data: { method: "text" },
          title: "Nomini yozib qo‘shish",
          desc: "Kitob katalogda bo‘lmasa, nomi va muallifini o‘zingiz yozasiz."
        }) +
        choiceCard({
          ic: "camera", tone: "soft", action: "wizard-pick-method", data: { method: "photo" },
          title: "Muqovani rasmga olish",
          desc: "Kitob qo‘lingizda, lekin nomini yozishga erinsangiz — old muqovasini suratga oling."
        })
      );
      return;
    }
    this.showMethod(method);
  },
  showMethod: async function (method) {
    const self = this;
    if (method === "rec") {
      await Catalog.open(this.childAge);
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
        self.coverPhotoFile = input.files[0];      // muqova qilib qo‘yish uchun saqlaymiz
        zone.innerHTML = '<div class="spinner"></div>Rasm tayyorlanmoqda…';
        const prepared = await prepareImage(input.files[0], "cover");
        zone.innerHTML = '<div class="spinner"></div>Muqova o‘qilmoqda…';
        const fd = new FormData();
        fd.append("photo", prepared.blob, "cover.jpg");
        try {
          const res = await api("/api/parent/cover_read", { method: "POST", body: fd });
          self.confirmCover(res.title, res.author);
        } catch (e) {
          // AI o‘qiy olmasa — qo‘lda yozish oynasi ochiladi, ish to‘xtamaydi
          toast("Muqovani o‘qib bo‘lmadi, nomini o‘zingiz yozing");
          self.confirmCover("", "");
        }
      };
    }
  },
  // Bezakli muqovalarda AI adashishi mumkin — shuning uchun natija
  // hech qachon jimgina saqlanmaydi, avval ota-ona tasdiqlaydi.
  confirmCover: function (title, author) {
    openModal("Kitobni tasdiqlang",
      '<p class="section-sub">Muqovadan o‘qildi. Xato bo‘lsa, shu yerda tuzatib qo‘ying.</p>' +
      '<label class="field-label">Kitob nomi</label>' +
      '<input id="wiz-cover-title" class="text-input" value="' + escapeHtml(title || "") + '" placeholder="Kitob nomi" />' +
      '<label class="field-label">Muallif</label>' +
      '<input id="wiz-cover-author" class="text-input" value="' + escapeHtml(author || "") + '" placeholder="Muallif" />' +
      '<label class="field-label">Jami sahifa soni (ixtiyoriy)</label>' +
      '<input id="wiz-cover-pages" type="number" class="text-input" placeholder="120" />' +
      '<button class="btn btn-primary btn-block" data-action="wizard-save-cover">Qo‘shish</button>'
    );
  },
  saveCoverBook: async function () {
    const title = document.getElementById("wiz-cover-title").value.trim();
    const author = document.getElementById("wiz-cover-author").value.trim();
    const pages = Number(document.getElementById("wiz-cover-pages").value || 0);
    if (!title) { toast("Kitob nomini kiriting"); return; }
    const res = await api("/api/parent/plans/" + this.planId + "/books", {
      method: "POST",
      body: { title: title, author: author, total_pages: pages }
    });
    toast('"' + res.title + '" qo‘shildi');

    // Katalogda bu kitobning muqovasi bo‘lmasa — ota-ona olgan rasmni
    // muqova qilib qo‘yishni taklif qilamiz. Bo‘lsa, ortiqcha so‘ramaymiz.
    const self = this;
    if (this.coverPhotoFile && !coverFile(title, author) && !res.cover_file) {
      const photo = this.coverPhotoFile;
      this.coverPhotoFile = null;
      openCropper(photo, "cover", async function (blob) {
        const fd = new FormData();
        fd.append("photo", blob, "cover.webp");
        try {
          await api("/api/parent/books/" + res.book_id + "/cover", { method: "POST", body: fd });
          toast("Muqova saqlandi");
        } catch (e) { toast(e.error || "Muqovani saqlab bo‘lmadi"); }
        closeModal();
        self.afterBookAdded();
      }, { skip: true, onSkip: function () { self.afterBookAdded(); } });
      return;
    }
    this.coverPhotoFile = null;
    this.afterBookAdded();
  },
  addRecBook: async function (idx) {
    // Tavsiya ro‘yxatidagi matn allaqachon toza — AI'ga yubormaymiz.
    // Shu sabab kitob bir zumda qo‘shiladi, oldingidek kutish yo‘q.
    const text = this.recBooks[idx];
    const dot = text.indexOf(".");
    const title = dot > 0 ? text.slice(0, dot).trim() : text.trim();
    const author = dot > 0 ? text.slice(dot + 1).trim().replace(/\.$/, "") : "";
    const res = await api("/api/parent/plans/" + this.planId + "/books", {
      method: "POST",
      body: { title: title, author: author }
    });
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

// ==========================================================
// KITOBLAR KATALOGI — muqovali javon
// ==========================================================
// Ota-ona kitobni shu yerdan tanlaydi: nomi, muallifi va muqovasi tayyor.
// Ya'ni AI chaqirilmaydi — kitob bir zumda qo‘shiladi.
const Catalog = {
  all: [],          // barcha kitoblar (bir marta yuklanadi)
  ageKey: "8",      // tanlangan yosh guruhi ("all" — barchasi)
  query: "",

  AGE_TABS: [
    { key: "3", label: "3-5 yosh" },
    { key: "6", label: "6-7 yosh" },
    { key: "8", label: "8-11 yosh" },
    { key: "12", label: "12+ yosh" },
    { key: "all", label: "Barchasi" }
  ],

  ageKeyFor: function (age) {
    if (age <= 5) return "3";
    if (age <= 7) return "6";
    if (age <= 11) return "8";
    return "12";
  },

  open: async function (childAge) {
    this.query = "";
    this.ageKey = this.ageKeyFor(childAge || 10);
    if (!this.all.length) this.all = await api("/api/parent/catalog");
    openModal("Kitob tanlang",
      '<div class="cat-search">' + icon("search", 16, 2) +
      '<input id="cat-q" class="cat-input" placeholder="Kitob yoki muallif nomi" autocomplete="off" />' +
      '</div>' +
      '<div class="cat-tabs" id="cat-tabs"></div>' +
      '<div id="cat-body"></div>',
      "modal-tall"
    );
    const self = this;
    const input = document.getElementById("cat-q");
    input.addEventListener("input", function () {
      self.query = input.value.trim().toLowerCase();
      self.renderBody();
    });
    this.renderTabs();
    this.renderBody();
  },

  renderTabs: function () {
    const self = this;
    document.getElementById("cat-tabs").innerHTML = this.AGE_TABS.map(function (t) {
      return '<button class="cat-tab' + (t.key === self.ageKey ? " is-on" : "") +
        '" data-action="cat-age" data-key="' + t.key + '">' + t.label + '</button>';
    }).join("");
  },

  setAge: function (key) {
    this.ageKey = key;
    this.renderTabs();
    this.renderBody();
  },

  filtered: function () {
    const self = this;
    return this.all.filter(function (b) {
      if (self.ageKey !== "all" && b.age !== self.ageKey) return false;
      if (!self.query) return true;
      return (b.title + " " + b.author).toLowerCase().indexOf(self.query) !== -1;
    });
  },

  renderBody: function () {
    const list = this.filtered();
    const body = document.getElementById("cat-body");
    if (!body) return;
    if (!list.length) {
      body.innerHTML = '<div class="cat-empty">' + icon("book-open", 34, 1.4) +
        '<p>Bunday kitob topilmadi</p>' +
        '<button class="btn btn-outline btn-block" data-action="wizard-pick-method" data-method="text">Nomini o‘zim yozaman</button></div>';
      return;
    }
    const self = this;
    body.innerHTML =
      '<p class="cat-count">' + list.length + ' ta kitob</p>' +
      '<div class="cat-grid">' + list.map(function (b) {
        const idx = self.all.indexOf(b);
        return '<button class="cat-item" data-action="cat-pick" data-idx="' + idx + '">' +
          coverHtml(b.title, b.author, "cat-cover") +
          '<span class="cat-title">' + escapeHtml(b.title) + '</span>' +
          '<span class="cat-author">' + escapeHtml(b.author || "") + '</span>' +
          '</button>';
      }).join("") + '</div>' +
      '<button class="btn btn-outline btn-block cat-manual" data-action="wizard-pick-method" data-method="text">Katalogda yo‘qmi? Nomini yozing</button>';
  },

  pick: async function (idx) {
    const b = this.all[idx];
    if (!b) return;
    const res = await api("/api/parent/plans/" + Wizard.planId + "/books", {
      method: "POST",
      body: { title: b.title, author: b.author }
    });
    toast('"' + res.title + '" qo‘shildi');
    Wizard.afterBookAdded();
  }
};

// ---------------- ISHGA TUSHIRISH ----------------
boot();
