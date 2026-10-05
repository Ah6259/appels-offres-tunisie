// Test automatique d'« Alertes appels d'offres Tunisie » — à lancer après chaque modification :
//   node tools/test_site.mjs                 (teste le site de ce dossier)
//   node tools/test_site.mjs --racine X      (teste une copie, ex. pour le sabotage volontaire)
// jsdom s'installe une fois par PC (dans ce dossier) :  npm install --no-save --no-package-lock jsdom
import { JSDOM } from "jsdom";
import { readFileSync, existsSync, readdirSync, statSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { createHash } from "crypto";

const i = process.argv.indexOf("--racine");
const root = i > 0 ? process.argv[i + 1] : join(dirname(fileURLToPath(import.meta.url)), "..");
const URL_SITE = "https://ah6259.github.io/appels-offres-tunisie/";
const lire = f => readFileSync(join(root, f), "utf8");
let erreurs = 0, total = 0;
const check = (desc, cond) => { total++; if (!cond) { console.log("FAIL " + desc); erreurs++; } else console.log("OK   " + desc); };

// ---- Données de référence (même règle que construire_site.py) ------------------
const etat = JSON.parse(lire("donnees/etat-source.json"));
const JOUR = etat.construit_le;
const plus = (d, n) => new Date(Date.parse(d + "T00:00:00Z") + n * 86400000).toISOString().slice(0, 10);
const brut = JSON.parse(lire("donnees/appels-offres.json"));
const tous = Object.values(brut.appels_offres);
const ouverts = tous.filter(a => a.date_limite ? a.date_limite >= JOUR : (a.date_publication && a.date_publication >= plus(JOUR, -30)));
check(`données : ${ouverts.length} appels d'offres ouverts le ${JOUR} (au moins 1)`, ouverts.length > 0);

// ---- Chargement d'une page comme un navigateur ---------------------------------
async function page(chemin, params = "") {
  // chaque <script src> est remplacé par son contenu, puis tout s'exécute dans l'ordre de la page
  const dossier = dirname(join(root, chemin));
  // (les scripts externes, comme GoatCounter, ne sont pas chargés)
  const html = lire(chemin).replace(/<script([^>]*) src="(?!https?:)([^"?]+)(\?[^"]*)?"([^>]*)><\/script>/g,
    (_, a, src) => `<script>${readFileSync(join(dossier, src), "utf8")}</script>`);
  const dom = new JSDOM(html, { url: URL_SITE + chemin.replace("index.html", "") + "?" + params,
                               runScripts: "dangerously", pretendToBeVisual: true });
  await new Promise(ok => dom.window.addEventListener("load", ok));
  return dom.window;
}
const texte = el => (el ? el.textContent : "").replace(/[⁦-⁩ ]/g, " ").replace(/\s+/g, " ").trim();
// cartes retenues par les filtres (les 15 premières sont affichées, la suite avec « Afficher plus »)
const visibles = d => [...d.querySelectorAll("#liste .ao")].filter(c => c.dataset.ok === "1");
const affichees = d => [...d.querySelectorAll("#liste .ao")].filter(c => !c.hidden);
const changer = (w, id, v) => { const s = w.document.getElementById(id); s.value = v; s.dispatchEvent(new w.Event("change")); };

// ---- 1. Accueil ----------------------------------------------------------------
let w = await page("index.html", `lang=fr&jour=${JOUR}`);
let d = w.document;
let cartes = visibles(d);
check(`accueil : ${ouverts.length} cartes retenues`, cartes.length === ouverts.length);
check("accueil : 15 cartes affichées d'abord, les suivantes cachées", affichees(d).length === Math.min(15, ouverts.length) &&
  affichees(d).every((c, k) => c === cartes[k]));
if (ouverts.length > 15) {
  check("bouton « Afficher plus » avec le nombre restant", !d.getElementById("plus").hidden && texte(d.getElementById("plus")).includes(String(ouverts.length - 15)));
  d.getElementById("plus").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  check("« Afficher plus » montre 15 cartes de plus", affichees(d).length === Math.min(30, ouverts.length));
}
// Images : icône du métier sur chaque carte, sprite, carte de la Tunisie, illustration
check("images : icône du métier sur chaque carte (symbole existant)", cartes.every(c => {
  const u = c.querySelector(".ic-m use"); return u && d.getElementById(u.getAttribute("href").slice(1)) && u.getAttribute("href") === "#i-" + c.dataset.metier; }));
check("images : 10 icônes de métier dans la page", d.querySelectorAll("symbol[id^='i-']").length === 10);
// Vraies photos : chaque fichier de assets/photos a un crédit (auteur + licence) sous la photo ET dans « À propos »
const photos = existsSync(join(root, "assets/photos")) ? readdirSync(join(root, "assets/photos")).filter(f => /\.(jpe?g|webp|png)$/i.test(f)) : [];
const cssPhotos = lire("assets/style.css").replace(/\s+/g, "");
check("photo du bandeau : mosaïque de vraies photos (téléphone 2 × 2, ordinateur 4 côte à côte), dégradé bleu, ≤ 150 Ko",
  photos.length >= 2 && !!d.querySelector(".hero.hero-photo") &&
  /hero-photo\{background:linear-gradient\([^)]*rgba[^;]*url\(photos\/marches-publics-mosaique-carre\.jpg\)/.test(cssPhotos) &&
  /@media\(min-width:700px\)\{\.hero\.hero-photo\{background-image:linear-gradient\([^;]*url\(photos\/marches-publics-mosaique\.jpg\)/.test(cssPhotos) &&
  photos.every(f => statSync(join(root, "assets/photos", f)).size <= 150000));
check("photo du bandeau : plus la photo du casque de chantier (pas que le BTP)", !photos.some(f => /chantier-monastir/.test(f)) && !/chantier-monastir/.test(cssPhotos));
const credit = d.querySelector(".hero .credit-photo");
const creditAuteurs = ["Habib M'henni", "Touzrimounir", "M. Rais"];
check("photo du bandeau : crédit de CHAQUE photo affiché (4 auteurs, licences CC, liens source Wikimedia)", !!credit &&
  creditAuteurs.every(a => texte(credit).includes(a)) && (texte(credit).match(/CC BY/g) || []).length === 4 &&
  [...credit.querySelectorAll("a")].filter(a => /commons\.wikimedia\.org\/wiki\/File:/.test(a.href)).length === 4 &&
  photos.every(f => (credit.dataset.photo || "").split(" ").includes("assets/photos/" + f)));
const bulles = [...d.querySelectorAll(".carte-tn .tn-b")];
check("carte de la Tunisie : 24 gouvernorats, chacun lien vers sa page", bulles.length === 24 &&
  bulles.every(b => b.getAttribute("href") === `gouvernorat/${b.dataset.gouv}/`));
check("carte de la Tunisie : nombre de chaque bulle = appels d'offres ouverts du gouvernorat", bulles.every(b => {
  const t = b.querySelector("text"); const n = cartes.filter(c => c.dataset.gouv === b.dataset.gouv).length;
  return t ? +t.textContent === n : n === 0; }));
check("accueil : chaque carte a un lien « fiche officielle » HAICOP vers SON numéro",
  cartes.every(c => { const a = c.querySelector("a.officiel");
    return a && a.href === "https://www.marchespublics.gov.tn/fr/appels-doffres/" + c.id && a.target === "_blank" && a.rel.includes("noopener"); }));
check("accueil : chaque carte a objet, acheteur, date limite et caution",
  cartes.every(c => texte(c.querySelector("h3")) && c.querySelector(".acheteur") && texte(c.querySelector(".limite b")) && c.querySelectorAll(".ao-infos > div").length === 2));
check("accueil : objets laissés dans leur langue (sens arabe pour un objet arabe)",
  cartes.every(c => { const h = c.querySelector("h3"); return /[؀-ۿ]/.test(h.textContent) ? h.dir === "rtl" : h.dir === "ltr"; }));
const lims = cartes.map(c => c.dataset.limite || "9999");
check("accueil : tri par date limite la plus proche", lims.every((x, k) => !k || lims[k - 1] <= x));
const ecart = (a, b) => Math.round((Date.parse(a) - Date.parse(b)) / 86400000);
check("accueil : date limite en rouge si moins de 7 jours (et seulement alors)",
  cartes.every(c => c.classList.contains("urgent") === (!!c.dataset.limite && ecart(c.dataset.limite, JOUR) < 7)));
check("accueil : « dans N jours » calculé", cartes.every(c => /jours|aujourd|demain|fiche/.test(texte(c.querySelector(".reste")))));
check("accueil : compteur « nouveaux » présent", /^\d+$/.test(texte(d.querySelector("#r-nouveaux b"))) && /nouveaux/.test(texte(d.querySelector("#r-nouveaux span"))));
check("accueil : compteur des ouverts = cartes", +texte(d.querySelector("#r-ouverts b")) === ouverts.length);
check("accueil : badges de confiance (HAICOP, gratuit, chaque jour)",
  /Source officielle HAICOP/.test(texte(d.querySelector(".confiance"))) && /Gratuit, sans inscription/.test(texte(d.querySelector(".confiance"))) && /chaque jour/.test(texte(d.querySelector(".confiance"))));
check("accueil : pastille « Mis à jour le … » avec la date de la dernière lecture",
  texte(d.querySelector('.maj [data-l="fr"]')) === "Mis à jour le" && /\d\d\/\d\d\/\d{4}/.test(texte(d.querySelector(".maj"))));
check("accueil : pas d'avertissement quand les données sont du jour", !d.getElementById("alerte-panne").classList.contains("on"));
check("accueil : liens vers les pages métiers et gouvernorats",
  d.querySelectorAll("#grille-metiers a").length === 10 && d.querySelectorAll("#grille-gouv a").length === 26);
check("accueil : aucun lien vide ou javascript:", [...d.querySelectorAll("a")].every(a => a.getAttribute("href") && !/^javascript:/i.test(a.getAttribute("href"))));

// Filtre métier
const parMetier = {};
ouverts.forEach(a => parMetier[a.metier] = (parMetier[a.metier] || 0) + 1);
const slugM = Object.fromEntries([...d.querySelectorAll("#f-metier option")].map(o => [o.dataset.fr, o.value]));
const metierMax = Object.keys(parMetier).sort((a, b) => parMetier[b] - parMetier[a])[0];
const optM = [...d.querySelectorAll("#f-metier option")].find(o => o.value && cartes.some(c => c.dataset.metier === o.value) &&
  cartes.filter(c => c.dataset.metier === o.value).length === parMetier[metierMax]);
check(`filtre métier : option trouvée pour « ${metierMax} »`, !!optM);
changer(w, "f-metier", optM.value);
cartes = visibles(d);
check(`filtre métier : ${parMetier[metierMax]} cartes, toutes du bon métier`, cartes.length === parMetier[metierMax] && cartes.every(c => c.dataset.metier === optM.value));
check("filtre métier : compteur mis à jour", texte(d.getElementById("compte")).startsWith(String(cartes.length)));
check("filtre métier : nombre affiché dans l'option", optM.textContent.includes(`(${parMetier[metierMax]})`));
// Filtre gouvernorat combiné
const g = cartes[0].dataset.gouv;
changer(w, "f-gouv", g);
cartes = visibles(d);
check("filtres métier + gouvernorat combinés", cartes.length >= 1 && cartes.every(c => c.dataset.metier === optM.value && c.dataset.gouv === g));
d.getElementById("effacer").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
check("bouton « Tout afficher » remet tout", visibles(d).length === ouverts.length);
// Gouvernorat seul
changer(w, "f-gouv", g);
check("filtre gouvernorat seul", visibles(d).every(c => c.dataset.gouv === g) && visibles(d).length === ouverts.filter(a => d.querySelector(`#${a.numero}`).dataset.gouv === g).length);
changer(w, "f-gouv", "");
// Tri « plus récents »
changer(w, "f-tri", "recent");
const pubs = visibles(d).map(c => c.dataset.pub);
check("tri « plus récents d'abord »", pubs.every((x, k) => !k || pubs[k - 1] >= x));
changer(w, "f-tri", "limite");
// Filtre dans l'adresse
w = await page("index.html", `lang=fr&jour=${JOUR}&metier=${optM.value}`);
check("filtre dans l'adresse (?metier=…)", visibles(w.document).length === parMetier[metierMax]);

// Expiration et ancienneté selon la date du VISITEUR
const premier = ouverts.filter(a => a.date_limite).sort((a, b) => a.date_limite.localeCompare(b.date_limite))[0];
w = await page("index.html", `lang=fr&jour=${plus(premier.date_limite, 1)}`);
d = w.document;
check("un appel d'offres expiré (date du visiteur) est masqué", d.getElementById(premier.numero).hidden);
check("données de plus de 2 jours : avertissement daté visible",
  d.getElementById("alerte-panne").classList.contains("on") && /depuis le \d\d\/\d\d\/\d{4}/.test(texte(d.getElementById("alerte-panne"))));
const dernier = ouverts.map(a => a.date_limite || "").sort().pop();
w = await page("index.html", `lang=fr&jour=${plus(dernier, 1)}`);
d = w.document;
check("tout expiré : aucune carte, message « aucun appel d'offres », site non vide (grilles, sources)",
  visibles(d).length === 0 && affichees(d).length === 0 && !d.getElementById("vide").hidden && d.querySelectorAll("#grille-metiers a").length === 10);
w = await page("index.html", `lang=fr&jour=${plus(JOUR, 1)}`);
check("données d'hier : pas encore d'avertissement", !w.document.getElementById("alerte-panne").classList.contains("on"));

// ---- 2. Arabe -------------------------------------------------------------------
w = await page("index.html", `lang=ar&jour=${JOUR}`);
d = w.document;
check("arabe : lang=ar et dir=rtl", d.documentElement.lang === "ar" && d.documentElement.dir === "rtl");
check("arabe : en-tête et pied en arabe", /طلبات العروض/.test(texte(d.getElementById("entete"))) && /جميع الحقوق محفوظة/.test(texte(d.getElementById("pied"))));
check("arabe : options des filtres en arabe", /كل الاختصاصات/.test(d.querySelector("#f-metier option").textContent));
check("arabe : compteur en arabe avec nombre isolé", /⁦\d+⁩ طلب عروض/.test(d.getElementById("compte").textContent));
check("arabe : « بعد N يومًا » sur les cartes", visibles(d).some(c => /يومًا|اليوم|غدًا/.test(c.querySelector(".reste").textContent)));
check("arabe : bouton vers le français", texte(d.querySelector(".langue")) === "Français");
w = await page("index.html", `lang=fr&jour=${JOUR}`);
check("français par défaut avec ?lang=fr", w.document.documentElement.lang === "fr" && w.document.documentElement.dir === "ltr");

// ---- 3. Toutes les pages : SEO, sources, ©, cache ----------------------------
const sitemap = lire("sitemap.xml");
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
check("sitemap : 40 pages (accueil, 10 métiers, 26 gouvernorats, à propos, publier, enchères)", urls.length === 40);
const v = createHash("sha1").update(Buffer.concat(["style.css", "page.js", "app.js"].map(f => Buffer.from(readFileSync(join(root, "assets", f), "latin1").replace(/\r\n/g, "\n"), "latin1")))).digest("hex").slice(0, 8);
let okSeo = true, okSrc = true, okV = true, okH1 = true, okFichiers = true, okCopy = true, okTrad = true;
for (const u of urls) {
  const chemin = u.replace(URL_SITE, "") + "index.html";
  if (!existsSync(join(root, chemin))) { okFichiers = false; console.log("   page manquante : " + chemin); continue; }
  const h = lire(chemin);
  const seo = /<title>[^<]{20,}<\/title>/.test(h) && /<meta name="description" content="[^"]{50,}"/.test(h) &&
    h.includes(`<link rel="canonical" href="${u}">`) && h.includes(`property="og:image" content="${URL_SITE}assets/og-image-v5.jpg"`) && h.includes(`<meta property="og:image:type" content="image/jpeg">`) &&
    /property="og:title"/.test(h) && /name="viewport"/.test(h);
  if (!seo) { okSeo = false; console.log("   SEO incomplet : " + chemin); }
  if (!(h.match(/\?v=([0-9a-f]+)/g) || []).every(x => x === "?v=" + v)) { okV = false; console.log("   ?v= périmé : " + chemin); }
  if (!/<h1><span data-l="fr">[^<]+<\/span><span data-l="ar">[^<]+<\/span><\/h1>/.test(h)) { okH1 = false; console.log("   h1 FR+AR : " + chemin); }
  if (!/HAICOP/.test(h) || !/marchespublics\.gov\.tn/.test(h)) okSrc = false;
  if (!/©/.test(h)) okCopy = false;
  if (!/<html [^>]*translate="no"/.test(h) || !h.includes('<meta name="google" content="notranslate">')) { okTrad = false; console.log("   traduction automatique non bloquée : " + chemin); }
}
check("toutes les pages du sitemap existent", okFichiers);
check("toutes les pages : titre, description, canonical, og:image, og:title, viewport", okSeo);
check(`toutes les pages : ?v=${v} (empreinte des fichiers assets, change à chaque modification)`, okV);
check("toutes les pages : titre h1 en français ET en arabe", okH1);
check("toutes les pages : mention de la source HAICOP + lien officiel", okSrc);
check("toutes les pages : mention © (même sans JavaScript)", okCopy);
check("toutes les pages : pas de traduction automatique par Chrome (translate=\"no\" + meta google notranslate)", okTrad);
w = await page("index.html", `jour=${JOUR}`);
check("pied de page : source HAICOP, « pas officiel », ©", /Source : HAICOP/.test(texte(w.document.getElementById("pied"))) &&
  /n'est pas officiel/.test(texte(w.document.getElementById("pied"))) && /© 2026/.test(texte(w.document.getElementById("pied"))));
try {
  const ld = JSON.parse(lire("index.html").match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1]);
  check("accueil : FAQ JSON-LD valide", ld["@type"] === "FAQPage" && ld.mainEntity.length >= 3);
} catch (e) { check("accueil : FAQ JSON-LD valide", false); }
check("accueil : seulement 4 balises <script> dont GoatCounter (aucun script venu des données)", (lire("index.html").match(/<script/g) || []).length === 4);

// ---- 4. Pages métier et gouvernorat ------------------------------------------
let okM = true, okG = true;
for (const u of urls.filter(x => /\/(metier|gouvernorat)\//.test(x))) {
  const chemin = u.replace(URL_SITE, "") + "index.html";
  const [, type, slug] = chemin.match(/^(metier|gouvernorat)\/([^/]+)\//);
  const pw = await page(chemin, `jour=${JOUR}`);
  const cs = visibles(pw.document);
  const attendu = ouverts.filter(a => { const c = d.getElementById(a.numero); return c && c.dataset[type === "metier" ? "metier" : "gouv"] === slug; }).length;
  const ok = cs.every(c => c.dataset[type === "metier" ? "metier" : "gouv"] === slug) && cs.length === attendu &&
    (cs.length > 0 || !pw.document.getElementById("vide").hidden);
  if (!ok) { console.log(`   ${chemin} : ${cs.length} cartes, attendu ${attendu}`); type === "metier" ? okM = false : okG = false; }
}
check("pages métier : seulement les appels d'offres du métier (ou message « aucun »)", okM);
check("pages gouvernorat : seulement ceux du gouvernorat (ou message « aucun »)", okG);
w = await page("gouvernorat/tunis/index.html", `jour=${JOUR}`);
check("page gouvernorat : filtre métier présent, pas de filtre gouvernorat", !!w.document.getElementById("f-metier") && !w.document.getElementById("f-gouv"));
w = await page("metier/informatique/index.html", `jour=${JOUR}`);
check("page métier : grande icône du métier dans le bandeau", !!w.document.querySelector(".hero .hero-ic.ic-informatique use"));

// ---- 5. À propos, fichiers de base ------------------------------------------
w = await page("a-propos/index.html", "lang=fr");
const ap = texte(w.document.querySelector("main"));
check("à propos : avertissement « pas officiel » + « vérifiez toujours la fiche officielle »", /n'est pas officiel/.test(ap) && /vérifiez toujours la fiche officielle/.test(ap));
check("à propos : source HAICOP, TUNEPS, lecture lente", /HAICOP/.test(ap) && /TUNEPS/.test(ap) && /lentement/.test(ap));
check("robots.txt avec le sitemap", /Sitemap: https:\/\/ah6259\.github\.io\/appels-offres-tunisie\/sitemap\.xml/.test(lire("robots.txt")));
check("LICENSE « tous droits réservés »", /Tous droits réservés/i.test(lire("LICENSE")));
// taille d'une image JPEG : lue dans son en-tête SOF (marqueurs FFC0 à FFC2)
const tailleJpeg = b => { for (let o = 2; o < b.length - 9;) { const m = b[o + 1], n = b.readUInt16BE(o + 2);
  if (m >= 0xC0 && m <= 0xC2) return [b.readUInt16BE(o + 7), b.readUInt16BE(o + 5)]; o += 2 + n; } return [0, 0]; };
const jpg = readFileSync(join(root, "assets/og-image-v5.jpg"));
const [lj, hj] = tailleJpeg(jpg);
check("image d'aperçu v5 (mosaïque) 1200 × 630, source tools/og-image.html à jour", lire("tools/og-image.html").includes("og-image-v5.jpg") &&
  lire("tools/og-image.html").includes("marches-publics-mosaique") && creditAuteurs.every(a => lire("tools/og-image.html").includes(a)) && lj === 1200 && hj === 630);
check(`image d'aperçu JPEG < 250 Ko (sinon WhatsApp n'affiche qu'une petite vignette) : ${Math.round(jpg.length / 1024)} Ko`,
  jpg[0] === 0xFF && jpg[1] === 0xD8 && jpg.length < 250000);
check("logo, favicon, icône iPhone", ["assets/logo.svg", "favicon.ico", "assets/apple-touch-icon.png"].every(f => existsSync(join(root, f))));
// manifeste : id UNIQUE = chemin du site (sinon Chrome croit le site « déjà installé » : tous les sites partagent ah6259.github.io)
let man = {}; try { man = JSON.parse(lire("manifest.webmanifest")); } catch (e) {}
check("manifeste présent, id unique = chemin du site, start_url/scope ./, icônes 192, 512 et maskable existantes",
  man.id === "/appels-offres-tunisie/" && man.start_url === "./" && man.scope === "./" && man.display === "standalone" && !!man.name && !!man.short_name
  && ["192x192", "512x512"].every(t => man.icons?.some(i => i.sizes === t)) && man.icons?.some(i => i.purpose === "maskable")
  && man.icons.every(i => existsSync(join(root, i.src))));
check("toutes les pages : lien vers le manifeste, icône iPhone et theme-color", urls.every(u => { const c = u.replace(URL_SITE, ""), r = "../".repeat(c.split("/").length - 1), h = lire(c + "index.html");
  return h.includes(`<link rel="manifest" href="${r}manifest.webmanifest">`) && h.includes(`<link rel="apple-touch-icon" href="${r}assets/apple-touch-icon.png">`) && h.includes('<meta name="theme-color"'); }));
check(".gitignore : node_modules et captures", /node_modules/.test(lire(".gitignore")) && /captures/.test(lire(".gitignore")));

// ---- 6. Recherche par mots-clés (FR + AR, accents, casse, numéro, résumé) ----------
const tape = (w, v) => { const q = w.document.getElementById("f-q"); q.value = v; q.dispatchEvent(new w.Event("input")); };
const norm = t => t.toLowerCase().normalize("NFKD").replace(/[\p{M}ـ]/gu, "")
  .replace(/[أإآٱ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي");
w = await page("index.html", `lang=fr&jour=${JOUR}`);
d = w.document;
check("recherche : champ présent sur l'accueil, les pages métier, gouvernorat et enchères",
  !!d.getElementById("f-q") && ["metier/btp-genie-civil/index.html", "gouvernorat/sfax/index.html", "encheres/index.html"].every(c => /id="f-q"/.test(lire(c))));
tape(w, "Tender-104049");
check("recherche : par numéro « Tender-104049 » -> 1 carte", visibles(d).length === 1 && visibles(d)[0].id === "Tender-104049");
tape(w, "ETUDE");
check(`recherche : insensible aux accents et à la casse (« ETUDE » trouve « Étude », ${visibles(d).length} cartes)`,
  visibles(d).length >= 1 && visibles(d).some(c => /Étude/.test(c.querySelector("h3").textContent)));
tape(w, "AMENAGEMENT SALLE");
check("recherche : « AMENAGEMENT SALLE » (sans accent) trouve « Aménagement d'une salle de sport » (Tender-103999)",
  visibles(d).some(c => c.id === "Tender-103999"));
tape(w, "تهيئه");
const nAm = visibles(d).length;
check(`recherche : en arabe, « تهيئه » trouve « تهيئة » (${nAm} cartes, toutes contiennent le mot)`,
  nAm >= 3 && visibles(d).every(c => norm(c.textContent).includes(norm("تهيئه"))));
tape(w, "Grombalia");
check("recherche : trouve aussi dans le résumé traduit (« Grombalia » -> objet en arabe Tender-104049)",
  visibles(d).some(c => c.id === "Tender-104049") && !/Grombalia/.test(d.getElementById("Tender-104049").querySelector("h3").textContent));
tape(w, "travaux bizerte");
check("recherche : plusieurs mots = tous présents", visibles(d).length >= 1 && visibles(d).every(c => /travaux/.test(norm(c.textContent)) && /bizerte|بنزرت/.test(norm(c.textContent))));
tape(w, "nabeul");
changer(w, "f-metier", "btp-genie-civil");
check("recherche + filtre métier combinés", visibles(d).length >= 1 && visibles(d).every(c => c.dataset.metier === "btp-genie-civil" && /nabeul|نابل/.test(norm(c.textContent))));
tape(w, "zzzqqq");
check("recherche sans résultat : message « aucun » + compteur 0", visibles(d).length === 0 && !d.getElementById("vide").hidden && texte(d.getElementById("compte")).startsWith("0"));
d.getElementById("effacer").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
check("« Tout afficher » vide aussi la recherche", d.getElementById("f-q").value === "" && visibles(d).length === ouverts.length);
w = await page("index.html", `lang=fr&jour=${JOUR}&q=Tender-104049`);
check("recherche dans l'adresse (?q=…)", visibles(w.document).length === 1);

// ---- 7. Résumé traduit (glossaire maison) --------------------------------------
w = await page("index.html", `lang=fr&jour=${JOUR}`);
d = w.document;
const tr = d.querySelector("#Tender-104049 .trad");
check("résumé traduit : objet arabe -> « Aménagement — centre pour personnes âgées — Grombalia »",
  !!tr && tr.lang === "fr" && texte(tr.querySelector(".trad-t")) === "≈ Aménagement — centre pour personnes âgées — Grombalia");
check("résumé traduit : mention « traduction automatique approximative » sur chaque résumé",
  d.querySelectorAll(".trad").length >= 10 && [...d.querySelectorAll(".trad")].every(t => /traduction automatique approximative/.test(texte(t))));
check("résumé traduit : objet français -> résumé arabe (rtl)", (() => { const t = d.querySelector("#Tender-104006 .trad"); return !!t && t.dir === "rtl" && /قرطاج/.test(t.textContent); })());
check("résumé traduit : rien d'affiché quand l'objet est trop peu reconnu (Tender-104043)", !d.querySelector("#Tender-104043 .trad"));

// ---- 8. Rappels avant la date limite (date du téléphone) -------------------------
const ref = ouverts.filter(a => a.date_limite).sort((a, b) => a.date_limite.localeCompare(b.date_limite)).pop();
const etiquette = async (n, lang = "fr") => { const pw = await page("index.html", `lang=${lang}&jour=${plus(ref.date_limite, -n)}`);
  return [pw, pw.document.getElementById(ref.numero).querySelector(".rappel")]; };
let [pw, r] = await etiquette(7);
check("étiquette « J-7 » 7 jours avant", !r.hidden && texte(r) === "J-7" && !r.classList.contains("fort"));
[pw, r] = await etiquette(2);
check("étiquette « J-2 » (rouge) 2 jours avant", !r.hidden && texte(r) === "J-2" && r.classList.contains("fort"));
[pw, r] = await etiquette(0);
check("étiquette « Dernier jour » le jour même", !r.hidden && texte(r) === "Dernier jour");
[pw, r] = await etiquette(2, "ar");
check("étiquette en arabe « بقي يومان »", texte(r) === "بقي يومان");
[pw, r] = await etiquette(8);
check("pas d'étiquette 8 jours avant", r.hidden);
[pw, r] = await etiquette(1);
const bt = pw.document.getElementById("bientot");
const items = [...pw.document.querySelectorAll("#bientot-liste li a")];
check("« Clôturent bientôt » : visible, au plus 5, la plus proche d'abord, lien vers la carte",
  !bt.hidden && items.length >= 1 && items.length <= 5 &&
  items.every(a => /^#Tender-\d+$/.test(a.getAttribute("href")) && !!pw.document.querySelector(a.getAttribute("href"))) &&
  ["Dernier jour", "J-1"].includes(texte(items[0].querySelector(".rappel"))));
w = await page("index.html", `lang=fr&jour=${plus(JOUR, -60)}`);
check("« Clôturent bientôt » caché quand rien ne clôture dans les 7 jours", w.document.getElementById("bientot").hidden);
// lien direct #Tender-… : carte montrée même au-delà des 15 premières
const loin = ouverts.slice().sort((a, b) => (b.date_limite || "9").localeCompare(a.date_limite || "9"))[0];
w = await page("index.html", `lang=fr&jour=${JOUR}`);
w.location.hash = "#" + loin.numero;
w.dispatchEvent(new w.HashChangeEvent("hashchange"));
check("lien direct #Tender-… (Telegram) : la carte est montrée et mise en avant",
  !w.document.getElementById(loin.numero).hidden && w.document.getElementById(loin.numero).classList.contains("visee"));

// ---- 9. Telegram, entreprises privées, ventes aux enchères --------------------------
const reglagesPy = lire("robot/reglages.py");
const canalVide = /^TELEGRAM_CANAL_URL = ""/m.test(reglagesPy);
check("bouton Telegram : caché tant que l'adresse du canal est vide (réglage unique robot/reglages.py)",
  canalVide ? urls.every(u => !/btn-telegram/.test(lire(u.replace(URL_SITE, "") + "index.html"))) : /btn-telegram/.test(lire("index.html")));
w = await page("publier/index.html", "lang=fr");
d = w.document;
const formVide = /^FORMULAIRE_PRIVES_URL = ""/m.test(reglagesPy);
check("page « Publier » : « Bientôt » tant que le formulaire n'est pas réglé, sinon bouton vers Google Forms",
  formVide ? /Bientôt/.test(texte(d.getElementById("btn-publier"))) : /^https:\/\/(forms\.gle|docs\.google\.com\/forms)\//.test(d.getElementById("btn-publier").href));
check("page « Publier » : mention « non vérifié par HAICOP » + liens refusés expliqués",
  /non vérifié par HAICOP/.test(texte(d.querySelector("main"))) && /liens Internet ne sont pas acceptés/.test(texte(d.querySelector("main"))));
const prives = (existsSync(join(root, "donnees/prives.json")) ? JSON.parse(lire("donnees/prives.json")).publies : []).filter(p => p.date_limite >= JOUR);
w = await page("index.html", `lang=fr&jour=${JOUR}`);
d = w.document;
check(`entreprises privées : ${prives.length} carte(s) sur l'accueil, chacune « non vérifié par HAICOP », section cachée si aucune`,
  d.querySelectorAll("#liste-prives .ao.prive").length === prives.length && [...d.querySelectorAll("#liste-prives .ao")].every(c => /non vérifié par HAICOP/.test(texte(c))) &&
  d.getElementById("prives").hidden === (prives.length === 0));
const ench = Object.values(JSON.parse(lire("donnees/encheres.json")).ventes).filter(x => x.date_limite >= JOUR);
w = await page("encheres/index.html", `lang=fr&jour=${JOUR}`);
d = w.document;
check(`ventes aux enchères : ${ench.length} cartes ouvertes, chacune avec l'avis officiel de la Douane`,
  ench.length > 0 && visibles(d).length === ench.length &&
  visibles(d).every(c => /^https:\/\/www\.douane\.gov\.tn\//.test(c.querySelector("a.officiel").href) && c.querySelector("a.officiel").rel.includes("noopener")));
check("ventes aux enchères : source « Douane tunisienne » + « pas officiel »", /Douane tunisienne/.test(texte(d.querySelector("main"))) && /n'est pas officiel/.test(texte(d.querySelector("main"))));
check("ventes aux enchères : compteur « ventes aux enchères ouvertes »", /ventes? aux enchères ouvertes?/.test(texte(d.getElementById("compte"))));
const premiereE = ench.slice().sort((a, b) => a.date_limite.localeCompare(b.date_limite))[0];
w = await page("encheres/index.html", `lang=fr&jour=${plus(premiereE.date_limite, 1)}`);
check("ventes aux enchères : une vente expirée (date du visiteur) est masquée", w.document.getElementById(premiereE.id).hidden);
check("pied de page : liens « Ventes aux enchères » et « Publier un appel d'offres »",
  !!w.document.querySelector('#pied a[href="../encheres/"]') && !!w.document.querySelector('#pied a[href="../publier/"]'));
w = await page("a-propos/index.html", "lang=fr");
const lisCredits = [...w.document.querySelectorAll("#credits-photos li")];
check("à propos : crédit de chaque photo de la mosaïque (4 photos : auteur, licence, source)", lisCredits.length === 4 &&
  creditAuteurs.every(a => lisCredits.some(li => texte(li).includes(a))) &&
  lisCredits.every(li => /CC BY/.test(texte(li)) && li.querySelector('a[href*="commons.wikimedia.org/wiki/File:"]')) &&
  photos.every(f => lisCredits.every(li => (li.dataset.photo || "").split(" ").includes("assets/photos/" + f))));

// ---- 10. Sécurité, anti-robots d'IA, anti-copie --------------------------------
const robots = lire("robots.txt");
const blocs = robots.split(/\n\s*\n/).map(b => b.trim());
const interdit = ua => blocs.some(b => b.split("\n").some(l => l.trim().toLowerCase() === "user-agent: " + ua.toLowerCase()) && /^Disallow: \/\s*$/m.test(b));
const IA = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-Web", "anthropic-ai", "CCBot", "Google-Extended", "Applebot-Extended",
  "PerplexityBot", "Bytespider", "Amazonbot", "Meta-ExternalAgent", "FacebookBot", "Diffbot", "Omgilibot", "cohere-ai", "ImagesiftBot",
  "HTTrack", "WebCopier", "WebZIP", "Offline Explorer", "wget", "SiteSnagger"];
check(`robots.txt : les ${IA.length} robots d'IA et aspirateurs sont interdits`, IA.every(interdit));
check("robots.txt : Googlebot, Bingbot et les autres robots restent autorisés", ["Googlebot", "Bingbot", "*"].every(u => !interdit(u)));
let okMeta = true, okGc = true;
for (const u of urls) {
  const h = lire(u.replace(URL_SITE, "") + "index.html");
  if (!/<meta name="robots" content="noai, noimageai">/.test(h) || !/<meta name="referrer" content="strict-origin-when-cross-origin">/.test(h)) okMeta = false;
  const csp = (h.match(/http-equiv="Content-Security-Policy" content="([^"]+)"/) || [])[1] || "";
  if (!/script-src 'self' https:\/\/gc\.zgo\.at;/.test(csp) || !/object-src 'none'/.test(csp) || !/form-action 'self' https:\/\/docs\.google\.com/.test(csp) ||
      /unsafe-eval/.test(csp) || /script-src[^;]*unsafe-inline/.test(csp)) { okMeta = false; console.log("   CSP : " + u); }
  if (!h.includes('<script data-goatcounter="https://prix-eaux-tunisie.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>') ||
      !/connect-src[^;]*https:\/\/prix-eaux-tunisie\.goatcounter\.com/.test(csp) || !/img-src[^;]*https:\/\/prix-eaux-tunisie\.goatcounter\.com/.test(csp)) {
    okGc = false; console.log("   GoatCounter : " + u); }
  if ([...h.matchAll(/<a [^>]*href="https?:\/\/[^"]+"[^>]*>/g)].some(m => !/rel="[^"]*noopener/.test(m[0]))) { okMeta = false; console.log("   lien externe sans noopener : " + u); }
}
check("toutes les pages : meta noai, referrer, CSP stricte (scripts du site seulement, formulaires Google permis), liens externes noopener", okMeta);
check("toutes les pages : statistiques GoatCounter (sans cookies) chargées, CSP compatible (script gc.zgo.at, envoi vers le compteur)", okGc);
const pj = lire("assets/page.js"), css = lire("assets/style.css").replace(/\s+/g, "");
check("anti-copie : script commun chargé (clic droit/glisser sur images, source ajoutée au texte copié, anti-iframe)",
  /contextmenu/.test(pj) && /dragstart/.test(pj) && /clipboardData\.setData/.test(pj) && /Source : /.test(pj) && /window\.top !== window\.self/.test(pj));
check("anti-copie : cartes non sélectionnables, mais numéros, liens, contacts et champs le restent",
  /\.ao,[^{]*\{-webkit-user-select:none;user-select:none/.test(css) && /\.aoa,\.ao\.ao-type,\.ao\.contact,input,textarea,select\{-webkit-user-select:text;user-select:text/.test(css));
w = await page("index.html", `lang=fr&jour=${JOUR}`);
let copie = "";
const h3 = w.document.querySelector("#liste .ao h3");
const sel = w.getSelection(); const rg = w.document.createRange(); rg.selectNodeContents(h3); sel.removeAllRanges(); sel.addRange(rg);
const ev = new w.Event("copy", { bubbles: true, cancelable: true }); ev.clipboardData = { setData: (t, v) => { copie = v; } };
h3.dispatchEvent(ev);
check("anti-copie : le texte copié d'une carte reçoit « Source : … — © … tous droits réservés »",
  /Source : https:\/\/ah6259\.github\.io\/appels-offres-tunisie\//.test(copie) && /tous droits réservés/.test(copie));
check("formulaires toujours utilisables : recherche et filtres actifs", !w.document.getElementById("f-q").disabled && !w.document.getElementById("f-metier").disabled);
// Aucun secret dans le dépôt (jetons Telegram, clés Google, clés privées, jetons GitHub, e-mails privés)
const fichiers = [];
const parcourir = dossier => { for (const f of readdirSync(join(root, dossier))) {
  if (["node_modules", ".git", "captures", "__pycache__"].includes(f)) continue;
  const c = join(dossier, f);
  if (statSync(join(root, c)).isDirectory()) parcourir(c); else if (/\.(py|js|mjs|json|md|yml|yaml|txt|html|css|xml|csv)$/.test(f)) fichiers.push(c); } };
parcourir(".");
const secrets = fichiers.filter(f => { const t = lire(f);
  return /\b\d{8,10}:AA[A-Za-z0-9_-]{30,}/.test(t) || /AIza[0-9A-Za-z_-]{35}/.test(t) || /-----BEGIN [A-Z ]*PRIVATE KEY-----/.test(t) ||
    /gh[pousr]_[A-Za-z0-9]{30,}/.test(t) || /[A-Za-z0-9._%+-]+@(yahoo|gmail|hotmail|outlook)\.[a-z]{2,}/i.test(t); });
check(`aucun secret dans le dépôt (${fichiers.length} fichiers vérifiés : jetons, clés, e-mails privés)`, secrets.length === 0);
if (secrets.length) console.log("   à vérifier : " + secrets.join(", "));

console.log(`\n${total - erreurs}/${total} vérifications réussies` + (erreurs ? ` — ${erreurs} ÉCHEC(S) : ne pas publier.` : " — tout est bon."));
process.exit(erreurs ? 1 : 0);
