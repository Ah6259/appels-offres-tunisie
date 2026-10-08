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
- 42 pages générées par `robot/construire_site.py` : accueil, 10 métiers, 26 gouvernorats (24 + « Plusieurs » + « National »), à propos,
  `publier/` (entreprises privées), `encheres/` (ventes aux enchères de la Douane), `abonnement/` + `abonnement/conditions/` (Alertes Pro).
- Couleur principale ardoise #24476B (même famille visuelle qu'« Outils pratiques Tunisie »).
- Bandeau de l'accueil : **mosaïque de 4 vraies photos prises en Tunisie** (05/10 soir, Ahmed : « pas que la construction ») :
  BTP, informatique, santé, port (`PHOTOS` + `MOSAIQUE` / `MOSAIQUE_MOBILE` dans construire_site.py ; 4 côte à côte sur ordinateur,
  2 × 2 sur téléphone) + dégradé bleu ; crédit de CHAQUE photo sous le titre, dans « À propos » et sur `og-image-v6.jpg`. Toute nouvelle photo : licence
  vérifiée, preuve dans `preuves conditions d'utilisation/<date>/photos/`, pas de visage ni d'emblème, ≤ 150 Ko.
- SVG maison : icônes métiers (`ICONES_METIER`), carte schématique de la Tunisie (`carte_tunisie()`).
- **Carte de la Tunisie EN HAUT du bandeau** (08/10/2026, règle d'Ahmed : même place sur TOUS les sites, comme les annuaires) :
  `hero_carte()` sur l'accueil (à droite du titre ; sous le texte sur téléphone) et sur chaque page de gouvernorat (le sien en doré,
  `actif`) ; app.js ne recompte les bulles que sur l'accueil (sinon 0 partout). Plus de carte en bas dans « Par gouvernorat ».
- **Réglages d'Ahmed : `robot/reglages.py` seul** (canal Telegram, WhatsApp, formulaire Google + CSV). Vide = caché / « Bientôt ».
- Recherche `#f-q` (FR + AR, sans accents, `?q=`), résumé traduit `robot/glossaire.py` (≥ 50 % de mots reconnus sinon rien,
  jamais inventer), étiquettes J-7…J-1 / Dernier jour + « Clôturent bientôt » (date du visiteur), liens `#Tender-…`.
- Sources : HAICOP (appels d'offres), **Douane tunisienne** (ventes aux enchères, `robot/lire_douane.py`, 1 page/jour,
  preuves du 05/10/2026), entreprises privées (Google Forms → `robot/prives.py`, mention « non vérifié par HAICOP »).
- Telegram : `robot/telegram.py` (secrets `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CANAL`), mémoire `donnees/telegram-envoyes.json`.
- Sécurité (consigne commune du 05/10) : robots.txt anti-IA, meta noai + CSP + referrer, anti-copie légère dans page.js/style.css.
- Accueil : 15 cartes d'abord, bouton « Afficher plus ». Filtres métier + gouvernorat, tri date limite / plus récents, `?metier=` `?gouv=`.
- `?jour=AAAA-MM-JJ` simule la date du visiteur (tests).
- Statistiques **GoatCounter** (anonymes, sans cookies, 05/10/2026) sur toutes les pages : compteur partagé
  `https://prix-eaux-tunisie.goatcounter.com` (constante `COMPTEUR` + `CSP` dans construire_site.py ; pages séparées par chemin).
