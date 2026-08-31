// ==========================================================
// BILIG AI — Mini App frontend logikasi (vanilla JS)
// Yangi arxitektura: 4 ta doimiy tab — Bosh sahifa, Kitobxona, Do‘kon, Reyting
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
  selectedChildId: null,   // Ota-ona tanlagan "faol farzand" konteksti (Bosh sahifa/Kitobxona/Reyting uchun)
  activeChildId: null,     // "Bolaxona" rejimida to‘liq bola ekraniga o‘tilganda
  activeChildName: null,
  currentTab: "home",
  childrenCache: [],
  ratingMode: "passport",
  storeView: "shop",       // do‘kon ichida: "shop" (sovg‘alar javoni) yoki "wallet"
  storeItems: [],          // ota-ona sovg‘alari — tahrir oynasi shu ro‘yxatdan to‘ldiriladi
  storeChildren: [],       // narx maslahati uchun: farzandning haftalik yig‘imi
  storeBalance: 0,         // bolaning balansi — xarid tasdig‘ida ko‘rsatiladi
  walletRate: 0,
  walletShowSom: false,
  feed: [],                // ota-onaning o‘qilmagan xabarlari
  subPage: null,           // tab ichidagi ichki sahifa (masalan farzand kartasi)
  groupId: null,           // ochilgan guruh (Guruhlar ko‘rinishi ichida)
  groupTab: "members",     // guruh ichida: a'zolar yoki reyting
  groupPeriod: "week",     // guruh reytingi: week / month / all
  groupMemberId: null,     // ochilgan a'zoning kartochkasi
  groupFound: null,        // qidiruv natijasi; null bo‘lsa qidiruv qilinmagan
  groupQuery: "",
};

// ---------------- IKONALAR (Feather uslubi, emoji YO‘Q) ----------------
const ICON_PATHS = {
  // --- Sof chiziqli (to‘ldirishsiz) ---
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  "chevron-right": '<polyline points="9 18 15 12 9 6"/>',
  "chevron-down": '<polyline points="6 9 12 15 18 9"/>',
  // Ulashish — nishonni Telegram orqali yuborish tugmasida ishlatiladi
  share: '<circle cx="18" cy="5.4" r="2.7"/><circle cx="6" cy="12" r="2.7"/><circle cx="18" cy="18.6" r="2.7"/><line x1="8.4" y1="10.8" x2="15.6" y2="6.6"/><line x1="8.4" y1="13.2" x2="15.6" y2="17.4"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  "arrow-right": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  clock: '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
  refresh: '<path d="M20.5 12a8.5 8.5 0 1 1-2.6-6.1"/><polyline points="20.6 4.2 20.6 9.1 15.7 9.1"/>',

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
  "arrow-left": '<path d="M19 12H5"/><path d="m11 18-6-6 6-6"/>',
  // Hamyon — do‘kon ichidagi hisob bo‘limi
  wallet: [
    '<path d="M3.2 8.4a2.6 2.6 0 0 1 2.6-2.6h12.4a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5.8a2.6 2.6 0 0 1-2.6-2.6z"/>',
    '<path d="M3.2 8.4a2.6 2.6 0 0 1 2.6-2.6h12.4a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5.8a2.6 2.6 0 0 1-2.6-2.6z"/><path d="M3.2 9.9h17"/><path d="M20.9 12.2h-3.1a1.9 1.9 0 0 0 0 3.8h3.1a.8.8 0 0 0 .8-.8v-2.2a.8.8 0 0 0-.8-.8z"/>'],
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
  // Uch nuqta — a'zo ustidagi amallar oynasini ochadi
  more: '<circle cx="12" cy="5.5" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="12" cy="18.5" r="1.6"/>',
  star: [
    '<path d="M12 2.9c.35 0 .67.2.83.52l2.42 4.9 5.41.79c.75.11 1.05 1.03.5 1.56l-3.91 3.81.92 5.39c.13.75-.65 1.32-1.32.96L12 18.29l-4.85 2.55c-.67.36-1.45-.21-1.32-.96l.92-5.39-3.91-3.81c-.55-.53-.25-1.45.5-1.56l5.41-.79 2.42-4.9c.16-.32.48-.52.83-.52z"/>',
    '<path d="M12 2.9c.35 0 .67.2.83.52l2.42 4.9 5.41.79c.75.11 1.05 1.03.5 1.56l-3.91 3.81.92 5.39c.13.75-.65 1.32-1.32.96L12 18.29l-4.85 2.55c-.67.36-1.45-.21-1.32-.96l.92-5.39-3.91-3.81c-.55-.53-.25-1.45.5-1.56l5.41-.79 2.42-4.9c.16-.32.48-.52.83-.52z"/>'],
};

// Rasm va bezak fayllari o‘zgarganda shu raqamni oshiring — shunda telefon
// eski nusxani emas, yangisini yuklaydi (index.html dagi ?v= bilan bir xil).
// Rasmlar telefonda bir hafta saqlanadi, shuning uchun raqamsiz yangilanish
// foydalanuvchiga umuman yetib bormaydi.
const ASSET_V = "16";

// Kitob qo‘shish kartochkasi bezagi — o‘qiyotgan boyo‘g‘li maskoti
const HERO_MASCOT = '<img class="hero-mascot" src="/mascots/mascot-boyogli-oqish-cutout.webp?v=' + ASSET_V + '" alt="">';

// ---------------- KITOB MUQOVALARI ----------------
// covers/index.json — kitob nomi bo‘yicha muqova faylini topish jadvali.
let COVER_INDEX = null;

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

// ---------------- XABARLAR LENTASI (ikkala rolda ham) ----------------
// Kartochka «Xush kelibsan» kutib olish kartochkasi bilan bir xil ko‘rinishda:
// iliq fon va maskot. Ega shu ko‘rinishni tanladi — u chiroyliroq va
// ilovaning bolalar uchun mo‘ljallangani shundan bilinib turadi.
//
// Har xabar turining O‘Z maskoti bor: sovg‘a — quyoncha, nishon — sherbola,
// test — qaldirg‘och va hokazo.
const FEED_MASCOTS = {
  badge: "sherbola-galaba",
  book_done: "tulki-oqish",
  test: "qaldirgoch-tekshiruv",
  voice: "kiyik-tekshiruv",
  talk: "olmaxon-2",
  gift: "quyoncha-sovga",
  gift_given: "quyoncha-sovga",
  gift_wait: "quyoncha-sovga",
  new_book: "tulki-oqish",
  coins: "qorbars-tanga",
  book_request: "olmaxon-1",
  child_linked: "tipratikan-salom",
  summary: "tipratikan-salom",
  talk_check: "tipratikan-salom",
  unseen_badges: "tipratikan-salom",
  streak: "sherbola-galaba",
  // Boyo‘g‘li faqat BOLA lentasida ishlatiladi — ota-ona bosh sahifasidagi
  // «Kitob qo‘shish» kartasi bilan yonma-yon tushmaydi.
  streak_warn: "boyogli-oylanish",
  shield_used: "qorbars-tanga"
};

// Javob talab qiladigan xabarlar — kartochkada «Javob berish →» chiqadi
// va bosilsa savol oynasi ochiladi.
const FEED_ASK = { talk_check: 1, unseen_badges: 1, streak_warn: 1 };
// Kartochkadagi tugma matni — har xabar turi uchun o‘zicha.
const FEED_GO = { unseen_badges: "Ko‘rish →", streak_warn: "Nima qilay? →" };
// Diqqat: bu nomlar `webapp/mascots/trim/` dagi fayllarga AYNAN mos kelishi
// kerak. U yerda «olmaxon» emas, «olmaxon-1» va «olmaxon-2» bor.
// Boyo‘g‘li ataylab ishlatilmadi: ota-ona bosh sahifasida shundoq ham
// «Kitob qo‘shish» kartochkasida boyo‘g‘li turadi, ikkitasi yonma-yon
// tushib qolardi.

function feedCardHtml() {
  const list = State.feed || [];
  if (!list.length) return "";
  const n = list[0];
  const rest = list.length - 1;
  const mascot = FEED_MASCOTS[n.kind] || "tipratikan-salom";
  const ask = FEED_ASK[n.kind];
  return '<div class="welc feed-card' + (ask ? " is-ask" : "") + '"' +
    (ask ? ' data-action="feed-open" data-id="' + n.id + '" data-kind="' + n.kind +
           '" data-topic="' + escapeHtml(n.body || "") + '"' : "") + '>' +
    '<div class="t">' +
    // Xabar QAYSI farzand haqidaligi. Lenta ota-onaning o‘ziniki — u hamma
    // farzandlar bo‘yicha keladi, «faol» farzandga bog‘liq emas. Kartochka
    // esa faol farzand belgisining ostida turadi, shuning uchun ism
    // ko‘rsatilmasa xabar noto‘g‘ri farzandga tegishlidek ko‘rinardi.
    (n.child_name
      ? '<span class="fc-who">' + avatarMarkup(n.avatar_id || "fox", 20) +
        escapeHtml(n.child_name) + '</span>'
      : "") +
    '<b>' + escapeHtml(n.title) + '</b>' +
    (n.body ? '<span>' + escapeHtml(n.body) + '</span>' : "") +
    (ask ? '<span class="go">' +
      (FEED_GO[n.kind] || "Javob berish →") + '</span>' : "") +
    '<span class="fc-meta">' + dayLabel(n.created_at) +
    (rest ? ' · yana ' + rest + ' ta xabar' : '') + '</span>' +
    '</div>' +
    '<div class="m"><img src="/mascots/trim/mascot-' + mascot + '.webp?v=' + ASSET_V + '" alt=""></div>' +
    '<button class="fc-x" data-action="feed-read" data-id="' + n.id + '" aria-label="Yopish">' +
    icon("x", 15, 2.4) + '</button>' +
    '</div>';
}

// ---------------- KECHKI SUHBAT (Oila iftixori nishoni) ----------------
// Tasdiqni faqat ota-ona beradi — uchta javobdan biri, tamom.
// Nishon FAQAT «a'lo javob berdi» tanlanganda beriladi.
function openTalkCheck(notifId, kind, topic) {
  openModal("Kechki suhbat",
    (topic ? '<p class="talk-topic">' + escapeHtml(topic) + '</p>' : "") +
    '<p class="section-sub">Bugun farzandingiz bilan shu mavzuda gaplashdingizmi?</p>' +
    '<button class="btn btn-primary btn-block" data-action="talk-parent" data-id="' + notifId + '" data-a="great">Gaplashdik, a\'lo javob berdi</button>' +
    '<button class="btn btn-outline btn-block" data-action="talk-parent" data-id="' + notifId + '" data-a="ok">Gaplashdik, o‘rtacha javob</button>' +
    '<button class="btn btn-block" data-action="talk-parent" data-id="' + notifId + '" data-a="missed">Bugun ulgurmadik</button>'
  );
}

// ---------------- «PARVOZING UZILMASIN» OGOHLANTIRISHI ----------------
// Ega talabi: xabarning O‘ZIDA Qanot sotib olish yo‘li bo‘lsin — bola
// do‘konni qidirib yurmasin.
async function openStreakWarn(notifId) {
  let f = { have: 0, max: 3, price: 15, can_buy: false };
  try { f = await api("/api/child/freeze" + asChildQuery()); } catch (e) {}
  const full = f.have >= f.max;
  let html = '<p class="section-sub">Bugun hali o‘qimading. Kitob ochsang, parvozing davom etadi.</p>';
  if (f.have > 0) {
    html += '<p class="section-sub">Hozir sende <b>' + f.have + '</b> ta Qanot bor — ' +
            'o‘qimasang, bittasi sarflanadi.</p>';
  }
  html += '<button class="btn btn-primary btn-block" data-action="warn-go-read" data-id="' +
          notifId + '">Kitobni ochish</button>';
  if (!full) {
    html += '<button class="btn btn-outline btn-block" data-action="warn-buy-qanot" data-id="' +
            notifId + '"' + (f.can_buy ? "" : " disabled") + '>Qanot olish — ' +
            (f.price || 15) + ' Bilig</button>';
    if (!f.can_buy) html += '<p class="section-sub">Qanot uchun Bilig yetarli emas.</p>';
  }
  openModal("Parvozing uzilmasin", html);
}

async function buyQanotFromWarn(notifId) {
  const res = await api("/api/child/freeze/buy" + asChildQuery(), { method: "POST" });
  if (!res.ok) { toast(res.message); return; }
  closeModal();
  await readFeed(Number(notifId));
  mascotToast("qorbars-tanga", "Qanot olindi",
              "Endi bir kun o‘qiy olmasang ham, parvozing uzilmaydi.");
  refreshHeader();
}

// Xabar raqamidan tekshiruv raqamini olamiz — lentadagi yozuvda saqlanadi.
function feedRefOf(notifId) {
  const n = (State.feed || []).filter(function (x) { return x.id === Number(notifId); })[0];
  return n ? n.ref_id : 0;
}

async function answerTalkParent(notifId, answer) {
  const ref = feedRefOf(notifId);
  const res = await api("/api/parent/talk_check/" + ref, {
    method: "POST", body: { answer: answer }
  });
  closeModal();
  if (res.new_badge) {
    mascotToast("sherbola-galaba", "«Oila iftixori» nishoni berildi",
                (res.child_name || "Farzandingiz") + " uni siz bilan bo‘lgan suhbat uchun qo‘lga kiritdi.");
  } else if (answer === "missed") {
    toast("Mayli, ertaga ulgurasiz");
  } else {
    toast("Rahmat, yozib qo‘ydik");
  }
  await refreshFeed();
}

// Lentani serverdan qayta o‘qib, kartochkani yangilaydi.
async function refreshFeed() {
  try {
    const d = isChildView()
      ? await api("/api/child/home" + asChildQuery())
      : await api("/api/parent/home/" + State.selectedChildId);
    State.feed = d.feed || [];
  } catch (e) { State.feed = []; }
  const slot = document.getElementById("feed-slot");
  if (slot) slot.innerHTML = feedCardHtml();
}

// «x» bosildi: xabar o‘qildi deb belgilanadi va keyingisi chiqadi.
// Bola va ota-ona xabarlari alohida saqlanadi, shuning uchun manzil ham har xil.
async function readFeed(notifId) {
  const slot = document.getElementById("feed-slot");
  const card = slot ? slot.querySelector(".feed-card") : null;
  if (card) card.classList.add("is-leaving");
  // Nishon xabari bazada yozuv emas (raqami 0) — u boshqacha yopiladi.
  if (Number(notifId) === 0) {
    try { await api("/api/child/badges/seen" + asChildQuery(), { method: "POST" }); } catch (e) {}
    State.feed = (State.feed || []).filter(function (n) { return n.id !== 0; });
    if (slot) slot.innerHTML = feedCardHtml();
    return;
  }
  const path = isChildView() ? "/api/child/feed/" : "/api/parent/feed/";
  const res = await api(path + notifId + "/read" + (isChildView() ? asChildQuery() : ""),
                        { method: "POST" });
  State.feed = res.feed || [];
  if (slot) slot.innerHTML = feedCardHtml();
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
            title: "Muqovani joyla", hint: "Kitob muqovasi ramka ichida qolsin" },
  gift:   { w: 260, h: 200, outW: 420, outH: 320, round: false, quality: 0.72,
            maxBytes: 56 * 1024,
            title: "Sovg‘a rasmi", hint: "Sovg‘a ramka ichida yaqqol ko‘rinsin" }
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

  // Server bir muddat ishlatilmasa uyquga ketadi va birinchi so‘rov
  // javobsiz qolishi mumkin. Ilgari shunda ekranda quruq «Server
  // xatoligi» chiqardi. Endi ma'lumot SO‘RASH (GET) jimgina qayta
  // urinib ko‘riladi. Ma'lumot YUBORISH takrorlanmaydi — aks holda
  // bitta test ikki marta topshirilgan bo‘lib qolardi.
  const isGet = fetchOpts.method === "GET";
  const tries = isGet ? 3 : 1;
  let res = null;
  for (let attempt = 0; attempt < tries; attempt++) {
    if (attempt) await new Promise(function (r) { setTimeout(r, attempt * 1200); });
    try {
      res = await fetch(url, fetchOpts);
    } catch (err) {
      res = null;                   // aloqa uzildi — yana urinamiz
      continue;
    }
    if (res.status >= 500 && attempt < tries - 1) continue;
    break;
  }
  if (!res) throw { error: "Aloqa uzildi. Internetni tekshirib, qaytadan urining.", offline: true };

  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) {
    throw (data || { error: res.status >= 500
      ? "Server javob bermadi. Bir zumdan keyin qaytadan urining."
      : "So‘rov bajarilmadi. Qaytadan urining." });
  }
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
  syncBackButton();
}
function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
  document.getElementById("modal-body").innerHTML = "";
  syncBackButton();
}

// ==========================================================
// «ORQAGA» TUGMASI
// ==========================================================
// Ega talabi: bir sahifa ortga qaytish yo‘li bo‘lsin. Telegram oynasining
// O‘Z tugmasidan foydalanamiz — u tepada, «Yopish» yonida chiqadi va
// telefonning orqaga ishorasi bilan ham ishlaydi. Ilova ichiga yana bitta
// tugma qo‘yilsa, ekran tor bo‘lib qolardi.
//
// Qaytish tartibi: ochiq oyna → hamyon/ichki sahifa → bosh sahifa.
function isModalOpen() {
  const o = document.getElementById("modal-overlay");
  return !!o && !o.classList.contains("hidden");
}

function syncBackButton() {
  // Oyna ochiq bo‘lsa, sarlavha oynaning ostida qoladi — u yerdagi tugma
  // ko‘rinmaydi, oynaning o‘z «x» belgisi ishlaydi.
  const canGoBack = !!State.subPage ||
    (State.currentTab === "store" && State.storeView === "wallet") ||
    (State.currentTab && State.currentTab !== "home");

  const btn = document.getElementById("header-back");
  if (btn) btn.classList.toggle("hidden", !canGoBack);

  // Telegramniki ham yonma-yon ishlaydi: u ochiq oynani ham yopa oladi.
  if (!tg || !tg.BackButton) return;
  if (canGoBack || isModalOpen()) tg.BackButton.show(); else tg.BackButton.hide();
}

async function goBack() {
  haptic();
  if (isModalOpen()) { closeModal(); return; }
  if (State.currentTab === "store" && State.storeView === "wallet") {
    State.storeView = "shop";
    await renderStoreTab();
    syncBackButton();
    return;
  }
  if (State.subPage === "group") {
    State.groupId = null;
    State.subPage = null;
    await renderRatingTab();
    syncBackButton();
    return;
  }
  if (State.subPage) {
    State.subPage = null;
    document.getElementById("app-main").innerHTML = skeleton("home");
    await renderParentHome();
    syncBackButton();
    return;
  }
  if (State.currentTab !== "home") switchTab("home");
}

