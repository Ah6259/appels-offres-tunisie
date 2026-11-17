/* Page 404 COMMUNE des sites clicvia.com (outils communs/page-404, 17/11/2026, règle commune § 58 point 14).
   Ahmed : « Page introuvable » fait partir le visiteur. Donc, avant de le dire, la page CHERCHE l'adresse :
   1) sur ce site avec ou sans « / » final ; 2) sur nos autres sites (liste lue sur l'accueil de clicvia.com : un nouveau site est trouvé
   seul ; GitHub Pages répond « Access-Control-Allow-Origin: * »). Pendant la recherche : « Recherche de la page… ».
   Trouvée = renvoi direct ; sinon « Page introuvable » avec les boutons Accueil et Tous nos services (8 s au plus). */
(function () {
  var p = location.pathname, ici = location.origin;
  var titre = document.getElementById("titre"), texte = document.getElementById("texte"), ar = document.getElementById("texte-ar");
  if (!window.fetch || !window.Promise || p === "/" || p.length > 300) return;
  var fini = false, minuteur;
  var fin = function (trouve) {
    if (fini) return; fini = true; clearTimeout(minuteur);
    if (trouve) { location.replace(trouve + location.search + location.hash); return; }
    titre.textContent = "Page introuvable"; texte.textContent = "Cette adresse n'existe pas (ou plus)."; ar.textContent = "هذه الصفحة غير موجودة.";
  };
  titre.textContent = "Recherche de la page…"; texte.textContent = "Un instant : nous cherchons cette page."; ar.textContent = "لحظة من فضلك: نبحث عن هذه الصفحة.";
  minuteur = setTimeout(function () { fin(null); }, 8000);
  var essai = function (u) { return fetch(u, { method: "HEAD", mode: "cors", redirect: "follow" }).then(function (r) { return r.ok ? u : null; }, function () { return null; }); };
  var autre = /\/$/.test(p) ? p.replace(/\/+$/, "") : p + "/";
  essai(ici + autre).then(function (u) {
    if (u) return fin(u);
    return fetch("https://clicvia.com/", { cache: "no-store" }).then(function (r) { return r.text(); }).then(function (h) {
      var vus = {}, hotes = [], m, re = /https:\/\/([a-z0-9-]+)\.clicvia\.com/g;
      while ((m = re.exec(h))) { var b = "https://" + m[1] + ".clicvia.com"; if (m[1] !== "www" && b !== ici && !vus[b]) { vus[b] = 1; hotes.push(b); } }
      var reste = hotes.length; if (!reste) return fin(null);
      hotes.forEach(function (b) { essai(b + p).then(function (u) { if (u) fin(u); if (--reste === 0) fin(null); }); });
    });
  }).catch(function () { fin(null); });
})();
