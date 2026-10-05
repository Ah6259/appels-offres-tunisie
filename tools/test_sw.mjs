// Test du service worker (installation sur le téléphone) — à lancer après chaque modification :
//   node tools/test_sw.mjs            (ou : node tools/test_sw.mjs <dossier>  pour tester une copie sabotée)
// Le sw.js est exécuté dans un faux navigateur (cache + réseau simulés) : on vérifie ce qu'il SERT vraiment.
import { readFileSync, existsSync, readdirSync, statSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join, relative } from "path";
import vm from "vm";

// ---- Réglages propres à ce site ------------------------------------------------
const RACINE = "/appels-offres-tunisie/";                 // portée du service worker = dossier du site
const JS_COMMUN = "assets/page.js";           // fichier JS chargé par toutes les pages, qui enregistre sw.js
const EXCLUS = [];            // pages qui ne doivent JAMAIS être mises en cache
const IGNORER = ["node_modules", ".git", "tools", "captures", "preuves conditions d'utilisation"];
// --------------------------------------------------------------------------------

const root = process.argv[2] || join(dirname(fileURLToPath(import.meta.url)), "..");
const lire = f => readFileSync(join(root, f), "utf8");
let erreurs = 0;
const check = (desc, cond) => { console.log((cond ? "OK   " : "FAIL ") + desc); if (!cond) erreurs++; };

// ---- 1. Fichiers ------------------------------------------------------------------
check("sw.js existe à la racine du site", existsSync(join(root, "sw.js")));
const sw = existsSync(join(root, "sw.js")) ? lire("sw.js") : "";
const js = existsSync(join(root, JS_COMMUN)) ? lire(JS_COMMUN) : "";
const reg = js.match(/navigator\.serviceWorker\.register\(\s*["']([^"']+)["']\s*,\s*\{\s*scope\s*:\s*["']([^"']+)["']\s*\}\s*\)/);
check(`${JS_COMMUN} enregistre ${RACINE}sw.js avec la portée ${RACINE}`, !!reg && reg[1] === RACINE + "sw.js" && reg[2] === RACINE);
check("enregistrement protégé (\"serviceWorker\" in navigator, try/catch, pas en file:)",
  /["']serviceWorker["']\s+in\s+navigator/.test(js) && /try\s*\{[^]*serviceWorker\.register[^]*\}\s*catch/.test(js) && /https:/.test(js));
check("sw.js : CACHE_VERSION et nom de cache propre au site", /const CACHE_VERSION\s*=/.test(sw) && /const PREFIXE\s*=\s*"[a-z-]+-"/.test(sw));

// toutes les pages HTML du site
const pages = [];
(function parcourir(d) {
  for (const n of readdirSync(join(root, d))) {
    const p = d ? d + "/" + n : n;
    if (IGNORER.includes(p) || IGNORER.includes(n) && !d) continue;
    if (statSync(join(root, p)).isDirectory()) parcourir(p);
    else if (n.endsWith(".html") && !n.startsWith("google")) pages.push(p);
  }
})("");
check(`pages trouvées (${pages.length})`, pages.length > 0);
const nomJs = JS_COMMUN.split("/").pop();
const sansJs = pages.filter(p => !new RegExp(`<script[^>]+src="[^"]*${nomJs.replace(".", "\\.")}(\\?[^"]*)?"`).test(lire(p)));
check(`toutes les pages chargent ${JS_COMMUN}` + (sansJs.length ? " — manque : " + sansJs.slice(0, 5).join(", ") : ""), !sansJs.length);
const enLigne = pages.filter(p => [...lire(p).matchAll(/<script(?![^>]*\bsrc=)([^>]*)>/g)].some(m => !/application\/ld\+json/.test(m[1])));
check("aucun script en ligne dans les pages (CSP)" + (enLigne.length ? " — " + enLigne.slice(0, 5).join(", ") : ""), !enLigne.length);
const cspKo = pages.filter(p => {
  const m = lire(p).match(/http-equiv="Content-Security-Policy" content="([^"]+)"/);
  if (!m) return false;
  const dir = Object.fromEntries(m[1].split(";").map(s => s.trim().split(/\s+/)).filter(t => t[0]).map(t => [t[0], t.slice(1)]));
  const worker = dir["worker-src"] || dir["child-src"] || dir["script-src"] || dir["default-src"] || ["*"];
  return !worker.includes("'self'") && !worker.includes("*");
});
check("CSP : le service worker du site est permis (worker-src / script-src / default-src 'self')" + (cspKo.length ? " — " + cspKo.join(", ") : ""), !cspKo.length);
const iosKo = pages.filter(p => { const s = lire(p);
  return !/<meta name="apple-mobile-web-app-capable" content="yes">/.test(s) || !/<meta name="apple-mobile-web-app-title" content="[^"]+">/.test(s)
      || !/<link rel="apple-touch-icon" href="[^"]+">/.test(s) || !/<link rel="manifest" href="[^"]+">/.test(s); });
