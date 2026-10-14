/* Section « Votre avis » (règle d'Ahmed du 05/10/2026 : sur chacun de ses sites).
   - Rien n'est envoyé sans clic sur « Envoyer ».
   - Envoi à Formspree (formulaire mwlpakqj, le même que le site des prix de l'eau) sans quitter la page.
   - Champs envoyés : note (facultative), message (obligatoire, 1000 caractères max), email (OBLIGATOIRE depuis le 15/10/2026, demande d'Ahmed : pouvoir répondre à chaque message),
     site (nom du site, champ caché), page (adresse de la page), _subject, _gotcha (piège à robots : vide).
   - Fichier externe : aucun script en ligne (CSP). Textes en français et en arabe selon la langue de la page. */
(function () {
  var ADRESSE = "https://formspree.io/f/mwlpakqj";
  var MAX = 1000;
  var ar = function () { return document.documentElement.lang === "ar"; };
  var T = function (fr, a) { return ar() ? a : fr; };

  // textes d'aide (placeholder) dans la langue de la page : data-ph-fr / data-ph-ar
  function placeholders() {
    var champs = document.querySelectorAll("#avis-form [data-ph-fr]");
    for (var i = 0; i < champs.length; i++) {
      var c = champs[i];
      c.setAttribute("placeholder", ar() ? (c.getAttribute("data-ph-ar") || "") : (c.getAttribute("data-ph-fr") || ""));
    }
  }

  function brancher() {
    var form = document.getElementById("avis-form");
    if (!form || form.getAttribute("data-branche")) return;
    form.setAttribute("data-branche", "1");
    var statut = document.getElementById("avis-status");
    var bouton = form.querySelector("button[type=submit]");
    var message = form.querySelector("[name=message]");
    var compte = document.getElementById("avis-compte");
    var dire = function (classe, fr, a) { statut.className = classe; statut.textContent = T(fr, a); };

    placeholders();
    if (window.MutationObserver)
      new MutationObserver(placeholders).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
    document.addEventListener("langue", placeholders);

    var compter = function () { if (compte) compte.textContent = message.value.length + " / " + MAX; };

    // 15/10/2026 (demande d'Ahmed) : e-mail obligatoire ; après l'envoi, le formulaire est remplacé DANS la carte « Votre avis »
    // par une confirmation bien visible (#avis-merci, créée ici si la page ne l'a pas)
    var M = function (fr, a, e) { return T(fr, a); };
    var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); };
    var boite = document.getElementById("avis-merci");
    if (!boite) {
      boite = document.createElement("div");
      boite.id = "avis-merci"; boite.className = "avis-merci"; boite.hidden = true; boite.tabIndex = -1;
      boite.setAttribute("role", "status"); boite.setAttribute("aria-live", "polite");
      form.parentNode.insertBefore(boite, form.nextSibling);
    }
    var merci = function (mail) {
      form.reset(); compter(); statut.className = ""; statut.textContent = "";
      boite.innerHTML = '<p class="avis-merci-titre">✅ ' + esc(M("Merci ! Votre avis a bien été envoyé.", "شكرًا! تم إرسال رأيك بنجاح.", "Thank you! Your feedback has been sent.")) + "</p><p>" + esc(M("Nous l’avons bien reçu et nous vous répondrons à l’adresse :", "وصلنا رأيك وسنرد عليك على العنوان:", "We have received it and will reply to:")) + ' <b dir="ltr">' + esc(mail) +
        '</b></p><button type="button" class="btn-avis-autre">' + esc(M("Envoyer un autre message", "أرسل رسالة أخرى", "Send another message")) + "</button>";
      boite.querySelector("button").addEventListener("click", function () { boite.hidden = true; form.hidden = false; message.focus(); });
      form.hidden = true; boite.hidden = false;
      try { boite.focus({ preventScroll: true }); boite.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (x) { /* ancien navigateur */ }
    };
    message.addEventListener("input", compter);
    compter();

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (bouton.disabled) return;
      var texte = (message.value || "").trim();
      if (!texte) {
        dire("err", "Écrivez votre message avant d'envoyer.", "اكتب رسالتك قبل الإرسال.");
        message.focus();
        return;
      }
      var champMail = form.querySelector("[name=email]"), mail = champMail ? (champMail.value || "").trim() : "";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(mail)) {
        statut.className = "err"; statut.textContent = M("Écrivez votre adresse e-mail (obligatoire) pour que nous puissions vous répondre.", "اكتب بريدك الإلكتروني (إجباري) لنتمكن من الرد عليك.", "Write your e-mail address (required) so we can reply to you.");
        if (champMail) champMail.focus();
        return;
      }
      if (texte.length > MAX) {
        dire("err", "Message trop long : " + MAX + " caractères au maximum.", "الرسالة طويلة جدًا: " + MAX + " حرف على الأكثر.");
        return;
      }
      var piege = form.querySelector("[name=_gotcha]");
      if (piege && piege.value) {                    // rempli = robot : on ne l'envoie pas
        merci(mail);
        return;
      }
      form.querySelector("[name=page]").value = location.href.split("#")[0];
      var donnees = new FormData(form);
      donnees.set("message", texte);
      bouton.disabled = true;
      dire("", "Envoi…", "جارٍ الإرسال…");
      fetch(ADRESSE, { method: "POST", body: donnees, headers: { "Accept": "application/json" } })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          merci(mail);
        })
        .catch(function () {
          dire("err", "Échec de l'envoi — vérifiez votre connexion et réessayez plus tard.", "تعذّر الإرسال — تحقّق من الاتصال وأعد المحاولة لاحقًا.");
        })
        .then(function () { bouton.disabled = false; });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", brancher);
  else brancher();
})();
