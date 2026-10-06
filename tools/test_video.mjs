// Test de la page vidéo (video/) et du bouton « Partager » (lien vers la page vidéo + adresse du site, jamais de fichier).
// Lancer : node tools/test_video.mjs   (jsdom : npm install --no-save --no-package-lock jsdom)
// Copié par l'outil vidéos d'Ahmed (dossier privé « videos (outil) ») ; page refaite par tools/page_video.mjs.
import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const { JSDOM, VirtualConsole } = createRequire(import.meta.url)("jsdom");
const SITE = "https://ah6259.github.io/appels-offres-tunisie/", BASE = new URL(SITE).pathname, DEFAUT = "fr";
const VIDEOS = ["presentation"];                 // vidéos (sans .mp4)
const MODE = "bouton";                   // « bouton » (.partager) ou « lien-wa » (liens wa.me de partage)
const APROPOS = "a-propos/index.html";             // page À propos (modèle de la page vidéo), vide s'il n'y en a pas
const lire = f => readFileSync(join(root, f), "utf8");
let ok = 0; const pb = [];
const check = (nom, cond) => { if (cond) ok++; else { pb.push(nom); console.log("ÉCHEC : " + nom); } };

// 1. vidéos : présentes, ≤ 8 Mo, 1080 × 1920 ; couverture ; aperçu 1200 × 630 pour WhatsApp / Facebook
function dimensions(buf) {
  for (let i = buf.indexOf("tkhd"); i > 0; i = buf.indexOf("tkhd", i + 4)) {
    const v = buf[i + 4], b = i + 8 + (v === 1 ? 32 : 20) + 8 + 8 + 36;
    const w = buf.readUInt32BE(b) / 65536, h = buf.readUInt32BE(b + 4) / 65536;
    if (w && h) return [w, h];
  }
  return [0, 0];
}
// piste son (musique de fond CC0) : présente (mp4a) et débit > 0 (lu dans la boîte esds)
function debitSon(buf) {
  const i = buf.indexOf("esds"); if (i < 0 || buf.indexOf("soun") < 0 || buf.indexOf("mp4a") < 0) return 0;
  let j = i + 8; const lng = () => { while (buf[j] & 0x80) j++; j++; };
  if (buf[j] !== 0x03) return 0; j++; lng(); j += 3;
  if (buf[j] !== 0x04) return 0; j++; lng();
  return Math.max(buf.readUInt32BE(j + 5), buf.readUInt32BE(j + 9));
}
for (const v of VIDEOS) {
  const f = join(root, "assets/video", v + ".mp4"), existe = existsSync(f);
  const buf = existe ? readFileSync(f) : Buffer.alloc(0), [w, h] = existe ? dimensions(buf) : [0, 0];
  check(`vidéo ${v}.mp4 présente, ≤ 8 Mo, 1080 × 1920 (${(buf.length / 1e6).toFixed(1)} Mo, ${w} × ${h})`, existe && buf.length <= 8e6 && w === 1080 && h === 1920);
  check(`vidéo ${v}.mp4 : piste son présente (musique de fond), débit > 0`, existe && debitSon(buf) > 0);
}
const jpeg = f => existsSync(join(root, f)) && readFileSync(join(root, f)).subarray(0, 2).toString("hex") === "ffd8";
check("couverture et aperçu JPEG de la page vidéo", jpeg("assets/video/couverture.jpg") && jpeg("assets/video/apercu-video.jpg"));
// 2. service worker et CSP
check("service worker : les .mp4 ne passent jamais par le cache", lire("sw.js").includes('/\\.mp4$/i.test(url.pathname)) return'));
const cspDe = h => (h.match(/http-equiv="Content-Security-Policy" content="([^"]*)"/) || [])[1] || "";
const autorise = (csp, n) => { const d = x => csp.split(";").map(y => y.trim()).find(y => y.startsWith(x + " ")) || ""; return d(n) ? d(n).includes("'self'") : d("default-src").includes("'self'"); };
// 3. page vidéo
const pv = existsSync(join(root, "video/index.html")) ? lire("video/index.html") : "";
check("page video/ : lecteur (controls, playsinline, poster), gros bouton « Ouvrir le site », bouton Partager",
  /<video class="video-lecteur" controls playsinline preload="metadata"[^>]*poster="\.\.\/assets\/video\/couverture\.jpg" src="\.\.\/assets\/video\/presentation\.mp4"/.test(pv)
  && /<a class="btn-video-site" href="\.\.\/"/.test(pv) && pv.includes("data-partager-video") && pv.includes("افتح الموقع"));
check("page video/ : og:type video.other, og:video mp4 1080 × 1920, og:image 1200 × 630, canonique",
  pv.includes('<meta property="og:type" content="video.other">') && pv.includes(`<meta property="og:video:secure_url" content="${SITE}assets/video/presentation.mp4">`)
  && pv.includes('<meta property="og:video:type" content="video/mp4">') && pv.includes('<meta property="og:video:width" content="1080">')
  && pv.includes(`<meta property="og:image" content="${SITE}assets/video/apercu-video.jpg">`) && pv.includes('<meta property="og:image:height" content="630">')
  && pv.includes(`<link rel="canonical" href="${SITE}video/">`) && (pv.match(/property="og:image"/g) || []).length === 1);