check("iPhone : apple-mobile-web-app-capable, -title, apple-touch-icon et manifeste sur toutes les pages" + (iosKo.length ? " — manque : " + iosKo.slice(0, 5).join(", ") : ""), !iosKo.length);

// ---- 2. Comportement (faux navigateur) ----------------------------------------------
const ORIGINE = "https://ah6259.github.io";
function navigateur() {
  const magasins = new Map();                     // nom -> Map(url -> {corps, statut, type})
  const ouvrir = nom => { if (!magasins.has(nom)) magasins.set(nom, new Map()); const m = magasins.get(nom);
    const cle = r => typeof r === "string" ? r : r.url;
    return {
      async match(r, o = {}) { let u = cle(r); let x = m.get(u);
        if (!x && o.ignoreSearch) { const b = u.split("?")[0]; for (const [k, v] of m) if (k.split("?")[0] === b) { x = v; break; } }
        return x ? new Response(x.corps, { status: x.statut, headers: { "Content-Type": x.type } }) : undefined; },
      async put(r, rep) { m.set(cle(r), { corps: await rep.text(), statut: rep.status, type: rep.headers.get("Content-Type") || "" }); },
      async keys() { return [...m.keys()].map(url => ({ url })); },
      async delete(r) { return m.delete(cle(r)); } }; };
  const caches = { open: async n => ouvrir(n), keys: async () => [...magasins.keys()], delete: async n => magasins.delete(n), _m: magasins };
  const ecoute = {}; const etat = { skip: 0, claim: 0, reseau: [] };
  let reseau = async () => { throw new TypeError("Failed to fetch"); };
  const self = { location: new URL(ORIGINE + RACINE + "sw.js"), addEventListener: (t, f) => { ecoute[t] = f; },
    skipWaiting: () => { etat.skip++; return Promise.resolve(); }, clients: { claim: () => { etat.claim++; return Promise.resolve(); } } };
  const ctx = vm.createContext({ self, caches, URL, Response, Headers, Promise, console, TypeError,
    fetch: (...a) => { etat.reseau.push(a[0].url || a[0]); return reseau(...a); } });
  vm.runInContext(sw, ctx);
  const rep = (corps, type = "text/html") => { const r = new Response(corps, { status: 200, headers: { "Content-Type": type } });
    Object.defineProperty(r, "type", { value: "basic" }); return r; };
  async function demande(chemin, { methode = "GET", mode = "cors", absolue = false } = {}) {
    const url = absolue ? chemin : ORIGINE + RACINE + chemin;
    const attente = []; let reponse;
    ecoute.fetch({ request: { url, method: methode, mode, headers: new Headers() },
      respondWith: p => { reponse = p; }, waitUntil: p => attente.push(p) });
    if (!reponse) return { intercepte: false };
    let r; try { r = await reponse; } catch (e) { r = undefined; }
    await Promise.allSettled(attente);
    return { intercepte: true, statut: r && r.status, corps: r && r.type !== "error" ? await r.text() : null };
  }
  return { ecoute, etat, caches, demande, rep, set reseau(f) { reseau = f; },
    garde: async (nom, chemin, corps) => (await caches.open(nom)).put(ORIGINE + RACINE + chemin, rep(corps)),
    lu: async (nom, chemin) => { const r = await (await caches.open(nom)).match(ORIGINE + RACINE + chemin); return r && r.text(); } };
}

