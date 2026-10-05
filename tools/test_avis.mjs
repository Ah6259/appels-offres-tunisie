// Test de la section « Votre avis » (règle d'Ahmed du 05/10/2026 : sur chacun de ses sites) — à lancer après chaque modification :
//   node tools/test_avis.mjs            (ou : node tools/test_avis.mjs <dossier>  pour tester une copie sabotée)
// jsdom s'installe une fois par PC :  npm install --no-save --no-package-lock jsdom
// Les pages sont ouvertes comme sur GitHub Pages (https) ; l'envoi à Formspree est SIMULÉ (aucun vrai message envoyé).
import jsdom from "jsdom";
const { JSDOM, VirtualConsole, ResourceLoader } = jsdom;
import { readFileSync, existsSync, readdirSync, statSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

// ---- Réglages propres à ce site ------------------------------------------------
const SITE = "Alertes appels d'offres Tunisie";                                         // valeur du champ caché « site »
const BASE = "https://ah6259.github.io/appels-offres-tunisie/";            // adresse de l'accueil en ligne
const IGNORER = ["node_modules", ".git", "tools", "captures", "preuves conditions d'utilisation"];
// --------------------------------------------------------------------------------
const FORMSPREE = "https://formspree.io/f/mwlpakqj";

const root = process.argv[2] || join(dirname(fileURLToPath(import.meta.url)), "..");
const lire = f => readFileSync(join(root, f), "utf8");
let erreurs = 0, total = 0;
const check = (desc, cond) => { total++; console.log((cond ? "OK   " : "FAIL ") + desc); if (!cond) erreurs++; };

// toutes les pages HTML du site
const pages = [];
(function parcourir(d) {
  for (const n of readdirSync(join(root, d))) {
    const p = d ? d + "/" + n : n;
    if (IGNORER.includes(n) && !d || IGNORER.includes(p)) continue;
    if (statSync(join(root, p)).isDirectory()) parcourir(p);
    else if (n.endsWith(".html") && !n.startsWith("google")) pages.push(p);
  }
})("");
check(`pages trouvées (${pages.length})`, pages.length > 0 && pages.includes("index.html"));

// ---- 1. Sécurité : CSP et scripts ----------------------------------------------------
const directives = s => { const m = s.match(/http-equiv="Content-Security-Policy" content="([^"]+)"/);
  return m ? Object.fromEntries(m[1].split(";").map(x => x.trim().split(/\s+/)).filter(t => t[0]).map(t => [t[0], t.slice(1)])) : null; };
const cspAccueil = directives(lire("index.html"));
check("accueil : CSP présente", !!cspAccueil);
check("accueil : CSP connect-src autorise https://formspree.io", !!cspAccueil && (cspAccueil["connect-src"] || cspAccueil["default-src"] || []).includes("https://formspree.io"));
const cspKo = pages.filter(p => { const d = directives(lire(p)); if (!d) return false;
  return !(d["connect-src"] || d["default-src"] || []).includes("https://formspree.io") || (d["form-action"] && !d["form-action"].includes("https://formspree.io")); });
check("CSP de chaque page : connect-src (et form-action) autorisent formspree.io" + (cspKo.length ? " — " + cspKo.slice(0, 5).join(", ") : ""), !cspKo.length);
const enLigne = pages.filter(p => [...lire(p).matchAll(/<script(?![^>]*\bsrc=)([^>]*)>/g)].some(m => !/application\/ld\+json/.test(m[1])));
check("aucun script en ligne (CSP)" + (enLigne.length ? " — " + enLigne.slice(0, 5).join(", ") : ""), !enLigne.length);
const onAttr = pages.filter(p => /<[a-z][^>]*\son[a-z]+\s*=/i.test(lire(p)));
check("aucun attribut on…= dans les pages" + (onAttr.length ? " — " + onAttr.slice(0, 5).join(", ") : ""), !onAttr.length);
check("assets/avis.js existe et envoie à " + FORMSPREE, existsSync(join(root, "assets/avis.js")) && lire("assets/avis.js").includes(`"${FORMSPREE}"`));
check("accueil : assets/avis.js chargé par un fichier externe", /<script[^>]+src="assets\/avis\.js(\?[^"]*)?"/.test(lire("index.html")));

