/* Réglage d'Alertes appels d'offres (Alertes Pro) pour le parcours commun du Pass (assets/pass-commun.js, copie du module de
   projets-ahmed : « outils communs/pass-commun/ » ; NE PAS modifier pass-commun.js ici, voir son LISEZMOI.md). Page abonnement/ (FR)
   et ar/abonnement/ (AR). Ici seulement ce qui est PROPRE à ce site : nom, formules 1 mois / 1 an, format du code (6 caractères sans
   O/0/I/1 : celui des codes déjà vendus), entreprise, métiers, gouvernorats, lien Telegram avec les choix, ligne « pour_activer » du
   bouton « activer-abonne » du dépôt privé « appels-offres-abonnes », nom de l'entreprise dans le message WhatsApp.
   Fichier externe : aucun script en ligne (CSP). */
(function () {
  var PC = window.PassCommun;
  if (!PC) return;
  PC.brancher({
    site: "appels-offres",                          // clé du site dans email-clients/sites.json (e-mail automatique)
    type: "alertes",                                // alertes payées sur Telegram (pas de code à taper sur le site)
    langues: ["fr", "ar"],
    nomSite: { fr: "Alertes appels d'offres Tunisie", ar: "طلبات العروض تونس" },
    // E-mail automatique (A.17) EN SERVICE depuis le 25/11/2026 ; false = phrases [data-email-auto] cachées et rien envoyé
    emailAuto: true,
    ids: { form: "abo-form", statut: "abo-status", apres: "apres-abo", attente: "abo-attente", nouvelle: "abo-nouvelle" },
    code: { alphabet: "ABCDEFGHJKLMNPQRSTUVWXYZ23456789", longueur: 6 },
    formules: { "1 mois": { ar: "شهر" }, "1 an": { ar: "سنة" } },
    formuleDefaut: "1 mois",
    etapes: ["nom",
      function (c) { return c.val("entreprise") ? null : { fr: "Indiquez le nom de votre entreprise.", ar: "اكتب اسم مؤسستك.", champ: "entreprise" }; },
      "telephone", "email",
      function (c) { return c.extra.metiers.length ? null : { fr: "Cochez au moins un métier.", ar: "اختر اختصاصًا واحدًا على الأقل." }; },
      function (c) { return c.extra.gouv.length ? null : { fr: "Cochez au moins un gouvernorat (ou « Toute la Tunisie »).", ar: "اختر ولاية واحدة على الأقل (أو «كل الولايات»)." }; },
      "formule", "conditions"],
    // « Toute la Tunisie » et les gouvernorats un par un s'excluent
    brancher: function (p) {
      var form = p.form, tous = document.getElementById("g-tous");
      form.addEventListener("change", function (e) {
        var c = e.target;
        if (!c || c.name !== "gouvernorats") return;
        var g = form.querySelectorAll('input[name="gouvernorats"]');
        for (var i = 0; i < g.length; i++) {
          if (c === tous && c.checked && g[i] !== tous) g[i].checked = false;
          if (c !== tous && c.checked && tous) tous.checked = false;
        }
      });
    },
    // champs du site : métiers et gouvernorats cochés
    lire: function (c) {
      c.extra.metiers = PC.coches(c.form, "metiers");
      c.extra.gouv = PC.coches(c.form, "gouvernorats");
    },
    // lien Telegram qui contient les choix (vide si le robot n'est pas réglé) : le robot crée l'inscription, en attente du paiement
    telegram: function (c) {
      var f = c.form, robot = f.getAttribute("data-robot");
      if (!robot) return "";
      return "https://t.me/" + robot + "?start=e" + c.code + "_" +
        PC.encoder(c.extra.metiers, (f.getAttribute("data-metiers") || "").split(",")) + "_" +
        PC.encoder(c.extra.gouv, (f.getAttribute("data-gouv") || "").split(","));
    },
    // Formspree : métiers et gouvernorats en UNE ligne chacun (ex. « btp-genie-civil, informatique ») ; « pour_activer » réservé ici pour
    // garder l'ordre des champs de toujours (pour_activer puis code ; le module le remplit ensuite)
    formspree: function (d, c) {
      d.delete("metiers"); d.delete("gouvernorats");
      d.set("metiers", c.extra.metiers.join(", "));
      d.set("gouvernorats", c.extra.gouv.join(", "));
      d.set("pour_activer", "");
    },
    // ligne prête pour le bouton « activer-abonne » (dépôt privé)
    pourActiver: function (c) {
      return "nom: " + c.nom + " (" + c.val("entreprise") + ") ; telephone: " + c.tel + " ; metiers: " + c.extra.metiers.join(",") +
        " ; gouvernorats: " + c.extra.gouv.join(",") + " ; code: " + c.code;
    },
    // champs du site dans la demande d'e-mail automatique (noms attendus par verifier() du service, sites.json « champs »)
    email: function (c) { return { entreprise: c.val("entreprise"), metiers: c.extra.metiers, gouvernorats: c.extra.gouv }; },
    // message WhatsApp de la preuve : nom de l'entreprise (sinon le nom) — jamais gardé par le téléphone
    nomWa: function (c) { return c.val("entreprise") || c.nom; }
  });
})();
