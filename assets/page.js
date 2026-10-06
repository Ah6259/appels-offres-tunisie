/* Langue (français / arabe), en-tête et pied de page communs, petites fonctions */
(function () {
  const html = document.documentElement;
  const racine = html.dataset.racine || "";
  let langue = "fr";
  try { langue = localStorage.getItem("langue") || (navigator.language || "").startsWith("ar") && "ar" || "fr"; } catch (e) {}
  const demande = new URLSearchParams(location.search).get("lang");
  if (demande === "ar" || demande === "fr") langue = demande;

  window.T = (fr, ar) => html.lang === "ar" ? ar : fr;
  // Nombres et dates isolés dans un texte arabe (U+2066 … U+2069)
  window.iso = t => "⁦" + t + "⁩";

  function cadre() {
    const e = document.getElementById("entete");
    if (e) e.innerHTML = `
      <div class="wrap">
        <a class="logo" href="${racine || "./"}">
          <img class="logo-mark" src="${racine}assets/logo.svg" alt="" width="34" height="34">
          <span class="logo-nom">${T("Alertes appels d'offres", "تنبيهات طلبات العروض")}
            <small>${T("Tunisie · source officielle HAICOP", "تونس · المصدر الرسمي: الهيئة العليا للطلب العمومي")}</small></span>
        </a>
        <div class="entete-boutons">
          <a class="entete-pro" href="${racine}abonnement/">${T("Alertes Pro", "تنبيهات Pro")}</a>
          <button class="partager" type="button" aria-label="${T("Partager cette page", "شارك هذه الصفحة")}" title="${T("Partager", "شارك")}"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg></button>
          <button class="langue" type="button">${T("العربية", "Français")}</button>
        </div>
      </div>`;
    const p = document.getElementById("pied");
    const maj = document.body.dataset.majTexte || "";
    if (p) p.innerHTML = `
      <div class="wrap">
        <div class="pied-logo"><img src="${racine}assets/logo.svg" alt="" width="24" height="24"> ${T("Alertes appels d'offres Tunisie", "تنبيهات طلبات العروض تونس")}</div>
        <nav>
          <a href="${racine || "./"}">${T("Tous les appels d'offres", "كل طلبات العروض")}</a>
          <a href="${racine}#metiers">${T("Par métier", "حسب الاختصاص")}</a>
          <a href="${racine}#gouvernorats">${T("Par gouvernorat", "حسب الولاية")}</a>
          <a href="${racine}encheres/">${T("Ventes aux enchères", "البيوعات بالمزاد")}</a>
          <a href="${racine}publier/">${T("Publier un appel d'offres", "نشر طلب عروض")}</a>
          <a href="${racine}abonnement/">${T("Alertes Pro (abonnement)", "تنبيهات Pro (اشتراك)")}</a>
          <a href="${racine}a-propos/">${T("À propos et sources", "من نحن والمصادر")}</a>
          <a href="${racine}#avis">${T("Votre avis", "رأيك")}</a>
        </nav>
        <p>${T(`Source : <a href="https://www.marchespublics.gov.tn/fr/appels-doffres" rel="noopener">HAICOP — Haute Instance de la Commande Publique</a> (marchespublics.gov.tn). Chaque annonce renvoie à sa fiche officielle.`,
               `المصدر: <a href="https://www.marchespublics.gov.tn/ar/appels-doffres" rel="noopener">الهيئة العليا للطلب العمومي</a> (${iso("marchespublics.gov.tn")}). كل إعلان مرفق برابط بطاقته الرسمية.`)}</p>
        ${maj ? `<p>${T("Dernière lecture de la source : ", "آخر قراءة للمصدر: ")}${iso(maj)}</p>` : ""}
        <p>${T("Ce site n'est pas officiel : résumés indicatifs, seule la fiche officielle fait foi. Les noms des organismes appartiennent à leurs propriétaires.",
               "هذا الموقع ليس رسميًا: ملخصات للإرشاد فقط، والبطاقة الرسمية هي المرجع الوحيد. أسماء الهياكل ملك لأصحابها.")}</p>
        <p>© 2026 ${T("Alertes appels d'offres Tunisie — tous droits réservés.", "تنبيهات طلبات العروض تونس — جميع الحقوق محفوظة.")}</p>
      </div>`;
    document.querySelectorAll(".langue").forEach(b =>
      b.addEventListener("click", () => appliquer(html.lang === "ar" ? "fr" : "ar")));
    // bouton Partager (demande d'Ahmed) : menu de partage du téléphone, sinon WhatsApp avec le lien de la page
    document.querySelectorAll(".partager").forEach(b => b.addEventListener("click", async () => {
      const url = location.href.split("#")[0].replace(/[?&]lang=(fr|ar)/, ""), titre = document.title.split(" | ")[0];
      try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: "partage" + location.pathname.replace("/appels-offres-tunisie/", "/"), title: "Partage", event: true }); } catch (e) {}
      { const v = window.VIDEO_PRESENTATION(); return window.partagerVideo(v.url, v.nom, titre, url); }
    }));
  }

  function appliquer(l) {
    html.lang = l; html.dir = l === "ar" ? "rtl" : "ltr";
    try { localStorage.setItem("langue", l); } catch (e) {}
    cadre();
    document.dispatchEvent(new Event("langue"));
  }
  document.addEventListener("DOMContentLoaded", () => appliquer(langue));

  // ---- Protection légère contre la copie (sans gêner les visiteurs) -------------------------
  // 1) Pas d'affichage dans le cadre (iframe) d'un autre site.
  try {
    if (window.top !== window.self && window.top.location.hostname !== location.hostname) window.top.location = location.href;
  } catch (e) { try { window.top.location = location.href; } catch (e2) {} }
  // 2) Images et photos : ni clic droit ni glisser-déposer.
  const estImage = t => t && t.closest && t.closest("img, svg, .hero-photo, .carte-tn");
  document.addEventListener("contextmenu", e => { if (estImage(e.target) && !e.target.closest("a, input, textarea")) e.preventDefault(); });
  document.addEventListener("dragstart", e => { if (estImage(e.target)) e.preventDefault(); });
  // 3) Texte copié depuis une carte : on ajoute la source et la mention « tous droits réservés ».
  document.addEventListener("copy", e => {
    const sel = window.getSelection ? String(window.getSelection()) : "";
    const n = window.getSelection && window.getSelection().anchorNode;
    const el = n && (n.nodeType === 1 ? n : n.parentElement);
    if (!sel || !el || !el.closest || !el.closest(".ao, .liste, main") || el.closest("input, textarea")) return;
    if (!e.clipboardData) return;
    e.clipboardData.setData("text/plain", sel + "\n\nSource : " + location.href.split("#")[0] + " — © Alertes appels d'offres Tunisie, tous droits réservés.");
    e.preventDefault();
  });
})();

