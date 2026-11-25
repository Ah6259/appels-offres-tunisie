# Mémoire du projet — Alertes appels d'offres Tunisie

## EN TOUT PREMIER (24/11/2026, problème vu par Ahmed)
- La mémoire générale, les « update workflow » et le journal de TOUS les sites sont dans le dépôt PRIVÉ **`Ah6259/projets-ahmed`**
  (le dépôt général), PAS ici. Une session ouverte sur ce seul dépôt ne voit donc pas le dernier travail d'Ahmed (le 24/11, une session
  a répondu « dernier update workflow : 22/11 » alors qu'il y en avait deux le jour même dans projets-ahmed).
- **Au début de CHAQUE session, avant de répondre quoi que ce soit** : si `../projets-ahmed` n'existe pas, le brancher
  (`add_repo` Ah6259/projets-ahmed, puis `git clone --depth 30 https://github.com/Ah6259/projets-ahmed ../projets-ahmed`) ; sinon `git pull` ;
  puis `python3 "debut de session.py" appels-offres` dans `../projets-ahmed` et en résumer le résultat à Ahmed.
- « Dernier workflow / dernière mise à jour » = regarder `git log` de projets-ahmed ET de ce dépôt (toutes branches), jamais un seul.

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
1. `node tools/test_site.mjs` (155 vérifications), `node tools/test_sw.mjs` (service worker), `node tools/test_avis.mjs` (Votre avis) `python tools/test_pannes.py` (86 scénarios) et `python tools/test_rapports.py` (50 vérifications, Rapports du mois).
   Construire avec la date des données (`--aujourdhui AAAA-MM-JJ` = jour de la dernière lecture) sinon le test « données d'hier » échoue.
   jsdom : `npm install --no-save --no-package-lock jsdom` (node_modules ignoré).
