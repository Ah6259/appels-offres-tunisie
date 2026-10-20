/* RECHERCHE « AU SON » — outil commun à TOUS les sites d'Ahmed (règle commune § 27, 18/10/2026).
   Ahmed : « Jerba et Djerba c'est pareil mais la recherche ne donne pas le même résultat ».
   Un nom tunisien s'écrit de plusieurs façons en lettres latines : on compare « au son », avec le MÊME calcul pour ce que le
   visiteur tape ET pour la liste où l'on cherche. Copier ce fichier tel quel dans assets/ (ne pas le modifier dans un site :
   le corriger ici puis recopier partout). Utilisation :
     const cle = sonRecherche.cle("Houmt Souk")            -> " humt suk "  (texte de la liste, calculé une fois)
     sonRecherche.trouve(" humt suk ", "houmet essouk")    -> true          (ce que tape le visiteur)
   Règles : Dj = J · Ou = W = U · Q = K · Sh = Ch · Ph = F · Y = I · lettres doublées · article collé (Essouk = Souk) ·
   el / al / l' / le / la / les · « e » ou « a » entre deux consonnes (Houmet = Houmt, Ghazela = Ghazala) · mots collés
   (Bousaid = Bou Said) · mot en cours de frappe sans « e »/« a » final. L'arabe est seulement normalisé (أ إ آ = ا, ة = ه, ى = ي). */
(function (racine) {
  function base(t) {
    return " " + String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .replace(/[ً-ٰٕـ]/g, "").replace(/[إأآٱ]/g, "ا").replace(/ى/g, "ي").replace(/ة/g, "ه").replace(/ؤ/g, "و").replace(/ئ/g, "ي")
      .replace(/([؀-ۿ])([a-z0-9])/g, "$1 $2").replace(/([a-z0-9])([؀-ۿ])/g, "$1 $2")   // latin et arabe collés -> deux mots (20/10/2026)
      .replace(/[^a-z0-9؀-ۿ]+/g, " ").trim() + " ";
  }
  function cle(t) {
    return base(t).replace(/ e([bcdfgjklmnpqrstvxz])\1/g, " $1").replace(/dj/g, "j").replace(/sh/g, "ch").replace(/ph/g, "f").replace(/q/g, "k")
      .replace(/ou/g, "u").replace(/w/g, "u").replace(/y/g, "i").replace(/([a-z])\1+/g, "$1")
      .replace(/ (el|al|l|le|la|les) /g, " ").replace(/ (el|al|l|le|la|les) /g, " ")
      .replace(/([bcdfghjklmnpqrstvxz])[ea](?=[bcdfghjklmnpqrstvxz])/g, "$1").replace(/ +/g, " ");
  }
  function mots(tape) {                       // mots de ce que tape le visiteur (le dernier peut être en cours de frappe)
    var m = cle(tape).trim().split(" ").filter(Boolean);
    if (m.length && m[m.length - 1].length > 1) m[m.length - 1] = m[m.length - 1].replace(/[ea]+$/, "");
    return m;
  }
  // vrai si TOUS les mots tapés commencent un mot de la liste, ou si les mots collés commencent une suite de mots (Bousaid)
  function trouve(cleListe, tape) {
    var m = mots(tape); if (!m.length) return true;
    if (m.every(function (x) { return cleListe.indexOf(" " + x) >= 0; })) return true;
    var colle = m.join(""); if (colle.length < 4) return false;
    var w = cleListe.trim().split(" ");
    return w.some(function (x, i) { return (x + (w[i + 1] || "") + (w[i + 2] || "")).indexOf(colle) === 0; });
  }
  var api = { cle: cle, mots: mots, trouve: trouve };
  if (typeof module === "object" && module.exports) module.exports = api; else racine.sonRecherche = api;
})(typeof window !== "undefined" ? window : this);