/* Installation sur le téléphone : service worker PRUDENT (sw.js : réseau d'abord pour les pages et les données).
   Seulement en https (jamais en file: pendant les tests locaux). */
if ("serviceWorker" in navigator && location.protocol === "https:") {
  window.addEventListener("load", () => {
    try { navigator.serviceWorker.register("/appels-offres-tunisie/sw.js", { scope: "/appels-offres-tunisie/" }).catch(() => {}); } catch (e) { /* rien : le site marche sans */ }
  });
}

/* >>> vidéo de présentation (fabriquée par l'outil vidéos d'Ahmed) */
// Vidéo à partager : anglais par défaut sur le site des conférences (version française si la page est en français).
window.VIDEO_PRESENTATION = function () {
  var fr = false && document.documentElement.lang === "fr";
  return { url: "/appels-offres-tunisie/assets/video/presentation" + (fr ? "-fr" : "") + ".mp4", nom: "appels-offres-tunisie" + (fr ? "-fr" : "") + ".mp4" };
};
/* Partage de la vidéo de présentation (demande d'Ahmed, octobre 2026) : le bouton « Partager » envoie la VIDÉO + le lien
   (dans le texte) quand le téléphone sait partager un fichier (Instagram, Facebook, TikTok, WhatsApp…) ; sinon le lien
   seul (menu de partage du téléphone, sinon WhatsApp). « Préparation de la vidéo… » pendant le téléchargement ; si le
   téléphone refuse le partage après l'attente (geste trop ancien), la vidéo reste prête : un second toucher la partage. */
