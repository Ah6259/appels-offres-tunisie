/* Section « Votre avis » (règle d'Ahmed du 05/10/2026 : sur chacun de ses sites).
   - Rien n'est envoyé sans clic sur « Envoyer ».
   - Envoi à Formspree (formulaire mwlpakqj, le même que le site des prix de l'eau) sans quitter la page.
   - Champs envoyés : note (facultative), message (obligatoire, 1000 caractères max), email (facultatif),
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
      if (texte.length > MAX) {
        dire("err", "Message trop long : " + MAX + " caractères au maximum.", "الرسالة طويلة جدًا: " + MAX + " حرف على الأكثر.");
        return;
      }
      var piege = form.querySelector("[name=_gotcha]");
      if (piege && piege.value) {                    // rempli = robot : on ne l'envoie pas
        form.reset(); compter();
        dire("ok", "Merci ! Votre avis a bien été envoyé.", "شكرًا! تم إرسال رأيك.");
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
          form.reset(); compter();
          dire("ok", "Merci ! Votre avis a bien été envoyé.", "شكرًا! تم إرسال رأيك.");
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
