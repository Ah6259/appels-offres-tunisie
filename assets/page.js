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
        <button class="langue" type="button">${T("العربية", "Français")}</button>
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
          <a href="${racine}a-propos/">${T("À propos et sources", "من نحن والمصادر")}</a>
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
  }

  function appliquer(l) {
    html.lang = l; html.dir = l === "ar" ? "rtl" : "ltr";
    try { localStorage.setItem("langue", l); } catch (e) {}
    cadre();
    document.dispatchEvent(new Event("langue"));
  }
  document.addEventListener("DOMContentLoaded", () => appliquer(langue));
})();
