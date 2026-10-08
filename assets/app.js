/* Liste des appels d'offres : recherche par mots-clés (FR + AR), filtres métier + gouvernorat, tri,
   dates limites calculées avec la date du VISITEUR (une annonce expirée disparaît même si le robot s'est arrêté),
   étiquettes « J-7 … J-1 / Dernier jour », section « Clôturent bientôt ». */
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

  // Recherche : minuscules, sans accents ni voyelles arabes ; أإآٱ→ا, ة→ه, ى→ي
  const normaliser = t => (t || "").toLowerCase().normalize("NFKD").replace(/[\p{M}ـ]/gu, "")
    .replace(/[أإآٱ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي").replace(/[’'`]/g, " ").replace(/\s+/g, " ").trim();

  const PAR_PAGE = 15;          // cartes montrées d'abord (téléphone) ; « Afficher plus » pour la suite
  const RAPPEL = 7;             // étiquette « J-N » jusqu'à 7 jours avant la date limite
  let pret = false, cartes = [], prives = [], liste = null, montrees = PAR_PAGE, cible = "";

  function rappel(reste) {
    if (reste === null || reste < 0 || reste > RAPPEL) return null;
    if (reste === 0) return T("Dernier jour", "آخر يوم");
    return T(`J-${reste}`, reste === 1 ? "بقي يوم" : reste === 2 ? "بقي يومان" : `بقيت ${iso(reste)} أيام`);
  }

  function etatCartes(liste, jour) {
    liste.forEach(c => {
      const lim = c.dataset.limite;
      const reste = lim ? ecart(lim, jour) : null;
      c.dataset.expire = reste !== null && reste < 0 ? "1" : "";
      c.dataset.reste = reste === null ? "" : reste;
      c.classList.toggle("urgent", reste !== null && reste >= 0 && reste < 7);
      const s = c.querySelector(".reste");
      if (s) s.textContent = reste === null ? T("voir la fiche", "انظر البطاقة")
        : reste < 0 ? T("expiré", "انتهى الأجل")
        : reste === 0 ? T("aujourd'hui !", "اليوم!")
        : reste === 1 ? T("demain !", "غدًا!")
        : T(`dans ${reste} jours`, `بعد ${iso(reste)} يومًا`);
      const n = c.querySelector(".nouveau");
      if (n) n.hidden = !(c.dataset.pub && ecart(jour, c.dataset.pub) <= 1);
      const r = c.querySelector(".rappel"), txt = rappel(reste);
      if (r) {
        r.hidden = !txt;
        r.textContent = txt || "";
        r.classList.toggle("fort", reste !== null && reste <= 2);
      }
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

  // Texte cherché d'une carte : objet, résumé traduit, acheteur, métier et gouvernorat (FR + AR), numéro.
  // Calculé une seule fois, avant que les étiquettes de date (qui changent) soient écrites.
  const texteCarte = c => {
    if (c._q === undefined) {
      const copie = c.cloneNode(true);
      copie.querySelectorAll(".reste,.rappel,.nouveau,.officiel,.ao-infos > div > span").forEach(x => x.remove());
      c._q = normaliser(copie.textContent + " " + c.id);
    }
    return c._q;
  };

  function appliquer() {
    const jour = aujourdHui();
    etatCartes(cartes, jour);
    etatCartes(prives, jour);
    const fm = document.getElementById("f-metier"), fg = document.getElementById("f-gouv"), ft = document.getElementById("f-tri");
    const fq = document.getElementById("f-q");
    remplirOptions(fm, "metier");
    remplirOptions(fg, "gouv");
    if (ft) ft.querySelectorAll("option").forEach(o => { o.textContent = T(o.dataset.fr, o.dataset.ar); });
    if (fq) fq.placeholder = T(fq.dataset.fr, fq.dataset.ar);
    const m = fm ? fm.value : "", g = fg ? fg.value : "", tri = ft ? ft.value : "limite";
    const mots = normaliser(fq ? fq.value : "").split(" ").filter(Boolean);
    const garde = c => !c.dataset.expire && (!m || c.dataset.metier === m) && (!g || c.dataset.gouv === g) &&
      mots.every(x => texteCarte(c).includes(x));
    let visibles = 0;
    cartes.forEach(c => {
      const ok = garde(c);
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
    // une carte visée par l'adresse (#Tender-…) est toujours montrée, même au-delà des 15 premières
    tries.forEach(c => { c.hidden = !c.dataset.ok || (rang++ >= montrees && c.id !== cible); });
    const plus = document.getElementById("plus");
    if (plus) {
      const reste = visibles - Math.min(visibles, montrees);
      plus.hidden = reste <= 0;
      plus.textContent = T(`Afficher plus (${reste} autre${reste > 1 ? "s" : ""})`, `عرض المزيد (${iso(reste)})`);
    }
    // Entreprises privées : mêmes filtres, pas de pagination
    let nPrives = 0;
    prives.forEach(c => { const ok = garde(c); c.hidden = !ok; c.dataset.ok = ok ? "1" : ""; if (ok) nPrives++; });
    const bp = document.getElementById("prives");
    if (bp) bp.hidden = nPrives === 0;

    const compte = document.getElementById("compte");
    if (compte) {
      const u = compte.dataset;
      const libelle = u.un ? T(`${visibles} ${visibles > 1 ? u.pl : u.un}`, `${iso(visibles)} ${u.ar}`)
        : T(`${visibles} appel${visibles > 1 ? "s" : ""} d'offres ouvert${visibles > 1 ? "s" : ""}`, `${iso(visibles)} طلب عروض مفتوح`);
      compte.innerHTML = "";
      const sp = document.createElement("span");
      sp.textContent = libelle;
      compte.appendChild(sp);
      if (m || g || mots.length) {
        const b = document.createElement("button");
        b.type = "button"; b.id = "effacer"; b.textContent = T("Tout afficher", "عرض الكل");
        compte.appendChild(b);
      }
    }
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
    // Carte de la Tunisie : nombres recalculés avec la date du visiteur, seulement sur l'accueil (qui a TOUS les appels d'offres) ;
    // sur une page de gouvernorat la liste ne contient que ce gouvernorat : on garde les nombres du robot
    if (document.getElementById("f-gouv")) document.querySelectorAll(".tn-b[data-gouv] text").forEach(t => {
      t.textContent = ouvertes.filter(c => c.dataset.gouv === t.parentNode.dataset.gouv).length;
    });
    const rU = document.getElementById("r-urgent");
    if (rU) rU.querySelector("b").textContent = ouvertes.filter(c => c.classList.contains("urgent")).length;

    // « Clôturent bientôt » (accueil) : les 5 dates limites les plus proches, dans les 7 jours
    const bt = document.getElementById("bientot");
    if (bt) {
      const proches = ouvertes.filter(c => c.dataset.reste !== "" && +c.dataset.reste <= RAPPEL)
        .sort((a, b) => (+a.dataset.reste - +b.dataset.reste) || (+b.dataset.num - +a.dataset.num)).slice(0, 5);
      const ol = document.getElementById("bientot-liste");
      ol.innerHTML = "";
      const lang = document.documentElement.lang === "ar" ? "ar" : "fr";
      proches.forEach(c => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = "#" + c.id;
        const et = document.createElement("span");
        et.className = "rappel" + (+c.dataset.reste <= 2 ? " fort" : "");
        et.textContent = rappel(+c.dataset.reste);
        const ob = document.createElement("span");
        ob.className = "b-objet";
        const h = c.querySelector("h3");
        ob.textContent = h ? h.textContent : c.id;
        if (h) ob.dir = h.dir;
        const lieu = document.createElement("small");
        const pg = c.querySelector(`.pastille.gouv [data-l="${lang}"]`);
        lieu.textContent = pg ? pg.textContent : "";
        a.append(et, ob, lieu);
        li.appendChild(a);
        ol.appendChild(li);
      });
      bt.hidden = proches.length === 0;
    }

    // Avertissement daté : données anciennes (selon la date du visiteur) ou panne signalée par le robot
    const al = document.getElementById("alerte-panne");
    if (al) {
      const maj = (document.body.dataset.maj || "").slice(0, 10);
      const age = maj ? ecart(jour, maj) : 99;
      const panne = document.body.dataset.panne === "1";
      if (age >= 2 || panne) {
        al.classList.add("on");
        al.textContent = maj
          ? T(`⚠️ La source officielle n'a pas pu être lue depuis le ${fr(maj)} : la liste peut être incomplète. Vérifiez toujours sur le portail officiel.`,
              `⚠️ تعذّرت قراءة المصدر الرسمي منذ ${iso(fr(maj))}: قد تكون القائمة ناقصة. تثبّت دائمًا في البوابة الرسمية.`)
          : T("⚠️ Données indisponibles : consultez le portail officiel.", "⚠️ المعطيات غير متوفرة: راجع البوابة الرسمية.");
      } else al.classList.remove("on");
    }
  }

  // Lien direct vers une carte (#Tender-104049, depuis Telegram ou « Clôturent bientôt »)
  function allerA() {
    let id = "";
    try { id = decodeURIComponent((location.hash || "").slice(1)); } catch (e) { return; }
    const c = id && document.getElementById(id);
    if (!c || !c.classList.contains("ao") || c.parentNode !== liste) return;
    cible = id;
    appliquer();
    document.querySelectorAll(".ao.visee").forEach(x => x.classList.remove("visee"));
    c.classList.add("visee");
    if (c.scrollIntoView) c.scrollIntoView({ block: "center" });
  }

  document.addEventListener("langue", () => {
    if (!pret) {
      liste = document.getElementById("liste");
      if (!liste) return;
      cartes = Array.from(liste.querySelectorAll(".ao"));
      const lp = document.getElementById("liste-prives");
      prives = lp ? Array.from(lp.querySelectorAll(".ao")) : [];
      cartes.concat(prives).forEach(texteCarte);
      ["f-metier", "f-gouv", "f-tri"].forEach(id => {
        const s = document.getElementById(id);
        if (s) s.addEventListener("change", () => { montrees = PAR_PAGE; appliquer(); });
      });
      const fq = document.getElementById("f-q");
      if (fq) {
        if (params.get("q")) fq.value = params.get("q").slice(0, 100);
        fq.addEventListener("input", () => { montrees = PAR_PAGE; appliquer(); });
      }
      const plus = document.getElementById("plus");
      if (plus) plus.addEventListener("click", () => { montrees += PAR_PAGE; appliquer(); });
      document.addEventListener("click", e => {
        if (e.target.id !== "effacer") return;
        ["f-metier", "f-gouv", "f-q"].forEach(id => { const s = document.getElementById(id); if (s) s.value = ""; });
        montrees = PAR_PAGE;
        appliquer();
      });
      // Filtre dans l'adresse : ?metier=informatique&gouv=sfax&q=route
      [["f-metier", "metier"], ["f-gouv", "gouv"]].forEach(([id, p]) => {
        const s = document.getElementById(id), v = params.get(p);
        if (s && v && Array.from(s.options).some(o => o.value === v)) s.value = v;
      });
      window.addEventListener("hashchange", allerA);
      pret = true;
    }
    appliquer();
    if (location.hash) allerA();
  });
})();
