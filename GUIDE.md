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
6. **Style** repris d'Outils pratiques Tunisie (cartes, bandeau dégradé, badges de confiance), couleur ardoise.
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

## À faire avant publication (Ahmed)
- Créer le dépôt public `Ah6259/appels-offres-tunisie` avec le contenu de `site/`, activer GitHub Pages (branche main, racine).
- Vérifier sur le téléphone, puis Search Console (sitemap) et GoatCounter.
- Plus tard : canal Telegram (secret `TELEGRAM_BOT_TOKEN`), puis WhatsApp.
- Option prudente : courte lettre à la HAICOP pour présenter le service gratuit.