const mCache = sw.match(/const PREFIXE\s*=\s*"([^"]+)"/), mVer = sw.match(/const CACHE_VERSION\s*=\s*"([^"]+)"/);
const nomCache = mCache && mVer ? mCache[1] + mVer[1] : "?";

try {
  // install / activate
  let b = navigateur();
  check("installation : skipWaiting()", (b.ecoute.install && (b.ecoute.install({ waitUntil: () => {} }), b.etat.skip === 1)) === true);
  await b.caches.open(nomCache); await b.caches.open(mCache[1] + "ancien"); await b.caches.open("autre-site-1");
  const att = []; b.ecoute.activate({ waitUntil: p => att.push(p) }); await Promise.all(att);
  const restants = await b.caches.keys();
  check("activation : ancien cache du site supprimé, cache actuel gardé", !restants.includes(mCache[1] + "ancien") && restants.includes(nomCache));
  check("activation : caches des AUTRES sites (même origine) non touchés", restants.includes("autre-site-1"));
  check("activation : clients.claim()", b.etat.claim === 1);

  // pages : réseau d'abord
  b = navigateur();
  await b.garde(nomCache, "", "ANCIENNE page");
  b.reseau = async () => b.rep("NOUVELLE page");
  let r = await b.demande("", { mode: "navigate" });
  check("page HTML : la réponse du RÉSEAU est servie même si une copie existe (réseau d'abord)", r.intercepte && r.corps === "NOUVELLE page");
  check("page HTML : la réponse du réseau est mise en cache", await b.lu(nomCache, "") === "NOUVELLE page");
  b.reseau = async () => { throw new TypeError("Failed to fetch"); };
  r = await b.demande("", { mode: "navigate" });
  check("hors connexion : la copie en cache est servie", r.corps === "NOUVELLE page");
  r = await b.demande("?lang=ar", { mode: "navigate" });
  check("hors connexion : ?lang=ar retrouve la page en cache", r.corps === "NOUVELLE page");
  r = await b.demande("page-jamais-vue/", { mode: "navigate" });
  check("hors connexion sans copie : page « Hors connexion » FR + AR (503)", r.statut === 503 && /Hors connexion/.test(r.corps) && /الإنترنت/.test(r.corps));

  // données : réseau d'abord, même avec ?v=
  for (const f of ["data/prix.json?v=1", "donnees/liste.json", "data/votes.js", "assets/x.json?v=2"]) {
    b = navigateur(); await b.garde(nomCache, f, "ANCIEN"); b.reseau = async () => b.rep("NOUVEAU", "application/json");
    r = await b.demande(f);
    check(`données ${f} : réseau d'abord`, r.corps === "NOUVEAU");
  }
  // fichiers versionnés : cache puis mise à jour
  b = navigateur(); await b.garde(nomCache, "assets/style.css?v=1", "ANCIEN css");
  b.reseau = async () => b.rep("NOUVEAU css", "text/css");
  r = await b.demande("assets/style.css?v=1");
  check("CSS versionné (?v=) : copie en cache servie tout de suite", r.corps === "ANCIEN css");
  check("CSS versionné : mise à jour en arrière-plan", await b.lu(nomCache, "assets/style.css?v=1") === "NOUVEAU css");
  r = await b.demande("assets/style.css?v=2");
  check("CSS nouvelle version : lue sur le réseau, ancienne version retirée du cache",
    r.corps === "NOUVEAU css" && !(await b.lu(nomCache, "assets/style.css?v=1")));
  // fichier non versionné : réseau d'abord
  b = navigateur(); await b.garde(nomCache, "assets/logo.png", "ANCIEN"); b.reseau = async () => b.rep("NOUVEAU", "image/png");
  r = await b.demande("assets/logo.png");
  check("fichier sans ?v= : réseau d'abord", r.corps === "NOUVEAU");

  // jamais en cache
  b = navigateur(); b.reseau = async () => b.rep("x");
  check("requête POST : non interceptée", !(await b.demande("", { methode: "POST" })).intercepte);
  for (const u of ["https://prix-eaux-tunisie.goatcounter.com/count?p=/", "https://gc.zgo.at/count.js", "https://docs.google.com/forms/d/x/formResponse",
                   "https://api.telegram.org/bot/x", "https://fonts.googleapis.com/css2?family=x"])
    check(`autre origine non interceptée : ${new URL(u).host}`, !(await b.demande(u, { absolue: true })).intercepte);
  check("autre site d'Ahmed (même origine, autre dossier) non intercepté", !(await b.demande(ORIGINE + "/autre-site/", { absolue: true, mode: "navigate" })).intercepte);
  for (const x of EXCLUS) {
    const rx = await b.demande(x, { mode: "navigate" });
    check(`${x} : jamais interceptée ni mise en cache`, !rx.intercepte && !(await b.lu(nomCache, x)));
  }
} catch (e) {
  check("le service worker s'exécute sans erreur : " + e.message, false);
}

console.log(erreurs ? `\n${erreurs} ÉCHEC(S)` : "\nTout est vert.");
process.exit(erreurs ? 1 : 0);
