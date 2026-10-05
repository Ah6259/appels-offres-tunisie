// Test automatique d'« Alertes appels d'offres Tunisie » — à lancer après chaque modification :
//   node tools/test_site.mjs                 (teste le site de ce dossier)
//   node tools/test_site.mjs --racine X      (teste une copie, ex. pour le sabotage volontaire)
// jsdom s'installe une fois par PC (dans ce dossier) :  npm install --no-save --no-package-lock jsdom
import { JSDOM } from "jsdom";
import { readFileSync, existsSync } from "fs";
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
  const html = lire(chemin).replace(/<script([^>]*) src="([^"?]+)(\?[^"]*)?"([^>]*)><\/script>/g,
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
check("images : illustration du bandeau", !!d.querySelector(".hero-illu") && existsSync(join(root, "assets/illustration-accueil.svg")));
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
check("sitemap : 38 pages (accueil, 10 métiers, 26 gouvernorats, à propos)", urls.length === 38);
const v = createHash("sha1").update(Buffer.concat(["style.css", "page.js", "app.js"].map(f => Buffer.from(readFileSync(join(root, "assets", f), "latin1").replace(/\r\n/g, "\n"), "latin1")))).digest("hex").slice(0, 8);
let okSeo = true, okSrc = true, okV = true, okH1 = true, okFichiers = true, okCopy = true;
for (const u of urls) {
  const chemin = u.replace(URL_SITE, "") + "index.html";
  if (!existsSync(join(root, chemin))) { okFichiers = false; console.log("   page manquante : " + chemin); continue; }
  const h = lire(chemin);
  const seo = /<title>[^<]{20,}<\/title>/.test(h) && /<meta name="description" content="[^"]{50,}"/.test(h) &&
    h.includes(`<link rel="canonical" href="${u}">`) && h.includes(`property="og:image" content="${URL_SITE}assets/og-image-v2.png"`) &&
    /property="og:title"/.test(h) && /name="viewport"/.test(h);
  if (!seo) { okSeo = false; console.log("   SEO incomplet : " + chemin); }
  if (!(h.match(/\?v=([0-9a-f]+)/g) || []).every(x => x === "?v=" + v)) { okV = false; console.log("   ?v= périmé : " + chemin); }
  if (!/<h1><span data-l="fr">[^<]+<\/span><span data-l="ar">[^<]+<\/span><\/h1>/.test(h)) { okH1 = false; console.log("   h1 FR+AR : " + chemin); }
  if (!/HAICOP/.test(h) || !/marchespublics\.gov\.tn/.test(h)) okSrc = false;
  if (!/©/.test(h)) okCopy = false;
}
check("toutes les pages du sitemap existent", okFichiers);
check("toutes les pages : titre, description, canonical, og:image, og:title, viewport", okSeo);
check(`toutes les pages : ?v=${v} (empreinte des fichiers assets, change à chaque modification)`, okV);
check("toutes les pages : titre h1 en français ET en arabe", okH1);
check("toutes les pages : mention de la source HAICOP + lien officiel", okSrc);
check("toutes les pages : mention © (même sans JavaScript)", okCopy);
w = await page("index.html", `jour=${JOUR}`);
check("pied de page : source HAICOP, « pas officiel », ©", /Source : HAICOP/.test(texte(w.document.getElementById("pied"))) &&
  /n'est pas officiel/.test(texte(w.document.getElementById("pied"))) && /© 2026/.test(texte(w.document.getElementById("pied"))));
try {
  const ld = JSON.parse(lire("index.html").match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1]);
  check("accueil : FAQ JSON-LD valide", ld["@type"] === "FAQPage" && ld.mainEntity.length >= 3);
} catch (e) { check("accueil : FAQ JSON-LD valide", false); }
check("accueil : seulement 3 balises <script> (aucun script venu des données)", (lire("index.html").match(/<script/g) || []).length === 3);

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
const png = readFileSync(join(root, "assets/og-image-v2.png"));
check("image d'aperçu 1200 × 630", png.readUInt32BE(16) === 1200 && png.readUInt32BE(20) === 630);
check("logo, favicon, icône iPhone", ["assets/logo.svg", "favicon.ico", "assets/apple-touch-icon.png"].every(f => existsSync(join(root, f))));
check(".gitignore : node_modules et captures", /node_modules/.test(lire(".gitignore")) && /captures/.test(lire(".gitignore")));

console.log(`\n${total - erreurs}/${total} vérifications réussies` + (erreurs ? ` — ${erreurs} ÉCHEC(S) : ne pas publier.` : " — tout est bon."));
process.exit(erreurs ? 1 : 0);
