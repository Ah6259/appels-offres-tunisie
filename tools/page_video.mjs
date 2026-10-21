// Page(s) vidéo du site (video/, video-pro/…) : fabriquées à partir de la page À propos déjà construite, pour garder
// EXACTEMENT le même en-tête, pied de page, CSP, sécurité et numéros ?v= que le reste du site.
// Copié par l'outil vidéos d'Ahmed (dossier privé « videos (outil) »). Appelé à la fin de la construction des pages.
// Réglages : tools/page_video.json (nom, titres, pages, couleur…). Ajoute aussi les pages au sitemap.xml.
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { join } from "path";

const esc = s => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
// texte dans la langue par défaut du site + data-v<langue> pour le changement de langue (assets : bloc « vidéo de présentation »)
const txt = (o, defaut) => `${Object.entries(o).map(([l, t]) => ` data-v${l}="${esc(t)}"`).join("")}>${esc(o[defaut] ?? o.fr)}`;

// 21/10/2026 (Ahmed) : lancement automatique SANS le son (seul permis par les navigateurs) + « Activer le son » (assets/video-son.js)
const SON = {"fr": "🔊 Activer le son", "ar": "🔊 شغّل الصوت", "en": "🔊 Turn on the sound"};
const SON_JS = "// Page vidéo (21/10/2026, Ahmed : « pourquoi la vidéo ne se lance pas toute seule ? ») : les navigateurs interdisent le lancement\n// automatique d'une vidéo AVEC le son ; elle se lance donc toute seule SANS le son, et « Activer le son » la reprend depuis le début\n// avec le son. Écrit par tools/page_video (outil vidéos d'Ahmed) : ne pas modifier ici. Style posé par le script (CSP : pas de style en ligne).\n(function () {\n  \"use strict\";\n  var v = document.querySelector(\".video-lecteur\"), b = document.querySelector(\".btn-video-son\");\n  if (!v || !b) return;\n  if (v.hasAttribute(\"muted\")) v.muted = true;\n  var st = { display: \"block\", margin: \"-4px auto 14px\", padding: \"11px 22px\", border: \"0\", borderRadius: \"999px\", background: \"#1d1d1f\",\n             color: \"#fff\", font: \"inherit\", fontWeight: \"700\", fontSize: \"1.05rem\", cursor: \"pointer\", whiteSpace: \"nowrap\" };\n  for (var k in st) b.style[k] = st[k];\n  function cacher() { b.hidden = !v.muted; b.style.display = v.muted ? \"block\" : \"none\"; }\n  b.addEventListener(\"click\", function () {\n    v.muted = false;\n    try { v.currentTime = 0; } catch (e) { /* vidéo pas encore prête */ }\n    var p = v.play();\n    if (p && p.catch) p.catch(function () { /* refusé : les commandes de la vidéo restent là */ });\n    cacher();\n  });\n  v.addEventListener(\"volumechange\", cacher);\n  var p = v.play();\n  if (p && p.catch) p.catch(function () { /* lancement automatique bloqué : le bouton lance la vidéo avec le son */ });\n  cacher();\n})();\n";

