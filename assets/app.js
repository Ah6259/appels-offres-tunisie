/* Liste des appels d'offres : filtres métier + gouvernorat, tri, dates limites calculées
   avec la date du VISITEUR (une annonce expirée disparaît même si le robot s'est arrêté). */
(function () {
  const JOUR = 86400000;
  const params = new URLSearchParams(location.search);

  // Date du visiteur (AAAA-MM-JJ). ?jour=AAAA-MM-JJ sert aux tests.
  function aujourdHui() {
    const p = params.get("jour");
    if (p && /^\d{4}-\d{2}-\d{2}$/.test(p)) return p;
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }
  const ecart = (a, b) => Math.round((Date.parse(a + "T00:00:00Z") - Date.parse(b + "T00:00:00Z")) / JOUR);
  const fr = d => `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;
  const jm = d => `${d.slice(8, 10)}/${d.slice(5, 7)}`;

  const PAR_PAGE = 15;          // cartes montrées d'abord (téléphone) ; « Afficher plus » pour la suite
  let pret = false, cartes = [], liste = null, montrees = PAR_PAGE;

  function etatCartes(jour) {
    cartes.forEach(c => {
      const lim = c.dataset.limite;
      const reste = lim ? ecart(lim, jour) : null;
      c.dataset.expire = reste !== null && reste < 0 ? "1" : "";
      c.classList.toggle("urgent", reste !== null && reste >= 0 && reste < 7);
      const s = c.querySelector(".reste");
      if (s) s.textContent = reste === null ? T("voir la fiche", "انظر البطاقة")
        : reste < 0 ? T("expiré", "انتهى الأجل")
        : reste === 0 ? T("aujourd'hui !", "اليوم!")
        : reste === 1 ? T("demain !", "غدًا!")
        : T(`dans ${reste} jours`, `بعد ${iso(reste)} يومًا`);
      const n = c.querySelector(".nouveau");
      if (n) n.hidden = !(c.dataset.pub && ecart(jour, c.dataset.pub) <= 1);
    });
  }

  function remplirOptions(sel, cle) {
    if (!sel) return;
    const ouvertes = cartes.filter(c => !c.dataset.expire);
    sel.querySelectorAll("option").forEach(o => {
      const n = o.value ? ouvertes.filter(c => c.dataset[cle] === o.value).length : ouvertes.length;
      o.textContent = T(o.dataset.fr, o.dataset.ar) + " (" + n + ")";
    });
  }

  function appliquer() {
    const jour = aujourdHui();
    etatCartes(jour);
    const fm = document.getElementById("f-metier"), fg = document.getElementById("f-gouv"), ft = document.getElementById("f-tri");
    remplirOptions(fm, "metier");
    remplirOptions(fg, "gouv");
    if (ft) ft.querySelectorAll("option").forEach(o => { o.textContent = T(o.dataset.fr, o.dataset.ar); });
    const m = fm ? fm.value : "", g = fg ? fg.value : "", tri = ft ? ft.value : "limite";
    let visibles = 0;
    cartes.forEach(c => {
      const ok = !c.dataset.expire && (!m || c.dataset.metier === m) && (!g || c.dataset.gouv === g);
      c.dataset.ok = ok ? "1" : "";
      if (ok) visibles++;
    });
    // Tri : date limite la plus proche d'abord (sans date à la fin), ou plus récents d'abord
    const tries = cartes.slice().sort((a, b) => {
      if (tri === "recent") return (b.dataset.pub || "").localeCompare(a.dataset.pub || "") || (+b.dataset.num - +a.dataset.num);
      return (a.dataset.limite || "9999").localeCompare(b.dataset.limite || "9999") || (+b.dataset.num - +a.dataset.num);
    });
    tries.forEach(c => liste.appendChild(c));
    let rang = 0;
    tries.forEach(c => { c.hidden = !c.dataset.ok || rang++ >= montrees; });
    const plus = document.getElementById("plus");
    if (plus) {
      const reste = visibles - Math.min(visibles, montrees);
      plus.hidden = reste <= 0;
      plus.textContent = T(`Afficher plus (${reste} autre${reste > 1 ? "s" : ""})`, `عرض المزيد (${iso(reste)})`);
    }

    const compte = document.getElementById("compte");
    if (compte) compte.innerHTML = `<span>${T(`${visibles} appel${visibles > 1 ? "s" : ""} d'offres ouvert${visibles > 1 ? "s" : ""}`,
      `${iso(visibles)} طلب عروض مفتوح`)}</span>` + ((m || g) ? `<button type="button" id="effacer">${T("Tout afficher", "عرض الكل")}</button>` : "");
    const vide = document.getElementById("vide");
    if (vide) vide.hidden = visibles > 0;

    // Résumé du jour (accueil)
    const ouvertes = cartes.filter(c => !c.dataset.expire);
    const rN = document.getElementById("r-nouveaux");
    if (rN) {
      const pubs = ouvertes.map(c => c.dataset.pub).filter(Boolean).sort();
      const dernier = pubs[pubs.length - 1] || "";
      const auj = ouvertes.filter(c => c.dataset.pub === jour).length;
      const jourAff = auj ? jour : dernier;
      const n = auj || ouvertes.filter(c => c.dataset.pub === dernier && dernier).length;
      rN.querySelector("b").textContent = n;
      rN.querySelector("span").textContent = auj ? T("nouveaux aujourd'hui", "جديدة اليوم")
        : dernier ? T(`nouveaux le ${jm(jourAff)}`, `جديدة يوم ${iso(jm(jourAff))}`) : T("nouveaux", "جديدة");
    }
    const rO = document.getElementById("r-ouverts");
    if (rO) rO.querySelector("b").textContent = ouvertes.length;
    // Carte de la Tunisie : nombres recalculés avec la date du visiteur
    document.querySelectorAll(".tn-b[data-gouv] text").forEach(t => {
      t.textContent = ouvertes.filter(c => c.dataset.gouv === t.parentNode.dataset.gouv).length;
    });
    const rU = document.getElementById("r-urgent");
    if (rU) rU.querySelector("b").textContent = ouvertes.filter(c => c.classList.contains("urgent")).length;

    // Avertissement daté : données anciennes (selon la date du visiteur) ou panne signalée par le robot
    const al = document.getElementById("alerte-panne");
    if (al) {
      const maj = (document.body.dataset.maj || "").slice(0, 10);
      const age = maj ? ecart(jour, maj) : 99;
      const panne = document.body.dataset.panne === "1";
      if (age >= 2 || panne) {
        al.classList.add("on");
        al.textContent = maj
          ? T(`⚠️ La source officielle n'a pas pu être lue depuis le ${fr(maj)} : la liste peut être incomplète. Vérifiez toujours sur le portail de la HAICOP.`,
              `⚠️ تعذّرت قراءة المصدر الرسمي منذ ${iso(fr(maj))}: قد تكون القائمة ناقصة. تثبّت دائمًا في بوابة الهيئة العليا للطلب العمومي.`)
          : T("⚠️ Données indisponibles : consultez le portail de la HAICOP.", "⚠️ المعطيات غير متوفرة: راجع بوابة الهيئة العليا للطلب العمومي.");
      } else al.classList.remove("on");
    }
  }

  document.addEventListener("langue", () => {
    if (!pret) {
      liste = document.getElementById("liste");
      if (!liste) return;
      cartes = Array.from(liste.querySelectorAll(".ao"));
      ["f-metier", "f-gouv", "f-tri"].forEach(id => {
        const s = document.getElementById(id);
        if (s) s.addEventListener("change", () => { montrees = PAR_PAGE; appliquer(); });
      });
      const plus = document.getElementById("plus");
      if (plus) plus.addEventListener("click", () => { montrees += PAR_PAGE; appliquer(); });
      document.addEventListener("click", e => {
        if (e.target.id !== "effacer") return;
        ["f-metier", "f-gouv"].forEach(id => { const s = document.getElementById(id); if (s) s.value = ""; });
        montrees = PAR_PAGE;
        appliquer();
      });
      // Filtre dans l'adresse : ?metier=informatique&gouv=sfax
      [["f-metier", "metier"], ["f-gouv", "gouv"]].forEach(([id, p]) => {
        const s = document.getElementById(id), v = params.get(p);
        if (s && v && Array.from(s.options).some(o => o.value === v)) s.value = v;
      });
      pret = true;
    }
    appliquer();
  });
})();
