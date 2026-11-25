/* Parcours d'achat COMMUN des Pass Clicvia (règle commune § 70, PASS.1 du 25/11/2026) — UN seul script pour tous les sites.
   ORIGINAL : projets-ahmed/outils communs/pass-commun/pass-commun.js. Dans un site, ce fichier est une COPIE (assets/pass-commun.js) :
   NE JAMAIS LA MODIFIER DANS LE SITE. On améliore ICI, puis `python3 synchroniser.py` recopie partout (voir LISEZMOI.md).

   Ce que fait le module (consignes : CONSIGNES.md du même dossier) :
   - vérifie le formulaire : nom, téléphone (8 chiffres en Tunisie, ou international), e-mail, formule, conditions, + les vérifications
     propres au site (crochets) dans l'ordre choisi par le site ; piège anti-robot `_gotcha` (rempli = rien n'est envoyé) ;
   - crée le code de commande (crypto.getRandomValues) dans l'alphabet et la longueur DU site (format des codes vendus inchangé) ;
   - l'envoie à Formspree (mwlpakqj) avec la ligne `pour_activer … ; code: <CODE>` ;
   - demande l'e-mail automatique (api-email.clicvia.com) UNE fois par commande, sans attendre (jamais bloquant) ;
   - affiche la page « Dernière étape » ([data-code], [data-formule], liens WhatsApp avec code + nom + formule, liens Telegram) ;
   - garde la commande dans le téléphone (localStorage « pass-commande » : code, formule, date [+ lien Telegram] ; JAMAIS nom,
     téléphone ni e-mail ; 60 jours) ; au retour : bandeau « commande en attente » ; sites à code tapé : le code est essayé tout seul
     (crochet `essayerCode` du site) ; bouton « Nouvelle commande ».
   ES5 simple, aucun script en ligne (CSP). Textes FR / AR / EN ici ; un site ne change un texte que par son réglage (`textes`).

   Utilisation dans une page : balise script de « …/assets/pass-commun.js?v=… », puis celle de « …/assets/pass-reglages.js?v=… »
   (jamais la balise fermante écrite ici : certains tests recopient ce fichier DANS la page), où pass-reglages.js appelle  PassCommun.brancher({ … réglage du site … })  (forme du réglage : LISEZMOI.md). */
