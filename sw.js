// Service worker PRUDENT (installation sur le téléphone + secours hors connexion).
// - Pages HTML et données (JSON, dossiers data/ donnees/, fichiers sans ?v=) : RÉSEAU D'ABORD.
//   La réponse du réseau est toujours servie (et gardée en cache) ; le cache ne sert QUE si le réseau échoue.
// - CSS / JS / images versionnés (?v=) : cache puis mise à jour en arrière-plan (le ?v= change à chaque modification).
// - Jamais en cache : requêtes non-GET, autres sites (statistiques, formulaires, Telegram, polices…), pages exclues.
// Changer CACHE_VERSION pour vider le cache de tous les téléphones.
const CACHE_VERSION = "1";
const PREFIXE = "appels-offres-tunisie-";                       // propre à ce site : tous les sites partagent ah6259.github.io
const CACHE = PREFIXE + CACHE_VERSION;
const PORTEE = new URL("./", self.location.href).pathname;   // dossier du site, ex. /appels-offres-tunisie/
const EXCLUS = [];                          // chemins jamais mis en cache (relatifs au site)
const STATIQUE = /\.(css|js|png|jpe?g|svg|webp|gif|ico|woff2?)$/i;
const DONNEES = /\/(data|donnees)\/|\.json$/i;

const HORS_LIGNE = `<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Hors connexion</title>
<style>body{font-family:system-ui,sans-serif;max-width:32rem;margin:3rem auto;padding:0 1rem;text-align:center;color:#223}
p{line-height:1.6}button{font-size:1rem;padding:.6rem 1.2rem;border-radius:.5rem;border:1px solid #889;background:#fff}</style></head>
<body><h1>Hors connexion</h1><p>Cette page n'est pas encore enregistrée sur ce téléphone. Vérifiez votre connexion Internet puis réessayez.</p>
<p dir="rtl" lang="ar">لا يوجد اتصال بالإنترنت. هذه الصفحة غير محفوظة على هاتفك بعد. تحقّق من الاتصال ثم أعد المحاولة.</p>
<p><a href="${PORTEE}">Accueil · الرئيسية</a></p></body></html>`;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(noms => Promise.all(noms.filter(n => n.startsWith(PREFIXE) && n !== CACHE).map(n => caches.delete(n))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;                                  // formulaires, envois : jamais
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;                   // autres sites : on laisse passer
  if (!url.pathname.startsWith(PORTEE)) return;                      // autres sites d'Ahmed (même origine)
  const chemin = url.pathname.slice(PORTEE.length);
  if (EXCLUS.some(x => chemin.startsWith(x))) return;               // pages exclues : jamais en cache
  if (req.headers.has("range")) return;
  if (url.searchParams.has("v") && STATIQUE.test(url.pathname) && !DONNEES.test(url.pathname)) {
    e.respondWith(cachePuisMaj(e, req, url));
  } else {
    e.respondWith(reseauDabord(e, req));
  }
});

// Pages et données : le réseau d'abord, toujours ; le cache seulement si le réseau échoue.
async function reseauDabord(e, req) {
  try {
    const rep = await fetch(req);
    if (rep.ok && rep.status === 200 && rep.type === "basic") {
      const copie = rep.clone();
      e.waitUntil(caches.open(CACHE).then(c => c.put(req, copie)).catch(() => {}));
    }
    return rep;
  } catch (err) {
    const cache = await caches.open(CACHE);
    const garde = await cache.match(req) || (req.mode === "navigate" ? await cache.match(req, { ignoreSearch: true }) : undefined);
    if (garde) return garde;
    if (req.mode === "navigate") {
      return new Response(HORS_LIGNE, { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } });
    }
    return Response.error();
  }
}

// Fichiers versionnés (?v=) : la copie gardée tout de suite, mise à jour en arrière-plan.
async function cachePuisMaj(e, req, url) {
  const cache = await caches.open(CACHE);
  const garde = await cache.match(req);
  const maj = fetch(req).then(async rep => {
    if (rep.ok && rep.status === 200 && rep.type === "basic") {
      // on retire les anciennes versions du même fichier (autre ?v=)
      for (const r of await cache.keys()) {
        const u = new URL(r.url);
        if (u.pathname === url.pathname && u.search !== url.search) await cache.delete(r);
      }
      await cache.put(req, rep.clone());
    }
    return rep;
  });
  if (garde) { e.waitUntil(maj.catch(() => {})); return garde; }
  return maj;
}