- Installation sur le téléphone : `manifest.webmanifest` avec `"id": "/appels-offres-tunisie/"` (UNIQUE : tous les sites d'Ahmed
  partagent l'origine ah6259.github.io ; sans id, Chrome disait « déjà installée »), icônes `assets/icons/` (192, 512, maskable)
  tirées de `assets/logo.svg`. Lien dans le gabarit ; vérifié par le test.
- **Service worker** (05/10/2026, installation complète Chrome/Android + iPhone) : `sw.js` à la racine, portée `/appels-offres-tunisie/`,
  enregistré à la fin de `assets/page.js` (https seulement, try/catch). **Réseau d'abord** pour les pages HTML et les données
  (`donnees/`, JSON : le visiteur voit toujours la dernière liste ; le cache ne sert que hors connexion, sinon page « Hors connexion » FR+AR) ;
  CSS/JS/images avec `?v=` : cache puis mise à jour. Jamais en cache : non-GET, autres origines (Google Forms, GoatCounter…), autres
  sites d'Ahmed. Caches `appels-offres-tunisie-<CACHE_VERSION>` (on ne supprime QUE les nôtres). Vieille version bloquée → changer
  `CACHE_VERSION`. Meta iPhone (`apple-mobile-web-app-capable`, `-title`) dans le gabarit de construire_site.py.
  Test : `node tools/test_sw.mjs` (faux navigateur ; accepte un dossier en argument), lancé aussi par maj.yml.

- **Votre avis** (05/10/2026, règle d'Ahmed : sur chacun de ses sites) : section `#avis` en bas de l'accueil (constante `AVIS`
  dans construire_site.py : carte FR + AR, note 😀🙂😐🙁 facultative, message obligatoire ≤ 1000 caractères, e-mail facultatif),
  lien « Votre avis » dans le pied de page (`page.js`). `assets/avis.js` (fichier externe, compté dans l'empreinte `?v=`) envoie par
  `fetch` à `https://formspree.io/f/mwlpakqj` (Accept JSON) seulement au clic, avec les champs cachés `site` = « Alertes appels
  d'offres Tunisie », `page`, `_subject` et le piège `_gotcha`. CSP (`FORMSPREE`) : `connect-src` + `form-action`. Champs
  sélectionnables malgré l'anti-copie ; le service worker laisse passer formspree.io. Formspree gratuit = 50 envois/mois pour
  TOUS les sites (même formulaire). Test : `node tools/test_avis.mjs` (accepte un dossier en argument), aussi dans tests.yml et maj.yml.

## Robustesse (voir README « Plan de continuité »)
- `statut_source` / `derniere_lecture_reussie` dans `donnees/appels-offres.json` ; `donnees/etat-source.json` pour l'alerte.
- Panne = source injoignable, liste < 30 %, format changé, champs vides — jamais « aucun appel d'offres ».
- Sauvegarde `donnees/appels-offres.sauvegarde.json` ; bandeau daté si dernière lecture ≥ 2 jours.
- Issue GitHub « Source HAICOP en panne depuis le … » ouverte / fermée automatiquement par `maj.yml`.
- Robots : `maj.yml` (quotidien), `battement-de-coeur.yml` (mensuel), `tests.yml` (push) ; groupe `maj-site`.

## Avant chaque publication
1. `node tools/test_site.mjs` (142 vérifications), `node tools/test_sw.mjs` (service worker), `node tools/test_avis.mjs` (Votre avis) et `python tools/test_pannes.py` (87 scénarios).
   Construire avec la date des données (`--aujourdhui AAAA-MM-JJ` = jour de la dernière lecture) sinon le test « données d'hier » échoue.
   jsdom : `npm install --no-save --no-package-lock jsdom` (node_modules ignoré).
2. Le `?v=` est automatique (empreinte de style.css, page.js, app.js, avis.js, abonnement.js) : **reconstruire** après toute modification de ces fichiers.
3. `bash tools/captures.sh` si l'affichage change (340/390 px, FR + AR), regarder les images.
4. Image d'aperçu `assets/og-image-v6.jpg` : si on la change, **nouveau nom** (-v7). Toujours en **JPEG < 250 Ko**
   (capture PNG de `tools/og-image.html` puis conversion Pillow qualité 88) : au-delà, WhatsApp n'affiche qu'une petite vignette.
   L'ancien `og-image-v4.png` n'est plus utilisé (peut être supprimé).
5. Toutes les pages ont `translate="no"` + meta google notranslate (Chrome traduisait en anglais) : vérifié par le test.

## Mise à jour du 05/10/2026 (soir)
- **Icône (famille commune des 5 sites)** : un seul symbole en aplats 2-3 tons, accent doré `#F2B33D`, sans texte ni brillance (règle d'Ahmed : jamais d'effet « image IA » ni de clip-art). Ce site : **mégaphone (un « appel » d'offres annoncé)**. Source = `assets/logo.svg` ; PNG 192/512 = dessin arrondi, maskable 512 et iPhone 180 = même dessin sur carré plein, symbole à 78 %. Générateur (hors dépôt) : `_claude code project/icones des sites - generateur.py`. Changer l'icône → renouveler `CACHE_VERSION` de `sw.js`.
- **« Gratuit » mis en avant** (titres Google, descriptions, aperçus de partage, manifeste), seulement là où c'est vrai : la CONSULTATION reste gratuite. Depuis le 06/10/2026, la partie payante (Alertes Pro) est annoncée par un bouton doré (accord écrit d'Ahmed).
- **Aperçus WhatsApp** : tous les sites sont réglés pareil (1200 × 630, JPEG léger). WhatsApp sur PC fait de petites vignettes : envoyer les liens depuis le téléphone (ou transférer un message préparé sur le téléphone).
- **Règle d'Ahmed : tout tourne sur internet (GitHub), sans son PC ni son intervention, « même s'il meurt ».**
- Titres : « consultation gratuite » (pas « alertes gratuites » : les alertes personnalisées deviendront payantes) ; descriptions « Gratuit, sans inscription » (`robot/construire_site.py`).

## Alertes Pro — partie payante (06/10/2026, accord écrit d'Ahmed : « commencer par Appels d'offres »)
- Offre : alertes PERSONNALISÉES (métiers + gouvernorats) chaque matin sur Telegram. **25 DT/mois ou 199 DT/an**, **14 jours d'essai
  gratuit**, « Sans engagement au-delà d'un an », **pas de renouvellement automatique** (rappel 3 jours avant, puis l'alerte s'arrête).
  La consultation du site reste GRATUITE (titres « consultation gratuite », « Gratuit, sans inscription » dans le texte d'intro, FAQ honnête).
- Constantes `ABO` + `pages_abonnement()` dans `robot/construire_site.py`. Bouton doré « Alertes Pro » dans l'en-tête de CHAQUE page
  (`assets/page.js`, classe `entete-pro`) + gros bouton `#btn-pro-accueil` dans le bandeau de l'accueil + lien dans le pied.
- Page `abonnement/` : prix + avantages tout de suite, `<details id="paiement">` « Paiement » (D17, IZI au 24 321 390, montant,
  motif = nom de l'entreprise), bouton vert « Envoyer la preuve de paiement par WhatsApp » (wa.me/21624321390, texte prérempli),
  formulaire Formspree `mwlpakqj` (nom, entreprise, téléphone 8 chiffres, e-mail, cases métiers, cases gouvernorats + « Toute la
  Tunisie », essai ou paiement direct, case conditions). `assets/abonnement.js` (externe, chargé seulement sur cette page) envoie
  métiers / gouvernorats en une ligne + `pour_activer` (à recopier dans le bouton du dépôt privé), puis montre `#apres-abo`
  (confirmation, paiement, WhatsApp avec le nom de l'entreprise, instructions Telegram). `abonnement/conditions/` : page sobre.
- Réglage `TELEGRAM_ROBOT_ALERTES` (robot/reglages.py) : nom du robot sans @ ; vide -> « le lien Telegram vous est envoyé à l'activation ».
- **Abonnés = données personnelles : JAMAIS dans ce dépôt** (le test le vérifie : pas de abonnes.json, aucun chat_id).
  Ils sont dans le dépôt **PRIVÉ** `Ah6259/appels-offres-abonnes` (dossier PC `alertes appels d'offres Tunisie/abonnes (prive)/`) :
  robot `alertes.yml` chaque jour 07h00 UTC (lit la liste publique `donnees/appels-offres.json`), bouton `activer-abonne.yml`
  (essai / paye / modifier / arret / liste ; le résumé donne le CODE + lien WhatsApp vers le client), secret `TELEGRAM_BOT_TOKEN`.
  Ses listes de métiers/gouvernorats (`tools/classement.py`) = copie de celles de ce fichier : à garder identiques.
- CSS : `[hidden]{display:none !important}`, `fieldset` avec `min-width:0` (sinon débordement en arabe), piège anti-robot 1 px.
- **Pas de faux boutons** (Ahmed, 06/10/2026) : rangée de badges « Source officielle / Gratuit / Mis à jour » supprimée (cartes avec icône qui ne menaient nulle part) ; le test vérifie sur toutes les pages qu'aucune carte avec icône n'est sans lien.
- **Bouton « Partager »** (06/10/2026, demande d'Ahmed) : icône ronde `.partager` dans `.entete-boutons` des 42 pages (page.js, FR+AR) ; menu de partage du téléphone (`navigator.share`), sinon WhatsApp (`wa.me`) avec l'adresse sans `#` ni `?lang` ; clic compté `partage/<page>` dans GoatCounter. Test : partie 12 de test_site.mjs.

- **Vidéo de présentation** (06/10/2026) : `assets/video/presentation.mp4`, 1080 × 1920, + couverture et aperçu 1200 × 630 (`apercu-video.jpg`). Musique de fond : J. S. Bach, Aria des Variations Goldberg (enregistrement Musopen, CC0, Wikimedia Commons ; preuve dans le dossier privé `videos (outil)/preuves musique/`). Page **`video/`** (lecteur + gros bouton « Ouvrir le site » + Partager, og:video / og:image) : réglages `tools/page_video.json`, fabriquée par tools/page_video.py, appelé par robot/construire_site.py. Le bouton « Partager » envoie un LIEN : la page vidéo + l'adresse du site dans le texte (`window.partagerLien`, bloc « vidéo de présentation » en fin du JS commun), jamais le fichier. Test `node tools/test_video.mjs`.
  Pour la refaire : `python fabriquer.py appels-offres` puis `python brancher_partage.py appels-offres` dans le dossier PRIVÉ du PC `videos (outil)/`.

- **Langue en mémoire (06/10/2026)** : la mémoire du navigateur (localStorage) est PARTAGÉE par tous les sites d'ah6259.github.io : `page.js` n'accepte que « fr » ou « ar » (sinon langue par défaut). Ne jamais écrire une autre valeur sous la clé « langue ».