(function () {
  "use strict";
  var VERSION = "2026-11-25d";
  var FORMSPREE = "https://formspree.io/f/mwlpakqj";
  var EMAIL_API = "https://api-email.clicvia.com/inscription";
  var WHATSAPP = "21624321390";
  var CLE = "pass-commande", JOURS = 60;
  var B32 = "0123456789abcdefghijklmnopqrstuv";
  var EMAIL_OK = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  // Textes communs. Un site peut en remplacer un par `textes: { cle: { fr, ar, en } }` dans son réglage.
  var TEXTES = {
    nom: { fr: "Indiquez votre nom.", ar: "اكتب اسمك.", en: "Enter your name." },
    telephone: { fr: "Téléphone : 8 chiffres, par exemple 24 321 390.", ar: "الهاتف: ⁦8⁩ أرقام، مثال ⁦24 321 390⁩.",
                 en: "Phone: 8 digits, for example 24 321 390." },
    telephoneInternational: { fr: "Téléphone : 8 à 15 chiffres, avec l'indicatif (ex. +216 24 321 390).",
                              en: "Phone: 8 to 15 digits, with country code (e.g. +216 24 321 390).", ar: "الهاتف: من ⁦8⁩ إلى ⁦15⁩ رقمًا مع رمز البلد." },
    emailVide: { fr: "Indiquez votre e-mail : vous y recevez votre code et les étapes du paiement.", ar: "اكتب بريدك الإلكتروني: يصلك عليه رمزك وخطوات الدفع.",
                 en: "Enter your e-mail: you receive your code and the payment steps there." },
    emailVideSansAuto: { fr: "Indiquez votre e-mail.", ar: "اكتب بريدك الإلكتروني.", en: "Enter your e-mail." },
    emailInvalide: { fr: "Indiquez une adresse e-mail valide.", ar: "اكتب بريدًا إلكترونيًا صحيحًا.", en: "Enter a valid e-mail address." },
    formule: { fr: "Choisissez une formule.", ar: "اختر صيغة.", en: "Choose a plan." },
    conditions: { fr: "Cochez « J'accepte les conditions de l'abonnement ».", ar: "يجب الموافقة على شروط الاشتراك.", en: "Tick “I accept the subscription terms”." },
    envoi: { fr: "Envoi…", ar: "جارٍ الإرسال…", en: "Sending…" },
    merci: { fr: "Merci ! Votre inscription a bien été envoyée.", ar: "شكرًا! تم إرسال تسجيلك.", en: "Thank you! Your sign-up has been sent." },
    // échec de Formspree, sites à alertes Telegram : le robot crée l'inscription seul, on continue (echec: "continuer")
    echecContinuer: { fr: "Inscription non envoyée (connexion), mais votre code fonctionne : ouvrez Telegram ci-dessous.",
                      ar: "لم يُرسل التسجيل (الاتصال)، لكن رمزك يعمل: افتح تيليغرام أسفله.",
                      en: "Sign-up not sent (connection), but your code works: open Telegram below." },
    // échec de Formspree, sites à code tapé : on reste sur le formulaire, MÊME code au nouvel essai (echec: "reessayer")
    echecReessayer: { fr: "Échec de l'envoi — vérifiez votre connexion et réessayez, ou écrivez-nous sur WhatsApp au 24 321 390.",
                      ar: "تعذّر الإرسال — تحقّق من الاتصال وأعد المحاولة، أو راسلنا عبر واتساب على ⁦24321390⁩.",
                      en: "Sending failed — check your connection and try again, or write to us on WhatsApp at +216 24 321 390." },
    verification: { fr: "Vérification de votre commande…", ar: "جارٍ التثبت من طلبك…", en: "Checking your order…" },
    attentePaiement: { fr: "En attente de votre paiement : dès qu'il est vérifié, votre Pass s'ouvrira tout seul ici.",
                       ar: "في انتظار دفعتك: بعد التثبت منها تُفتح باقتك هنا وحدها.",
                       en: "Waiting for your payment: once it is checked, your Pass will open here by itself." },
    attenteImpossible: { fr: "En attente de votre paiement (vérification impossible pour le moment : revenez plus tard).",
                         ar: "في انتظار دفعتك (التثبت غير ممكن الآن: عد لاحقًا).",
                         en: "Waiting for your payment (cannot check for now: come back later)." },
    waDebut: { fr: "Voici ma preuve de paiement", ar: "هذا وصل الدفع", en: "Here is my payment proof" },
    waCode: { fr: "code", ar: "الرمز", en: "code" }
  };

  // ---- petits outils (aussi utilisés par les réglages des sites) ----
  function coches(form, nom) {
    var res = [], c = form.querySelectorAll('input[name="' + nom + '"]');
    for (var i = 0; i < c.length; i++) if (c[i].checked) res.push(c[i].value);
    return res;
  }
  // téléphone tunisien : 8 chiffres (espaces et indicatif 216 acceptés) -> « 24321390 », sinon ""
  function telephoneTn(v) {
    var n = String(v || "").replace(/\D/g, "");
    if (n.length === 11 && n.indexOf("216") === 0) n = n.slice(3);
    return n.length === 8 ? n : "";
  }
  // téléphone international : 8 à 15 chiffres (on garde le « + » de l'indicatif)
  function telephoneInternational(v) {
    var brut = String(v || "").trim(), n = brut.replace(/\D/g, "");
    if (n.length < 8 || n.length > 15) return "";
    return (brut.charAt(0) === "+" || n.length > 8 ? "+" : "") + n;
  }
  // choix -> lien Telegram : même calcul que decoder_choix() des robots privés (listes TRIÉES, 5 cases par caractère, « x » = tous)
  function encoder(choix, liste) {
    if (choix.indexOf("tous") >= 0) return "x";
    var s = "";
    for (var k = 0; k < Math.ceil(liste.length / 5); k++) {
      var v = 0;
      for (var j = 0; j < 5; j++) if (5 * k + j < liste.length && choix.indexOf(liste[5 * k + j]) >= 0) v |= 1 << j;
      s += B32[v];
    }
    return s;
  }
  // code de commande : alphabet et longueur DU site (256 est un multiple de 32 : chaque caractère a la même chance)
  function nouveauCode(alphabet, longueur) {
    var t = new Uint8Array(longueur), c = "", k;
    try { crypto.getRandomValues(t); } catch (e) { for (k = 0; k < longueur; k++) t[k] = Math.floor(Math.random() * 256); }
    for (k = 0; k < longueur; k++) c += alphabet[t[k] % alphabet.length];
    return c;
  }
  function aujourdhui() { return new Date().toISOString().slice(0, 10); }
  function echapperRe(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  var PC = window.PassCommun = {
    version: VERSION, textes: TEXTES, cle: CLE, jours: JOURS, formspree: FORMSPREE, emailApi: EMAIL_API, whatsapp: WHATSAPP,
    coches: coches, telephoneTn: telephoneTn, telephoneInternational: telephoneInternational, encoder: encoder, nouveauCode: nouveauCode,
    brancher: brancher
  };
  window.ESSAI_ALERTES = { encoder: encoder };   // nom gardé : les tests des sites l'utilisent

  function brancher(R) {
    R = R || {};
    PC.reglage = R;
    var langues = R.langues || ["fr", "ar"];
    var ids = R.ids || {};
    var idForm = ids.form || "pass-form", idStatut = ids.statut || "pass-status", idApres = ids.apres || "apres-pass",
        idAttente = ids.attente || "commande-attente", idNouvelle = ids.nouvelle || "nouvelle-commande";
    var alphabet = (R.code && R.code.alphabet) || "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    var longueur = (R.code && R.code.longueur) || 6;
    var FORMAT = new RegExp("^[" + echapperRe(alphabet).replace(/-/g, "\\-") + "]{" + longueur + "}$");
    var emailAutoOn = R.emailAuto !== false;
    var gratuit = R.type === "alertes-gratuit";
    var modeEchec = R.echec || (R.type === "pass-code" ? "reessayer" : "continuer");
    var etapes = R.etapes || (gratuit ? ["nom", "telephone", "email", "conditions"] : ["nom", "telephone", "email", "formule", "conditions"]);

    function langue() { var l = document.documentElement.lang; return langues.indexOf(l) >= 0 ? l : langues[0]; }
    function choisir(o) { if (!o) return ""; var l = langue(); return o[l] != null ? o[l] : (o.fr != null ? o.fr : o.en); }
    function texte(cle) { return choisir((R.textes && R.textes[cle]) || TEXTES[cle]); }
    function affiche(brut, formule) { return R.code && R.code.affiche ? R.code.affiche(brut, formule) : brut; }
    function formuleLue(f) { var x = R.formules && R.formules[f]; return x && x[langue()] != null ? x[langue()] : (f || ""); }
    function nomSite() { return choisir(R.nomSite) || ""; }

    // message WhatsApp de la preuve : « Voici ma preuve de paiement — <site> — code <CODE> — <nom> — <formule> » (nom : jamais gardé)
    function lienWa(code, formule, nom) {
      var p = [texte("waDebut"), nomSite(), texte("waCode") + " " + code];
      if (nom) p.push(nom);
      if (formule) p.push(formuleLue(formule));
      return "https://wa.me/" + WHATSAPP + "?text=" + encodeURIComponent(p.join(" — "));
    }
    function emailAuto() {
      var x = document.querySelectorAll("[data-email-auto]");
      for (var i = 0; i < x.length; i++) x[i].hidden = !emailAutoOn;
    }
    // remplit toute la page : code (gros + motif), formule, liens WhatsApp, liens Telegram
    function remplir(cmd, nom) {
      var i, code = affiche(cmd.code, cmd.formule), x = document.querySelectorAll("[data-code]");
      for (i = 0; i < x.length; i++) x[i].textContent = code;
      x = document.querySelectorAll("[data-formule]");
      for (i = 0; i < x.length; i++) x[i].textContent = formuleLue(cmd.formule);
      x = document.querySelectorAll(R.selecteurWa || "a.btn-wa");
      for (i = 0; i < x.length; i++) x[i].setAttribute("href", lienWa(code, cmd.formule, nom));
      emailAuto();
      x = document.querySelectorAll("a[data-tg]");
      for (i = 0; i < x.length; i++) if (cmd.tg) x[i].setAttribute("href", cmd.tg);
      if (R.apresRemplir) R.apresRemplir({ code: code, brut: cmd.code, formule: cmd.formule, tg: cmd.tg || "", nom: nom || "", lienWa: lienWa });
    }
    function memoriser(cmd) {
      var m = { code: cmd.code, formule: cmd.formule, date: aujourdhui() };
      if (R.telegram) m.tg = cmd.tg || "";
      try { localStorage.setItem(CLE, JSON.stringify(m)); } catch (e) {}
    }
    function oublier() { try { localStorage.removeItem(CLE); } catch (e) {} }
    // commande gardée : code au bon format, formule lisible, lien Telegram à nous, moins de 60 jours ; sinon effacée
    function relire() {
      var c = null;
      try { c = JSON.parse(localStorage.getItem(CLE) || "null"); } catch (e) { oublier(); return null; }   // abîmée : effacée
      if (!c) return null;
      var t = Date.parse(String(c.date || "") + "T00:00:00Z");
      if (!FORMAT.test(c.code || "") || typeof c.formule !== "string" || !(t > 0) || Date.now() - t > JOURS * 864e5
          || (c.tg && !/^https:\/\/t\.me\//.test(c.tg))) { oublier(); return null; }
      return c;
    }
    window.PASS_COMMANDE = { cle: CLE, jours: JOURS, relire: relire };

    function envoyerEmail(d) {
      if (!emailAutoOn || !window.fetch) return;
      try {
        fetch(EMAIL_API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(d), keepalive: true })
          .catch(function () {});
      } catch (e) {}
    }

    function demarrer() {
      var form = document.getElementById(idForm);
      if (!form || form.getAttribute("data-branche")) return;
      form.setAttribute("data-branche", "1");
      emailAuto();
      var statut = document.getElementById(idStatut);
      var bouton = form.querySelector("button[type=submit]");
      var apres = document.getElementById(idApres);
      var attente = document.getElementById(idAttente);
      var enCours = null;                         // commande du formulaire (même code si l'envoi est refait)
      function dire(classe, t) { if (!statut) return; statut.className = classe; statut.textContent = typeof t === "string" ? t : choisir(t); }
      function champ(n) { return form.querySelector('[name="' + n + '"]'); }
      function val(n) { var x = champ(n); return x ? String(x.value || "").trim() : ""; }
      // état de la commande au retour ; classesEtat (facultatif) : classe CSS de la ligne selon l'état (ex. { attenteImpossible: "err" })
      function etatCommande(t) {
        var x = document.querySelectorAll("[data-etat-commande]");
        for (var i = 0; i < x.length; i++) { x[i].textContent = t ? texte(t) : ""; if (R.classesEtat) x[i].className = (t && R.classesEtat[t]) || ""; }
      }
      function fermerAttente() { if (attente) attente.hidden = true; if (apres) apres.hidden = true; form.hidden = false; etatCommande(""); }
      if (R.brancher) R.brancher({ form: form, champ: champ, val: val });

      // retour sur la page : la commande en attente est montrée à la place du formulaire
      // attendreRetour (facultatif) : promesse du site à attendre avant (ex. revérification du Pass déjà gardé) ;
      // si le visiteur a déjà envoyé le formulaire entre-temps, le retour n'est plus montré
      function retour() {
      if (form.hidden || enCours) return;
      var cmd = relire();
      if (cmd && R.dejaActif && R.dejaActif(cmd, affiche(cmd.code, cmd.formule))) { oublier(); cmd = null; }
      if (cmd && attente) {
        remplir(cmd);
        attente.hidden = false; form.hidden = true;
        if (R.apresAuRetour && apres) apres.hidden = false;   // facultatif : la page « Dernière étape » reste montrée sous le bandeau
        if (R.auRetour) R.auRetour({ cmd: cmd, code: affiche(cmd.code, cmd.formule), form: form, attente: attente, apres: apres });
        if (R.essayerCode) {                      // sites à code tapé : même vérification que « J'ai un code »
          etatCommande("verification");
          var essai;
          try { essai = R.essayerCode(affiche(cmd.code, cmd.formule), cmd); } catch (e) { essai = null; }
          if (essai && essai.then) essai.then(function (r) {
            var e = r && r.etat;
            if (e === "ok" || e === "expire") { oublier(); fermerAttente(); if (R.passOuvert) R.passOuvert(r); }
            else etatCommande(e === "inconnu" ? "attentePaiement" : "attenteImpossible");
          }, function () { etatCommande("attenteImpossible"); });
          else etatCommande("attenteImpossible");
        }
      }
      }
      var attendu = null;
      try { attendu = R.attendreRetour ? R.attendreRetour() : null; } catch (e) { attendu = null; }
      if (attendu && attendu.then) attendu.then(retour, retour); else retour();
      var nouvelle = document.getElementById(idNouvelle);
      if (nouvelle) nouvelle.addEventListener("click", function () {
        oublier(); enCours = null;
        fermerAttente();
        if (R.nouvelle) R.nouvelle({ form: form, champ: champ, val: val });
        var n = champ("nom"); if (R.focusNouvelle !== false && n && n.focus) n.focus();   // focusNouvelle: false = pas de curseur
      });

      form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (bouton && bouton.disabled) return;
        var c = { form: form, champ: champ, val: val, langue: langue(), nom: val("nom"), email: val("email"), extra: {} };
        c.tel = R.telephone === "international" ? telephoneInternational(val("telephone")) : telephoneTn(val("telephone"));
        var coche = form.querySelector('input[name="formule"]:checked');
        c.formule = coche ? coche.value : (R.formuleDefaut || "");
        if (R.lire) R.lire(c);
        // vérifications dans l'ordre du site : les 5 communes (noms) et celles du site (fonctions : null = bon, sinon { fr, ar, en, champ })
        for (var i = 0; i < etapes.length; i++) {
          var et = etapes[i], err = null, foc = null;
          if (typeof et === "function") { err = et(c); foc = err && err.champ; }
          else if (et === "nom") { if (!c.nom) { err = "nom"; foc = "nom"; } }
          else if (et === "telephone") { if (!c.tel) { err = R.telephone === "international" ? "telephoneInternational" : "telephone"; foc = "telephone"; } }
          else if (et === "email") {
            if (!c.email) { err = emailAutoOn ? "emailVide" : "emailVideSansAuto"; foc = "email"; }
            else if (!EMAIL_OK.test(c.email)) { err = "emailInvalide"; foc = "email"; }
          }
          else if (et === "formule") { if (!c.formule) err = "formule"; }
          else if (et === "conditions") { var cc = champ("conditions"); if (!cc || !cc.checked) err = "conditions"; }
          if (err) {
            dire("err", typeof err === "string" ? texte(err) : err);
            if (foc && champ(foc) && champ(foc).focus) champ(foc).focus();
            return;
          }
        }

        // formulaire valide : le code de commande est créé maintenant (le même si l'envoi doit être refait)
        if (!enCours || enCours.formule !== c.formule) enCours = { code: nouveauCode(alphabet, longueur), formule: c.formule, email: false };
        c.brut = enCours.code;
        c.code = affiche(c.brut, c.formule);
        c.tg = R.telegram ? (R.telegram(c) || "") : "";
        var cmdNouvelle = { code: c.brut, formule: c.formule, tg: c.tg };
        var nomWa = R.nomWa ? R.nomWa(c) : c.nom;
        var fini = function (robot) {
          remplir(cmdNouvelle, nomWa);            // code en gros, motif, WhatsApp pré-rempli (code + nom), « Ouvrir Telegram »
          if (!robot) memoriser(cmdNouvelle);     // le téléphone se souvient de la commande (rien de personnel)
          enCours = null;
          form.hidden = true;
          if (attente) attente.hidden = true;
          if (apres) { apres.hidden = false; if (apres.scrollIntoView) try { apres.scrollIntoView({ block: "start" }); } catch (x) {} }
          if (R.apresEnvoi) R.apresEnvoi(c);
        };
        var piege = champ("_gotcha");
        if (piege && piege.value) { fini(true); return; }   // rempli = robot : rien n'est envoyé ni gardé

        var page = champ("page"); if (page) page.value = location.href.split("#")[0];
        var donnees = new FormData(form);
        donnees.set("telephone", c.tel);
        if (R.formspree) R.formspree(donnees, c);
        donnees.set("code", c.code);              // code de commande (motif du paiement)
        // ligne prête pour le bouton d'activation du dépôt privé : le robot active CE code tel quel
        donnees.set("pour_activer", R.pourActiver ? R.pourActiver(c) : "nom: " + c.nom + " ; telephone: " + c.tel + " ; code: " + c.code);
        // e-mail automatique au client (code, prix, paiement, WhatsApp… ; langue de la page ; Ahmed en copie) : une fois par commande
        if (!enCours.email) {
          enCours.email = true;
          var j = { site: R.site, langue: c.langue, nom: c.nom, email: c.email, code: c.code, formule: c.formule };
          if (R.telegram) j.lien_telegram = c.tg;
          var plus = R.email ? R.email(c) : null;
          if (plus) for (var k in plus) if (Object.prototype.hasOwnProperty.call(plus, k)) j[k] = plus[k];
          envoyerEmail(j);
        }
        if (bouton) bouton.disabled = true;
        dire("", texte("envoi"));
        fetch(R.formspreeAdresse || FORMSPREE, { method: "POST", body: donnees, headers: { "Accept": "application/json" } })
          .then(function (r) {
            if (!r.ok) throw new Error("HTTP " + r.status);
            dire("ok", texte("merci"));
            fini(false);
          })
          .catch(function () {
            if (modeEchec === "continuer") { dire("", texte("echecContinuer")); fini(false); }
            else dire("err", texte("echecReessayer"));
          })
          .then(function () { if (bouton) bouton.disabled = false; });
      });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", demarrer);
    else demarrer();
    // jsdom / tests : DOMContentLoaded peut être relancé à la main ; le garde « data-branche » évite un double branchement
    document.addEventListener("DOMContentLoaded", demarrer);
  }
})();