check("page video/ : CSP (vidéo autorisée) et en-tête / pied communs", autorise(cspDe(pv), "media-src") && /id="entete"|class="entete"|<header/.test(pv) && /id="pied"|<footer/.test(pv));
if (APROPOS) {
  const v = h => [...new Set((h.match(/\?v=[\w.-]+/g) || []))].sort().join(" ");
  check("page video/ : mêmes numéros ?v= que la page À propos (relancer node tools/page_video.mjs si À propos change)", v(pv) === v(lire(APROPOS)));
}
check("page video/ : dans le sitemap", lire("sitemap.xml").includes(`<loc>${SITE}video/</loc>`));

// 4. bouton Partager avec un faux téléphone
async function ouvrir(page, query = "") {
  const html = lire(page);
  const scripts = [...html.matchAll(/<script[^>]*src="([^"]+)"[^>]*><\/script>/g)].map(m => m[1]).filter(s => !/^https?:/.test(s));
  const dom = new JSDOM(html.replace(/<script[^>]*src="[^"]*"[^>]*><\/script>/g, ""), { runScripts: "outside-only", url: SITE + page.replace(/index\.html$/, "") + query, pretendToBeVisual: true, virtualConsole: new VirtualConsole() });
  const w = dom.window;
  w.goatcounter = { count: () => {} };
  w.fetch = async () => ({ ok: true, json: async () => ({}), text: async () => "" });
  for (const s of scripts) {
    const chemin = join(root, dirname(page), s.split("?")[0]);
    if (existsSync(chemin)) { try { w.eval(readFileSync(chemin, "utf8")); } catch (e) { /* script qui attend le vrai réseau */ } }
  }
  await new Promise(r => setTimeout(r, 80));
  return w;
}
async function essai({ page = "index.html", query = "", share = true, cible } = {}) {
  const w = await ouvrir(page, query), n = w.navigator, j = { partages: [], telecharges: [], ouvert: "" };
  if (share) {
    Object.defineProperty(n, "canShare", { configurable: true, value: () => true });
    Object.defineProperty(n, "share", { configurable: true, value: async x => { j.partages.push(x); } });
  }
  w.fetch = async u => { j.telecharges.push(String(u)); return { ok: true }; };
  w.open = u => { j.ouvert = u; };
  const b = w.document.querySelector(cible || (MODE === "bouton" ? ".partager" : 'a[href^="https://wa.me/?text="]'));
  if (b) b.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
  await new Promise(r => setTimeout(r, 80));
  j.bouton = !!b; return j;
}
let j = await essai();
const p = j.partages[0] || {};
check("Partager : envoie le lien de la page vidéo (url) et l'adresse du site dans le texte, aucun fichier",
  j.bouton && p.url === SITE + "video/" && String(p.text).includes(SITE) && !p.files && !j.telecharges.length);
j = await essai({ share: false });
check("Partager sans menu de partage : WhatsApp avec la page vidéo et l'adresse du site",
  j.ouvert.startsWith("https://wa.me/?text=") && decodeURIComponent(j.ouvert).includes(SITE + "video/") && !j.telecharges.length);
j = await essai({ page: "video/index.html", cible: "[data-partager-video]" });
check("page vidéo : le bouton « Partager la vidéo » partage la page vidéo", (j.partages[0] || {}).url === SITE + "video/" && !(j.partages[0] || {}).files);
const autre = ["fr", "ar", "en"].find(l => l !== DEFAUT && (pv.includes(`data-v${l}=`)));
if (autre) {
j = await essai({ query: "?lang=" + autre });
check(`Partager (page en « ${autre} ») : page vidéo dans la même langue`, (j.partages[0] || {}).url === SITE + "video/?lang=" + autre);
// 5. page vidéo dans l'autre langue (textes, vidéo de la langue)
{
  const w = await ouvrir("video/index.html", "?lang=" + autre);
  await new Promise(r => setTimeout(r, 120));
  const b = w.document.querySelector(".btn-video-site"), v = w.document.querySelector(".video-lecteur");
  const attendu = { fr: "Ouvrir le site", ar: "افتح الموقع", en: "Open the website" }[autre];
  check(`page vidéo en « ${autre} » : bouton traduit${VIDEOS.includes("presentation-" + autre) ? " et vidéo de la langue" : ""}`,
    !!b && b.textContent === attendu && (!VIDEOS.includes("presentation-" + autre) || v.getAttribute("src") === `../assets/video/presentation-${autre}.mp4`));
}
}
// 6. lien « Vidéo de présentation » (accueil, À propos) -> page vidéo
for (const page of ["index.html", APROPOS].filter(Boolean)) {
  const w = await ouvrir(page);
  for (let k = 0; k < 60 && !w.document.querySelector("#lien-video a"); k++) await new Promise(r => setTimeout(r, 50));
  const a = w.document.querySelector("#lien-video a");
  check(`lien « Vidéo de présentation » sur ${page} -> page vidéo`, !!a && a.getAttribute("href") === BASE + "video/");
}
console.log(pb.length ? `${pb.length} PROBLÈME(S) sur ${ok + pb.length} vérifications (page vidéo et partage)` : `TOUT PASSE (${ok} vérifications : page vidéo et partage)`);
process.exit(pb.length ? 1 : 0);
