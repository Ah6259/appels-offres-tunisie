/* Inscription « Alertes Pro » (page abonnement/) — accord d'Ahmed du 06/10/2026.
   - Rien n'est envoyé sans clic sur « Envoyer mon inscription ».
   - Envoi à Formspree (formulaire mwlpakqj, le même que « Votre avis ») sans quitter la page.
   - Les métiers et gouvernorats cochés sont envoyés en UNE ligne chacun (ex. « btp-genie-civil, informatique »),
     prête à recopier dans le bouton GitHub « activer-abonne » du dépôt privé.
   - Après l'envoi : le formulaire est remplacé par la confirmation, les modes de paiement et les instructions Telegram.
   - Fichier externe : aucun script en ligne (CSP). Textes en français et en arabe selon la langue de la page. */
(function () {
  var ADRESSE = "https://formspree.io/f/mwlpakqj";
  var ar = function () { return document.documentElement.lang === "ar"; };
  var T = function (fr, a) { return ar() ? a : fr; };

  function coches(form, nom) {
    var res = [], c = form.querySelectorAll('input[name="' + nom + '"]');
    for (var i = 0; i < c.length; i++) if (c[i].checked) res.push(c[i].value);
    return res;
  }
  // téléphone tunisien : 8 chiffres (on accepte les espaces et l'indicatif 216)
  function telephone(v) {
    var n = String(v || "").replace(/\D/g, "");
    if (n.length === 11 && n.indexOf("216") === 0) n = n.slice(3);
    return n.length === 8 ? n : "";
  }

  // Essai IMMÉDIAT (14/10/2026, règle commune § 15) : même calcul que decoder_choix() du robot privé :
  // listes TRIÉES, 5 cases par caractère, « x » = tous
  var B32 = "0123456789abcdefghijklmnopqrstuv", ALPH = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
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
  function nouveauCode() {
    var t = new Uint8Array(6), c = "";
    try { crypto.getRandomValues(t); } catch (e) { for (var k = 0; k < 6; k++) t[k] = Math.floor(Math.random() * 256); }
    for (var i = 0; i < 6; i++) c += ALPH[t[i] % ALPH.length];
    return c;
  }
  window.ESSAI_ALERTES = { encoder: encoder };

  function brancher() {
    var form = document.getElementById("abo-form");
    if (!form || form.getAttribute("data-branche")) return;
    form.setAttribute("data-branche", "1");
    var statut = document.getElementById("abo-status");
    var bouton = form.querySelector("button[type=submit]");
    var apres = document.getElementById("apres-abo");
    var dire = function (classe, fr, a) { statut.className = classe; statut.textContent = T(fr, a); };

    // « Toute la Tunisie » et les gouvernorats un par un s'excluent
    var tous = document.getElementById("g-tous");
    form.addEventListener("change", function (e) {
      var c = e.target;
      if (!c || c.name !== "gouvernorats") return;
      var g = form.querySelectorAll('input[name="gouvernorats"]');
      for (var i = 0; i < g.length; i++) {
        if (c === tous && c.checked && g[i] !== tous) g[i].checked = false;
        if (c !== tous && c.checked && tous) tous.checked = false;
      }
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (bouton.disabled) return;
      var val = function (n) { var x = form.querySelector('[name="' + n + '"]'); return x ? String(x.value || "").trim() : ""; };
      var champ = function (n) { return form.querySelector('[name="' + n + '"]'); };
      var tel = telephone(val("telephone"));
      var metiers = coches(form, "metiers"), gouv = coches(form, "gouvernorats");
      if (!val("nom")) { dire("err", "Indiquez votre nom.", "اكتب اسمك."); champ("nom").focus(); return; }
      if (!val("entreprise")) { dire("err", "Indiquez le nom de votre entreprise.", "اكتب اسم مؤسستك."); champ("entreprise").focus(); return; }
      if (!tel) { dire("err", "Téléphone : 8 chiffres, par exemple 24 321 390.", "الهاتف: ⁦8⁩ أرقام، مثال ⁦24 321 390⁩."); champ("telephone").focus(); return; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(val("email"))) { dire("err", "Indiquez une adresse e-mail valide.", "اكتب بريدًا إلكترونيًا صحيحًا."); champ("email").focus(); return; }
      if (!metiers.length) { dire("err", "Cochez au moins un métier.", "اختر اختصاصًا واحدًا على الأقل."); return; }
      if (!gouv.length) { dire("err", "Cochez au moins un gouvernorat (ou « Toute la Tunisie »).", "اختر ولاية واحدة على الأقل (أو «كل الولايات»)."); return; }
      if (!champ("conditions").checked) { dire("err", "Cochez « J'accepte les conditions de l'abonnement ».", "يجب الموافقة على شروط الاشتراك."); return; }

      var code = nouveauCode();
      var lien = "https://t.me/" + form.getAttribute("data-robot") + "?start=e" + code + "_" +
        encoder(metiers, (form.getAttribute("data-metiers") || "").split(",")) + "_" + encoder(gouv, (form.getAttribute("data-gouv") || "").split(","));
      var fini = function () {
        var c = document.getElementById("abo-code"), o = document.getElementById("abo-ouvrir-tg");
        if (c) c.textContent = code;
        if (o && form.getAttribute("data-robot")) o.setAttribute("href", lien);
        // lien WhatsApp de la preuve de paiement : on ajoute le nom de l'entreprise au message prérempli
        var liens = document.querySelectorAll("#abo-preuve, #abo-preuve-apres");
        for (var i = 0; i < liens.length; i++) {
          var base = liens[i].getAttribute("data-texte") || "";
          liens[i].setAttribute("href", "https://wa.me/21624321390?text=" + encodeURIComponent(base + val("entreprise") + " — code " + code));
        }
        form.hidden = true;
        if (apres) { apres.hidden = false; if (apres.scrollIntoView) try { apres.scrollIntoView({ block: "start" }); } catch (x) {} }
      };
      var piege = champ("_gotcha");
      if (piege && piege.value) { fini(); return; }          // rempli = robot : rien n'est envoyé

      champ("page").value = location.href.split("#")[0];
      var donnees = new FormData(form);
      donnees.delete("metiers"); donnees.delete("gouvernorats");
      donnees.set("telephone", tel);
      donnees.set("metiers", metiers.join(", "));
      donnees.set("gouvernorats", gouv.join(", "));
      // ligne prête pour le bouton « activer-abonne » (dépôt privé)
      donnees.set("pour_activer", "nom: " + val("nom") + " (" + val("entreprise") + ") ; telephone: " + tel +
        " ; metiers: " + metiers.join(",") + " ; gouvernorats: " + gouv.join(","));
      donnees.set("code", code);                               // code de l'essai (motif du paiement)
      bouton.disabled = true;
      dire("", "Envoi…", "جارٍ الإرسال…");
      fetch(ADRESSE, { method: "POST", body: donnees, headers: { "Accept": "application/json" } })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          dire("ok", "Merci ! Votre inscription a bien été envoyée.", "شكرًا! تم إرسال تسجيلك.");
          fini();
        })
        .catch(function () {
          // l'essai ne dépend pas de cet envoi : le robot Telegram le crée seul ; on continue quand même
          dire("", "Inscription non envoyée (connexion), mais votre essai fonctionne : ouvrez Telegram ci-dessous.",
               "لم يُرسل التسجيل (الاتصال)، لكن تجربتك تعمل: افتح تيليغرام أسفله.");
          fini();
        })
        .then(function () { bouton.disabled = false; });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", brancher);
  else brancher();
})();