// ---- 2. Pages ouvertes comme dans un navigateur ----------------------------------------
// fichiers du site lus sur le disque ; tout le reste (GoatCounter, polices…) n'est pas chargé
function fichierLocal(url) {
  if (!url.startsWith(BASE)) return null;
  let f = decodeURIComponent(new URL(url).pathname.slice(new URL(BASE).pathname.length));
  if (!f || f.endsWith("/")) f += "index.html";
  return existsSync(join(root, f)) ? readFileSync(join(root, f)) : null;
}
const TYPES = { js: "application/javascript", css: "text/css", svg: "image/svg+xml", json: "application/json", html: "text/html" };
function ressources() {
  if (jsdom.requestInterceptor)                                  // jsdom 30 et plus
    return { interceptors: [jsdom.requestInterceptor(req => {
      const corps = fichierLocal(req.url);
      if (!corps) return new Response("", { status: 404 });
      const ext = new URL(req.url).pathname.split(".").pop();
      return new Response(corps, { headers: { "Content-Type": TYPES[ext] || "application/octet-stream" } });
    })] };
  class Chargeur extends ResourceLoader {                        // jsdom 29 et moins
    fetch(url) { const c = fichierLocal(url); return c ? Promise.resolve(c) : null; }
  }
  return new Chargeur();
}
async function ouvrir(chemin, { lang = "fr" } = {}) {
  const fautes = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => { if (!/Not implemented|Could not load (img|link|script)/.test(e.message)) fautes.push(e.message); });
  const appels = [];
  const dom = new JSDOM(lire(chemin), {
    url: BASE + chemin.replace(/index\.html$/, "") + "?lang=" + lang,
    runScripts: "dangerously", resources: ressources(), pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      // faux fetch : on note chaque envoi, rien ne part sur Internet
      w.fetch = (url, opts = {}) => { appels.push({ url: String(url), opts }); return (w.__reseau || (() => Promise.resolve({ ok: true, status: 200 })))(url, opts); };
    }
  });
  await new Promise(ok => dom.window.addEventListener("load", ok));
  await new Promise(ok => setTimeout(ok, 30));
  dom.window.appels = appels; dom.window.fautes = fautes;
  return dom.window;
}
const attendre = (ms = 20) => new Promise(ok => setTimeout(ok, ms));
const envoyer = (w, form) => form.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
const champs = body => { const o = {}; for (const [k, v] of body.entries()) o[k] = v; return o; };

let w = await ouvrir("index.html"), d = w.document;
check("accueil : aucune erreur JavaScript" + (w.fautes.length ? " — " + w.fautes[0] : ""), !w.fautes.length);
const sec = d.getElementById("avis"), form = d.getElementById("avis-form");
check("accueil : section #avis présente avec le formulaire #avis-form", !!sec && !!form && sec.contains(form));
check("section : titre et textes en français ET en arabe", !!sec && /Votre avis/.test(sec.innerHTML) && /[؀-ۿ]/.test(sec.querySelector('[data-l="ar"]')?.textContent || ""));
check("formulaire : action = " + FORMSPREE + ", méthode POST", form?.getAttribute("action") === FORMSPREE && /post/i.test(form?.getAttribute("method") || ""));
const msg = form?.querySelector("textarea[name=message]"), mail = form?.querySelector("input[name=email]");
check("message : obligatoire, 1000 caractères max", !!msg && msg.required && msg.maxLength === 1000);
check("e-mail : facultatif, type email, « pour vous répondre »", !!mail && mail.type === "email" && !mail.required && /pour vous répondre/.test(sec.textContent));
check("note facultative : 4 choix (😀🙂😐🙁), aucun obligatoire", form?.querySelectorAll("input[type=radio][name=note]").length === 4 && ![...form.querySelectorAll("input[name=note]")].some(r => r.required));
check(`champ caché site = « ${SITE} »`, form?.querySelector("input[type=hidden][name=site]")?.value === SITE);
check("champ caché page présent", !!form?.querySelector("input[type=hidden][name=page]"));
const piege = form?.querySelector("input[name=_gotcha]");
check("anti-spam : champ piège _gotcha caché (hors écran, tabindex -1)", !!piege && piege.tabIndex === -1 && piege.getAttribute("aria-hidden") === "true");
check("mention « envoyé au créateur du site (service Formspree) »", /Votre avis est envoyé au créateur du site \(service Formspree\)/.test(sec?.textContent || ""));
check("bouton Envoyer (type submit)", !!form?.querySelector("button[type=submit]"));
check("rien n'est envoyé au chargement de la page (aucun appel réseau)", w.appels.length === 0);
check("placeholder du message en français", /erreur/.test(msg?.getAttribute("placeholder") || ""));

// champs utilisables malgré l'anti-copie : aucun événement bloqué
const evts = ["selectstart", "copy", "paste", "cut", "contextmenu", "keydown", "mousedown", "dragstart", "input"];
const bloques = [];
for (const el of [msg, mail]) for (const t of evts) {
  const ev = new w.Event(t, { bubbles: true, cancelable: true }); el.dispatchEvent(ev); if (ev.defaultPrevented) bloques.push(el.name + ":" + t);
}
check("champs non bloqués par l'anti-copie (sélection, copier/coller, clic droit, saisie)" + (bloques.length ? " — " + bloques.join(", ") : ""), !bloques.length);
const css = (existsSync(join(root, "assets/style.css")) ? lire("assets/style.css") : "");
check("CSS : champs de l'avis sélectionnables (user-select:text)", /\.avis textarea,\.avis input\{-webkit-user-select:text;user-select:text\}/.test(css));