if (tg && tg.BackButton) tg.BackButton.onClick(function () { goBack(); });
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
  // Ma'lumot kelmasa ham sarlavha ESKI holatda qolib ketmasligi kerak:
  // shunda ilova bir joyi ota-ona, bir joyi bola bo‘lib chalkashardi.
  // Shu sabab so‘rov muvaffaqiyatsiz bo‘lsa, bor bilganimiz bilan
  // sarlavhani baribir to‘g‘rilaymiz.
  let me = State.me || {};
  try {
    me = await api("/api/me");
    State.me = me;
  } catch (e) {
    me = { name: State.activeChildName || (State.me && State.me.name) || "",
           role: State.role, avatar_id: (State.me && State.me.avatar_id) || "fox" };
  }
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
  { id: "plans", label: "Kitobxona", icon: "book-open" },
  { id: "store", label: "Do‘kon", icon: "cart" },
  { id: "bolaxona", label: "Bolaxona", icon: "users" },
];
// Bolada to‘rtinchi tab yo‘q: natija, nishonlar, guruhlar va reyting
// sarlavhadagi kubok belgisi ichiga yig‘ildi. Sabab — uyda bitta telefon
// bo‘lishi mumkin, ya'ni ota-ona ham shu bo‘limga kira olishi kerak,
// uning pastki qatorida esa «Bolaxona» turadi.
const TABS_CHILD = [
  { id: "home", label: "Bosh sahifa", icon: "home" },
  { id: "plans", label: "Kitobxona", icon: "book-open" },
  { id: "store", label: "Do‘kon", icon: "cart" },
];
const TABS_PARENT_ACTING = [
  { id: "home", label: "Bosh sahifa", icon: "home" },
  { id: "plans", label: "Kitobxona", icon: "book-open" },
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
  // Ko‘rinishni AVVAL to‘liq almashtiramiz, so‘ng ma'lumot so‘raymiz.
  // Ilgari teskarisi edi: so‘rov bajarilmay qolsa, pastdagi tugmalar
  // ota-onaniki, sarlavha va tepadagi lenta esa bolaniki bo‘lib qolardi.
  // Aynan shunda «Bolaxona rejimi» yozuvi turib, ota-ona hamyoni —
  // Bilig kursi bilan birga — ochilib ketardi.
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
  switchTab("home");
  await refreshHeader();
}

// Sarlavhada bitta belgi — kubok. Ichida to‘rtta ko‘rinish bor:
// natija, nishonlar, guruhlar va reyting. Ilgari bu yerda uchta alohida
// tugma turardi va uzun ism ularga sig‘masdi.
// Global reyting olib tashlandi (2026-08-31, ega qarori): butun ilova
// bo‘yicha ro‘yxatda o‘rtacha bola hech qachon ko‘rinmasdi va bu unga
// rag‘bat bermasdi; qolaversa begona bolalarning ismi ochiq turardi.
// Uning o‘rnini guruh reytingi egalladi — oila ham o‘ziga guruh ochadi.
const RATING_VIEWS = [
  { mode: "passport", icon: "chart", label: "Natijam" },
  { mode: "badges", icon: "award", label: "Nishonlar" },
  { mode: "groups", icon: "users", label: "Guruhlar" },
];

function renderHeaderNav() {
  const box = document.getElementById("header-nav");
  if (!box) return;
  // Bola rejimida ham, ota-ona kabinetida ham bir joyda turadi
  const on = State.currentTab === "rating";
  box.innerHTML = '<button class="icon-btn' + (on ? " is-on" : "") +
    '" data-action="open-rating" aria-label="Natijalar" title="Natijalar">' +
    icon("trophy", 18, 1.8) + '</button>';
}

function ratingChipsHtml(mode) {
  return '<div class="chip-row">' + RATING_VIEWS.map(function (v) {
    return '<button class="chip' + (v.mode === mode ? " active" : "") +
      '" data-action="open-rating" data-mode="' + v.mode + '">' +
      icon(v.icon, 16, 2) + escapeHtml(v.label) + '</button>';
  }).join("") + '</div>';
}

function openRatingFromHeader() {
  document.querySelectorAll(".tab-btn").forEach(function (b) { b.classList.remove("active"); });
  State.currentTab = "rating";
  State.subPage = null;
  syncBackButton();
  const main = document.getElementById("app-main");
  main.innerHTML = skeleton("rows");
  renderRatingTab().catch(function (e) { main.innerHTML = '<div class="empty-state">' + escapeHtml(e.error || "Xatolik yuz berdi") + '</div>'; });
}

function isChildView() { return State.role === "child" || !!State.activeChildId; }
function asChildQuery() {
  const cid = State.activeChildId || (State.role === "parent" ? State.selectedChildId : null);
  return cid ? "?as_child=" + cid : "";
}