window.partagerVideo = (function () {
  var pret = null;                                   // { cle, fichier } : vidéo déjà téléchargée
  function langue() { return document.documentElement.lang || "fr"; }
  function M(fr, en, ar) { var l = langue(); return l === "ar" ? ar : l === "en" ? en : fr; }
  function message(texte) {
    var m = document.getElementById("partage-msg");
    if (!texte) { if (m) m.hidden = true; return; }
    if (!m) { m = document.createElement("div"); m.id = "partage-msg"; m.className = "partage-msg"; m.setAttribute("role", "status"); document.body.appendChild(m); }
    m.textContent = texte; m.hidden = false;
  }
  function lienSeul(titre, url) {
    if (navigator.share) {
      return navigator.share({ title: titre, text: titre, url: url }).then(function () { return "lien"; }, function (e) {
        if (e && e.name === "AbortError") return "annule";
        window.open("https://wa.me/?text=" + encodeURIComponent(titre + " " + url), "_blank", "noopener"); return "whatsapp";
      });
    }
    window.open("https://wa.me/?text=" + encodeURIComponent(titre + " " + url), "_blank", "noopener");
    return Promise.resolve("whatsapp");
  }
  return function (video, nomFichier, titre, url) {
    var possible = false;
    try { possible = !!(navigator.share && navigator.canShare && window.File && window.fetch && navigator.canShare({ files: [new File([""], nomFichier, { type: "video/mp4" })] })); } catch (e) {}
    if (!possible) return lienSeul(titre, url);
    var etape = (pret && pret.cle === video) ? Promise.resolve() : (function () {
      message(M("Préparation de la vidéo…", "Preparing the video…", "جارٍ تحضير الفيديو…"));
      return fetch(video).then(function (r) {
        if (!r.ok) throw new Error("vidéo absente");
        return r.blob();
      }).then(function (b) {
        var f = new File([b], nomFichier, { type: "video/mp4" });
        if (!navigator.canShare({ files: [f] })) throw new Error("fichier refusé");
        pret = { cle: video, fichier: f };
      });
    })();
    return etape.then(function () {
      return navigator.share({ files: [pret.fichier], title: titre, text: titre + " " + url });
    }).then(function () { message(""); return "video"; }, function (e) {
      if (e && e.name === "AbortError") { message(""); return "annule"; }
      if (e && e.name === "NotAllowedError" && pret && pret.cle === video) {
        message(M("Vidéo prête : touchez encore « Partager »", "Video ready: tap “Share” again", "الفيديو جاهز: المس « شارك » مرة أخرى"));
        setTimeout(function () { message(""); }, 6000); return "pret";
      }
      message(""); return lienSeul(titre, url);
    });
  };
})();
// Lien discret « Vidéo de présentation » en bas de l'accueil et de À propos (pour la regarder, la télécharger, la publier).
(function () {
  function poser() {
    var p = location.pathname.replace(/index\.html$/, "");
    if (p !== "/appels-offres-tunisie/" && p !== "/appels-offres-tunisie/a-propos/") return;
    var el = document.getElementById("lien-video");
    if (!el) {
      el = document.createElement("p"); el.id = "lien-video"; el.className = "lien-video";
      var a = document.createElement("a"); el.appendChild(a);
      var m = document.querySelector("main"); if (m) m.insertAdjacentElement("afterend", el); else document.body.appendChild(el);
    }
    var l = document.documentElement.lang, lien = el.firstChild;
    lien.href = window.VIDEO_PRESENTATION().url;
    lien.textContent = l === "ar" ? "الفيديو التقديمي" : l === "en" ? "Presentation video" : "Vidéo de présentation";
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { setTimeout(poser, 0); }); else setTimeout(poser, 0);
  document.addEventListener("langue", function () { setTimeout(poser, 0); });
})();
/* <<< vidéo de présentation */
