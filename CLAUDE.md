# Mémoire du projet — Alertes appels d'offres Tunisie

Fichier lu automatiquement par Claude Code au début de chaque session dans ce dossier.
**Dépôt PUBLIC : rien de personnel ni de secret ici.** À tenir à jour avec README et GUIDE.

## Qui et comment travailler
- Propriétaire : Ahmed (compte GitHub `Ah6259`), débutant. Expliquer simplement, **en français**.
- **Demander l'accord d'Ahmed avant de modifier le site** (sauf s'il dit « fais »). **Demander avant d'installer un logiciel.**
- Appliquer les **règles communes à tous ses sites** (`regles communes a tous les sites.md`, dossier parent des projets).
- Ne jamais citer de site concurrent (site, README, code, tests). Seules les sources officielles sont citées.

## Le site
- Prévu : https://ah6259.github.io/appels-offres-tunisie/ — dépôt `Ah6259/appels-offres-tunisie` (pas encore créé au 05/10/2026).
  Ce dossier `site/` est la **racine du dépôt** (robot, données, pages, tests, workflows).
- Source : portail officiel **HAICOP** (marchespublics.gov.tn), robots autorisés par son robots.txt. Lire **lentement**.
  Toujours « source : HAICOP » + lien vers la fiche officielle de chaque annonce. TUNEPS n'est pas lu (échanges chiffrés).
- Les preuves (robots.txt, charte) sont dans le dossier parent `preuves conditions d'utilisation/` : **jamais publiées**.
- 40 pages générées par `robot/construire_site.py` : accueil, 10 métiers, 26 gouvernorats (24 + « Plusieurs » + « National »), à propos,
  `publier/` (entreprises privées), `encheres/` (ventes aux enchères de la Douane).
- Couleur principale ardoise #24476B (même famille visuelle qu'« Outils pratiques Tunisie »).
- Bandeau de l'accueil : **mosaïque de 4 vraies photos prises en Tunisie** (05/10 soir, Ahmed : « pas que la construction ») :
  BTP, informatique, santé, port (`PHOTOS` + `MOSAIQUE` / `MOSAIQUE_MOBILE` dans construire_site.py ; 4 côte à côte sur ordinateur,
  2 × 2 sur téléphone) + dégradé bleu ; crédit de CHAQUE photo sous le titre, dans « À propos » et sur `og-image-v4.png`. Toute nouvelle photo : licence
  vérifiée, preuve dans `preuves conditions d'utilisation/<date>/photos/`, pas de visage ni d'emblème, ≤ 150 Ko.
- SVG maison : icônes métiers (`ICONES_METIER`), carte schématique de la Tunisie (`carte_tunisie()`).
- **Réglages d'Ahmed : `robot/reglages.py` seul** (canal Telegram, WhatsApp, formulaire Google + CSV). Vide = caché / « Bientôt ».
- Recherche `#f-q` (FR + AR, sans accents, `?q=`), résumé traduit `robot/glossaire.py` (≥ 50 % de mots reconnus sinon rien,
  jamais inventer), étiquettes J-7…J-1 / Dernier jour + « Clôturent bientôt » (date du visiteur), liens `#Tender-…`.
- Sources : HAICOP (appels d'offres), **Douane tunisienne** (ventes aux enchères, `robot/lire_douane.py`, 1 page/jour,
  preuves du 05/10/2026), entreprises privées (Google Forms → `robot/prives.py`, mention « non vérifié par HAICOP »).
- Telegram : `robot/telegram.py` (secrets `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CANAL`), mémoire `donnees/telegram-envoyes.json`.
- Sécurité (consigne commune du 05/10) : robots.txt anti-IA, meta noai + CSP + referrer, anti-copie légère dans page.js/style.css.
- Accueil : 15 cartes d'abord, bouton « Afficher plus ». Filtres métier + gouvernorat, tri date limite / plus récents, `?metier=` `?gouv=`.
- `?jour=AAAA-MM-JJ` simule la date du visiteur (tests).

## Robustesse (voir README « Plan de continuité »)
- `statut_source` / `derniere_lecture_reussie` dans `donnees/appels-offres.json` ; `donnees/etat-source.json` pour l'alerte.
- Panne = source injoignable, liste < 30 %, format changé, champs vides — jamais « aucun appel d'offres ».
- Sauvegarde `donnees/appels-offres.sauvegarde.json` ; bandeau daté si dernière lecture ≥ 2 jours.
- Issue GitHub « Source HAICOP en panne depuis le … » ouverte / fermée automatiquement par `maj.yml`.
- Robots : `maj.yml` (quotidien), `battement-de-coeur.yml` (mensuel), `tests.yml` (push) ; groupe `maj-site`.

## Avant chaque publication
1. `node tools/test_site.mjs` (108 vérifications) et `python tools/test_pannes.py` (85 scénarios).
   jsdom : `npm install --no-save --no-package-lock jsdom` (node_modules ignoré).
2. Le `?v=` est automatique (empreinte de style.css, page.js, app.js) : **reconstruire** après toute modification de ces fichiers.
3. `bash tools/captures.sh` si l'affichage change (340/390 px, FR + AR), regarder les images.
4. Image d'aperçu `assets/og-image-v4.png` : si on la change, **nouveau nom** (-v5).
5. Toutes les pages ont `translate="no"` + meta google notranslate (Chrome traduisait en anglais) : vérifié par le test.