2. Le `?v=` est automatique (empreinte de style.css, page.js, son.js, app.js, avis.js, pass-commun.js, pass-reglages.js) : **reconstruire** après toute modification de ces fichiers.
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
- Offre : alertes PERSONNALISÉES (métiers + gouvernorats) chaque matin sur Telegram. **25 DT/mois ou 199 DT/an**, **plus d'essai
  gratuit depuis le 20/10/2026**, « Sans engagement au-delà d'un an », **pas de renouvellement automatique** (rappel 3 jours avant, puis l'alerte s'arrête).
  La consultation du site reste GRATUITE (titres « consultation gratuite », « Gratuit, sans inscription » dans le texte d'intro, FAQ honnête).
- Constantes `ABO` + `pages_abonnement()` dans `robot/construire_site.py`. Bouton doré « Alertes Pro » dans l'en-tête de CHAQUE page
  (`assets/page.js`, classe `entete-pro`) + gros bouton `#btn-pro-accueil` dans le bandeau de l'accueil + lien dans le pied.
- Page `abonnement/` : prix + avantages tout de suite, `<details id="paiement">` « Paiement » (D17, IZI au 24 321 390, montant,
  motif = nom de l'entreprise), bouton vert « Envoyer la preuve de paiement par WhatsApp » (wa.me/21624321390, texte prérempli),
  formulaire Formspree `mwlpakqj` (nom, entreprise, téléphone 8 chiffres, e-mail, cases métiers, cases gouvernorats + « Toute la
  Tunisie », essai ou paiement direct, case conditions). `assets/pass-commun.js` + `assets/pass-reglages.js` (module commun, voir le 25/11/2026 en bas ; externes, chargés seulement sur cette page) envoient
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

- **Adresse depuis le 11/10/2026 : https://appels-offres.clicvia.com/** (domaine clicvia.com d'Ahmed, ligne DNS `CNAME appels-offres → ah6259.github.io` nuage gris, fichier `CNAME`). L'ancienne adresse ah6259.github.io/appels-offres-tunisie/ redirige seule. Site à la racine « / » : `BASE_SITE` de assets/page.js (sw.js, vidéo) ; GoatCounter garde le préfixe `/appels-offres-tunisie`. Si l'outil vidéo réécrit le bloc VIDEO_SITE, remettre `"base": BASE_SITE` et l'ORIGINE appels-offres.clicvia.com.

- **Visibilité Google (12/10/2026, règle commune § 8)** : liens vers nos autres sites en `https://<site>.clicvia.com/` (jamais `ah6259.github.io`), lien « Tous nos services » → https://clicvia.com/ dans le pied de page, `robots.txt` avec ligne Sitemap, `sitemap.xml` daté, JSON-LD sur l'accueil, clé IndexNow `377f054ba9c5ed40d6796adc8d87d1e8.txt` à la racine (ne pas supprimer : robot `indexnow` du portail). Contrôle : `node "outils visibilite/controle.mjs"` (dépôt projets-ahmed). Sitemap envoyé dans Search Console par Ahmed le 12/10/2026.

- **Google + Bing (12/10/2026)** : sitemap envoyé par Ahmed dans Google Search Console et dans Bing Webmaster Tools (site clicvia.com/), indexation de l'accueil demandée. Pour un nouveau site : mêmes gestes, voir `nouveau site - procedure.md` § 4 étape 5 (dépôt projets-ahmed).

## Rapports du mois (18/10/2026, demande d'Ahmed, règle commune § 25)
- Articles AUTOMATIQUES mais VRAIS pour Google : `robot/rapports.py`, appelé par `construire_site.py` (donc par `maj.yml`, chaque jour).
  Pages `rapports/` (liste des mois), `rapports/AAAA-MM/` (bilan : en bref, par métier, par gouvernorat, acheteurs, délais et cautions,
  procédures, ventes aux enchères de la Douane, méthode, « Citer ces chiffres », JSON-LD Article + FAQ + fil d'Ariane) et sous-pages
  `rapports/AAAA-MM/gouvernorat|metier/<slug>/` (liste des fiches du mois + liens officiels). Lien « Rapports du mois » dans le pied (page.js).
- Chaque phrase = un comptage (ou une médiane) des annonces GRATUITES du site ; rien d'Alertes Pro. Le texte dit « relevés par notre
  robot » (pas le total officiel du portail). Minimums écrits : classement ≥ 3 appels d'offres par ligne et ≥ 3 lignes, médiane ≥ 5 valeurs,
  sous-page ≥ 10 appels d'offres (au plus 25 par mois, jamais « Plusieurs », « National », « Autres »).
- Historique `donnees/rapports.json` (fiches du mois en forme courte + chiffres + `derniere_date`) : mois en cours recalculé chaque jour,
  mois fini FIGÉ le 3 du mois suivant puis jamais modifié ; un mois déjà fini au premier passage n'est pas créé après coup.
  Évolution seulement si le mois précédent est « complet » (robot en marche dès son 1er jour ; `robot_depuis` = 04/10/2026, donc pas
  d'évolution avant décembre 2026), sur la même période pour le mois en cours. Octobre 2026 = « Premier rapport » + avertissement
  « relevés en partie avant le 04/10 ». Plan du site : lastmod = date des chiffres. Test : `python tools/test_rapports.py` (maj.yml + tests.yml).
- **Image d'aperçu PROPRE à chaque rapport (18/10/2026, Ahmed : Facebook montrait l'image du site)** : `robot/apercus.py` (Pillow, polices
  DejaVu dans `robot/polices/`, modèle d'Immobilier Tunisie) dessine `apercu-<empreinte 8>.jpg` 1200 × 630 dans le dossier de CHAQUE page
  (bilan du mois + sous-pages : nombre d'appels d'offres relevés, part du total, date des chiffres) ; nom = empreinte du contenu (Facebook
  reprend la nouvelle image quand les chiffres changent), anciennes images effacées ; og:image + `image` du JSON-LD Article ; liste
  `rapports/` et sans Pillow : og-image-v6.jpg. maj.yml et tests.yml installent pillow. Test dans test_rapports.py et test_site.mjs.
- **Partage des rapports (18/10/2026, demande d'Ahmed)** : sur TOUTES les pages des rapports, UN seul bouton « Partager ce rapport »
  (`bloc_partage` de rapports.py, en haut dans le bandeau ET en bas ; jamais de boutons Facebook / WhatsApp séparés) + signature
  « Un rapport de Alertes appels d'offres Tunisie · appels-offres.clicvia.com » sous le titre ; description = « Alertes appels d'offres Tunisie
  — rapport du mois. … ». Code : écouteur `button[data-partage-rapport]` dans assets/page.js (menu du téléphone, sinon texte + lien copiés
  « Lien copié ✓ », sinon prompt ; clic GoatCounter `partage/…`). Classe `rp-partager` (PAS `partager` : réservé au bouton vidéo de l'en-tête).


## Visiteur simulé (18/10/2026, règle générale)
- `python tools/visiteur_simule.py` (outil COMMUN, copie identique dans chaque site : ne pas le modifier ici) : liens/images morts, puis Chromium à 390 px (page trop large, image cassée, « NaN/undefined », page vide) + scénarios `tools/scenarios-visiteur.json` (recherche, filtres, résultat affiché, groupes « croissant »). Lancé par tests.yml. Nouvelle recherche, nouveau filtre ou nouveau formulaire → ajouter un scénario. Page `video/` : `preload="none"` (la couverture reste affichée ; la page finit de charger sans attendre la vidéo, moins de données sur téléphone ; le visiteur simulé la voyait « non chargée » avec `metadata`).

## Code personnel des Alertes Pro (18/10/2026, contrôle commun « case du code »)
- Ce site n'a AUCUNE case où le visiteur tape un code : `abonnement/` CRÉE le code (6 caractères, module commun `assets/pass-commun.js` réglé par `assets/pass-reglages.js`), l'affiche
  (`#abo-code`) et le met dans le lien Telegram ; rien dans localStorage. Plus d'essai gratuit depuis le 20/10/2026.
- Corrigé : le bloc « Paiement », le libellé « Entreprise (motif du paiement et facture) » et les conditions disaient « motif = nom de
  l'entreprise » alors que les étapes disent « Motif : votre code personnel » -> partout « code personnel » ; libellé « Entreprise
  (pour la facture) » (test dans test_site.mjs).

- **Lieux officiels (18/10/2026, règle commune § 11.11)** : test_site.mjs vérifie dans les deux sens que la liste « Gouvernorat », les pages et la carte = les 24 gouvernorats de La Poste + les exceptions « national » et « plusieurs » (groupes, jamais des gouvernorats) ; la carte de l'accueil entoure le gouvernorat choisi dans le filtre (app.js).

- **Recherche « au son » (18/10/2026, règle commune § 27)** : la case « Rechercher » utilise `assets/son.js` (outil commun de projets-ahmed, copié TEL QUEL, chargé avant app.js, compté dans le `?v=`) : Djerba = Jerba, Kairouan = Qairouan, Hammamet = Hamamet (l'ancienne recherche « mot contenu » reste valable en plus). Test dans test_site.mjs (paires + mot réel avec consonne doublée + « zzzzqqq » = 0).

- **19/10/2026 — Visiteur simulé : contrôle des ESPACES (règle commune § 29)** : nouvelle copie commune installée, 0 anomalie, aucun défaut d'espace sur ce site.

- **20/10/2026 — PLUS D'ESSAI GRATUIT** (Ahmed : « Enlève tous les essais gratuits ») : aucune mention d'essai sur le site (bouton doré
  de l'accueil, page `abonnement/`, conditions renumérotées 1-8, titres, descriptions, FAQ JSON-LD) ; formule 1 mois (cochée) ou 1 an ;
  le code reste créé sur la page, le robot privé le met « en attente » jusqu'au paiement. Test : « aucune page ne parle d'essai
  gratuit » dans test_site.mjs.
- **20/10/2026** : le robot `maj-appels-offres` a été bloqué à tort par le test de recherche au son (il avait tiré « etudes » et fabriqué
  « ettudes », lu exprès comme l'article « Ett… ») ; test corrigé (faute jamais au début du mot), robot relancé, vert. Les robots rouges
  sont désormais réparés seuls par la tâche Claude « Réparer les robots rouges » (règle commune § 33, projets-ahmed).

- **RÈGLE D'AHMED (25/10/2026, règle commune § 44) : la page « Comment fonctionne le site ? » (`a-propos/`, bloc « Comment fonctionne
  le site ? » de robot/construire_site.py, FR + AR ; elle sert aussi de modèle à la page `video/`) est mise à jour à CHAQUE modification
  visible du site, dans le même envoi** : à quoi sert le site, mode d'emploi, une ligne par fonction visible, sources, méthode,
  gratuit / payant (Alertes Pro), vos données, mises à jour, site indépendant, crédits des photos. Lien « Comment fonctionne le site ? »
  dans le pied de page (page.js) et sur l'accueil (carte « Comment ça marche ? »). Test `FONCTIONS` dans tools/test_site.mjs
  (repère dans le site -> phrase attendue dans la page) : une fonction absente = test rouge. Nouvelle fonction = une ligne dans
  `FONCTIONS` + son explication dans la liste `fonctions` de construire_site.py.

- **08/11/2026 — plan SEO d'Ahmed appliqué à ce site (phase 2, contrôle commun `outils visibilite/controle_seo.mjs` de projets-ahmed ;
  plan : `consignes des taches/seo-appels-offres.md`)** : `titre_seo()` / `desc_seo()` dans `page()` (titre <= 70 caractères, description <= 165 :
  suffixe « | Alertes appels d'offres » retiré, coupe à un séparateur ou en fin de phrase) ; titres de l'accueil, des métiers et des
  gouvernorats raccourcis (« Appels d'offres Tunisie : N ouverts, consultation gratuite ») ; h2 « La liste » au-dessus des cartes (plus
  de saut h1 -> h3) ; test « SEO : titre de 10 à 70 caractères et description de 40 à 170 ». Les tests du site ont besoin de
  `node --max-old-space-size=6144` ici (mémoire). Reste (phase 2 point 7) : une adresse par langue (FR et AR mêlés sous lang="fr").

- **08/11/2026 — UNE ADRESSE PAR LANGUE (plan SEO d'Ahmed, phase 2 point 7, « suivant » d'Ahmed ; méthode de l'Immobilier et de Concours)** :
  `robot/langues.py` (copie adaptée) : chaque page fabriquée par `page()` est écrite deux fois par `construire()` : `<chemin>/` en français seul
  (lang="fr", data-langue-fixe="fr", data-autre-langue) et `ar/<chemin>/` en arabe seul (lang="ar" dir="rtl", titre = H1 arabe + « | طلبات
  العروض تونس », description = `DESC_AR[chemin]` (métiers, gouvernorats, rapports du mois et leurs sous-pages : une description arabe propre
  à chaque page, sinon le 1er paragraphe arabe), canonical et og:url ar/, données Google françaises retirées, fichiers pris à la racine :
  data-racine un niveau plus bas, data-site = dossier des pages), hreflang fr / ar / x-default sur les deux ; `LG.MIROIR` = pages du jour
  (video/ garde une seule adresse `?lang=ar` : `tools/page_video.py` retire data-langue-fixe du modèle) ; `LG.nettoyer()`. Plan du site :
  pages FR + AR. Pied statique de `page()` en deux langues. Titres des bilans du mois : le mois en tête (« Bilan d’octobre 2026 : … »), sinon
  la coupe à 70 caractères donnait le même titre à tous les mois. `retirer_langue` laisse un espace à la place d'un texte retiré (sinon
  « civil » + « Kairouan » se collaient dans le texte lu : la recherche au son le voyait). `assets/page.js` : langue de l'adresse, bouton
  de langue = autre adresse (`window.allerVers` pour les tests), ancien lien `?lang=ar` renvoyé, langue gardée renvoyée seulement en venant du
  site ; liens des pages de l'en-tête / du pied = `${site}` (`window.racinePages()`). Tests : `page(…, "lang=ar")` ouvre ar/<chemin> ;
  bloc « une adresse par langue » (hreflang, canonical, titres et descriptions uniques, liens valides, bouton) ; test_avis, test_video,
  test_rapports adaptés ; 2 scénarios du visiteur simulé sur ar/. Page a-propos : ligne « ع / Fr » mise à jour.

- **08/11/2026 (soir, leçon de Concours)** : `langues.nettoyer()` ne retire une page arabe que si sa page FRANÇAISE a disparu du disque (plus
  jamais « hors des pages du jour » : à Concours, les pages arabes de 10 anciens concours avaient été retirées alors que leurs pages françaises
  restaient, liens hreflang morts, robot Tests rouge). Test « toute page française qui annonce une page arabe l'a sur le disque » (tout le site).

## Page 404 + Confidentialité / Conditions (17/11/2026, règle commune § 58)
- `404.html` + `404.js` à la racine = page 404 COMMUNE (`outils communs/page-404/installer.py`, projets-ahmed) : ne pas les modifier ici, réinstaller.
- Liens « Confidentialité » et « Conditions d'utilisation » (pages communes clicvia.com, FR / AR) dans le pied de CHAQUE page
  (pied statique de `construire_site.py` + pied de `assets/page.js`). Test qui bloque dans `tools/test_site.mjs` ; test_sw / test_avis ignorent 404.html.
- Sur le PC : `PYTHON=python node tools/test_site.mjs` (sinon « python3 » de Windows ne répond pas et 4 tests de recherche échouent).

## Certificat EXPIRÉ de la HAICOP (17/11/2026, décision d'Ahmed : « lire malgré le certificat »)
- Le certificat de www.marchespublics.gov.tn a expiré le 16/11/2026 à 9h : plus aucun relevé depuis le 15/11, robot rouge (§ 51, > 2 jours).
- `telecharger()` de `robot/lire_haicop.py` refait l'essai SANS vérification du certificat SEULEMENT si la raison est « certificate has
  expired » ET l'adresse commence par `PREFIXE_SITE` (même méthode que la Douane) ; tout autre défaut de certificat ou autre domaine = panne.
  Dès que la HAICOP renouvelle son certificat, la lecture vérifiée repasse seule. Tests : 3 scénarios dans `tools/test_pannes.py`.

- **19/11/2026 — ACCUEIL LÉGER (Ahmed, CV.3)** : l'accueil écrivait ses 443 appels d'offres (833 Ko FR, 860 Ko AR, 17 600 éléments : 9 s avant d'être
  utilisable sur un téléphone moyen). Toute liste de plus de `SEUIL_LISTE` (60) n'a que les `PREMIERES_LISTE` (30) dates limites les plus proches dans la
  page ; le reste est écrit entre les repères `RESTE_DEBUT`/`RESTE_FIN`, puis APRÈS `LG.versions()` (langue et liens déjà adaptés) retiré de chaque
  version et enregistré dans `liste.json` / `ar/<chemin>liste.json` (`separer_reste()`). app.js le charge au 1er geste (filtre, tri, recherche, « Afficher
  plus », lien #Tender-…) ou TOUT DE SUITE si la page date d'un autre jour que le visiteur (`data-jour`) ; avant : compteurs, carte et résumé = chiffres
  de la construction. Tests : page() du test charge le reste (sauf { leger: true }) ; test_rapports lit aussi liste.json.
- Sur le PC, les tests de recherche ont besoin de `PYTHONUTF8=1 PYTHON=python` (sans UTF-8, le glossaire renvoie un JSON illisible : 4 échecs + arrêt du test).
- **21/11/2026 — mode sombre lisible (capture d'Ahmed, même correction que Concours)** : sur `abonnement/`, les étapes du paiement (`ol.paie-etapes`)
  gardaient un fond clair fixe (#EEF3F8) sous un texte devenu clair, et `var(--p)` n'existait pas (rond numéroté et liens D17 / IZI sans couleur).
  Fin de `assets/style.css` : `--p`, `--p-clair`, `--p-tres-clair`, `--p-sur` définis ; en sombre, texte foncé (#0D141D) sur `.btn-publier`,
  `.btn-video-site`, `.avis-envoyer`, `.rappel.fort` (J-1 / J-2). Contrôle de contraste (sombre ET clair) : 0 texte sous 3.
- **21/11/2026 — mode CLAIR plus lisible (accord d'Ahmed : « foncer un peu »)** : bloc clair `:root` de `assets/style.css` : `--rouge` #C2412F -> #B23A29
  (dates limites, « dans N jours »), `--or` #B7791F -> #8F5D14 (J-3/J-4), boutons WhatsApp #1F9D55 -> #15803D. Contrôle `mode_sombre.mjs --clair --seuil 4.5` : 0 ; sombre : 0.
- **21/11/2026 — Douane retirée de l'alarme (décision d'Ahmed, point A.10 : « retire-les »)** : la page des ventes aux enchères ne répond plus
  à GitHub ; `RETIREES` + `retirer()` de `tools/sources_en_panne.py` : encore essayée à chaque passage (les enchères reviennent seules), mais
  sa panne ne met plus `maj` en rouge (ligne « RETIRÉE » au journal) ; HAICOP et feuille des entreprises toujours surveillées. Test (99/99).

## 21-22/11/2026 — Google + IA (demande d'Ahmed : « que Google et les IA indexent nos sites »)
- État Search Console (21/11) : accueil « Discovered - currently not indexed » (Google ne l'a pas encore visité ; trouvé depuis clicvia.com).
- Accueil : 2e JSON-LD « WebSite » (nom FR/AR, éditeur `Organization` Clicvia + page Facebook) APRÈS la FAQ (les tests lisent la 1re balise
  = FAQ) ; test « JSON-LD WebSite avec l'éditeur Clicvia » + 7 balises <script> sur l'accueil (test_site.mjs). Page arabe : retiré par langues.py.
- `llms.txt` réécrit à la main SANS chiffre (l'ancien de l'outil commun du 13/10 disait « 179 ouverts », « 22 enchères »).
- « Comment fonctionne le site ? » (FR + AR) : « Publié par Clicvia… pour nous écrire : Votre avis » (carte « Un site indépendant »).

## 25/11/2026 — PASS.1 : parcours d'achat par le MODULE COMMUN (règle commune § 70.8, 2e site migré après Concours)
- `assets/abonnement.js` est SUPPRIMÉ. La page `abonnement/` (FR + ar/) charge `assets/pass-commun.js` (COPIE EXACTE du module
  `outils communs/pass-commun/pass-commun.js` de projets-ahmed : **ne jamais la modifier ici**) puis `assets/pass-reglages.js` (ce qui
  est propre au site : nom, formules 1 mois / 1 an, code 6 caractères sans O/0/I/1, entreprise, métiers, gouvernorats, « Toute la Tunisie »,
  lien Telegram, ligne `pour_activer`, champs de l'e-mail, nom de l'ENTREPRISE dans le message WhatsApp ; `emailAuto: true`).
  `assets/pass-commun.empreinte` = empreinte écrite par `synchroniser.py` ; test_site.mjs échoue si la copie est modifiée (et, si projets-ahmed
  est à côté — ou `PROJETS_AHMED=<dossier>` —, si elle diffère du module) ; la demande d'e-mail reste vérifiée par le vrai `verifier()`.
- Améliorer le parcours : modifier le module dans projets-ahmed, `python3 "outils communs/pass-commun/synchroniser.py"`, reconstruire, tests,
  envoyer CHAQUE site (LISEZMOI.md du module). Rien n'a changé pour le visiteur (comparaison avant / après, FR + AR : 110 étapes identiques ;
  seule différence voulue : piège anti-robot rempli = la commande n'est plus gardée dans le téléphone).

## 25/11/2026 — Vers la page d'achat (AO.1 + C.1) : encadrés sur les pages métier / gouvernorat, clics comptés — PAS de gratuité
- **Décision d'Ahmed (25/11/2026)** : amener les visiteurs vers `abonnement/` avec des encadrés liés au contenu de la page et compter les
  clics ; **aucune gratuité** (ni essai, ni formule, ni canal gratuit ; prix inchangés 25 DT / mois, 199 DT / an). Modèle : Alerte Concours (550bb92).
- **AO.1** : `encadre_metier()` / `encadre_gouv()` / `encadre_abo()` de `robot/construire_site.py` : au-dessus de la liste de chaque page
  `metier/<slug>/` et `gouvernorat/<slug>/` (FR + ar/), « N appels d'offres « Métier » ouverts. Recevez les prochains chaque matin sur Telegram. »
  (N = nombre de la liste ; 0 = « Aucun appel d'offres … ouvert aujourd'hui »), prix écrit, vrai bouton doré `a.btn-pro#encadre-btn` vers
  `abonnement/?metier=<slug>#inscription` ou `?gouv=<slug>` (`_adresse_abo()` ; rien pour « national » / « plusieurs », toujours compris).
  `assets/pass-reglages.js` (fonction `brancher`) coche ces cases d'après l'adresse (valeurs inconnues ignorées, « tous » exclusif) et montre
  `#abo-repris` (« Vos choix de la page précédente sont déjà cochés… »). `assets/pass-commun.js` (module commun) NON modifié.
- **C.1** : `assets/page.js` compte tout lien `a[data-clic]` en ÉVÉNEMENT GoatCounter `/appels-offres-tunisie/clic/<nom>` (seulement si
  `window.goatcounter.count` existe ; rien de cassé si bloqué ; pas de script en ligne). Noms : `abonnement-entete` (bouton doré de l'en-tête),
  `abonnement-pied` (lien du pied), `abonnement-accueil` (gros bouton de l'accueil), `abonnement-metier`, `abonnement-gouvernorat` (encadrés),
  `abonnement-a-propos` (« Voir les Alertes Pro » d'a-propos/). Dans GoatCounter : chercher « clic/ ».
- « Comment fonctionne le site ? » (FR + AR) : ligne de l'encadré + « nous comptons aussi les clics… » (Vos données) ; FONCTIONS + tests
  (bloc « 25/11/2026 (décision d'Ahmed : amener les visiteurs vers la page d'achat » de tools/test_site.mjs ; 5 sabotages tous vus).