function switchTab(tabId) {
  State.currentTab = tabId;
  State.subPage = null;
  // Hamyon do‘kon ichidagi ko‘rinish. Pastdagi tab qayta bosilsa,
  // foydalanuvchi sovg‘alar javonini kutadi — shuning uchun tiklanadi.
  if (tabId === "store") State.storeView = "shop";
  document.querySelectorAll(".tab-btn").forEach(function (b) { b.classList.toggle("active", b.dataset.tab === tabId); });
  const renderers = isChildView()
    ? { home: renderChildHome, plans: renderChildPlans, store: renderStoreTab, rating: renderRatingTab }
    : { home: renderParentHome, plans: renderParentPlans, store: renderStoreTab, bolaxona: renderBolaxonaTab };
  const fn = renderers[tabId];
  const main = document.getElementById("app-main");
  main.innerHTML = skeleton(SK_KIND[tabId] || "list");
  // Sahifa ochilmay qolsa — quruq xato matni emas, qayta urinish tugmasi
  // bilan tushunarli kartochka chiqadi.
  syncBackButton();
  if (fn) fn().catch(function (e) {
    main.innerHTML =
      '<div class="load-error">' +
      '<div class="load-error-icon">' + icon("refresh", 26, 1.7) + '</div>' +
      '<p class="load-error-title">Sahifa ochilmadi</p>' +
      '<p class="load-error-sub">' + escapeHtml(e.error || "Qaytadan urinib ko‘ring.") + '</p>' +
      '<button class="btn btn-primary" data-action="retry-tab" data-tab="' + tabId + '">Qayta urinish</button>' +
      '</div>';
  });
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
      case "retry-tab": switchTab(el.dataset.tab); break;
      case "close-modal": closeModal(); break;
      case "go-back": await goBack(); break;

      case "open-child-detail":
        State.selectedChildId = Number(el.dataset.id);
        State.subPage = "child-detail";
        await renderChildDetailPage(State.selectedChildId);
        syncBackButton();
        break;
      case "back-to-home":
        State.subPage = null;
        document.getElementById("app-main").innerHTML = skeleton("home");
        await renderParentHome();
        syncBackButton();
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
      case "open-catalog": await Catalog.openBrowse(); break;
      case "cat-back": await Catalog.openBrowse(); break;
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
      case "open-store-edit": openStoreEditModal(el.dataset.id); break;
      case "submit-store-save": await submitStoreSave(el.dataset.id || null); break;
      case "delete-store-item":
        await api("/api/parent/store/" + el.dataset.id, { method: "DELETE" });
        toast("Sovg‘a o‘chirildi"); closeModal(); switchTab("store");
        break;
      case "gift-photo": pickGiftPhoto(); break;
      case "gift-emoji-toggle": toggleEmojiGrid(); break;
      case "gift-emoji": pickGiftEmoji(el.dataset.e); break;
      case "quick-gift": await addQuickGift(el.dataset.name, el.dataset.price, el.dataset.emoji); break;
      case "open-rate": openRateModal(); break;
      case "submit-rate": await submitRate(); break;

      case "open-wallet": State.storeView = "wallet"; await renderStoreTab(); syncBackButton(); break;
      case "close-wallet": State.storeView = "shop"; await renderStoreTab(); syncBackButton(); break;
      case "gift-given": await markGiftGiven(Number(el.dataset.id)); break;
      case "feed-read": await readFeed(Number(el.dataset.id)); break;
      case "feed-open":
        if (el.dataset.kind === "unseen_badges") await showUnseenBadges();
        else if (el.dataset.kind === "streak_warn") await openStreakWarn(el.dataset.id);
        else openTalkCheck(el.dataset.id, el.dataset.kind, el.dataset.topic);
        break;
      case "warn-buy-qanot": await buyQanotFromWarn(el.dataset.id); break;
      case "warn-go-read": closeModal(); await readFeed(Number(el.dataset.id)); switchTab("plans"); break;
      case "talk-parent": await answerTalkParent(el.dataset.id, el.dataset.a); break;

      case "open-rec-book": openRecBookModal(el.dataset.i); break;
      case "open-badge": openBadgeModal(el.dataset.slug); break;
      case "share-badge": shareBadge(el.dataset.slug); break;
      case "open-done-books": openDoneBooksModal(); break;
      case "open-marathon": openMarathonModal(el.dataset.id); break;
      case "rec-add-confirm": {
        const rb = RecBooks[Number(el.dataset.i)] || {};
        await addRecommendedBook(rb.title, rb.author);
        break;
      }
      case "rec-ask-confirm": {
        const rb2 = RecBooks[Number(el.dataset.i)] || {};
        await askForBook(rb2.title, rb2.author);
        break;
      }
      case "add-book-for":
        State.selectedChildId = Number(el.dataset.id);
        await Wizard.start();
        break;

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
              State.childrenCache = await api("/api/parent/children");
              await refreshHeader();
              refreshAfterChildEdit(editChildId);
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
      case "open-talk": openTalkModal(Number(el.dataset.id), el.dataset.stage); break;
      case "voice-resend":
        VoiceDraft.triedBoth = false;      // qayta bosilganda ikkala usul yana sinaladi
        await sendVoice(Number(el.dataset.id),
                        State.me && State.me.voice_prefer === "asl");
        break;
      case "open-test": await openTestModal(Number(el.dataset.id), el.dataset.stage); break;
      case "select-test-opt": Test.select(el.dataset.qid, el.dataset.val); break;
      case "submit-test": await Test.submit(Number(el.dataset.book)); break;

      case "buy-item": openBuyConfirm(el.dataset.id, el.dataset.name, el.dataset.price); break;
      case "confirm-buy": await buyItem(Number(el.dataset.id)); break;
      case "toggle-goal": await toggleGoal(el.dataset.id, !!el.dataset.on); break;
      case "buy-freeze": await buyFreeze(); break;
      case "go-store-tab": switchTab("store"); break;

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
        if (el.dataset.mode) State.ratingMode = el.dataset.mode;
        State.groupId = null;
        State.groupFound = null;
        openRatingFromHeader();
        break;
      case "switch-child":
        State.selectedChildId = Number(el.dataset.id);
        await refreshHeader();
        if (State.currentTab === "rating") { renderRatingTab(); }
        else { switchTab(State.currentTab || "home"); }
        break;
      case "group-open":
        State.groupId = Number(el.dataset.id);
        State.groupTab = "members";
        State.groupMemberId = null;
        State.subPage = "group";
        await renderRatingTab();
        break;
      case "group-back":
        State.groupId = null;
        State.groupMemberId = null;
        State.subPage = null;
        await renderRatingTab();
        break;
      case "group-tab":
        State.groupTab = el.dataset.id;
        await renderRatingTab();
        break;
      case "group-period":
        State.groupPeriod = el.dataset.id;
        await renderGroupRating(State.groupId);
        break;
      case "group-member-card":
        State.groupMemberId = Number(el.dataset.id);
        await renderRatingTab();
        break;
      case "group-member-back":
        State.groupMemberId = null;
        await renderRatingTab();
        break;
      case "group-search": await groupSearchRun(); break;
      case "group-create": openGroupCreateModal(); break;
      case "group-create-save": await submitGroupCreate(); break;
      case "group-join": openGroupJoinModal(); break;
      case "group-join-save": await submitGroupJoin(); break;
      case "group-settings": await openGroupSettings(); break;
      case "group-settings-save": await submitGroupSettings(); break;
      case "group-request":
        await api(groupUrl("/api/groups/" + el.dataset.id + "/request"), { method: "POST", body: {} });
        toast("So‘rov yuborildi — admin tasdiqlaydi");
        await groupSearchRun();
        break;
      case "group-decide":
        await api(groupUrl("/api/groups/" + State.groupId + "/requests/" + el.dataset.id),
          { method: "POST", body: { action: el.dataset.act } });
        toast(el.dataset.act === "approve" ? "Qabul qilindi" : "Rad etildi");
        await renderRatingTab();
        break;
      case "group-member":
        openGroupMemberModal(Number(el.dataset.id), el.dataset.name, el.dataset.admin === "1");
        break;
      case "group-set-admin":
        await api(groupUrl("/api/groups/" + State.groupId + "/member/" + el.dataset.id),
          { method: "POST", body: { is_admin: el.dataset.val === "1" } });
        closeModal();
        toast("Bajarildi");
        await renderRatingTab();
        break;
      case "group-remove":
        await api(groupUrl("/api/groups/" + State.groupId + "/leave"),
          { method: "POST", body: { child_id: Number(el.dataset.id) } });
        closeModal();
        toast("Guruhdan chiqarildi");
        await renderRatingTab();
        break;
      case "group-leave":
        if (!confirm("Guruhdan chiqasizmi? O‘qigan kitoblaringiz o‘zingizda qoladi.")) break;
        await api(groupUrl("/api/groups/" + State.groupId + "/leave"), { method: "POST", body: {} });
        State.groupId = null;
        State.subPage = null;
        toast("Guruhdan chiqdingiz");
        await renderRatingTab();
        break;
      case "demo-fill": await demoFill(Number(el.dataset.id), el.dataset.name); break;
      case "demo-clear": await demoClear(Number(el.dataset.id), el.dataset.name); break;
    }
  } catch (err) {
    // err.message — brauzerning texnik matni («Cannot read properties…»).
    // Uni ko‘rsatmaymiz: foydalanuvchiga foydasi yo‘q, faqat qo‘rqitadi.
    toast(err.error || "Hozir bo‘lmadi. Qaytadan urinib ko‘ring.");
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
    main.innerHTML = emptyState("users", "Keling, farzandingizni qo‘shamiz",
      "Unga alohida telefon ham, alohida hisob ham shart emas.", {
        mascot: "tipratikan-salom",
        steps: ["Farzandingizning ismi, yoshi va avatarini tanlaysiz",
                "Unga birinchi kitobni qo‘yasiz",
                "U o‘qigan sahifasini rasmga oladi — qolganini AI bajaradi"],
        action: "open-add-child", label: "Farzand qo‘shish", btnIcon: "plus"
      });
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

  // ---- 1b. Xabarlar lentasi ----
  // Farzandlar faoliyati bo‘yicha eng so‘nggi xabar. «x» bosilsa u yopiladi
  // va keyingi o‘qilmagani chiqadi; xabar qolmasa — bo‘lim umuman yo‘qoladi.
  State.feed = primaryData.feed || [];
  html += '<div id="feed-slot">' + feedCardHtml() + '</div>';

  // ---- 2. Kitob qo‘shish ----
  html += '<div class="hero-card" data-action="open-add-plan">' +
    HERO_MASCOT +
    '<div class="icon-circle">' + icon("plus-circle", 22, 1.8) + '</div>' +
    '<p class="hc-title">Kitob qo‘shish</p>' +
    '<div style="display:flex;align-items:center;gap:6px;font-size:15px;font-weight:600;">Tezkor yoki marafon rejasi ' + icon("arrow-right", 15, 2) + '</div>' +
    '</div>';

  // ---- 3. So‘nggi natijalar (ilgari bu joyda 3 ta statistika qutisi turardi) ----
  html += '<p class="sec-label">So‘nggi natijalar</p>' +
    '<div class="res-card is-tappable" data-action="open-result">' +
    '<div class="res-who"><span class="av">' + avatarMarkup(primary.avatar_id || "fox", 48) + '</span>' +
    '<span>' + escapeHtml(primary.name) + '</span></div>' +
    '<div class="res-list">' +
    resRow("flame", "ic-flame", "Parvoz", primaryData.streak + " kun") +
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


  // ---- 6. Kitoblar javoni (yon tarafga siljitiladi) ----
  // Nishonlar qatori bu yerdan olib tashlandi (ega so‘radi) — u endi
  // «Farzand statistikasi» sahifasida, diagnostika bo‘limi tepasida turadi.
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
  main.innerHTML = skeleton("home");
  const data = await api("/api/parent/home/" + childId);
  const c = State.childrenCache.filter(function (x) { return x.id === childId; })[0] || {};

  // O‘ng tomonda tahrirlash — ism, yosh va avatarni shu yerdan ham
  // o‘zgartirish mumkin (Bolaxona ro‘yxatidagi tugma bilan bir xil oyna).
  let html = '<div class="detail-topbar">' +
    '<button class="back-link" data-action="back-to-home">' + icon("arrow-left", 16, 2) + ' Orqaga</button>' +
    '<button class="edit-link" data-action="edit-child"' +
      ' data-id="' + childId + '"' +
      ' data-name="' + escapeHtml(data.name || c.name || "") + '"' +
      ' data-age="' + (c.age || "") + '"' +
      ' data-avatar="' + (c.avatar_id || "fox") + '">' +
      icon("edit", 15, 2) + ' Tahrirlash</button>' +
    '</div>';

  html += '<div class="child-detail-header">' +
    '<span class="avatar-circle" style="width:64px;height:64px">' + avatarMarkup(c.avatar_id || "fox", 64) + '</span>' +
    '<p class="child-detail-name">' + escapeHtml(data.name || c.name || "") + '</p>' +
    '</div>';

  html += '<div class="stat-grid">' +
    '<div class="stat-box"><div class="num">' + data.streak + '</div><div class="lbl">Parvoz</div></div>' +
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

  // ---- 0. Xabarlar lentasi ----
  // Ko‘rilmagan nishonlar ham shu lentaga tushadi (ilgari alohida
  // «Xush kelibsan» kartochkasi turardi — ega uni olib tashlashni so‘radi).
  State.feed = data.feed || [];
  let html = '<div id="feed-slot">' + feedCardHtml() + '</div>';

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
      '<div style="font-size:15px;font-weight:600;display:flex;align-items:center;gap:6px">Kitobxonani ochish ' + icon("arrow-right", 15, 2) + '</div>' +
      '</div>';
  }

  // ---- 1b. Orzu qilingan sovg‘a ----
  // Bola do‘kondan bitta sovg‘ani maqsad qilib belgilaydi; unga qancha
  // qolgani shu yerda ko‘rinib turadi.
  if (data.goal) {
    const gl = data.goal;
    html += '<button class="goal-strip" data-action="go-store-tab">' +
      giftThumb(gl) +
      '<div class="gs-mid">' +
      '<p class="gs-name">Orzuim: ' + escapeHtml(gl.name) + '</p>' +
      '<div class="goal-bar"><i style="width:' + gl.percent + '%"></i></div>' +
      '<p class="gs-left">' + (gl.left ? 'Yana <b>' + gl.left + '</b> Bilig' : 'Yetdi! Do‘kondan olsang bo‘ladi') + '</p>' +
      '</div>' + icon("chevron-right", 16, 2.2) + '</button>';
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

  // ---- 6. Kitoblarim (3 tasi; qolgani Kitobxona bo‘limida) ----
  const books = data.shelf_books || data.active_books || [];
  html += '<p class="sec-label">Kitoblarim' +
    (books.length > 3 ? ' <span class="sw" data-action="go-plans-tab">' + icon("chevron-right", 12, 2.4) + '</span>' : "") + '</p>' +
    shelfHtml(books.slice(0, 3), "Hozircha kitob yo‘q — Kitobxonaga qarang.");

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

// ==========================================================
// YUKLANISH SKELETI
// ----------------------------------------------------------
// Ilgari har bir tab ochilganda kichkina g‘ildirak aylanardi, ekran esa
// bo‘m-bo‘sh turardi — foydalanuvchi «ilova qotib qoldimi?» deb o‘ylardi.
// Endi ekranning «soyasi» chiziladi: bo‘sh kartalar aynan keyin
// chiqadigan mazmun o‘rnida turadi. Shunda mazmun kelganda ekran
// sakramaydi va kutish qisqaroq tuyuladi.
// ==========================================================
function skLine(w, h) {
  return '<div class="sk-line" style="width:' + w + ';height:' + (h || 13) + 'px"></div>';
}

function skRepeat(n, html) {
  let out = "";
  for (let i = 0; i < n; i++) out += html;
  return out;
}

function skeleton(kind) {
  let body;
  if (kind === "grid") {
    body = '<div class="sk-grid">' + skRepeat(4, '<div class="sk-tile"></div>') + '</div>';
  } else if (kind === "rows") {
    body = '<div class="sk-card">' + skRepeat(5,
      '<div class="sk-row"><div class="sk-dot"></div><div class="sk-row-body">' +
      skLine("62%", 14) + skLine("38%", 11) + '</div></div>') + '</div>';
  } else if (kind === "home") {
    body = '<div class="sk-hero"></div>' +
      '<div class="sk-card">' + skLine("54%", 17) + skLine("88%") + skLine("64%") + '</div>' +
      '<div class="sk-grid sk-grid-3">' + skRepeat(3, '<div class="sk-tile sk-tile-sm"></div>') + '</div>' +
      '<div class="sk-card">' + skLine("46%", 15) + skLine("74%") + '</div>';
  } else {
    body = skRepeat(3, '<div class="sk-card sk-card-tall">' +
      skLine("58%", 17) + skLine("92%") + skLine("40%", 11) + '</div>');
  }
  return '<div class="sk-wrap" aria-busy="true" aria-label="Yuklanmoqda">' + body + '</div>';
}

// Qaysi tabga qaysi skelet mos keladi
const SK_KIND = { home: "home", plans: "list", store: "grid", bolaxona: "rows", rating: "rows" };

// ==========================================================
// BO‘SH EKRAN
// ----------------------------------------------------------
// Ilgari bu shunchaki ikona va ikki qator matn edi — foydalanuvchi
// «endi nima qilaman?» degan savol bilan qolardi. Endi uch qismdan
// iborat: maskot (ekran tirik ko‘rinadi), qisqa 1-2-3 yo‘riqnoma va
// eng muhimi — shu yerning O‘ZIDA turgan harakat tugmasi.
//
// opts = { mascot, steps: [...], action, label, btnIcon, data: {...} }
// Eski chaqiruvlar (opts'siz) avvalgidek ishlayveradi.
// ==========================================================
function emptyState(iconName, title, sub, opts) {
  opts = opts || {};
  const art = opts.mascot
    ? '<div class="em-mascot"><img src="/mascots/trim/mascot-' + opts.mascot + '.webp?v=' + ASSET_V + '" alt=""></div>'
    : '<div class="em-icon">' + icon(iconName, 38, 1.4) + '</div>';
  let steps = "";
  if (opts.steps && opts.steps.length) {
    steps = '<ol class="em-steps">' + opts.steps.map(function (t, i) {
      return '<li><span class="em-num">' + (i + 1) + '</span><span>' + escapeHtml(t) + '</span></li>';
    }).join("") + '</ol>';
  }
  let btn = "";
  if (opts.action) {
    let attrs = "";
    const data = opts.data || {};
    Object.keys(data).forEach(function (k) {
      attrs += ' data-' + k + '="' + escapeHtml(String(data[k])) + '"';
    });
    btn = '<button class="btn btn-primary em-btn" data-action="' + opts.action + '"' + attrs + '>' +
      (opts.btnIcon ? icon(opts.btnIcon, 17, 2) : "") +
      '<span>' + escapeHtml(opts.label || "Boshlash") + '</span></button>';
  }
  // Harakat tugmasi yo‘riqnomadan YUQORIDA turadi: foydalanuvchi avval
  // nima qilishini ko‘rsin, izohni esa xohlasa keyin o‘qiydi. Ilgari
  // tugma uchta qadamdan keyin, ekranning pastida qolib ketardi.
  return '<div class="empty-state">' + art +
    '<p class="em-title">' + title + '</p>' +
    (sub ? '<p class="em-sub">' + sub + '</p>' : "") + btn + steps + '</div>';
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
    main.innerHTML = emptyState("users", "Bolaxona hozircha bo‘sh",
      "Farzand qo‘shsangiz, uning ekraniga shu yerdan kirasiz.", {
        mascot: "tipratikan-salom",
        steps: ["Farzandingizni qo‘shasiz",
                "«Kirish» tugmasi orqali uning ekraniga o‘tasiz",
                "Kitob, test va do‘konni uning nomidan sinab ko‘rasiz"],
        action: "open-add-child", label: "Farzand qo‘shish", btnIcon: "plus"
      });
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
// DIQQAT: ilovaga yangi imkoniyat qo‘shilsa (yangi bo‘lim, xabar turi,
// sovg‘a xususiyati va h.k.) — `demo_data.py` ga ham qo‘shing. «To‘ldirish»
// bosilganda ega ilovaning ENG OXIRGI holatini to‘liq ko‘rishi kerak.
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
  if (!confirm(name + " profili namoyish uchun to‘liq to‘ldiriladi:\n" +
      "kitoblar, testlar, AI tahlillar, nishonlar, hamyon tarixi, sovg‘alar, " +
      "xabarnomalar va kechki suhbat savoli.\n\n" +
      "DIQQAT: uning hozirgi kitoblari, natijalari va xabarlari o‘chib ketadi. " +
      "Davom etamizmi?")) return;
  const res = await api("/api/admin/demo", { method: "POST", body: { child_id: childId, action: "fill" } });
  toast(res.books + " ta kitob, " + res.badges + " ta nishon, " +
        res.messages + " ta xabar, " + res.balance + " Bilig");
  State.childrenCache = await api("/api/parent/children");
  // Namoyish uchun darrov farzandning ekraniga kiramiz: bosh sahifaning
  // yuqorisida tipratikanli kutib olish kartochkasi turadi. Uni bosib,
  // to‘liq ekranli nishon tabrigini ko‘rsatish mumkin.
  State.selectedChildId = childId;
  State.activeChildId = childId;
  State.activeChildName = name;
  await setupTabsForRole();
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
  const addPlanBtn =
    '<button class="btn btn-primary btn-block" data-action="open-add-plan" style="display:flex;align-items:center;justify-content:center;gap:6px">' + icon("plus", 17, 2) + ' Yangi kitob qo‘shish</button>';
  let html = childSwitcherHtml();

  // «Alohida kitob» va «marafon kitobi» degan ajratish olib tashlandi:
  // ega buni tushunarsiz deb topdi. Endi O‘QILAYOTGAN hamma kitob bitta
  // ro‘yxatda turadi — marafon ichidagilari ham. Marafonning o‘zi esa
  // alohida kartochka bo‘lib, ichiga kirib ko‘riladi.
  const reading = [];
  const done = [];
  const marathons = [];
  plans.forEach(function (p) {
    if (p.type === "marathon") marathons.push(p);
    p.books.forEach(function (b) { (b.completed ? done : reading).push(b); });
  });

  if (!reading.length && !done.length && !marathons.length) {
    html += emptyState("book-open", "Birinchi kitobni tanlaymiz",
      "Katalogdan tanlaysiz yoki muqovasini rasmga olasiz — ikkalasi ham bir necha soniya.", {
        mascot: "tulki-oqish",
        steps: ["Kitobni tanlaysiz va necha kunda o‘qishni belgilaysiz",
                "Farzandingiz har kuni o‘qigan sahifasini rasmga oladi",
                "AI tekshiradi, test beradi va Bilig yozadi"],
        action: "open-add-plan", label: "Kitob qo‘shish", btnIcon: "plus"
      });
    html += await recShelfHtml(false);
    html += await familyReadingHtml();
    main.innerHTML = html;
    return;
  }

  html += addPlanBtn;
  html += await recShelfHtml(false);          // tavsiyalar yuqorida turadi

  if (reading.length) {
    html += '<p class="section-title">O‘qilayotgan kitoblar</p>';
    sortByLastRead(reading).forEach(function (b) { html += bookCardHtml(b, true); });
  }
  MarathonCache = marathons;
  if (marathons.length) {
    html += '<p class="section-title">Marafonlar</p>';
    marathons.forEach(function (p) { html += marathonCardHtml(p); });
  }
  html += doneShelfHtml(done);
  html += await familyReadingHtml();
  main.innerHTML = html;
}

// «Oila kitobxonligi» — qaysi farzand nima o‘qiyapti, rejasida nechta kitob.
// Ota-ona bitta qarashda butun oilaning holatini ko‘radi.
async function familyReadingHtml() {
  let kids = [];
  try { kids = await api("/api/parent/family_reading"); } catch (e) { return ""; }
  if (!kids.length) return "";
  return '<p class="sec-label">Oila kitobxonligi</p>' +
    '<div class="card fam-list">' + kids.map(function (c) {
      const cur = c.current;
      const pct = cur && cur.total_pages
        ? Math.min(100, Math.round(cur.pages_read * 100 / cur.total_pages)) : 0;
      return '<div class="fam-row">' +
        '<span class="fam-av">' + avatarMarkup(c.avatar_id, 44) + '</span>' +
        '<div class="fam-mid">' +
        '<p class="fam-name">' + escapeHtml(c.name) +
        '<span class="fam-age">' + c.age + ' yosh</span></p>' +
        (cur
          ? '<p class="fam-book">Hozir: «' + escapeHtml(cur.title) + '»</p>' +
            (cur.total_pages ? '<div class="goal-bar"><i style="width:' + pct + '%"></i></div>' : "") +
            '<p class="fam-meta">' + cur.pages_read +
            (cur.total_pages ? "/" + cur.total_pages : "") + ' bet · Rejada ' +
            c.book_count + ' ta · Tugatgan ' + c.done_count + ' ta</p>'
          : '<p class="fam-book is-soft">Hozir kitob o‘qimayapti</p>' +
            '<p class="fam-meta">Rejada ' + c.book_count + ' ta · Tugatgan ' +
            c.done_count + ' ta</p>' +
            '<button class="btn btn-outline fam-btn" data-action="add-book-for" data-id="' +
            c.id + '">Kitob qo‘yish</button>') +
        '</div></div>';
    }).join("") + '</div>';
}

// Eng oxirgi o‘qilgan kitob doim birinchi turadi — ega talabi: «Eng
// oxirgi o‘qiyotgan kitobi yuqorida turishi kerak. Hamma joyda.»
// Vaqti teng bo‘lsa (yoki hali o‘qilmagan bo‘lsa) ko‘proq o‘qilgani ustun.
function sortByLastRead(list) {
  return list.sort(function (a, b) {
    const x = a.last_read_at || "", y = b.last_read_at || "";
    if (x !== y) return x < y ? 1 : -1;
    return (b.pages_read || 0) - (a.pages_read || 0);
  });
}

// Yoshga mos tavsiyalar javoni. Kitobga bosilsa oyna ochiladi: ota-onada
// «Rejaga qo‘shish», bolada «So‘rayman» tugmasi bilan.
async function recShelfHtml(forChild) {
  let books = [], childName = "";
  try {
    if (forChild) {
      books = await api("/api/child/recommended" + asChildQuery());
    } else {
      const d = await api("/api/parent/recommended" +
        (State.selectedChildId ? "?child_id=" + State.selectedChildId : ""));
      books = d.books || [];
      childName = (d.child && d.child.name) || "";
    }
  } catch (e) { return ""; }
  if (!books.length) return "";

  // Sarlavhaning o‘zi tugma: o‘ngdagi «Barchasi» bosilsa butun javon
  // ochiladi (ega talabi — bazadagi hamma kitobni ko‘rish mumkin bo‘lsin).
  return '<button class="sec-more" data-action="open-catalog">' +
    '<span class="sec-label" style="margin:0">' +
    // Faqat ISM olinadi: to‘liq familiya bilan sarlavha ikki qatorga
    // tushib, «Barchasi» tugmasiga tiqilib qolardi.
    (forChild ? "Senga tavsiya"
              : (childName ? escapeHtml(childName.trim().split(/\s+/)[0]) + " yoshiga tavsiya"
                           : "Tavsiya etilgan kitoblar")) +
    '</span>' +
    '<span class="sec-more-go">Barchasi ' + icon("chevron-right", 15, 2.2) + '</span>' +
    '</button>' +
    '<p class="section-sub">' + (forChild
      ? "Yoqqanini bossang, kitob haqida o‘qiysan."
      : "Kitobni bosib, farzandingiz rejasiga qo‘shasiz.") + '</p>' +
    '<div class="rec-shelf">' + books.map(function (b, i) {
      RecBooks[i] = b;                       // oyna shu ro‘yxatdan to‘ldiriladi
      return '<button class="rec-item" data-action="open-rec-book" data-i="' + i + '">' +
        coverHtml(b.title, b.author, "rec-cover") +
        '<span class="rec-name">' + escapeHtml(b.title) + '</span>' +
        (b.author ? '<span class="rec-author">' + escapeHtml(b.author) + '</span>' : "") +
        '</button>';
    }).join("") + '</div>';
}

// Tavsiya javonidagi kitoblar — oyna shu ro‘yxatdan to‘ldiriladi.
const RecBooks = [];
// Katalogdan («Barchasi») ochilgan kitoblar shu ro‘yxatning yuqori
// raqamlariga yoziladi — tavsiya javonining o‘z raqamlari bilan
// to‘qnashmasin.
let CatSeq = 1000;

// Kitob haqidagi oyna. Ota-onada «Rejaga qo‘shish», bolada «So‘rayman».
// Kitob bazasi to‘lgach, bu yerga mavzu va qisqacha mazmun ham chiqadi.
function openRecBookModal(index, fromCatalog) {
  const b = RecBooks[Number(index)];
  if (!b) return;
  // Javondan kelingan bo‘lsa, «Bekor qilish» ilovani yopmaydi —
  // foydalanuvchini javonning o‘ziga qaytaradi.
  const backAction = fromCatalog ? "cat-back" : "close-modal";
  const kid = (State.childrenCache || []).filter(function (c) {
    return String(c.id) === String(State.selectedChildId);
  })[0];

  let html = '<div class="rec-head">' +
    coverHtml(b.title, b.author, "rec-modal-cover") +
    '<div class="rec-head-info">' +
    '<p class="rec-modal-title">' + escapeHtml(b.title) + '</p>' +
    (b.author ? '<p class="rec-modal-author">' + escapeHtml(b.author) + '</p>' : "") +
    (b.age_label ? '<span class="rec-badge">' + escapeHtml(b.age_label) + '</span>' : "") +
    (b.mood ? '<span class="rec-badge soft">' + escapeHtml(b.mood) + '</span>' : "") +
    '</div></div>';

  if (b.theme) html += '<p class="rec-theme">' + escapeHtml(b.theme) + '</p>';
  if (b.summary) html += '<p class="section-sub">' + escapeHtml(b.summary) + '</p>';
  if (!b.theme && !b.summary) {
    html += '<p class="section-sub">' + (isChildView()
      ? "Bu kitob sening yoshingga mos tanlangan."
      : "Bu kitob farzandingiz yoshiga mos tanlangan.") + '</p>';
  }

  if (isChildView()) {
    html += '<p class="rec-ask-q">Shu kitobni o‘qimoqchimisan? Ota-onangga xabar boradi.</p>' +
      '<button class="btn btn-primary btn-block" data-action="rec-ask-confirm" data-i="' + index + '">Ha, so‘rayman</button>' +
      '<button class="btn btn-outline btn-block" data-action="' + backAction + '">' +
      (fromCatalog ? "Orqaga" : "Yo‘q") + '</button>';
  } else {
    html += '<p class="section-sub">' + escapeHtml(kid ? kid.name : "Farzandingiz") +
      ' rejasiga qo‘shiladi.</p>' +
      '<button class="btn btn-primary btn-block" data-action="rec-add-confirm" data-i="' + index + '">Rejaga qo‘shish</button>' +
      '<button class="btn btn-outline btn-block" data-action="' + backAction + '">' +
      (fromCatalog ? "Orqaga" : "Bekor qilish") + '</button>';
  }
  openModal("Kitob haqida", html);
}

async function addRecommendedBook(title, author) {
  // Kitob qo‘shish sehrgaridagi bilan bir xil yo‘l: avval tezkor reja,
  // keyin unga kitob. Shu tufayli kitob oynasi va testlar avvalgidek ishlaydi.
  const childId = State.selectedChildId || (State.childrenCache[0] && State.childrenCache[0].id);
  if (!childId) { toast("Avval farzand qo‘shing"); return; }
  const plan = await api("/api/parent/plans", {
    method: "POST",
    body: { child_id: childId, name: "Tezkor mutolaa", prize: "", type: "quick" }
  });
  await api("/api/parent/plans/" + plan.plan_id + "/books", {
    method: "POST", body: { title: title, author: author, total_pages: 0 }
  });
  closeModal();
  toast("«" + title + "» qo‘shildi");
  switchTab("plans");
}

async function askForBook(title, author) {
  await api("/api/child/book_request" + asChildQuery(), {
    method: "POST", body: { title: title, author: author }
  });
  closeModal();
  mascotToast("boyogli-oqish", "Ota-onangga aytdik",
              "«" + title + "» kitobini so‘raganingni yetkazdik.");
}

// Tugallangan kitoblar — yon tarafga siljiydigan javon. Sarlavhani bosib
// hammasini to‘liq ro‘yxat bo‘lib ko‘rish mumkin.
const DoneBooks = { list: [] };

function doneShelfHtml(list) {
  DoneBooks.list = list || [];
  if (!DoneBooks.list.length) return "";
  return '<button class="sec-more" data-action="open-done-books">' +
    '<span class="section-title" style="margin:0">Tugallangan</span>' +
    '<span class="sec-more-go">' + DoneBooks.list.length + ' ta ' +
    icon("chevron-right", 15, 2.2) + '</span></button>' +
    '<div class="rec-shelf">' + DoneBooks.list.map(function (b) {
      return '<button class="rec-item" data-action="open-book" data-id="' + b.id + '">' +
        coverHtml(b.title, b.author, "rec-cover") +
        '<span class="rec-name">' + escapeHtml(b.title) + '</span>' +
        '<span class="rec-author done">Tugatildi</span>' +
        '</button>';
    }).join("") + '</div>';
}

function openDoneBooksModal() {
  const isParent = !isChildView();
  openModal("Tugallangan kitoblar",
    '<p class="section-sub">Jami ' + DoneBooks.list.length + ' ta kitob.</p>' +
    DoneBooks.list.map(function (b) { return bookCardHtml(b, isParent); }).join("")
  );
}

// Marafon ichi — nomi, sovrini, umumiy yo‘li va kitoblari
function openMarathonModal(planId) {
  const p = (MarathonCache || []).filter(function (x) { return String(x.id) === String(planId); })[0];
  if (!p) return;
  const total = p.books.length;
  const fin = p.books.filter(function (b) { return b.completed; }).length;
  const pct = total ? Math.round(fin / total * 100) : 0;
  openModal(p.name,
    (p.prize ? '<p class="mr-prize-big">Marra sovrini: <b>' + escapeHtml(p.prize) + '</b></p>' : "") +
    '<div class="progress-track"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
    '<div class="progress-label">' + fin + ' / ' + total + ' kitob</div>' +
    (total ? p.books.map(function (b) { return bookCardHtml(b, !isChildView()); }).join("")
           : '<p class="section-sub">Bu marafonga hali kitob qo‘shilmagan.</p>')
  );
}

let MarathonCache = [];

// Marafon — ixcham kartochka. Ichidagi kitoblar asosiy ro‘yxatda turgani
// uchun bu yerda takrorlanmaydi; kartochka bosilsa marafon oynasi ochiladi.
function marathonCardHtml(p) {
  const total = p.books.length;
  const done = p.books.filter(function (b) { return b.completed; }).length;
  const pct = total ? Math.round(done / total * 100) : 0;
  return '<button class="marathon is-tappable" data-action="open-marathon" data-id="' + p.id + '">' +
    '<div class="mr-head">' +
    '<div class="mr-ic">' + icon("award", 18, 1.9) + '</div>' +
    '<div style="min-width:0;flex:1">' +
    '<p class="mr-name">' + escapeHtml(p.name) + '</p>' +
    (p.prize ? '<p class="mr-prize">Marra sovrini: <b>' + escapeHtml(p.prize) + '</b></p>' : '') +
    '</div>' +
    '<span class="mr-count">' + done + '/' + total + '</span>' +
    '</div>' +
    '<div class="progress-track"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
    '<div class="mr-go">Marafonni ochish ' + icon("chevron-right", 15, 2.2) + '</div>' +
    '</button>';
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
  // Kartani bosish kitob oynasini ochadi — ota-onaga ham. Ilgari ota-onada
  // bu yo‘q edi va u «Kitob haqida», holat va Bolaxona tugmasi turgan
  // oynani umuman ocholmasdi. Ichidagi tugmalar (test tuzish, o‘chirish)
  // baribir ustun turadi: dispatcher eng ichkaridagi amalni oladi.
  return '<div class="card book-card" id="book-card-' + b.id + '" ' +
    'data-action="open-book" data-id="' + b.id + '">' +
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
  let html = await recShelfHtml(true);        // tavsiyalar yuqorida
  const reading = [];
  const done = [];
  const marathons = [];
  plans.forEach(function (p) {
    if (p.type === "marathon") marathons.push(p);
    p.books.forEach(function (b) { (b.completed ? done : reading).push(b); });
  });

  if (!reading.length && !done.length) {
    html += emptyState("book-open", "Hozircha kitob yo‘q",
      "Ota-onang tez orada senga kitob qo‘yadi.", {
        mascot: "boyogli-oylanish",
        steps: ["Kitob paydo bo‘lganda shu yerda ko‘rinadi",
                "O‘qigan sahifangni rasmga olib yuborasan",
                "Har sahifa uchun Bilig yig‘asan"]
      });
    document.getElementById("app-main").innerHTML = html;
    return;
  }

  if (reading.length) {
    html += '<p class="section-title">O‘qilayotgan kitoblar</p>';
    sortByLastRead(reading).forEach(function (b) { html += bookCardHtml(b, false); });
  }
  MarathonCache = marathons;
  if (marathons.length) {
    html += '<p class="section-title">Marafonlar</p>';
    marathons.forEach(function (p) { html += marathonCardHtml(p); });
  }
  html += doneShelfHtml(done);
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
  if (b.short_form) {
    // Qisqa asar: bola uni bir o‘tirishda o‘qiydi. Test o‘rniga AI ustoz
    // bitta savol beradi va bola ovozda javob qaytaradi (ega qarori).
    testsHtml = '<p class="section-sub" style="margin-top:18px">' +
      'Bu qisqa asar — test yo‘q. O‘qib bo‘lgach, AI ustozning savoliga ' +
      'ovozli javob berasan.</p>';
  } else if (b.has_test && b.test_final_only) {
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
    // Bosqich bolaning kelgan joyiga qarab ochiladi: 1-oraliq kitobning
    // uchdan biri, 2-oraliq uchdan ikkisi, yakuniy esa oxirigacha
    // o‘qilganda. Yopiq tugma «man etilgan» emas — pastda qancha bet
    // qolgani aytiladi, ya'ni bola nima qilishini biladi.
    // Uchta bosqich uchta kartochka bo‘lib turadi. Ega ikki narsani
    // so‘radi: ko‘rinish chiroyli bo‘lsin va QULF OCHILGANI ANIQ
    // ko‘rinsin. Shuning uchun ochiq bosqich ko‘k ramka, to‘q yozuv va
    // «Boshlash ›» chaqirig‘i bilan ajralib turadi; yopig‘i esa xira,
    // qulf belgisi bilan; bajarilgani yashil belgi bilan.
    const stages = b.stages || {};
    const stageBtn = function (stage, label) {
      const st = stages[stage] || { open: true, need_pages: 0 };
      if (b[stage + "_done"]) {
        return '<span class="test-tile is-done">' +
               '<span class="tt-ic">' + icon("check", 16, 2.6) + '</span>' +
               '<span class="tt-name">' + label + '</span>' +
               '<span class="tt-state">Bajarildi</span></span>';
      }
      if (!st.open) {
        return '<span class="test-tile is-locked">' +
               '<span class="tt-ic">' + icon("lock", 15, 2) + '</span>' +
               '<span class="tt-name">' + label + '</span>' +
               '<span class="tt-state">' +
               (st.need_pages ? "Yana " + st.need_pages + " bet" : "Yopiq") +
               '</span></span>';
      }
      return '<button class="test-tile is-open" data-action="open-test" data-id="' + bookId +
             '" data-stage="' + stage + '">' +
             '<span class="tt-ic">' + icon("arrow-right", 16, 2.4) + '</span>' +
             '<span class="tt-name">' + label + '</span>' +
             '<span class="tt-state">Boshlash</span>' +
             '</button>';
    };
    // Keyingi ochiladigan bosqich haqida bitta aniq jumla.
    let hint = "";
    const nextClosed = ["mid_test_1", "mid_test_2", "final_test"].filter(function (stage) {
      return !b[stage + "_done"] && stages[stage] && !stages[stage].open;
    })[0];
    if (nextClosed) {
      const nm = { mid_test_1: "1-oraliq", mid_test_2: "2-oraliq", final_test: "Yakuniy" }[nextClosed];
      hint = '<p class="section-sub" style="margin-top:8px">Yana ' +
             stages[nextClosed].need_pages + ' bet o‘qisang, ' + nm + ' test ochiladi.</p>';
    }
    testsHtml = '<p class="eyebrow" style="margin-top:18px">Bilim testlari</p><div class="test-row">' +
      stageBtn("mid_test_1", "1-oraliq") +
      stageBtn("mid_test_2", "2-oraliq") +
      stageBtn("final_test", "Yakuniy") +
      '</div>' + hint;
  } else {
    // Bolaga test qanday paydo bo‘lishini AYTMAYMIZ — aks holda u sahifa
    // rasmini test uchun yig‘adigan bo‘lib qoladi, o‘qish uchun emas.
    testsHtml = '<p class="section-sub" style="margin-top:18px">' +
      'Bu kitobda test yo‘q. O‘qishda davom et — kitob haqida ovozda ' +
      'gapirib bersang ham Bilig olasan.</p>';
  }
  // AI USTOZ SAVOLI — kitob boshida va oxirida bittadan. Bu erkin
  // xulosadan farq qiladi: savol aniq, javob baholanadi va ota-onaga
  // to‘liq hisobot boradi.
  const talk = b.talk || {};
  const talkNames = { start: "Kitob boshi", end: "Kitob yakuni" };
  const talkDescs = {
    start: "O‘qigan qisming haqida AI ustozning savoliga ovozda javob ber.",
    end: "Kitobni tugatding. AI ustozning yakuniy savoliga javob ber."
  };
  let talkCards = "";
  // Qisqa asarda «kitob boshi» savoli berilmaydi — bitta yakuniy savol.
  // Kitob haqida hech narsa bilmasak, savol bo‘sh chiqadi — bunday
  // savoldan ko‘ra yo‘qligi yaxshi (backend ham buni rad etadi).
  const talkStages = !b.talk_ready ? [] : (b.short_form ? ["end"] : ["start", "end"]);
  talkStages.forEach(function (st) {
    const t = talk[st];
    if (!t || t.done) return;
    if (t.open) {
      talkCards += choiceCard({
        // Suhbat pufakchasi — ilovada AI ustozning o‘z belgisi
        // (ota-onadagi «AI ustoz xulosasi» ham shu belgi bilan).
        // Ilgari savol belgisi turardi: ega uni «xunuk va yetarlicha
        // ma'no bermaydi» dedi (2026-08-31).
        ic: "message-circle", tone: "gold", action: "open-talk",
        data: { id: bookId, stage: st },
        title: talkNames[st], tag: "5 Bilig", desc: talkDescs[st]
      });
    }
  });
  let talkHtml = "";
  if (talkCards) {
    talkHtml = '<p class="eyebrow" style="margin-top:18px">AI ustoz savoli</p>' + talkCards;
  }

  // Ovozli xulosa har 15 betda bir marta ochiladi. Yopiq bo‘lsa —
  // «bo‘lmaydi» demaymiz, balki qancha o‘qish qolganini aytamiz.
  let voiceHtml;
  if (b.voice_open) {
    voiceHtml = choiceCard({
      ic: "mic", tone: "success", action: "open-voice", data: { id: bookId },
      title: b.has_voice ? "Yana bitta ovozli xulosa" : "Ovozli xulosa yuborish",
      desc: "Kitobni o‘z so‘zing bilan so‘zlab ber. Yaxshi so‘zlab bersang 3 Bilig."
    });
  } else {
    voiceHtml = '<div class="card" style="padding:14px 16px">' +
      '<p style="margin:0 0 4px;font-weight:700;color:var(--text)">Yana ' +
      b.voice_need_pages + ' bet o‘qishing kerak</p>' +
      '<p class="section-sub" style="margin:0">Ovozli xulosa har ' +
      b.voice_every_pages + ' betda bir marta ochiladi — o‘qigan sari yangisi ochiladi.</p>' +
      '</div>';
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
    voiceHtml +
    testsHtml +
    // AI ustoz savoli eng oxirida — ega qarori (2026-08-31).
    talkHtml
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

  // Kitob mazmuni o‘qish davomida o‘z-o‘zidan yig‘iladi. FAQAT ota-onaga
  // ko‘rsatiladi: bolaga tayyor mazmun berilsa, u kitobni o‘qimay qo‘yadi.
  const bb = b.book_base;
  let baseHtml = "";
  if (bb && bb.summary) {
    // Chipda faqat O‘Z-O‘ZIDAN tushunarli narsa turadi: yosh va mavzular.
    // Qiyinlik «o‘rta» deb yolg‘iz tursa hech nima anglatmaydi — u nomi
    // bilan, matn qatorida yoziladi.
    let chips = "";
    if (bb.age_band) chips += '<span class="chip">' + escapeHtml(bb.age_band) + ' yosh</span>';
    (bb.topics || []).slice(0, 6).forEach(function (t) {
      chips += '<span class="chip">' + escapeHtml(t) + '</span>';
    });

    const qator = [];
    if (bb.difficulty) qator.push('<b>Qiyinligi:</b> ' + escapeHtml(bb.difficulty));
    if (bb.mood) qator.push('<b>Kayfiyati:</b> ' + escapeHtml(bb.mood));

    baseHtml =
      '<p class="eyebrow" style="margin-top:18px">Kitob haqida</p>' +
      (chips ? '<div class="chip-row" style="margin-bottom:10px">' + chips + '</div>' : "") +
      '<div class="card" style="padding:14px 16px">' +
        '<p style="margin:0 0 10px">' + escapeHtml(bb.summary) + '</p>' +
        (bb.characters
          ? '<p class="section-sub" style="margin:0 0 6px"><b>Qahramonlar:</b> ' +
            escapeHtml(bb.characters) + '</p>' : "") +
        (bb.theme
          ? '<p class="section-sub" style="margin:0 0 6px"><b>G‘oyasi:</b> ' +
            escapeHtml(bb.theme) + '</p>' : "") +
        (bb.conclusion
          ? '<p class="section-sub" style="margin:0 0 6px"><b>Xulosasi:</b> ' +
            escapeHtml(bb.conclusion) + '</p>' : "") +
        (qator.length
          ? '<p class="section-sub" style="margin:0">' + qator.join(" · ") + '</p>' : "") +
      '</div>' +
      (bb.for_whom
        ? '<div class="card" style="padding:12px 14px;margin-top:8px">' +
            '<p class="section-sub" style="margin:0"><b>Kimga mos:</b> ' +
            escapeHtml(bb.for_whom) + '</p></div>'
        : "");
  }

  let testLines;
  if (!b.has_test) {
    testLines = statusRow("Bilim testi", false, "", "hali tuzilmagan") +
      '<p class="section-sub" style="margin:8px 0 0">Testni o‘zingiz ' +
      'tuzishingiz mumkin (pastdagi tugma), yoki farzandingiz sahifalarni ' +
      'rasmga olib borgani sari test o‘z-o‘zidan tuziladi.</p>';
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

    baseHtml +
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
    mascotToast("sherbola-galaba", "Parvozing " + res.streak + " kun!",
                "Bir kun ham qoldirmading. Zo‘rsan.");
  } else if (res.earned_bilig >= 5) {
    mascotToast("qorbars-tanga", "+" + res.earned_bilig + " Bilig!",
                "Xazinang o‘syapti — jami " + res.balance + " ta.");
  }
  showPageResultModal(res);
}
// Bet qo‘shilgandan keyingi tabrik oynasi. Ega eski ko‘rinishni («uchta
// bir xil quti») xunuk deb topdi. Endi bitta narsa bosh qahramon bo‘ladi:
// Bilig olingan bo‘lsa — Bilig, olinmagan bo‘lsa — yetib borilgan bet.
// Qolgani pastda, mayda va vazmin.
function showPageResultModal(res) {
  const gotBilig = res.earned_bilig > 0;
  const hero = gotBilig
    ? '<span class="wp-num">+' + res.earned_bilig + '</span>' +
      '<span class="wp-unit">Bilig</span>'
    : '<span class="wp-num">' + res.new_page + '</span>' +
      '<span class="wp-unit">bet</span>';
  const heroNote = gotBilig
    ? "Xazinangga qo‘shildi"
    : "Yo‘l davom etmoqda — har 5 betga 1 Bilig";

  openModal(gotBilig ? "Ajoyib natija" : "Yozib oldik",
    '<div class="win-panel">' +
    '<span class="win-glow"></span>' +
    '<div class="wp-hero">' + hero + '</div>' +
    '<p class="wp-note">' + heroNote + '</p>' +
    '<div class="wp-facts">' +
    '<div><b>' + res.new_page + '</b><span>Yetgan bet</span></div>' +
    '<div><b>' + res.streak + '</b><span>Parvoz kuni</span></div>' +
    '</div></div>' +
    (res.shield_used
      ? '<p class="wp-shield">' + icon("shield", 15, 2) +
        ' Qanot ishlatildi — parvozing uzilmadi.</p>'
      : "") +
    '<button class="btn btn-primary btn-block" data-action="close-modal">Davom etaman</button>'
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

// ==========================================================
// OVOZLI XULOSA
// ----------------------------------------------------------
// Yozib olingan ovoz SAQLANIB TURADI. Yuborish muvaffaqiyatsiz
// bo‘lsa, bola qaytadan gapirmaydi — o‘sha yozuvni bir bosishda
// qayta yuboradi. Yozuv faqat muvaffaqiyatli yuborilgandan keyin
// yoki bola «Qaytadan yozish» deganda o‘chadi.
// ==========================================================
// Hozirgi ovoz yozuvi nima uchun: bo‘sh bo‘lsa — erkin xulosa,
// "start"/"end" bo‘lsa — AI ustoz savoliga javob. Qayta yuborish
// tugmasi ham shu belgiga qarab to‘g‘ri manzilga yuboradi.
let TalkStage = null;

const VoiceDraft = {
  bookId: null,
  src: null,        // telefon yozgan asl fayl
  wav: null,        // AI uchun tayyorlangan nusxa (bir marta tayyorlanadi)
  seconds: 0,

  triedBoth: false,

  set: function (bookId, blob, seconds) {
    this.bookId = bookId; this.src = blob; this.wav = null;
    this.seconds = seconds || 0; this.triedBoth = false;
  },
  clear: function () {
    this.bookId = null; this.src = null; this.wav = null;
    this.seconds = 0; this.triedBoth = false;
  },
  has: function (bookId) { return this.src && this.bookId === bookId; },
  label: function () {
    if (!this.seconds) return "yozuv tayyor";
    const m = Math.floor(this.seconds / 60), sec = this.seconds % 60;
    return m ? (m + ":" + (sec < 10 ? "0" : "") + sec) : (sec + " soniya");
  }
};

function openVoiceModal(bookId, talkStage, question) {
  TalkStage = talkStage || null;
  const saved = VoiceDraft.has(bookId);
  openModal(TalkStage ? "AI ustoz savoli" : "Ovozli xulosa",
    (TalkStage
      ? '<div class="card" style="padding:14px 16px;margin-bottom:4px">' +
          '<p style="margin:0;font-weight:700;color:var(--text)">' + escapeHtml(question || "") + '</p>' +
        '</div>' +
        '<p class="section-sub">Shu savolga o‘z so‘zing bilan javob ber. Shoshilma — ' +
        'yarim daqiqadan ko‘proq gapirsang bo‘ladi.</p>'
      : '<p class="section-sub">Kitob haqida 1-2 daqiqa gapirib bering: nima haqida edi, sizga nima yoqdi?</p>') +
    '<div style="text-align:center;padding:16px 0">' +
    '<button id="rec-btn" class="icon-btn" style="width:76px;height:76px;border-radius:50%;background:var(--brand);color:#fff;margin:0 auto">' + icon("mic", 28, 1.7) + '</button>' +
    '<div id="rec-time" class="card-meta" style="margin-top:10px;color:var(--text-soft);font-size:15px">' +
      (saved ? "Yozuvingiz saqlanib turibdi (" + VoiceDraft.label() + ")" : "Yozishni boshlash uchun bosing") +
    '</div>' +
    '</div>' +
    '<div id="voice-actions"' + (saved ? "" : ' class="hidden"') + '>' +
    '<button class="btn btn-primary btn-block" id="voice-send-btn">Yuborish</button>' +
    '<button class="btn btn-outline btn-block" id="voice-retry-btn">Qaytadan yozish</button>' +
    '</div>' +
    '<input type="file" id="voice-file-input" accept="audio/*" class="hidden" />' +
    '<p class="section-sub" style="margin-top:10px">Mikrofon ishlamasa, <span style="text-decoration:underline;cursor:pointer" id="voice-upload-alt">audio fayl yuklang</span>.</p>'
  );

  const recBtn = document.getElementById("rec-btn");
  const timeEl = document.getElementById("rec-time");
  const actions = document.getElementById("voice-actions");

  recBtn.onclick = async function () {
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = []; recordSeconds = 0;
        // Past oqim tezligi — nutq uchun yetarli, fayl esa bir necha barobar
        // yengil bo‘ladi (sekin internetda shu hal qiluvchi).
        try {
          mediaRecorder = new MediaRecorder(stream, { audioBitsPerSecond: 32000 });
        } catch (e) {
          mediaRecorder = new MediaRecorder(stream);
        }
        mediaRecorder.ondataavailable = function (e) { audioChunks.push(e.data); };
        mediaRecorder.onstop = function () {
          const type = (mediaRecorder && mediaRecorder.mimeType) || "audio/webm";
          VoiceDraft.set(bookId, new Blob(audioChunks, { type: type }), recordSeconds);
          stream.getTracks().forEach(function (t) { t.stop(); });
          actions.classList.remove("hidden");
          timeEl.textContent = "Yozib olindi (" + VoiceDraft.label() + ") — endi yuboring";
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
    VoiceDraft.clear();
    actions.classList.add("hidden");
    timeEl.textContent = "Yozishni boshlash uchun bosing";
  };
  document.getElementById("voice-upload-alt").onclick = function () { document.getElementById("voice-file-input").click(); };
  document.getElementById("voice-file-input").onchange = function (e) {
    if (e.target.files.length) {
      VoiceDraft.set(bookId, e.target.files[0], 0);
      actions.classList.remove("hidden");
      timeEl.textContent = "Fayl tanlandi";
    }
  };

  // Server oxirgi marta qaysi format ishlaganini eslab qoladi — shundan
  // boshlaymiz. Odatda bu asl (yengil) fayl bo‘ladi.
  document.getElementById("voice-send-btn").onclick = function () {
    sendVoice(bookId, State.me && State.me.voice_prefer === "asl");
  };
}

async function openTalkModal(bookId, stage) {
  const q = asChildQuery();
  const data = await api("/api/child/book/" + bookId + "/talk" + q +
                         (q ? "&" : "?") + "stage=" + stage);
  if (!data.open) {
    toast("Bu savolga hali erta — yana " + data.need_pages + " bet o‘qi");
    return;
  }
  if (data.done) { toast("Bu savolga allaqachon javob bergansan"); return; }
  openVoiceModal(bookId, stage, data.question);
}

function voiceWait(title, sub) {
  openModal("AI Ustoz tinglamoqda",
    '<div class="empty-state" style="padding:26px 0"><div class="spinner"></div>' +
    '<p style="font-weight:700;color:var(--text);margin:12px 0 4px">' + title + '</p>' +
    (sub ? '<p style="margin:0">' + sub + '</p>' : "") + '</div>');
}

// Yuborish. Ovoz saqlanib turadi — xato bo‘lsa qaytadan gapirish shart emas.
//
// asl=true bo‘lsa, telefon yozgan ASL fayl yuboriladi (WAV ga o‘girilmaydi).
// Nega kerak: bot Telegram bergan OGG bilan muammosiz ishlaydi, ilovada esa
// WAV yuboriladi. Qaysi biri to‘g‘ri kelishini taxmin qilib o‘tirmaymiz —
// birinchisi bo‘lmasa, ikkinchisi avtomatik sinaladi. Qaysi biri ishlagani
// serverning jurnaliga yozilib qoladi.
async function sendVoice(bookId, asl) {
  if (!VoiceDraft.has(bookId)) { toast("Avval ovoz yozing yoki fayl tanlang"); return; }

  let sendBlob;
  if (asl) {
    sendBlob = VoiceDraft.src;
  } else {
    // AI uchun tayyorlangan nusxa bir marta yasaladi va saqlanadi — qayta
    // yuborishda telefon uni boshqatdan o‘girib o‘tirmaydi.
    if (!VoiceDraft.wav) {
      voiceWait("Ovoz tayyorlanmoqda…");
      let out = VoiceDraft.src;
      try { out = await audioToWav(VoiceDraft.src); } catch (e) { out = VoiceDraft.src; }
      if (!out || !out.size) { toast("Ovoz yozilmadi. Qaytadan urinib ko‘ring."); closeModal(); return; }
      VoiceDraft.wav = out;
    }
    sendBlob = VoiceDraft.wav;
  }

  voiceWait("Ovoz yuborilmoqda…", "Internet sekin bo‘lsa biroz kutishga to‘g‘ri keladi.");
  const fd = new FormData();
  const ext = (sendBlob.type || "").indexOf("wav") >= 0 ? "wav" : "webm";
  fd.append("audio", sendBlob, "summary." + ext);
  fd.append("meta", JSON.stringify({
    asl: VoiceDraft.src.type || "?",
    yuborilgan: sendBlob.type || "?",
    ogirilmagan: !!asl,
    soniya: VoiceDraft.seconds,
    kb: Math.round(sendBlob.size / 1024)
  }));

  try {
    const q = asChildQuery();
    const path = TalkStage
      ? "/api/child/book/" + bookId + "/talk" + q + (q ? "&" : "?") + "stage=" + TalkStage
      : "/api/child/book/" + bookId + "/voice" + q;
    const started = await api(path, { method: "POST", body: fd });
    voiceWait("AI Ustoz tinglayapti…", "Ovoz uzun bo‘lsa biroz ko‘proq kutadi.");
    let res = null;
    const until = Date.now() + 4 * 60 * 1000;
    while (Date.now() < until) {
      await new Promise(function (r) { setTimeout(r, 2500); });
      let st;
      try { st = await api("/api/child/voice_job/" + started.job_id + asChildQuery()); }
      catch (err) { continue; }              // aloqa uzildi — keyingi urinishda so‘raymiz
      if (st.status === "tayyor") { res = st.result; break; }
      if (st.status === "xato") throw { error: st.error };
    }
    if (!res) throw { error: "Kutish vaqti tugadi. Ovozingiz saqlanib qoldi — qayta yuborib ko‘ring." };

    VoiceDraft.clear();                      // muvaffaqiyat — yozuv endi kerak emas
    if (res.bonus_bilig > 0) {
      mascotToast("olmaxon-2", "AI ustoz seni tingladi",
                  "+" + res.bonus_bilig + " bonus Bilig — nutqing ravon edi.");
    }
    // Bilig chiqmadi, lekin urinish huquqi qoldi: AI ustoz maslahat berdi,
    // bola shu maslahat bilan qaytadan gapiradi. Bet «yonib ketmaydi».
    const canRetry = res.bonus_bilig === 0 && res.retry_left > 0;
    const stageNow = TalkStage;
    const showVoice = function () { openModal("AI Ustoz fikri",
      // Tanga chiqmagan bo‘lsa «+0» ko‘rsatmaymiz — bola uchun bu baho
      // emas, maslahat. AI ustozning so‘zi o‘zi yetarli.
      (res.bonus_bilig > 0
        ? '<div class="stat-grid" style="grid-template-columns:1fr">' +
          '<div class="stat-box"><div class="num">+' + res.bonus_bilig + '</div><div class="lbl">bonus Bilig</div></div>' +
          '</div>'
        : "") +
      '<div class="card">' + escapeHtml(res.feedback) + '</div>' +
      (canRetry
        ? '<p class="section-sub" style="color:var(--success-deep);font-weight:600">' +
            'Shoshilma — yana ' + res.retry_left + ' marta gapirib ko‘rsang bo‘ladi. ' +
            'Kitobni bir eslab, voqealarni o‘z so‘zing bilan boshidan aytib ber.</p>' +
          (stageNow
            ? '<button class="btn btn-primary btn-block" data-action="open-talk" data-id="' + bookId +
              '" data-stage="' + stageNow + '">Yana bir bor javob beraman</button>'
            : '<button class="btn btn-primary btn-block" data-action="open-voice" data-id="' + bookId +
              '">Yana bir bor gapiraman</button>') +
          '<button class="btn btn-outline btn-block" data-action="close-modal">Keyinroq</button>'
        : '<button class="btn btn-primary btn-block" data-action="close-modal">Ajoyib</button>')
    ); };
    if (res.new_badges && res.new_badges.length) celebrate(res.new_badges, showVoice);
    else showVoice();
    refreshHeader();
  } catch (e) {
    // Birinchi urinish WAV bilan edi va bo‘lmadi — endi telefon yozgan
    // ASL faylni sinab ko‘ramiz. Bu odatda ancha kichik bo‘ladi va
    // botdagi formatga yaqin. Foydalanuvchi hech narsa qilmaydi.
    if (!VoiceDraft.triedBoth) {
      VoiceDraft.triedBoth = true;
      voiceWait("Boshqa usulda urinib ko‘ryapmiz…", "Bir zum kuting.");
      return sendVoice(bookId, !asl);
    }
    // Texnik tafsilotlar serverning jurnaliga yoziladi. Bu yerda faqat
    // sodda gap va eng muhimi — ovoz saqlanib qolgani.
    const reason = e.error || "Hozir bo‘lmadi. Internet aloqasini tekshirib, qaytadan urining.";
    openModal("Ovozli xulosa yuborilmadi",
      '<p class="section-sub" style="margin-top:-4px">' + escapeHtml(reason) + '</p>' +
      '<p class="section-sub" style="color:var(--success-deep);font-weight:600">' +
        'Ovozingiz saqlanib qoldi — qaytadan gapirish shart emas.</p>' +
      '<button class="btn btn-primary btn-block" data-action="voice-resend" data-id="' + bookId + '">Shu ovozni qayta yuborish</button>' +
      '<button class="btn btn-outline btn-block" data-action="open-voice" data-id="' + bookId + '">Qaytadan yozish</button>');
  }
}

// Natijadan keyin xato javoblarni ko‘rsatish. Bola qayerda adashganini
// bilmasa, test unga hech narsa o‘rgatmaydi — faqat baho qo‘yadi.
function testReview(review) {
  if (!review || !review.length) return "";
  const wrong = review.filter(function (r) { return !r.ok; });
  if (!wrong.length) {
    return '<p class="review-all-ok">Barcha javoblar to‘g‘ri. Kitobni chindan tushunibsan.</p>';
  }
  let html = '<p class="review-head">Xato javoblar — ' + wrong.length + ' ta</p>';
  wrong.forEach(function (r) {
    html += '<div class="review-item">' +
      '<p class="review-q">' + escapeHtml(r.question) + '</p>' +
      (r.your
        ? '<p class="review-line bad"><span>Sening javobing</span>' + escapeHtml(r.your) + '</p>'
        : '<p class="review-line bad"><span>Sening javobing</span>javob bermading</p>') +
      '<p class="review-line good"><span>To‘g‘ri javob</span>' + escapeHtml(r.correct) + '</p>' +
      '</div>';
  });
  return html;
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
                res.earned_bilig ? "Kitobni chindan tushunibsan." : "Yaxshi urinish — davom et.");
    const showRes = function () { openModal("Natija",
      // Bolaga FOIZ ko‘rsatilmaydi (ega qarori): foiz baho bo‘lib
      // tuyuladi va ruhini tushiradi. Unga aniq son va rag‘bat kerak.
      '<div class="stat-grid">' +
      '<div class="stat-box"><div class="num">' + res.correct + '/' + res.total + '</div><div class="lbl">To‘g‘ri javob</div></div>' +
      '<div class="stat-box"><div class="num">+' + res.earned_bilig + '</div><div class="lbl">Bilig</div></div>' +
      '</div>' +
      (res.earned_bilig ? "" :
        '<p class="section-sub">Bu safar Bilig chiqmadi — savollarning ko‘pini ' +
        'to‘g‘ri yechish kerak edi. Keyingi bosqichda albatta chiqadi, ' +
        'kitobni sinchiklab o‘qib bor.</p>') +
      testReview(res.review) +
      '<button class="btn btn-primary btn-block" data-action="close-modal">Yopish</button>'
    ); };
    if (res.new_badges && res.new_badges.length) celebrate(res.new_badges, showRes);
    else showRes();
    refreshHeader();
  }
};

async function openTestModal(bookId, stage) {
  const q = asChildQuery();
  const questions = await api("/api/child/book/" + bookId + "/test" + q +
                              (q ? "&" : "?") + "stage=" + stage);
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
// TAB 3: DO‘KON VA HAMYON (ota-ona ham, bola ham shu yerda)
// ==========================================================
// Do‘kon ikki ko‘rinishga ega: sovg‘alar javoni (`shop`) va hamyon
// (`wallet`). Ikkinchisi alohida tab emas — pastdagi to‘rtta tab
// tartibi buzilmasin uchun do‘kon ichida ochiladi.

// Ota-ona sovg‘aga tanlaydigan belgilar. Klaviaturadan istalgan belgi
// qidirilmasin — kompyuterda bu noqulay va mos kelmaydigan belgi
// tushib qolishi mumkin edi.
const GIFT_EMOJI = [
  "🚲", "🛴", "⚽", "🏀", "🏐", "🎾", "🏸", "🛼",
  "🎁", "🧸", "🪀", "🧩", "🎨", "🖍️", "🪁", "🎯",
  "📚", "📗", "✏️", "🎒", "🔭", "🔬", "🧪", "🧲",
  "🍦", "🍫", "🍩", "🍕", "🍔", "🍓", "🥤", "🍿",
  "🎬", "🎡", "🏞️", "🏊", "🚗", "⌚", "🎧", "📱"
];

// Hamyon logosi — chiziqli ikona emas, o‘z rangi bilan chizilgan belgi.
// Bolalar uchun eng sevimli bo‘lim bo‘lgani uchun u yorqin va «tirik»
// ko‘rinishi kerak: ko‘k hamyon va uning ustidan tushayotgan oltin Bilig.
function walletLogo(size) {
  size = size || 40;
  return '<svg class="wallet-logo" width="' + size + '" height="' + size + '" viewBox="0 0 64 64" fill="none">' +
    // Bilig tangasi
    '<circle cx="41" cy="15" r="11" fill="#F59E0B"/>' +
    '<circle cx="41" cy="15" r="7.6" fill="#FBBF24"/>' +
    '<path d="M41 9.6l1.6 3.3 3.6.5-2.6 2.5.6 3.6-3.2-1.7-3.2 1.7.6-3.6-2.6-2.5 3.6-.5z" fill="#FEF3C7"/>' +
    // Hamyon tanasi
    '<rect x="6" y="25" width="48" height="31" rx="9" fill="#4E8EF7"/>' +
    // Qopqoq
    '<path d="M6 34v-1a9 9 0 0 1 9-9h30a9 9 0 0 1 9 9v1z" fill="#7EAFFA"/>' +
    // Karta uyasi
    '<rect x="34" y="34" width="26" height="13" rx="6.5" fill="#EAF2FF"/>' +
    '<circle cx="43" cy="40.5" r="3.1" fill="#F59E0B"/>' +
    '</svg>';
}

// Sovg‘a tasviri: ota-ona yuklagan rasm → belgi → bezak ikonasi.
function giftMedia(item, idx, inner) {
  const cls = "store-media tint-" + (idx % 4);
  if (item.photo && item.photo.indexOf("up:") === 0) {
    return '<div class="' + cls + ' has-photo"><img src="/uploads/gf/' +
      escapeHtml(item.photo.slice(3)) + '" alt="" loading="lazy">' + (inner || "") + '</div>';
  }
  if (item.emoji) {
    return '<div class="' + cls + '"><span class="store-emoji">' +
      escapeHtml(item.emoji) + '</span>' + (inner || "") + '</div>';
  }
  return '<div class="' + cls + '"><div class="store-icon-lg">' + icon("gift", 22, 1.6) +
    '</div>' + (inner || "") + '</div>';
}

// Kichik tasvir — hamyondagi ro‘yxatlar uchun
function giftThumb(item) {
  if (item.photo && item.photo.indexOf("up:") === 0) {
    return '<div class="gift-thumb has-photo"><img src="/uploads/gf/' +
      escapeHtml(item.photo.slice(3)) + '" alt="" loading="lazy"></div>';
  }
  if (item.emoji) return '<div class="gift-thumb"><span>' + escapeHtml(item.emoji) + '</span></div>';
  return '<div class="gift-thumb">' + icon("gift", 18, 1.8) + '</div>';
}

// 60000 → «60 000». Uzun raqam bo‘linmasa o‘qish qiyin.
function somFmt(n) {
  return String(Math.round(n || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " so‘m";
}

const MONTHS_SHORT = ["yan", "fev", "mar", "apr", "may", "iyn",
                      "iyl", "avg", "sen", "okt", "noy", "dek"];

function dayLabel(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const that = new Date(d); that.setHours(0, 0, 0, 0);
  const diff = Math.round((today - that) / 86400000);
  if (diff === 0) return "bugun";
  if (diff === 1) return "kecha";
  return d.getDate() + "-" + MONTHS_SHORT[d.getMonth()];
}

async function renderStoreTab() {
  if (State.storeView === "wallet") return renderWalletView();
  const main = document.getElementById("app-main");
  if (isChildView()) {
    const data = await api("/api/child/store" + asChildQuery());
    State.storeBalance = data.balance;
    let html = walletBarHtml('<b>' + data.balance + '</b> Bilig', "Hamyonim");
    html += await freezeCardHtml();
    if (!data.items.length) {
      html += emptyState("gift", "Do‘kon hozircha bo‘sh",
        "Ota-onang tez orada sovg‘alarni qo‘yadi — sen esa Bilig yig‘ib turaver.", {
          mascot: "quyoncha-sovga",
          steps: ["Kitob o‘qib, test va ovozli xulosa uchun Bilig yig‘asan",
                  "Sovg‘alar shu yerda paydo bo‘ladi",
                  "Yiqqan Biliging yetsa, sovg‘ani tanlaysan"]
        });
    } else {
      html += '<div class="store-grid">' + data.items.map(function (i, idx) {
        const isGoal = data.goal_item_id === i.id;
        const goalFab = '<button class="store-goal-fab' + (isGoal ? " on" : "") +
          '" data-action="toggle-goal" data-id="' + i.id + '" data-on="' + (isGoal ? "1" : "") +
          '" aria-label="Orzu qilib belgilash">' + icon("star", 13, 2) + '</button>';
        return '<div class="store-item' + (isGoal ? " is-goal" : "") + '">' +
          giftMedia(i, idx, goalFab) +
          '<div class="store-body">' +
          '<p class="store-name">' + escapeHtml(i.name) + '</p>' +
          '<div class="store-footer" style="margin-bottom:10px">' +
          '<span class="store-price-chip">' + icon("coin", 12, 2.2) + ' ' + i.price + '</span>' +
          (isGoal ? '<span class="goal-tag">' + icon("star", 11, 2.2) + ' Orzuim</span>' : "") +
          '</div>' +
          (i.affordable
            ? '<button class="btn btn-primary btn-block" style="padding:8px;font-size:14.5px" ' +
              'data-action="buy-item" data-id="' + i.id + '" data-name="' + escapeHtml(i.name) +
              '" data-price="' + i.price + '">Xarid qilish</button>'
            : '<div class="goal-bar"><i style="width:' + i.percent + '%"></i></div>' +
              '<p class="goal-left">Yana <b>' + i.left + '</b> Bilig kerak</p>') +
          '</div></div>';
      }).join("") + '</div>';
    }
    main.innerHTML = html;
  } else {
    const data = await api("/api/parent/store");
    State.storeChildren = data.children || [];
    State.storeItems = data.items || [];
    State.walletRate = data.rate || 0;
    State.walletShowSom = !!data.show_som;
    const items = data.items || [];

    let html = walletBarHtml(
      data.rate ? ('1 Bilig = <b>' + somFmt(data.rate) + '</b>') : 'Bilig kursi belgilanmagan',
      "Hamyon");
    html += items.length
      ? '<div class="grid-2" style="margin-bottom:16px">' +
        '<button class="btn btn-primary" data-action="open-store-add" style="display:flex;align-items:center;justify-content:center;gap:6px">' + icon("plus", 16, 2) + ' Sovg‘a</button>' +
        '<button class="btn btn-outline" data-action="open-rate">Bilig kursi</button></div>'
      : "";
    if (!items.length) {
      html += emptyState("gift", "Birinchi sovg‘ani qo‘yamiz",
        "Sovg‘a qimmat bo‘lishi shart emas — «1 soat multfilm» ham ajoyib rag‘bat.", {
          mascot: "quyoncha-sovga",
          steps: ["Sovg‘a nomini, belgisini va necha Bilig turishini yozasiz",
                  "Farzandingiz kitob o‘qib Bilig yig‘adi",
                  "U sovg‘ani tanlaganda sizga xabar keladi"],
          action: "open-store-add", label: "Sovg‘a qo‘shish", btnIcon: "plus"
        });
      html += '<p class="sec-label">Tayyor takliflar</p>' +
        '<p class="section-sub">Bosilsa — darrov do‘konga qo‘shiladi.</p>' +
        '<div class="quick-gifts">' + QUICK_GIFTS.map(function (q) {
          return '<button class="quick-gift" data-action="quick-gift" data-name="' + escapeHtml(q[0]) +
            '" data-price="' + q[1] + '" data-emoji="' + q[2] + '">' +
            '<span class="qg-emoji">' + q[2] + '</span>' +
            '<span class="qg-name">' + escapeHtml(q[0]) + '</span>' +
            '<span class="qg-price">' + icon("coin", 11, 2.2) + ' ' + q[1] + '</span></button>';
        }).join("") + '</div>';
    } else {
      html += '<div class="store-grid">' + items.map(function (i, idx) {
        const editFab = '<button class="store-edit-fab" data-action="open-store-edit" data-id="' + i.id +
          '" aria-label="Tahrirlash">' + icon("edit", 13, 2) + '</button>';
        // Butun kartochka bosilsa tahrir oynasi ochiladi — qalam belgisi
        // kichkina, ota-ona uni sezmasligi mumkin.
        return '<div class="store-item is-tappable" data-action="open-store-edit" data-id="' + i.id + '">' +
          giftMedia(i, idx, editFab) +
          '<div class="store-body">' +
          '<p class="store-name">' + escapeHtml(i.name) + '</p>' +
          '<div class="store-footer"><span class="store-price-chip">' + icon("coin", 12, 2.2) + ' ' + i.price + '</span>' +
          (data.rate ? '<span class="store-som">≈ ' + somFmt(i.price * data.rate) + '</span>' : "") +
          '</div>' +
          '</div></div>';
      }).join("") + '</div>';
    }
    main.innerHTML = html;
  }
}

// Qanot — o‘qilmagan kunda parvozni saqlab qoladi. Sovg‘a emas,
// shuning uchun do‘kon javonida emas, uning tepasida alohida turadi.
async function freezeCardHtml() {
  let f;
  try { f = await api("/api/child/freeze" + asChildQuery()); } catch (e) { return ""; }
  const full = f.have >= f.max;
  return '<div class="freeze-card">' +
    '<span class="fz-ic">' + icon("shield", 20, 1.9) + '</span>' +
    '<div class="fz-mid">' +
    '<p class="fz-title">Qanot</p>' +
    '<p class="fz-sub">Bir kun o‘qiy olmasang, parvozing uzilmaydi. ' +
    'Hozir sende <b>' + f.have + '</b> ta (eng ko‘pi ' + f.max + ' ta).</p>' +
    '</div>' +
    (full
      ? '<span class="fz-full">To‘la</span>'
      : '<button class="btn ' + (f.can_buy ? "btn-primary" : "btn-secondary") +
        ' fz-btn" data-action="buy-freeze"' + (f.can_buy ? "" : " disabled") + '>' +
        icon("coin", 13, 2.2) + ' ' + f.price + '</button>') +
    '</div>';
}

// Tayyor sovg‘a takliflari — do‘kon bo‘sh turmasin. Narxlar taxminiy:
// bola haftasiga o‘rtacha 20-30 Bilig yig‘adi.
const QUICK_GIFTS = [
  ["1 soat multfilm", 15, "🎬"],
  ["Muzqaymoq", 10, "🍦"],
  ["Do‘st bilan sayrga", 40, "🏞️"],
  ["Yangi kitob", 60, "📚"],
  ["Attraksionlar", 80, "🎡"],
  ["Konstruktor", 150, "🧩"]
];

function walletBarHtml(left, label) {
  return '<button class="wallet-bar" data-action="open-wallet">' +
    '<span class="wb-ic">' + walletLogo(30) + '</span>' +
    '<span class="wb-left">' + left + '</span>' +
    '<span class="wb-go">' + label + ' ' + icon("chevron-right", 15, 2.2) + '</span>' +
    '</button>';
}

// ---------------- HAMYON ----------------

async function renderWalletView() {
  const main = document.getElementById("app-main");
  return isChildView() ? renderChildWallet(main) : renderParentWallet(main);
}

async function renderChildWallet(main) {
  const d = await api("/api/child/wallet" + asChildQuery());
  let html = '<button class="back-link" data-action="close-wallet">' +
    icon("arrow-left", 16, 2) + ' Do‘kon</button>';

  html += '<div class="wallet-hero">' +
    '<div class="wh-glow"></div>' +
    '<div class="wh-logo">' + walletLogo(74) + '</div>' +
    '<p class="wh-lbl">Hamyoningda</p>' +
    '<div class="wh-coin"><b>' + d.balance + '</b><span>Bilig</span></div>' +
    (d.show_som && d.rate ? '<p class="wh-som">≈ ' + somFmt(d.balance * d.rate) + '</p>' : "") +
    '<div class="wh-split">' +
    '<div><b>' + d.earned + '</b><span>Jami yig‘gan</span></div>' +
    '<div><b>' + d.spent + '</b><span>Sarflagan</span></div>' +
    '</div></div>';

  html += '<p class="sec-label">Sovg‘alarim</p>';
  if (!d.purchases.length) {
    html += '<div class="card empty-soft">' + icon("gift", 20, 1.8) +
      '<p>Hali sovg‘a olmagansan. Bilig yig‘ib, do‘kondan tanlaysan.</p></div>';
  } else {
    html += '<div class="card wallet-list">' + d.purchases.map(function (p) {
      const given = p.status === "given";
      return '<div class="wl-row">' + giftThumb(p) +
        '<div class="wl-mid"><p class="wl-name">' + escapeHtml(p.name) + '</p>' +
        '<p class="wl-sub">' + dayLabel(p.created_at) + '</p></div>' +
        '<div class="wl-right">' +
        '<span class="store-price-chip">' + icon("coin", 11, 2.2) + ' ' + p.price + '</span>' +
        '<span class="pill ' + (given ? "pill-leaf" : "pill-gold") + '">' +
        (given ? "Qo‘lingda" : "Kutilmoqda") + '</span>' +
        '</div></div>';
    }).join("") + '</div>';
  }

  html += '<p class="sec-label">Harakatlar tarixi</p>';
  if (!d.history.length) {
    html += '<div class="card empty-soft">' + icon("clock", 20, 1.8) +
      '<p>Bilig harakatlari shu yerda ko‘rinadi.</p></div>';
  } else {
    html += '<div class="card wallet-list">' + d.history.map(function (h) {
      const plus = h.amount > 0;
      return '<div class="wl-row"><div class="wl-amt ' + (plus ? "up" : "down") + '">' +
        (plus ? "+" : "−") + Math.abs(h.amount) + '</div>' +
        '<div class="wl-mid"><p class="wl-name">' + escapeHtml(h.note || "Bilig") + '</p>' +
        '<p class="wl-sub">' + dayLabel(h.created_at) + '</p></div></div>';
    }).join("") + '</div>';
  }
  main.innerHTML = html;
}

async function renderParentWallet(main) {
  const d = await api("/api/parent/wallet");
  let html = '<button class="back-link" data-action="close-wallet">' +
    icon("arrow-left", 16, 2) + ' Do‘kon</button>' +
    '<div class="wallet-head">' + walletLogo(42) +
    '<div><p class="wh-head-title">Hamyon</p>' +
    '<p class="wh-head-sub">Bilig qayerdan kelib, qayerga ketmoqda</p></div></div>';

  html += '<div class="card rate-card" data-action="open-rate">' +
    '<div class="rate-left"><p class="rate-lbl">Bilig kursi</p>' +
    '<p class="rate-val">' + (d.rate ? '1 Bilig = ' + somFmt(d.rate) : 'Belgilanmagan') + '</p>' +
    '<p class="rate-note">' + (d.show_som
      ? 'Farzandingiz so‘mdagi qiymatni ko‘radi.'
      : 'Farzandingizga so‘m ko‘rsatilmaydi.') + '</p></div>' +
    '<span class="edit-link">O‘zgartirish</span></div>';

  if (!d.children.length) {
    html += emptyState("users", "Farzand qo‘shilmagan",
      "Hamyon farzandingiz Bilig yig‘a boshlagach to‘ladi.", { mascot: "boyogli-oqish" });
    main.innerHTML = html;
    return;
  }

  d.children.forEach(function (c) {
    // Ega eski ko‘rinishni xunuk deb topdi: ism kartochkadan tashqarida,
    // havoda osilib turardi. Endi har farzand BITTA yaxlit kartochka —
    // tepasida ismi va qo‘lidagi Biligi, pastida qayerdan kelib qayerga
    // ketgani.
    const head = '<div class="kw-head">' +
      '<span class="kw-av">' + avatarMarkup(c.avatar_id || "fox", 40) + '</span>' +
      '<span class="kw-id"><b>' + escapeHtml(c.name) + '</b><span>hamyoni</span></span>' +
      '<span class="kw-bal">' + icon("coin", 15, 2.2) + ' ' + c.balance + '</span>' +
      '</div>';
    if (!c.earned && !c.spent) {
      html += '<div class="kid-wallet">' + head +
        '<p class="kw-empty">Hali Bilig yig‘magan. Kitob o‘qiy boshlagach ' +
        'shu yerda ko‘rinadi.</p></div>';
      return;
    }
    html += '<div class="kid-wallet">' + head +
      '<div class="kw-split">' +
      '<div><b>' + c.earned + '</b><span>Yig‘gan</span></div>' +
      '<div><b>' + c.spent + '</b><span>Sarflagan</span></div>' +
      '<div><b>' + c.balance + '</b><span>Qolgan</span></div>' +
      '</div>' +
      (d.rate ? '<p class="kw-som">Qo‘lidagi Bilig ≈ ' + somFmt(c.balance * d.rate) + '</p>' : "") +
      '</div>';

    if (c.pending.length) {
      const owed = c.pending.reduce(function (a, p) { return a + p.price; }, 0);
      html += '<div class="promise-card">' +
        '<p class="pc-title">' + icon("gift", 16, 2) + ' Va\'da qilingan sovg‘a: ' +
        c.pending.length + ' ta</p>' +
        c.pending.map(function (p) {
          return '<div class="pc-row">' + giftThumb(p) +
            '<div class="wl-mid"><p class="wl-name">' + escapeHtml(p.name) + '</p>' +
            '<p class="wl-sub">' + p.price + ' Bilig' +
            (d.rate ? ' · ≈ ' + somFmt(p.price * d.rate) : "") +
            (p.days >= 1 ? ' · ' + p.days + ' kundan beri kutmoqda' : '') + '</p></div>' +
            '<button class="btn btn-primary pc-btn" data-action="gift-given" data-id="' + p.purchase_id +
            '">Berdim</button></div>';
        }).join("") +
        '<p class="pc-note">' + escapeHtml(promiseNote(c.name, owed, d.rate)) + '</p>' +
        '</div>';
    }
    if (c.given_count) {
      html += '<div class="card given-row">' + icon("check-circle", 17, 2) +
        '<span>Berilgan sovg‘alar: <b>' + c.given_count + ' ta</b>' +
        (d.rate ? ' · ' + somFmt(c.given_price * d.rate) : '') + '</span></div>';
    }
  });
  main.innerHTML = html;
}

// Ota-onaga samimiy, dashnom bermaydigan eslatma.
function promiseNote(childName, owed, rate) {
  const money = rate ? " (taxminan " + somFmt(owed * rate) + ")" : "";
  return childName + " bu sovg‘ani o‘z mehnati bilan — " + owed + " Bilig yig‘ib qo‘lga kiritdi" +
    money + ". Va'daga vafo qilish farzandga kitobdan ham ko‘proq saboq beradi.";
}

// ---------------- SOVG‘A QO‘SHISH VA TAHRIRLASH ----------------

// Tahrir oynasi to‘ldirilayotgan sovg‘a. Rasm tanlash oynasi shu oynaning
// O‘RNIGA ochiladi, shuning uchun yozilganlar shu yerda saqlab turiladi —
// aks holda rasm qo‘ygan ota-ona nom va narxni qaytadan yozardi.
const GiftDraft = { id: "", name: "", price: "", emoji: "", photo: "" };

function readGiftForm() {
  const n = document.getElementById("store-name");
  const pr = document.getElementById("store-price");
  if (n) GiftDraft.name = n.value;
  if (pr) GiftDraft.price = pr.value;
}

function openStoreEditModal(id, keep) {
  if (!keep) {
    const item = id ? (State.storeItems || []).find(function (x) { return String(x.id) === String(id); }) : null;
    GiftDraft.id = id || "";
    GiftDraft.name = item ? item.name : "";
    GiftDraft.price = item ? item.price : "";
    GiftDraft.emoji = item ? (item.emoji || "") : "";
    GiftDraft.photo = item ? (item.photo || "") : "";
  }
  const item = { name: GiftDraft.name, price: GiftDraft.price };

  openModal(id ? "Sovg‘ani tahrirlash" : "Yangi sovg‘a",
    '<div id="gift-preview">' + giftPreviewHtml() + '</div>' +
    '<div class="grid-2" style="margin-bottom:12px">' +
    '<button class="btn btn-outline" data-action="gift-photo" style="display:flex;align-items:center;justify-content:center;gap:6px">' +
    icon("image", 15, 2) + ' Rasm</button>' +
    '<button class="btn btn-outline" data-action="gift-emoji-toggle" style="display:flex;align-items:center;justify-content:center;gap:6px">' +
    icon("star", 15, 2) + ' Belgi</button></div>' +
    // Ega so‘radi: «Hamma telefonlarning o‘z emojilarini ulasakchi?»
    // Veb ilovada emoji klaviaturasini majburan ochib bo‘lmaydi, lekin
    // oddiy yozuv maydoni buni hal qiladi: ota-ona klaviaturasidagi
    // kulgich tugmasini bosib, xohlagan belgisini qo‘yadi. Pastdagi
    // tayyor ro‘yxat esa tez tanlash uchun qoladi.
    '<div id="gift-emoji-grid" class="emoji-box" hidden>' +
    '<label class="field-label" style="margin-top:0">O‘z belgingiz</label>' +
    '<input id="gift-emoji-input" class="text-input emoji-input" ' +
    'placeholder="Belgi qo‘ying" value="' + escapeHtml(GiftDraft.emoji || "") + '" ' +
    'oninput="setGiftEmojiFromInput(this.value)" />' +
    '<p class="emoji-hint">Klaviaturangizdagi kulgich tugmasini bosing — ' +
    'telefoningizdagi istalgan belgini qo‘ya olasiz.</p>' +
    '<p class="emoji-or">yoki tez tanlang</p>' +
    '<div class="emoji-grid">' + GIFT_EMOJI.map(function (e) {
      return '<button class="emoji-btn" data-action="gift-emoji" data-e="' + e + '">' + e + '</button>';
    }).join("") + '</div></div>' +
    '<label class="field-label">Sovg‘a nomi</label>' +
    '<input id="store-name" class="text-input" placeholder="Masalan: 1 soat multfilm" value="' +
    escapeHtml(item.name || "") + '" />' +
    '<label class="field-label">Narxi (Bilig)</label>' +
    '<input id="store-price" type="number" class="text-input" placeholder="20" value="' +
    (item.price || "") + '" oninput="updatePriceHint()" />' +
    '<p id="price-hint" class="price-hint">' + priceHintText(Number(item.price) || 0) + '</p>' +
    '<button class="btn btn-primary btn-block" data-action="submit-store-save" data-id="' + (id || "") + '">Saqlash</button>' +
    (id ? '<button class="btn btn-danger btn-block" data-action="delete-store-item" data-id="' + id + '">' +
      icon("trash", 15, 2) + ' O‘chirish</button>' : "")
  );
}

function giftPreviewHtml() {
  return giftMedia({ emoji: GiftDraft.emoji, photo: GiftDraft.photo }, 0, "") ;
}
function refreshGiftPreview() {
  const el = document.getElementById("gift-preview");
  if (el) el.innerHTML = giftPreviewHtml();
}

// Ota-onaga narx maslahati: bola haftasiga qancha Bilig yig‘ayotganidan
// kelib chiqib, sovg‘a qancha vaqtda qo‘lga kirishini aytadi.
function priceHintText(price) {
  const kids = State.storeChildren || [];
  if (!kids.length) return "";
  const kid = kids.find(function (k) { return String(k.id) === String(State.activeChildId); }) || kids[0];
  const weekly = kid.weekly || 0;
  if (!weekly) {
    return kid.name + " hali Bilig yig‘a boshlagani yo‘q — 15-40 Bilig oralig‘idan boshlang.";
  }
  if (!price) {
    return kid.name + " haftasiga o‘rtacha " + weekly + " Bilig yig‘moqda.";
  }
  const weeks = price / weekly;
  if (weeks < 0.5) {
    return kid.name + " haftasiga ~" + weekly + " Bilig yig‘adi. Bu sovg‘a bir necha kunda qo‘lga kiradi — " +
      "biroz qimmatroq qo‘ysangiz, qadri ortadi.";
  }
  if (weeks > 16) {
    return kid.name + " haftasiga ~" + weekly + " Bilig yig‘adi. Bunga " + Math.round(weeks) +
      " hafta ketadi — bola yo‘lda umidini uzishi mumkin.";
  }
  return kid.name + " haftasiga ~" + weekly + " Bilig yig‘moqda. Bu sovg‘a taxminan " +
    (weeks < 1 ? "bir haftada" : Math.round(weeks) + " haftada") + " qo‘lga kiradi.";
}
function updatePriceHint() {
  const el = document.getElementById("price-hint");
  const inp = document.getElementById("store-price");
  if (el && inp) el.textContent = priceHintText(Number(inp.value) || 0);
}

function toggleEmojiGrid() {
  const g = document.getElementById("gift-emoji-grid");
  if (g) g.hidden = !g.hidden;
}
function pickGiftEmoji(e) {
  GiftDraft.emoji = e; GiftDraft.photo = "";
  const inp = document.getElementById("gift-emoji-input");
  if (inp) inp.value = e;
  refreshGiftPreview();
  const g = document.getElementById("gift-emoji-grid");
  if (g) g.hidden = true;
}

// Ota-ona o‘z klaviaturasidan qo‘ygan belgi. Uzun matn yozib yuborilsa
// ham ilova buzilmasin uchun qisqartiriladi — bu maydon nom emas, BELGI.
function setGiftEmojiFromInput(v) {
  const clean = (v || "").replace(/\s+/g, "").slice(0, 8);
  GiftDraft.emoji = clean;
  if (clean) GiftDraft.photo = "";
  refreshGiftPreview();
}
function pickGiftPhoto() {
  readGiftForm();
  pickImage("gift", async function (blob) {
    const fd = new FormData();
    fd.append("photo", blob, "gift.webp");
    try {
      const res = await api("/api/parent/store/photo", { method: "POST", body: fd });
      GiftDraft.photo = res.photo; GiftDraft.emoji = "";
      // Kesish oynasi sovg‘a oynasining o‘rniga ochilgan edi — qaytaramiz.
      openStoreEditModal(GiftDraft.id, true);
    } catch (e) { toast(e.error || "Rasmni yuklab bo‘lmadi"); }
  });
}

async function submitStoreSave(id) {
  const name = document.getElementById("store-name").value.trim();
  const price = Number(document.getElementById("store-price").value);
  if (!name || !price) { toast("Nomi va narxini kiriting"); return; }
  const body = { name: name, price: price, emoji: GiftDraft.emoji, photo: GiftDraft.photo };
  await api("/api/parent/store" + (id ? "/" + id : ""), { method: "POST", body: body });
  closeModal(); toast("Saqlandi"); switchTab("store");
}

async function addQuickGift(name, price, emoji) {
  await api("/api/parent/store", { method: "POST", body: { name: name, price: Number(price), emoji: emoji } });
  toast("Do‘konga qo‘shildi"); switchTab("store");
}

function openRateModal() {
  const rate = State.walletRate || 0;
  openModal("Bilig kursi",
    '<p class="section-sub">1 Bilig necha so‘mga teng bo‘lishini belgilang. Bu faqat ' +
    'sizning hisobingiz uchun — sovg‘alarga qancha sarflayotganingizni ko‘rasiz.</p>' +
    '<input id="rate-input" type="number" class="text-input" placeholder="500" value="' + (rate || "") + '" />' +
    '<label class="switch-row"><span>Farzandim so‘mdagi qiymatni ko‘rsin</span>' +
    '<input id="rate-show" type="checkbox"' + (State.walletShowSom ? " checked" : "") + ' /></label>' +
    '<p class="section-sub">Tavsiya: o‘chiq qoldiring. Bilig o‘z qadrida qolgani ma\'qul — ' +
    'o‘qish «pul ishlash»ga aylanib qolmasin.</p>' +
    '<button class="btn btn-primary btn-block" data-action="submit-rate">Saqlash</button>'
  );
}
async function submitRate() {
  const rate = Number(document.getElementById("rate-input").value || 0);
  const show = document.getElementById("rate-show").checked;
  await api("/api/parent/rate", { method: "POST", body: { rate: rate, show_som: show } });
  closeModal(); toast("Bilig kursi saqlandi");
  State.walletRate = rate; State.walletShowSom = show;
  renderStoreTab();
}

// ---------------- XARID ----------------

function openBuyConfirm(id, name, price) {
  const left = (State.storeBalance || 0) - Number(price);
  openModal("Sovg‘ani olasanmi?",
    '<div class="buy-confirm">' +
    '<p class="bc-name">' + escapeHtml(name) + '</p>' +
    '<p class="bc-price">' + icon("coin", 18, 2.2) + ' <b>' + price + '</b> Bilig sarflanadi</p>' +
    '<p class="bc-left">Shundan keyin qo‘lingda <b>' + left + '</b> Bilig qoladi.</p>' +
    '</div>' +
    '<button class="btn btn-primary btn-block" data-action="confirm-buy" data-id="' + id + '">Ha, olaman</button>' +
    '<button class="btn btn-outline btn-block" data-action="close-modal">Hozircha yo‘q</button>'
  );
}

async function buyItem(itemId) {
  const res = await api("/api/child/store/" + itemId + "/buy" + asChildQuery(), { method: "POST" });
  if (!res.ok) { toast(res.message); return; }
  closeModal();
  mascotToast("quyoncha-sovga", "Sovg‘ang buyurtma qilindi",
              "Ota-onangga xabar yubordik.");
  refreshHeader(); renderStoreTab();
}

async function buyFreeze() {
  const res = await api("/api/child/freeze/buy" + asChildQuery(), { method: "POST" });
  if (!res.ok) { toast(res.message); return; }
  mascotToast("qorbars-tanga", "Qanot olindi",
              "Endi bir kun o‘qiy olmasang ham, parvozing uzilmaydi.");
  refreshHeader(); renderStoreTab();
}

async function toggleGoal(itemId, isOn) {
  await api("/api/child/goal" + asChildQuery(), {
    method: "POST", body: { item_id: isOn ? 0 : Number(itemId) }
  });
  toast(isOn ? "Orzu bekor qilindi" : "Orzu qilib belgilandi");
  renderStoreTab();
}

async function markGiftGiven(purchaseId) {
  await api("/api/parent/purchase/" + purchaseId + "/given", { method: "POST" });
  toast("Ajoyib — va'da bajarildi");
  renderStoreTab();
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
  const mode = State.ratingMode || "passport";
  main.innerHTML =
    childSwitcherHtml() +
    ratingChipsHtml(mode) +
    '<div id="rating-content">' + skeleton("rows") + '</div>';
  renderHeaderNav();
  const content = document.getElementById("rating-content");

  if (mode === "groups") {
    await renderGroupsView(content);
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
    '<div class="stat-box"><div class="num">' + p.streak + '</div><div class="lbl">Parvoz</div>' +
    (p.freezes ? '<div class="stat-extra">' + icon("shield", 12, 2.2) +
      ' ' + p.freezes + ' qanot</div>' : "") + '</div>' +
    '</div>' +
    calendarHtml(p.calendar) +
    booksStatHtml(p.books) +
    testStatHtml(p.tests);

  // Ko‘nikmalar diagnostikasi — faqat ota-onaga.
  // Bolaga foizli baho ko‘rsatish pedagogik jihatdan zararli: u o‘zini
  // baholanayotgandek his qiladi va stressga tushadi. Bolaga rag‘bat kerak.
  if (!isChildView()) {
    out += badgesBlockHtml(p.badges) +
      '<p class="eyebrow">Ko‘nikmalar diagnostikasi</p>' +
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

// ==========================================================
// GURUHLAR — kubok ichidagi uchinchi ko‘rinish
// ----------------------------------------------------------
// Ikki xil kirish yo‘li ataylab farq qiladi:
//   • taklif kodi bilan — darrov a'zo bo‘ladi;
//   • qidiruv orqali topilsa — admin tasdig‘i kutiladi.
// Guruhni ota-ona ochadi; xohlasa a'zo bolaga admin huquqini beradi.
// ==========================================================

function groupUrl(path) {
  const q = asChildQuery();
  if (!q) return path;
  return path + (path.indexOf("?") >= 0 ? "&" + q.slice(1) : q);
}

async function renderGroupsView(content) {
  if (State.groupId) { await renderGroupDetail(content, State.groupId); return; }

  const data = await api(groupUrl("/api/groups"));
  let out =
    '<div class="g-search">' +
    '<input id="group-q" class="g-input" placeholder="Guruh nomini qidiring" value="' +
    escapeHtml(State.groupQuery || "") + '">' +
    '<button class="btn btn-secondary g-find" data-action="group-search">' + icon("search", 18, 2) + '</button>' +
    '</div>';

  if (State.groupFound) {
    out += '<p class="section-sub">' + (State.groupFound.length
      ? State.groupFound.length + ' ta guruh topildi'
      : 'Bunday nomli guruh topilmadi') + '</p>';
    if (State.groupFound.length) {
      out += '<div class="card">' + State.groupFound.map(function (gr) {
        let end;
        if (gr.is_member) end = '<span class="pill pill-leaf">A\'zo</span>';
        else if (gr.pending) end = '<span class="pill pill-soft">Kutilmoqda</span>';
        else end = '<button class="btn btn-outline g-mini" data-action="group-request" data-id="' + gr.id + '">So‘rov</button>';
        return groupRowHtml(gr, end, gr.is_member ? gr.id : 0);
      }).join("") + '</div>';
    }
  }

  const mine = data.groups || [];
  if (mine.length) {
    out += '<p class="eyebrow">Mening guruhlarim</p><div class="card">' +
      mine.map(function (gr) {
        const badge = (gr.is_admin && gr.pending)
          ? '<span class="pill pill-gold">' + gr.pending + ' so‘rov</span>'
          : '<span class="g-end">' + icon("chevron-right", 16, 2.2) + '</span>';
        return groupRowHtml(gr, badge, gr.id);
      }).join("") + '</div>';
  }

  (data.waiting || []).forEach(function (w, i) {
    if (i === 0) out += '<p class="eyebrow">Javob kutilmoqda</p><div class="card" id="g-wait">';
    out += '<div class="list-row"><div style="display:flex;align-items:center;gap:10px;min-width:0">' +
      '<span class="g-mark sm">' + icon("users", 18, 2) + '</span>' +
      '<b style="font-size:15.5px">' + escapeHtml(w.name) + '</b></div>' +
      '<span class="pill pill-soft">Kutilmoqda</span></div>';
  });
  if ((data.waiting || []).length) out += '</div>';

  if (!mine.length && !State.groupFound) {
    out += '<div class="card">' + emptyState("users", "Hali guruhingiz yo‘q",
      "Guruh oching va taklif kodini do‘stlaringizga yuboring. Yoki yuqoridan qidirib so‘rov jo‘nating.") + '</div>';
  }

  out += '<div class="action-row">';
  if (data.can_create) {
    out += '<button class="btn btn-primary" data-action="group-create">Guruh ochish</button>';
  }
  out += '<button class="btn btn-secondary" data-action="group-join">Kod bilan qo‘shilish</button></div>';
  content.innerHTML = out;
}

function groupRowHtml(gr, endHtml, openId) {
  const act = openId ? ' data-action="group-open" data-id="' + openId + '"' : '';
  return '<div class="list-row g-row"' + act + '>' +
    '<div style="display:flex;align-items:center;gap:10px;min-width:0">' +
    '<span class="g-mark">' + icon("users", 20, 2) + '</span>' +
    '<div style="min-width:0">' +
    '<p class="g-name">' + escapeHtml(gr.name) + '</p>' +
    '<p class="g-meta">' + gr.members + " a'zo" +
    (gr.admin_name ? ' · ' + escapeHtml(gr.admin_name) : '') + '</p></div></div>' +
    endHtml + '</div>';
}

const GROUP_TABS = [
  { id: "members", icon: "users", label: "A\'zolar" },
  { id: "rating", icon: "trophy", label: "Reyting" },
];
const GROUP_PERIODS = [
  { id: "week", label: "Haftalik" },
  { id: "month", label: "Oylik" },
  { id: "all", label: "Umumiy" },
];

async function renderGroupDetail(content, gid) {
  if (State.groupMemberId) { await renderGroupMember(content, gid, State.groupMemberId); return; }
  const d = await api(groupUrl("/api/groups/" + gid));
  let out =
    '<div class="detail-topbar">' +
    '<button class="back-link" data-action="group-back">' + icon("arrow-left", 17, 2.2) + ' Guruhlar</button>' +
    (d.is_admin ? '<button class="edit-link" data-action="group-settings">' + icon("edit", 16, 2.2) + ' Sozlash</button>' : '') +
    '</div>' +
    '<div class="g-head"><span class="g-mark lg">' + icon("users", 26, 1.9) + '</span>' +
    '<div style="min-width:0"><p class="g-title">' + escapeHtml(d.name) + '</p>' +
    '<p class="g-meta">' + d.members.length + (d.max_members ? " / " + d.max_members : "") +
    " a'zo · Admin: " + escapeHtml(d.admin_name) + '</p></div></div>';

  out += '<div class="chip-row">' + GROUP_TABS.map(function (t) {
    return '<button class="chip' + (State.groupTab === t.id ? " active" : "") +
      '" data-action="group-tab" data-id="' + t.id + '">' + icon(t.icon, 16, 2) + t.label + '</button>';
  }).join("") + '<button class="chip is-soon">' + icon("clipboard-list", 16, 2) + 'Topshiriq</button></div>';

  if (State.groupTab === "rating") {
    content.innerHTML = out + '<div id="g-rating">' + skeleton("rows") + '</div>';
    await renderGroupRating(gid);
    return;
  }

  const reqs = d.requests || [];
  if (reqs.length) {
    out += '<div class="card g-req"><p class="g-req-t">' + reqs.length + ' ta so‘rov kutmoqda</p>' +
      reqs.map(function (r) {
        return '<div class="list-row">' +
          '<div style="display:flex;align-items:center;gap:10px;min-width:0">' +
          '<span class="g-av">' + avatarMarkup(r.avatar_id, 34) + '</span>' +
          '<div style="min-width:0"><p class="g-name">' + escapeHtml(r.name) + '</p>' +
          '<p class="g-meta">' + r.books + ' kitob</p></div></div>' +
          '<span class="g-req-btns">' +
          '<button class="icon-btn ok" data-action="group-decide" data-id="' + r.req_id + '" data-act="approve" aria-label="Tasdiqlash">' + icon("check", 16, 2.4) + '</button>' +
          '<button class="icon-btn" data-action="group-decide" data-id="' + r.req_id + '" data-act="reject" aria-label="Rad etish">' + icon("x", 16, 2.4) + '</button>' +
          '</span></div>';
      }).join("") + '</div>';
  }

  if (d.invite_code) {
    out += '<div class="card g-code" data-action="copy-code" data-code="' + escapeHtml(d.invite_code) + '">' +
      '<div><p class="eyebrow" style="margin:0">Taklif kodi</p>' +
      '<b class="g-code-val">' + escapeHtml(d.invite_code) + '</b>' +
      '<p class="g-code-note">Faqat adminga ko‘rinadi</p></div>' +
      '<span class="icon-btn">' + icon("copy", 16, 2.2) + '</span></div>';
  }

  out += '<div class="card">' + d.members.map(function (m) {
    const me = m.id === d.me;
    const end = d.is_admin && !me
      ? '<button class="icon-btn" data-action="group-member" data-id="' + m.id + '" data-name="' + escapeHtml(m.name) + '" data-admin="' + (m.is_admin ? 1 : 0) + '" aria-label="Sozlash">' + icon("more", 16, 2.2) + '</button>'
      : (m.is_admin ? '<span class="pill pill-brand">Admin</span>' : '<span class="g-end">' + m.books + ' kitob</span>');
    return '<div class="list-row g-row' + (me ? " me-row" : "") + '" data-action="group-member-card" data-id="' + m.id + '">' +
      '<div style="display:flex;align-items:center;gap:10px;min-width:0">' +
      '<span class="g-av">' + avatarMarkup(m.avatar_id, 36) + '</span>' +
      '<div style="min-width:0"><p class="g-name">' + escapeHtml(m.name) + '</p>' +
      '<p class="g-meta">' + m.books + ' kitob</p></div></div>' + end + '</div>';
  }).join("") + '</div>' +
    '<div class="action-row"><button class="btn btn-outline" data-action="group-leave">Guruhdan chiqish</button></div>';

  content.innerHTML = out;
}

async function renderGroupRating(gid) {
  const box = document.getElementById("g-rating");
  const d = await api(groupUrl("/api/groups/" + gid + "/rating?period=" + (State.groupPeriod || "week")));
  let out = '<div class="chip-row sub">' + GROUP_PERIODS.map(function (p) {
    return '<button class="chip chip-sm' + (State.groupPeriod === p.id ? " active" : "") +
      '" data-action="group-period" data-id="' + p.id + '">' + p.label + '</button>';
  }).join("") + '</div>';

  const rows = (d.list || []).filter(function (r) { return r.points > 0; });
  if (!rows.length) {
    box.innerHTML = out + '<div class="card">' + emptyState("trophy", "Hisob hali boshlanmagan",
      "Birinchi betlar o‘qilishi bilan ro‘yxat to‘la boshlaydi.") + '</div>';
    return;
  }
  out += '<div class="card">' + rows.map(function (r, i) {
    return '<div class="list-row g-row' + (r.is_me ? " me-row" : "") +
      '" data-action="group-member-card" data-id="' + r.id + '">' +
      '<div style="display:flex;align-items:center;gap:10px;min-width:0">' +
      '<div class="rank-chip ' + (i === 0 ? "top1" : "") + '">' + (i + 1) + '</div>' +
      '<span class="g-av sm">' + avatarMarkup(r.avatar_id, 32) + '</span>' +
      '<div style="min-width:0"><p class="g-name">' + escapeHtml(r.name) + '</p>' +
      '<p class="g-meta">' + r.pages + ' bet · ' + r.days + ' kun</p></div></div>' +
      '<div class="pill pill-brand">' + r.points + ' ball</div></div>';
  }).join("") + '</div>' +
    '<p class="g-note">Ball: har bet 1 (kuniga eng ko‘pi 40), tugatilgan kitob 20, ' +
    'to‘g‘ri test javobi 2, ovozli xulosa 5-15, AI ustoz savoli 10. ' +
    'Yig‘indi har kuni o‘qilganiga qarab ko‘payadi.</p>';
  box.innerHTML = out;
}

async function renderGroupMember(content, gid, cid) {
  const d = await api(groupUrl("/api/groups/" + gid + "/member/" + cid));
  let out =
    '<div class="detail-topbar">' +
    '<button class="back-link" data-action="group-member-back">' + icon("arrow-left", 17, 2.2) + ' Guruh</button>' +
    '</div>' +
    '<div class="g-card-head"><span class="g-av lg">' + avatarMarkup(d.avatar_id, 64) + '</span>' +
    '<p class="g-title">' + escapeHtml(d.name) + '</p>' +
    '<p class="g-meta">' + d.total_books + ' kitob · ' + d.total_pages + ' bet</p></div>' +
    '<div class="stat-grid">' +
    '<div class="stat-box"><div class="num">' + d.week_points + '</div><div class="lbl">Shu hafta ball</div></div>' +
    '<div class="stat-box"><div class="num">' + d.days + '</div><div class="lbl">Shu hafta kun</div></div>' +
    '</div>';

  const done = (d.books || []).filter(function (b) { return b.completed; });
  const now = (d.books || []).filter(function (b) { return !b.completed; });
  if (now.length) {
    out += '<p class="eyebrow">Hozir o‘qiyapti</p><div class="card">' +
      now.slice(0, 3).map(groupBookRow).join("") + '</div>';
  }
  if (done.length) {
    out += '<p class="eyebrow">O‘qib tugatgan</p><div class="card">' +
      done.map(groupBookRow).join("") + '</div>';
  }
  out += groupBadgesHtml(d.badges);
  content.innerHTML = out;
}

// A'zo kartochkasida faqat OLINGAN nishonlar ko‘rinadi. To‘liq javon
// (olinmaganlari bilan) — faqat o‘z bo‘limida; begona bolaning nimasi
// yetishmasligini ko‘rsatib turish o‘rinsiz.
function groupBadgesHtml(list) {
  const set = {};
  (list || []).forEach(function (b) { set[String(b).toLowerCase()] = true; });
  const have = BADGE_LIST.filter(function (b) { return set[b[1].toLowerCase()]; });
  if (!have.length) return "";
  return '<p class="eyebrow">Nishonlari</p><div class="g-badges">' + have.map(function (b) {
    return '<span class="g-badge"><span class="g-badge-art">' + badgeArt(b[0]) + '</span>' +
      escapeHtml(b[1]) + '</span>';
  }).join("") + '</div>';
}

function groupBookRow(b) {
  return '<div class="list-row">' +
    '<div style="min-width:0"><p class="g-name">' + escapeHtml(b.title) + '</p>' +
    '<p class="g-meta">' + escapeHtml(b.author || "") + '</p></div>' +
    '<span class="g-end">' + (b.completed
      ? icon("check-circle", 16, 2.2)
      : b.pages_read + ' bet') + '</span></div>';
}

function openGroupCreateModal() {
  openModal("Yangi guruh",
    '<p class="eyebrow">Guruh nomi</p>' +
    '<input id="g-name" class="g-input wide" placeholder="4-maktab, 7-B sinf" maxlength="48">' +
    '<p class="section-sub" style="margin:8px 0 14px">Nomni a\'zolar darrov tanisin: maktab va sinf, oila yoki mahalla nomi.</p>' +
    '<label class="g-switch"><input type="checkbox" id="g-searchable" checked>' +
    '<span><b>Qidiruvda ko‘rinsin</b><i>Boshqalar topib so‘rov yubora oladi</i></span></label>' +
    '<button class="btn btn-primary btn-block" data-action="group-create-save">Guruhni ochish</button>');
}

async function submitGroupCreate() {
  const name = (document.getElementById("g-name").value || "").trim();
  const searchable = document.getElementById("g-searchable").checked;
  const r = await api(groupUrl("/api/groups"), { method: "POST", body: { name: name, searchable: searchable } });
  closeModal();
  toast("Guruh ochildi");
  State.groupId = r.id;
  await renderRatingTab();
}

function openGroupJoinModal() {
  openModal("Kod bilan qo‘shilish",
    '<p class="section-sub" style="margin-top:0">Sizga yuborilgan taklif kodini kiriting — darrov a\'zo bo‘lasiz.</p>' +
    '<input id="g-code" class="g-input wide center" placeholder="BILIG-0000" maxlength="12">' +
    '<button class="btn btn-primary btn-block" data-action="group-join-save">Qo‘shilish</button>');
}

async function submitGroupJoin() {
  const code = (document.getElementById("g-code").value || "").trim();
  const r = await api(groupUrl("/api/groups/join"), { method: "POST", body: { code: code } });
  closeModal();
  toast(r.already ? "Siz allaqachon a'zosiz" : "Guruhga qo‘shildingiz");
  State.groupId = r.id;
  await renderRatingTab();
}

async function openGroupSettings() {
  const d = await api(groupUrl("/api/groups/" + State.groupId));
  openModal("Guruh sozlamasi",
    '<p class="eyebrow">Guruh nomi</p>' +
    '<input id="g-name" class="g-input wide" maxlength="48" value="' + escapeHtml(d.name) + '">' +
    '<p class="eyebrow" style="margin-top:16px">A\'zo soni chegarasi</p>' +
    '<input id="g-max" class="g-input wide" inputmode="numeric" placeholder="Cheklovsiz" value="' +
    (d.max_members ? d.max_members : "") + '">' +
    '<p class="section-sub" style="margin:8px 0 14px">Bo‘sh qoldirilsa cheklov bo‘lmaydi. Belgilansa, o‘sha songa yetgach yangi a\'zo qo‘shilmaydi. Eng ko‘pi — 300.</p>' +
    '<label class="g-switch"><input type="checkbox" id="g-searchable"' +
    (d.searchable ? " checked" : "") + '>' +
    '<span><b>Qidiruvda ko‘rinsin</b><i>Boshqalar topib so‘rov yubora oladi</i></span></label>' +
    '<button class="btn btn-primary btn-block" data-action="group-settings-save">Saqlash</button>');
}

async function submitGroupSettings() {
  const name = (document.getElementById("g-name").value || "").trim();
  const searchable = document.getElementById("g-searchable").checked;
  const maxRaw = (document.getElementById("g-max").value || "").replace(/\D/g, "");
  await api(groupUrl("/api/groups/" + State.groupId + "/update"),
    { method: "POST", body: { name: name, searchable: searchable, max_members: Number(maxRaw || 0) } });
  closeModal();
  toast("Saqlandi");
  await renderRatingTab();
}

function openGroupMemberModal(cid, name, isAdmin) {
  openModal(name,
    '<div class="g-member-act" data-action="group-set-admin" data-id="' + cid + '" data-val="' + (isAdmin ? 0 : 1) + '">' +
    '<div><b>' + (isAdmin ? "Admin huquqini olish" : "Admin huquqini berish") + '</b>' +
    '<i>Guruhni boshqara oladi: a\'zo qo‘shadi, chiqaradi</i></div>' +
    icon("chevron-right", 18, 2.2) + '</div>' +
    '<div class="g-member-act danger" data-action="group-remove" data-id="' + cid + '">' +
    '<div><b>Guruhdan chiqarish</b><i>O‘qigan kitoblari va natijalari o‘zida qoladi</i></div>' +
    icon("chevron-right", 18, 2.2) + '</div>');
}

async function groupSearchRun() {
  const box = document.getElementById("group-q");
  const q = (box ? box.value : "").trim();
  State.groupQuery = q;
  if (q.length < 2) { toast("Kamida ikki harf yozing"); return; }
  const r = await api(groupUrl("/api/groups/search?q=" + encodeURIComponent(q)));
  State.groupFound = r.list || [];
  await renderRatingTab();
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
    (c.longest > 1 ? ' · eng uzun parvoz <b>' + c.longest + '</b> kun' : '') + '</p>' +
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
  ["qalqon", "Qalqon", "Qanot ishlatilgandan keyin darhol qaytganda"],
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

// Lentadagi nishon xabari bosilganda — to‘liq ekranli tabrik
async function showUnseenBadges() {
  const data = await api("/api/child/home" + asChildQuery());
  const names = data.unseen_badges || [];
  try { await api("/api/child/badges/seen" + asChildQuery(), { method: "POST" }); } catch (e) {}
  celebrate(names, function () { if (State.currentTab === "home") renderChildHome(); });
}

function badgeArt(slug, size) {
  return '<img src="/badges/' + slug + '.svg?v=' + ASSET_V + '" alt="" loading="lazy">';
}

// To‘liq kolleksiya — olinmagan nishonlar xira va rangsiz turadi,
// shunda bola nimaga intilishini ko‘radi.
function badgeGridHtml(badgesStr) {
  const earned = earnedBadgeSet(badgesStr);
  BadgeEarnedSet = earned;        // tafsilot oynasi shundan foydalanadi
  const have = BADGE_LIST.filter(function (b) { return earned[b[1].toLowerCase()]; });
  const rest = BADGE_LIST.filter(function (b) { return !earned[b[1].toLowerCase()]; });
  const all = have.concat(rest);
  return '<p class="badge-count"><b>' + have.length + '</b> / ' + BADGE_LIST.length + ' nishon to‘plandi</p>' +
    '<div class="badge-grid">' + all.map(function (b) {
      const got = !!earned[b[1].toLowerCase()];
      // Nishon endi bosiladi: tafsiloti va ulashish tugmasi ochiladi.
      return '<button class="badge-tile' + (got ? "" : " is-locked") +
        '" data-action="open-badge" data-slug="' + b[0] + '">' +
        '<div class="badge-icon has-art">' + badgeArt(b[0]) + '</div>' +
        '<p>' + escapeHtml(b[1]) + '</p>' +
        '<span class="badge-cond">' + escapeHtml(got ? "Olingan" : b[2]) + '</span>' +
        '</button>';
    }).join("") + '</div>';
}
// ==========================================================
// NISHON TAFSILOTI VA ULASHISH
// ----------------------------------------------------------
// Ega so‘radi: «Nishon ustiga bosganda, tafsilotlar ko‘rinsin. Nishonlarni
// ijtimoiy tarmoqlarda ulashish mumkin bo‘lsin.»
//
// Ulashish Telegramning o‘z «yuborish» oynasi orqali ketadi — u yerdan
// istalgan suhbatga, kanalga yoki boshqa ilovaga uzatiladi.
let BadgeEarnedSet = {};        // qaysi nishonlar olingani — javon chizilganda yoziladi

function openBadgeModal(slug) {
  const b = BADGE_LIST.filter(function (x) { return x[0] === slug; })[0];
  if (!b) return;
  const got = !!BadgeEarnedSet[b[1].toLowerCase()];
  const meta = badgeMetaByName(b[1]) || {};
  const who = isChildView() ? "Sen" : "Farzandingiz";

  let html = '<div class="bd-art' + (got ? "" : " is-locked") + '">' + badgeArt(b[0]) + '</div>' +
    '<p class="bd-name">' + escapeHtml(b[1]) + '</p>' +
    '<p class="bd-state ' + (got ? "on" : "off") + '">' +
    icon(got ? "check-circle" : "lock", 14, 2.2) + ' ' +
    (got ? "Qo‘lga kiritilgan" : "Hali olinmagan") + '</p>';

  if (meta.msg) html += '<p class="bd-msg">' + escapeHtml(meta.msg) + '</p>';
  html += '<div class="bd-cond"><span>Sharti</span><b>' + escapeHtml(b[2]) + '</b></div>';
  if (!got) {
    html += '<p class="section-sub">' + who +
      ' shu shartni bajarsa, nishon shu yerda yonadi.</p>';
  }
  if (got) {
    html += '<button class="btn btn-primary btn-block" data-action="share-badge" ' +
      'data-slug="' + b[0] + '">' + icon("share", 16, 2) + ' Ulashish</button>';
  }
  html += '<button class="btn btn-outline btn-block" data-action="close-modal">Yopish</button>';
  openModal("Nishon", html);
}

function shareBadge(slug) {
  const b = BADGE_LIST.filter(function (x) { return x[0] === slug; })[0];
  if (!b) return;
  const name = (State.activeChildName || (State.me && State.me.name) || "").trim();
  const text = isChildView()
    ? "Men «" + b[1] + "» nishonini qo‘lga kiritdim! " + b[2] + ". Bilig AI — kitob o‘qish odati."
    : (name ? name + " " : "Farzandim ") + "«" + b[1] + "» nishonini qo‘lga kiritdi! " +
      b[2] + ". Bilig AI — kitob o‘qish odati.";
  const link = "https://t.me/share/url?url=" +
    encodeURIComponent(location.origin) + "&text=" + encodeURIComponent(text);
  if (tg && tg.openTelegramLink) tg.openTelegramLink(link);
  else window.open(link, "_blank");
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
// Tahrirlash oynasi ikki joydan ochiladi: Bolaxona ro‘yxatidan va
// farzandning batafsil sahifasidan. Saqlagandan keyin foydalanuvchini
// boshqa ekranga olib ketmaymiz — qaysi sahifada bo‘lsa, o‘sha yangilanadi.
function refreshAfterChildEdit(childId) {
  if (document.querySelector(".detail-topbar")) return renderChildDetailPage(Number(childId));
  if (State.currentTab === "bolaxona") return switchTab("bolaxona");
  return renderParentHome();
}

async function submitEditChild(id) {
  const name = document.getElementById("edit-child-name").value.trim();
  const age = Number(document.getElementById("edit-child-age").value);
  if (!name) { toast("Ismni kiriting"); return; }
  await api("/api/parent/children/" + id + "/profile", { method: "POST", body: { name: name, age: age, avatar_id: editChildAvatar } });
  closeModal();
  toast("Ma'lumotlar saqlandi");
  State.childrenCache = await api("/api/parent/children");
  refreshAfterChildEdit(id);
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
  // Ikki rejim bor:
  //   "wizard" — kitob qo‘shish sehrgari ichida: bosilgan kitob darrov
  //              rejaga tushadi.
  //   "browse" — «Barchasi» tugmasi orqali ochilgan javon: bosilgan kitob
  //              avval «Kitob haqida» oynasini ochadi. Ega talabi: bazadagi
  //              hamma kitobni shunchaki ko‘rib chiqish mumkin bo‘lsin.
  mode: "wizard",

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

  load: async function () {
    // Bola ota-ona bo‘limlariga kira olmaydi, shuning uchun unga o‘z
    // manzili beriladi — mazmuni bir xil.
    if (!this.all.length) {
      this.all = await api(isChildView() ? "/api/child/catalog" : "/api/parent/catalog");
    }
  },

  // «Barchasi» — butun javonni ko‘rish. Yosh chegarasisiz ochiladi.
  openBrowse: async function () {
    this.mode = "browse";
    this.query = "";
    this.ageKey = "all";
    await this.load();
    this.show("Barcha kitoblar");
  },

  open: async function (childAge) {
    this.mode = "wizard";
    this.query = "";
    this.ageKey = this.ageKeyFor(childAge || 10);
    await this.load();
    this.show("Kitob tanlang");
  },

  show: function (title) {
    openModal(title,
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
        (this.mode === "wizard"
          ? '<button class="btn btn-outline btn-block" data-action="wizard-pick-method" data-method="text">Nomini o‘zim yozaman</button>'
          : "") + '</div>';
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
      (this.mode === "wizard"
        ? '<button class="btn btn-outline btn-block cat-manual" data-action="wizard-pick-method" data-method="text">Katalogda yo‘qmi? Nomini yozing</button>'
        : "");
  },

  pick: async function (idx) {
    const b = this.all[idx];
    if (!b) return;
    if (this.mode === "browse") {
      // Javondan bosilgan kitob avval «Kitob haqida» oynasini ochadi:
      // ota-onada «Rejaga qo‘shish», bolada «So‘rayman» tugmasi bilan.
      const i = CatSeq++;
      RecBooks[i] = b;
      openRecBookModal(i, true);
      return;
    }
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