// envoi vide : refusé, rien n'est envoyé
msg.value = "   ";
envoyer(w, form); await attendre();
check("message vide : refusé, rien envoyé, message d'erreur", w.appels.length === 0 && d.getElementById("avis-status").className === "err" && /Écrivez votre message/.test(d.getElementById("avis-status").textContent));

// envoi normal (fetch simulé)
let liberer; w.__reseau = () => new Promise(ok => { liberer = () => ok({ ok: true, status: 200 }); });
[...form.querySelectorAll("input[name=note]")].find(r => r.value === "🙂 Bien").checked = true;
msg.value = "Test du formulaire d'avis"; mail.value = "lecteur@example.com";
envoyer(w, form); await attendre();
const bouton = form.querySelector("button[type=submit]");
check("pendant l'envoi : bouton désactivé, « Envoi… »", bouton.disabled && /Envoi/.test(d.getElementById("avis-status").textContent));
envoyer(w, form); await attendre();
check("double clic pendant l'envoi : un seul envoi", w.appels.length === 1);
liberer(); await attendre();
const a = w.appels[0] || { opts: {} };
const f = a.opts.body ? champs(a.opts.body) : {};
const accept = a.opts.headers && (a.opts.headers.Accept || a.opts.headers.accept);
check("envoi vers " + FORMSPREE + " en POST, Accept: application/json", a.url === FORMSPREE && a.opts.method === "POST" && accept === "application/json");
check(`champs envoyés : site = « ${SITE} », page = adresse de l'accueil, message, note, email`,
  f.site === SITE && f.page === BASE + "?lang=fr" && f.message === "Test du formulaire d'avis" && f.note === "🙂 Bien" && f.email === "lecteur@example.com");
check("champ piège _gotcha envoyé vide (Formspree rejette les robots)", f._gotcha === "");
check("après l'envoi : merci, formulaire vidé, bouton réactivé",
  d.getElementById("avis-status").className === "ok" && /Merci/.test(d.getElementById("avis-status").textContent) && msg.value === "" && !bouton.disabled);

// échec (Formspree refuse ou pas de connexion)
w.__reseau = () => Promise.resolve({ ok: false, status: 500 });
msg.value = "Deuxième essai"; envoyer(w, form); await attendre();
check("échec de Formspree : message d'échec, texte gardé, bouton réactivé",
  d.getElementById("avis-status").className === "err" && /Échec/.test(d.getElementById("avis-status").textContent) && msg.value === "Deuxième essai" && !bouton.disabled);
w.__reseau = () => Promise.reject(new TypeError("Failed to fetch"));
envoyer(w, form); await attendre();
check("pas de connexion : message d'échec", d.getElementById("avis-status").className === "err");

// robot qui remplit le piège : rien n'est envoyé
const avant = w.appels.length;
piege.value = "spam"; msg.value = "pub"; envoyer(w, form); await attendre();
check("champ piège rempli (robot) : rien n'est envoyé", w.appels.length === avant);
w.close();

// en arabe
w = await ouvrir("index.html", { lang: "ar" }); d = w.document;
const fa = d.getElementById("avis-form");
check("arabe : placeholder en arabe", /[؀-ۿ]/.test(fa.querySelector("textarea").getAttribute("placeholder") || ""));
w.__reseau = () => Promise.resolve({ ok: true, status: 200 });
fa.querySelector("textarea").value = "رأي"; envoyer(w, fa); await attendre();
check("arabe : message de succès en arabe", /شكرًا/.test(d.getElementById("avis-status").textContent));
w.__reseau = () => Promise.resolve({ ok: false, status: 500 });
fa.querySelector("textarea").value = "رأي"; envoyer(w, fa); await attendre();
check("arabe : message d'échec en arabe", /تعذّر الإرسال/.test(d.getElementById("avis-status").textContent));
w.close();

// ---- 3. Lien « Votre avis » dans le pied de page de TOUTES les pages ----------------------
const sansLien = [], fautes = [];
for (const p of pages) {
  const ww = await ouvrir(p);
  const pied = ww.document.getElementById("pied") || ww.document.querySelector("footer");
  const liens = pied ? [...pied.querySelectorAll("a[href]")] : [];
  const ok = liens.some(l => { const u = new URL(l.getAttribute("href"), ww.location.href);
    return u.hash === "#avis" && (u.origin + u.pathname).replace(/index\.html$/, "") === BASE && /Votre avis/.test(l.textContent); });
  if (!ok) sansLien.push(p);
  if (ww.fautes.length) fautes.push(p + " : " + ww.fautes[0]);
  ww.close();
}
check(`pied de page : lien « Votre avis » vers l'accueil#avis sur les ${pages.length} pages` + (sansLien.length ? " — manque : " + sansLien.slice(0, 5).join(", ") : ""), !sansLien.length);
check("aucune erreur JavaScript sur les pages" + (fautes.length ? " — " + fautes.slice(0, 3).join(" | ") : ""), !fautes.length);

console.log(erreurs ? `\n${erreurs} ÉCHEC(S) sur ${total}` : `\nTout est vert (${total} vérifications).`);
process.exit(erreurs ? 1 : 0);
