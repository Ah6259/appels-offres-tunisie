// Page vidéo (21/10/2026, Ahmed : « pourquoi la vidéo ne se lance pas toute seule ? ») : les navigateurs interdisent le lancement
// automatique d'une vidéo AVEC le son ; elle se lance donc toute seule SANS le son, et « Activer le son » la reprend depuis le début
// avec le son. Écrit par tools/page_video (outil vidéos d'Ahmed) : ne pas modifier ici. Style posé par le script (CSP : pas de style en ligne).
(function () {
  "use strict";
  var v = document.querySelector(".video-lecteur"), b = document.querySelector(".btn-video-son");
  if (!v || !b) return;
  if (v.hasAttribute("muted")) v.muted = true;
  var st = { display: "block", margin: "-4px auto 14px", padding: "11px 22px", border: "0", borderRadius: "999px", background: "#1d1d1f",
             color: "#fff", font: "inherit", fontWeight: "700", fontSize: "1.05rem", cursor: "pointer", whiteSpace: "nowrap" };
  for (var k in st) b.style[k] = st[k];
  function cacher() { b.hidden = !v.muted; b.style.display = v.muted ? "block" : "none"; }
  b.addEventListener("click", function () {
    v.muted = false;
    try { v.currentTime = 0; } catch (e) { /* vidéo pas encore prête */ }
    var p = v.play();
    if (p && p.catch) p.catch(function () { /* refusé : les commandes de la vidéo restent là */ });
    cacher();
  });
  v.addEventListener("volumechange", cacher);
  var p = v.play();
  if (p && p.catch) p.catch(function () { /* lancement automatique bloqué : le bouton lance la vidéo avec le son */ });
  cacher();
})();
