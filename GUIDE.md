# Guide — les étapes de création d'« Alertes appels d'offres Tunisie »

Guide réutilisable pour créer un autre site du même genre. Une ligne par étape, dans l'ordre.

## 04/10/2026 — Étude de la source
1. **TUNEPS** testé : échanges chiffrés → non utilisé. Source retenue : portail officiel de la **HAICOP**.
2. **robots.txt** de la HAICOP : tous les robots autorisés ; charte d'utilisation vide. Preuves datées sauvegardées
   (HTML, PDF, empreintes SHA-256) hors du dépôt.
3. **Robot de lecture** `lire_haicop.py` : Python seul, 1 page / 2,5 s, nom de robot honnête, mémoire des fiches déjà lues,
   classement par métier (mots-clés FR + AR) et par gouvernorat.
4. Test « GitHub peut-il lire le portail ? » : oui (codes 200, pas de blocage).

## 05/10/2026 — Construction du site (local, pas encore publié)
5. **Constructeur** `robot/construire_site.py` : pages statiques (accueil, 10 métiers, 26 gouvernorats, à propos), sitemap.
6. **Style** repris d'Outils pratiques Tunisie (cartes, bandeau dégradé ; plus de badges sans lien depuis le 06/10/2026), couleur ardoise.
7. **Français + arabe** dans la même page ; nombres et dates isolés (U+2066…U+2069) ; objets laissés dans leur langue.
8. **Dates selon le téléphone du visiteur** : annonces expirées masquées, rouge à moins de 7 jours, « dans N jours ».
9. **Robustesse** : sauvegarde des données, panne = jamais « vide », bandeau daté, état `etat-source.json`.
10. **Robot de lecture renforcé** : format changé, liste < 30 %, erreurs réseau = panne enregistrée (plus de plantage).
11. **Images SVG maison** : illustration du bandeau, une icône par métier, carte de la Tunisie à bulles.
12. **Image d'aperçu** 1200 × 630 et icônes (favicon, iPhone) fabriquées avec Chrome sans écran.
13. **Tests** : `test_site.mjs` (jsdom, pages chargées comme un navigateur) et `test_pannes.py` (portail simulé) ;
    **sabotages volontaires** : 4 sur le site, 2 sur les robots → tous détectés.
14. **Captures téléphone** 340/390 px en français et en arabe → corrections (langue cachée visible, date coupée,
    menu de tri en français, bouton arabe sur 2 lignes, page trop longue → « Afficher plus »).
15. **Workflows préparés** : quotidien (+ issue d'alerte automatique), battement de cœur mensuel, tests à chaque envoi.

## 05/10/2026 — Cinq améliorations (« fais les 5 ») + photo réelle + sécurité
16. **Recherche par mots-clés** FR + AR (accents, voyelles arabes et formes de l'alif ignorés), combinable avec les filtres.
17. **Résumé traduit** sans service payant : glossaire maison (≈ 360 entrées, arabe ↔ français) ; rien n'est affiché si moins
    de la moitié des mots sont reconnus ; mention « traduction automatique approximative ».
18. **Rappels** : étiquettes J-7 … J-1 / Dernier jour et « Clôturent bientôt » (date du téléphone) ; rubrique J-2 dans Telegram.
19. **Telegram** : un message groupé par jour, découpé si > 4096 caractères, mémoire anti-doublon ; rien si pas de secrets.
20. **Ventes aux enchères** : source officielle trouvée (Douane tunisienne, robots autorisés, preuves datées + Internet Archive) ;
    robot 1 page par jour + page `encheres/`.
21. **Publication gratuite** pour les entreprises privées : Google Forms → CSV publié → contrôles automatiques → page `publier/`.
22. **Vraie photo** libre de droits (Wikimedia Commons, CC BY 4.0) dans le bandeau et l'image d'aperçu v3, crédit + preuve.
23. **Sécurité** : robots.txt anti-IA, meta noai, CSP, anti-iframe, anti-copie légère, test « aucun secret ».
24. Tests : +42 vérifications du site, +43 scénarios ; **sabotages** : 6 sur le site, 5 sur les robots → tous détectés.
25. **Photo du bandeau pour TOUS les marchés** (05/10 soir, Ahmed : « pas que la construction ») : mosaïque de 4 vraies
    photos prises en Tunisie (chantier, ordinateur, chambre de clinique, conteneurs au port de Radès), assemblée avec Python
    Pillow (4 côte à côte sur ordinateur, 2 × 2 sur téléphone) ; licence de chaque photo vérifiée + preuve (HTML, PDF, API,
    SHA-256) ; crédit de chacune affiché. Image d'aperçu `og-image-v6.jpg`.
26. **Pas de traduction automatique** : Chrome proposait l'anglais (pages FR + AR) → `translate="no"` sur `<html>` et
    `<meta name="google" content="notranslate">` sur les 40 pages ; vérifié par le test (sabotage détecté).

## À faire avant publication (Ahmed)
- Créer le dépôt public `Ah6259/appels-offres-tunisie` avec le contenu de `site/`, activer GitHub Pages (branche main, racine).
- Vérifier sur le téléphone, puis Search Console (sitemap) et GoatCounter.
- Canal Telegram, formulaire Google, WhatsApp : suivre README, « Ce qu'Ahmed doit faire ».
- Option prudente : courte lettre à la HAICOP pour présenter le service gratuit.

## 05/10/2026 — Installation complète sur le téléphone (service worker)
- `sw.js` à la racine (portée `/appels-offres-tunisie/`), enregistré par `assets/page.js` (https seulement, jamais en `file:`).
- **Réseau d'abord** pour les pages et les données (la liste du jour est toujours servie ; cache seulement hors connexion,
  sinon page « Hors connexion » FR + AR) ; fichiers `?v=` : cache puis mise à jour.
- Meta iPhone dans le gabarit `robot/construire_site.py` : `apple-mobile-web-app-capable`, `apple-mobile-web-app-title`.
- Test `node tools/test_sw.mjs` (faux navigateur), aussi dans maj.yml ; sabotage vérifié (HTML en cache d'abord, POST, portée).
- Vieille version bloquée sur un téléphone : changer `CACHE_VERSION` dans `sw.js`.

## 05/10/2026 (soir) — icône et « gratuit »
- Icône mégaphone (famille commune des sites) ; titres « consultation gratuite » fabriqués par `robot/construire_site.py`.

## 06/10/2026 — Partie payante « Alertes Pro » (accord écrit d'Ahmed)
- Offre : alertes personnalisées sur Telegram, 25 DT/mois ou 199 DT/an, 14 jours d'essai, sans renouvellement automatique ;
  la consultation reste gratuite (titres et FAQ honnêtes).
- Bouton doré « Alertes Pro » dans l'en-tête de toutes les pages + gros bouton sur l'accueil → page `abonnement/` : prix et
  avantages tout de suite, bouton « Paiement » (D17, IZI, preuve WhatsApp), formulaire Formspree, conditions.
- Modèle de paiement repris des annuaires (offre Pro, preuve WhatsApp, bouton GitHub d'activation depuis le téléphone).
- Abonnés (données personnelles) dans un dépôt GitHub **privé** séparé, avec son robot quotidien (Telegram getUpdates +
  sendMessage, mémoire par abonné, rappel J-3, message de fin) et ses tests avec un faux Telegram.
- Tests : +30 vérifications du site (dont « aucune donnée d'abonné dans le dépôt public »), +2 scénarios de réglage,
  45 tests du robot privé ; sabotages volontaires détectés des deux côtés. Captures Edge 500 et 360 px FR + AR.
