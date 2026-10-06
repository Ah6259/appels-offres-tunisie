// Test de la vidéo de présentation et du bouton « Partager » (vidéo + lien, sinon lien seul).
// Lancer : node tools/test_video.mjs   (jsdom : npm install --no-save --no-package-lock jsdom)
// Copié par l'outil vidéos d'Ahmed (dossier privé « videos (outil) ») ; la vidéo se refait avec cet outil.
import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const { JSDOM, VirtualConsole } = createRequire(import.meta.url)("jsdom");
const SITE = "https://ah6259.github.io/appels-offres-tunisie/", BASE = new URL(SITE).pathname, NOM = "appels-offres-tunisie";
const VIDEOS = ["presentation"];                 // noms des vidéos (sans .mp4)
const MODE = "bouton";                   // « bouton » (.partager) ou « lien-wa » (liens wa.me de partage)
const lire = f => readFileSync(join(root, f), "utf8");
let ok = 0; const pb = [];
const check = (nom, cond) => { if (cond) ok++; else { pb.push(nom); console.log("ÉCHEC : " + nom); } };

// 1. vidéos : présentes, ≤ 8 Mo (WhatsApp), 1080 × 1920 (9:16), couverture JPEG
function dimensions(buf) {
  for (let i = buf.indexOf("tkhd"); i > 0; i = buf.indexOf("tkhd", i + 4)) {
    const v = buf[i + 4], b = i + 8 + (v === 1 ? 32 : 20) + 8 + 8 + 36;
    const w = buf.readUInt32BE(b) / 65536, h = buf.readUInt32BE(b + 4) / 65536;
    if (w && h) return [w, h];
  }
  return [0, 0];
}
for (const v of VIDEOS) {
  const f = join(root, "assets/video", v + ".mp4"), existe = existsSync(f);
  const buf = existe ? readFileSync(f) : Buffer.alloc(0), [w, h] = existe ? dimensions(buf) : [0, 0];
  check(`vidéo ${v}.mp4 présente, ≤ 8 Mo, 1080 × 1920 (${(buf.length / 1e6).toFixed(1)} Mo, ${w} × ${h})`, existe && buf.length <= 8e6 && w === 1080 && h === 1920);
  const c = join(root, "assets/video", v.replace("presentation", "couverture") + ".jpg");
  check(`couverture JPEG de ${v}`, existsSync(c) && readFileSync(c).subarray(0, 2).toString("hex") === "ffd8");
}
// 2. service worker : jamais de vidéo en cache ; 3. CSP : la vidéo et son téléchargement sont autorisés
check("service worker : les .mp4 ne passent jamais par le cache", lire("sw.js").includes('/\\.mp4$/i.test(url.pathname)) return'));
const accueil = lire("index.html");
const csp = (accueil.match(/http-equiv="Content-Security-Policy" content="([^"]*)"/) || [])[1] || "";
const dir = n => (csp.split(";").map(x => x.trim()).find(x => x.startsWith(n + " ")) || "");
const autorise = n => dir(n) ? dir(n).includes("'self'") : dir("default-src").includes("'self'");
check("CSP : vidéo (media-src) et téléchargement (connect-src) autorisés depuis le site", !!csp && autorise("media-src") && autorise("connect-src"));

// 4. bouton Partager avec un faux téléphone
async function ouvrir(page, query = "") {
  const html = lire(page);
  const scripts = [...html.matchAll(/<script[^>]*src="([^"]+)"[^>]*><\/script>/g)].map(m => m[1]).filter(s => !/^https?:/.test(s));
  const dom = new JSDOM(html.replace(/<script[^>]*src="[^"]*"[^>]*><\/script>/g, ""), { runScripts: "outside-only", url: SITE + page.replace(/index\.html$/, "") + query, pretendToBeVisual: true, virtualConsole: new VirtualConsole() });
  const w = dom.window;
  w.goatcounter = { count: () => {} };
  w.fetch = async () => ({ ok: true, json: async () => ({}), text: async () => "", blob: async () => new w.Blob([""]) });
  for (const s of scripts) {
    const chemin = join(root, dirname(page), s.split("?")[0]);
    if (existsSync(chemin)) { try { w.eval(readFileSync(chemin, "utf8")); } catch (e) { /* script qui attend le vrai réseau */ } }
  }
  await new Promise(r => setTimeout(r, 80));
  return w;
}
async function essai({ page = "index.html", query = "", fichiers = true, echec = false } = {}) {
  const w = await ouvrir(page, query), n = w.navigator, j = { partages: [], telecharges: [], ouvert: "" };
  Object.defineProperty(n, "canShare", { configurable: true, value: x => fichiers || !(x && x.files) });
  Object.defineProperty(n, "share", { configurable: true, value: async x => { j.partages.push(x); } });
  w.fetch = async u => { j.telecharges.push(String(u)); if (echec) throw new Error("réseau"); return { ok: true, blob: async () => new w.Blob(["mp4"], { type: "video/mp4" }) }; };
  w.open = u => { j.ouvert = u; };
  const b = MODE === "bouton" ? w.document.querySelector(".partager") : w.document.querySelector('a[href^="https://wa.me/?text="]');
  if (b) b.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
  await new Promise(r => setTimeout(r, 80));
  j.bouton = !!b; return j;
}
let j = await essai();
const p = j.partages[0] || {};
check("Partager : télécharge la vidéo et la partage avec le lien dans le texte",
  j.bouton && j.telecharges[0] === BASE + "assets/video/presentation.mp4" && p.files && p.files[0].name === NOM + ".mp4" && p.files[0].type === "video/mp4" && String(p.text).includes(SITE));
j = await essai({ fichiers: false });
check("Partager : sans partage de fichier possible → lien seul, aucune vidéo téléchargée",
  !j.telecharges.length && j.partages.length === 1 && !j.partages[0].files && String(j.partages[0].url).startsWith(SITE));
j = await essai({ echec: true });
check("Partager : vidéo injoignable → lien seul", j.partages.length === 1 && !j.partages[0].files && String(j.partages[0].url).startsWith(SITE));
if (VIDEOS.includes("presentation-fr")) {
  j = await essai({ query: "?lang=fr" });
  check("Partager (page en français) : la vidéo française", j.telecharges[0] === BASE + "assets/video/presentation-fr.mp4" && j.partages[0] && j.partages[0].files[0].name === NOM + "-fr.mp4");
}
// 5. lien « Vidéo de présentation » en bas de l'accueil et de À propos
for (const page of ["index.html", "a-propos/index.html"].filter(x => existsSync(join(root, x)))) {
  const w = await ouvrir(page);
  for (let k = 0; k < 60 && !w.document.querySelector("#lien-video a"); k++) await new Promise(r => setTimeout(r, 50));
  const a = w.document.querySelector("#lien-video a");
  check(`lien « Vidéo de présentation » sur ${page}`, !!a && a.getAttribute("href").startsWith(BASE + "assets/video/presentation"));
}
console.log(pb.length ? `${pb.length} PROBLÈME(S) sur ${ok + pb.length} vérifications (vidéo et partage)` : `TOUT PASSE (${ok} vérifications : vidéo et partage)`);
process.exit(pb.length ? 1 : 0);