export function pagesVideo(root, cfg = JSON.parse(readFileSync(join(root, "tools/page_video.json"), "utf8"))) {
  const modele = readFileSync(join(root, cfg.modele || "a-propos/index.html"), "utf8");
  const D = cfg.defaut || "fr", fait = [];
  for (const p of cfg.pages) {
    const url = cfg.site + p.chemin, mp4 = cfg.site + "assets/video/" + p.video + ".mp4";
    const titre = p.titre[D] ?? p.titre.fr, nom = cfg.nom[D] ?? cfg.nom.fr, desc = p.description[D] ?? p.description.fr;
    const og = `<link rel="canonical" href="${url}">
<meta property="og:type" content="video.other">
<meta property="og:site_name" content="${esc(nom)}">
<meta property="og:title" content="${esc(titre + " — " + nom)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${cfg.site}assets/video/${p.apercu}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:video" content="${mp4}">
<meta property="og:video:secure_url" content="${mp4}">
<meta property="og:video:type" content="video/mp4">
<meta property="og:video:width" content="1080">
<meta property="og:video:height" content="1920">
<meta name="twitter:card" content="summary_large_image">
`;
    let h = modele
      .replace(/<script type="application\/ld\+json">[\s\S]*?<\/script>\s*/g, "")
      .replace(/<link rel="canonical"[^>]*>\s*/g, "")
      .replace(/<link rel="alternate" hreflang[^>]*>\s*/g, "")      // la page vidéo n'est pas une traduction de la page modèle (portail, 21/10/2026 : dans l'original)
      .replace(/<meta (property="og:[^"]*"|name="twitter:[^"]*")[^>]*>\s*/g, "")
      .replace(/<title>[\s\S]*?<\/title>/, `<title>${esc(titre)} | ${esc(nom)}</title>`)
      .replace(/(<meta name="description" content=")[^"]*(")/, `$1${esc(desc)}$2`)
      .replace("</head>", og + "</head>")
      .replace(/(<body[^>]*\sdata-page=")[^"]*(")/, "$1video$2");
    // contenu remplacé : (bandeau +) <main>…</main> ; sans <main>, tout ce qui est entre </header> et <footer
    const m = h.search(/<main[\s>]/), hero = h.search(/<section class="hero/);
    const debut = m >= 0 ? (hero >= 0 && hero < m ? hero : m) : (h.indexOf("</header>") >= 0 ? h.indexOf("</header>") + "</header>".length : -1);
    const fin = m >= 0 ? h.indexOf("</main>") + "</main>".length : h.search(/<footer[\s>]/);
    if (debut < 0 || fin < debut) throw new Error("page modèle sans <main> : " + (cfg.modele || "a-propos/index.html"));
    const r = "../".repeat(p.chemin.split("/").filter(Boolean).length);
    const src = Object.entries(p.sources || {}).map(([l, v]) => ` data-src-${l}="${r}assets/video/${v}.mp4" data-poster-${l}="${r}assets/video/${v.replace("presentation", "couverture")}.jpg"`).join("");
    const corps = `<main class="wrap video-main">
<section class="video-page" id="video">
  <div class="video-tete">${cfg.logo ? `<img src="${r}${cfg.logo}" alt="" width="52" height="52">` : ""}<p class="video-nom"${txt(cfg.nom, D)}</p></div>
  <h1${txt(p.titre, D)}</h1>
${p.texte ? `  <p class="video-texte"${txt(p.texte, D)}</p>
` : ""}  <video class="video-lecteur" controls playsinline preload="${p.preload || cfg.preload || "metadata"}" width="1080" height="1920" poster="${r}assets/video/${p.couverture}" src="${r}assets/video/${p.video}.mp4"${src} autoplay muted></video>
  <button class="btn-video-son" type="button"${txt(Object.fromEntries(Object.keys(cfg.partager).map(l => [l, SON[l] || SON.fr])), D)}</button>
  <a class="btn-video-site" href="${r}${p.site}"${txt(p.bouton, D)}</a>
  <button class="btn-video-partager" type="button" data-partager-video${txt(cfg.partager, D)}</button>
</section>
</main>`;
    h = h.slice(0, debut) + corps + h.slice(fin);
    h = h.replace("</body>", `<script src="${r}assets/video-son.js" defer></script>\n</body>`);
    mkdirSync(join(root, p.chemin), { recursive: true });
    writeFileSync(join(root, p.chemin, "index.html"), h);
    fait.push(p.chemin);
  }
  mkdirSync(join(root, "assets"), { recursive: true });
  writeFileSync(join(root, "assets/video-son.js"), SON_JS);
  // sitemap : ajoute les pages vidéo si elles n'y sont pas
  const sm = join(root, "sitemap.xml");
  if (existsSync(sm)) {
    let s = readFileSync(sm, "utf8");
    const ajout = cfg.pages.map(p => cfg.site + p.chemin).filter(u => !s.includes(`<loc>${u}</loc>`));
    if (ajout.length) { s = s.replace("</urlset>", ajout.map(u => `  <url><loc>${u}</loc></url>\n`).join("") + "</urlset>"); writeFileSync(sm, s); }
  }
  return fait;
}

// lancé directement : node tools/page_video.mjs
if (process.argv[1] && process.argv[1].replace(/\\/g, "/").endsWith("tools/page_video.mjs")) {
  const root = join(import.meta.dirname || new URL(".", import.meta.url).pathname.replace(/^\/(\w:)/, "$1"), "..");
  console.log("Pages vidéo : " + pagesVideo(root).join(", "));
}
