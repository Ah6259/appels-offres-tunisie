# Alertes appels d'offres Tunisie

Site gratuit, sans inscription : chaque jour, les nouveaux **appels d'offres publics tunisiens**,
triés **par métier** et **par gouvernorat**, avec la date limite (en rouge à moins de 7 jours),
la caution provisoire et le lien vers la **fiche officielle**. Français + arabe (`?lang=ar`).

- Adresse prévue : https://appels-offres.clicvia.com/
- Source unique : portail officiel de la **HAICOP** (Haute Instance de la Commande Publique,
  www.marchespublics.gov.tn). Le cahier des charges se retire sur **TUNEPS**. Ce site n'est pas officiel.

Aussi : **recherche par mots-clés** (français et arabe, sans souci d'accents), **résumé traduit** des objets
(arabe -> français et inversement, glossaire maison, « traduction automatique approximative »), **rappels** « J-7 … J-1 /
Dernier jour » et section « Clôturent bientôt », **ventes aux enchères** de la Douane tunisienne (`encheres/`),
**publication gratuite** d'appels d'offres par les entreprises privées (`publier/`), **alerte Telegram** quotidienne.

**Partie payante « Alertes Pro »** (`abonnement/`) : alertes personnalisées (métiers + gouvernorats) chaque matin sur Telegram,
25 DT/mois ou 199 DT/an, 14 jours d'essai gratuit, sans renouvellement automatique. La consultation reste gratuite.

## Comment ça marche
| Étape | Fichier | Rôle |
|---|---|---|
| 1 | `robot/lire_haicop.py` | lit **lentement** les nouvelles fiches (1 page / 2,5 s), les classe par métier et gouvernorat → `donnees/appels-offres.json` |
| 1 b | `robot/lire_douane.py` | lit **1 page par jour** de la Douane tunisienne (ventes aux enchères publiques) → `donnees/encheres.json` |
| 1 c | `robot/prives.py` | lit les réponses du formulaire Google des entreprises (CSV publié), les **contrôle** → `donnees/prives.json` |
| 2 | `robot/construire_site.py` | fabrique les 40 pages : accueil, 10 métiers, 26 gouvernorats, à propos, publier, enchères, `sitemap.xml` ; résumés traduits par `robot/glossaire.py` |
| 3 | `tools/test_site.mjs` + `tools/test_pannes.py` | tests (le robot ne publie rien si un test échoue) |
| 4 | `robot/telegram.py` | UN message court groupé sur le canal Telegram (nouveaux par métier + « ⏰ Clôturent dans 2 jours ») ; mémoire `donnees/telegram-envoyes.json` |
| 5 | `.github/workflows/maj.yml` | fait 1 → 4 chaque jour à 6h05 (heure de Tunis) puis commit ; GitHub Pages republie |

**Réglages d'Ahmed : un seul fichier, `robot/reglages.py`** (adresse publique du canal Telegram, du canal WhatsApp,
du formulaire Google et de son CSV). Vide = bouton caché / « Bientôt ». Les jetons secrets ne vont JAMAIS dans ce fichier.

Pages : `index.html`, `metier/<métier>/`, `gouvernorat/<gouvernorat>/`, `a-propos/`, `publier/`, `encheres/`, `abonnement/`, `abonnement/conditions/`.
Fichiers à la main : `assets/style.css`, `assets/page.js` (langue, en-tête, pied), `assets/app.js` (filtres, tri,
recherche, étiquettes J-N, dates selon le téléphone du visiteur), `assets/logo.svg`, `assets/og-image-v6.jpg` (source : `tools/og-image.html`).
Photo du bandeau : **mosaïque de 4 vraies photos prises en Tunisie** (BTP, informatique, santé, port de Radès), car les
marchés publics ne sont pas que la construction : `assets/photos/marches-publics-mosaique.jpg` (ordinateur, 4 côte à côte) et
`-carre.jpg` (téléphone, 2 × 2). Wikimedia Commons : Habib M'henni (CC BY 4.0 et CC BY-SA 3.0), Touzrimounir (CC BY-SA 4.0),
M. Rais (CC BY-SA 3.0) ; crédit de chaque photo sous le bandeau, dans « À propos » et sur l'image d'aperçu ; preuves hors dépôt.
Toutes les pages : `translate="no"` + `<meta name="google" content="notranslate">` (Chrome proposait de traduire en anglais).
Icônes de métier et carte de la Tunisie : SVG faits maison.
**Votre avis** (accueil `#avis`, lien « Votre avis » dans le pied de page de toutes les pages) : note facultative (😀🙂😐🙁),
message (obligatoire, ≤ 1000 caractères), e-mail facultatif ; envoyé **seulement au clic** à Formspree (formulaire `mwlpakqj`,
commun à tous les sites d'Ahmed) avec les champs cachés `site` = « Alertes appels d'offres Tunisie » et `page`.
Code : `assets/avis.js` ; section : constante `AVIS` dans construire_site.py ; test : `node tools/test_avis.mjs` (envoi simulé).

## Lancer à la main (PC)
```
python robot/lire_haicop.py --max 40
python robot/lire_douane.py
python robot/prives.py
python robot/telegram.py --essai                   (affiche le message Telegram sans l'envoyer)
python robot/construire_site.py
npm install --no-save --no-package-lock jsdom     (une fois par PC)
node tools/test_site.mjs
node tools/test_sw.mjs
node tools/test_avis.mjs
python tools/test_pannes.py
bash tools/captures.sh                             (captures téléphone 340/390 px, FR + AR, dans captures/)
```

## Ce qu'Ahmed doit faire (une seule fois)

### 1. Canal Telegram (alertes quotidiennes)
1. Dans Telegram : Menu → **Nouveau canal** → nom « Alertes appels d'offres Tunisie », **public**, adresse par ex. `alertesaotunisie`.
2. Parler à **@BotFather** → `/newbot` → nom « Alertes AO Tunisie », identifiant finissant par `bot` → il donne un **jeton**
   (ne le donner à personne, ne jamais le coller dans le chat ni dans un fichier).
3. Dans le canal : Administrateurs → **Ajouter un administrateur** → le robot, avec le droit « Publier des messages ».
4. GitHub → dépôt `appels-offres-tunisie` → Settings → Secrets and variables → Actions → **New repository secret** :
   `TELEGRAM_BOT_TOKEN` = le jeton ; `TELEGRAM_CANAL` = `@alertesaotunisie` (l'adresse du canal avec @).
5. Dans `robot/reglages.py` : `TELEGRAM_CANAL_URL = "https://t.me/alertesaotunisie"` → le bouton « Recevoir les alertes
   sur Telegram » apparaît sur le site au prochain passage du robot.

Sans ces secrets, le robot ne fait rien (et ne sonne pas en échec). Un appel d'offres n'est **jamais** annoncé deux fois.

### 1 b. Alertes Pro (abonnement payant)
Les abonnés ne sont **jamais** dans ce dépôt public : ils sont dans le dépôt **privé** `Ah6259/appels-offres-abonnes`
(voir son README : activer un abonné depuis l'application GitHub du téléphone, bouton `activer-abonne`).
1. Créer le robot Telegram avec @BotFather (ou réutiliser celui du canal) et mettre son jeton dans les Secrets du dépôt
   **privé** : `TELEGRAM_BOT_TOKEN`.
2. Mettre son nom (sans @) dans `robot/reglages.py` : `TELEGRAM_ROBOT_ALERTES = "AlertesAOTunisieBot"`.
3. Chaque inscription arrive par e-mail (Formspree, ligne `pour_activer`) → bouton `activer-abonne` (action `essai`) →
   le résumé donne le CODE et un lien WhatsApp pour l'envoyer au client → le client envoie `/start CODE` au robot.
4. Preuve de paiement reçue sur WhatsApp → bouton `activer-abonne`, action `paye`, code + mois (1 ou 12) → facture.

### 2. WhatsApp (plus tard, rien à coder pour l'instant)
WhatsApp ne permet pas à un robot gratuit de publier dans un canal. Il faudra : créer un **canal WhatsApp**
(Actus → Canaux → Créer un canal), mettre son adresse dans `WHATSAPP_CANAL_URL` (`robot/reglages.py`) pour afficher
le bouton, puis recopier chaque jour le message Telegram (ou plus tard l'API WhatsApp Business, payante).

### 3. Formulaire « Publier un appel d'offres » (entreprises privées, gratuit)
1. https://forms.google.com → **Formulaire vide**, titre « Publier un appel d'offres — Alertes appels d'offres Tunisie ».
   Paramètres → Réponses : **ne pas** collecter les adresses e-mail. Créer ces questions, **dans cet ordre et avec ces
   mots** (le robot reconnaît les colonnes grâce à eux) :

   | Question | Type | Obligatoire |
   |---|---|---|
   | Nom de l'entreprise | Réponse courte | oui |
   | Objet de l'appel d'offres | Réponse courte (15 à 300 caractères) | oui |
   | Description (facultatif) | Paragraphe | non |
   | Métier | Liste déroulante : `BTP / génie civil`, `Électricité`, `Informatique`, `Fournitures et mobilier`, `Nettoyage / gardiennage`, `Alimentation`, `Médical / pharmacie`, `Transport / véhicules`, `Études / conseil`, `Autres` | oui |
   | Gouvernorat | Liste déroulante : Ariana, Béja, Ben Arous, Bizerte, Gabès, Gafsa, Jendouba, Kairouan, Kasserine, Kébili, Le Kef, Mahdia, La Manouba, Médenine, Monastir, Nabeul, Sfax, Sidi Bouzid, Siliana, Sousse, Tataouine, Tozeur, Tunis, Zaghouan, `Plusieurs gouvernorats`, `Toute la Tunisie` | oui |
   | Date limite de réception des offres | Date | oui |
   | Contact pour les candidats (e-mail ou téléphone de l'entreprise) | Réponse courte | oui |
   | Je certifie que ces informations sont exactes et j'accepte leur publication | Cases à cocher (une case « Oui ») | oui |
2. Onglet **Réponses** → icône Sheets → **Créer une feuille de calcul**. Dans la feuille : Fichier → Paramètres →
   Paramètres régionaux **France** (dates jj/mm/aaaa).
3. Feuille : Fichier → Partager → **Publier sur le Web** → feuille « Réponses au formulaire 1 » → format **CSV** →
   Publier → copier l'adresse (`https://docs.google.com/spreadsheets/d/e/…/pub?…output=csv`) dans `CSV_PRIVES_URL`.
4. Formulaire → **Envoyer** → lien → « Raccourcir l'URL » → copier (`https://forms.gle/…`) dans `FORMULAIRE_PRIVES_URL`.
5. Ensuite tout est automatique : chaque jour le robot contrôle (champs obligatoires, date limite à venir et ≤ 180 jours,
   pas de lien, pas de HTML, pas de publicité, pas de doublon, ≤ 3 par entreprise et par jour) et publie avec la mention
   « Publié par l'entreprise — non vérifié par HAICOP ». Pour retirer une annonce : **supprimer sa ligne** dans la feuille.

## Plan de continuité
Objectif : le site reste **en vie et honnête** même si la source tombe en panne ou si personne ne s'en occupe.

**Ce qui tourne tout seul**
- `maj.yml` chaque jour : lecture HAICOP → construction → tests → commit. Le `?v=` des fichiers CSS/JS est
  calculé automatiquement (empreinte des fichiers) : les téléphones ne gardent jamais un ancien style.
- `battement-de-coeur.yml` le 1er du mois : petit commit pour que GitHub ne mette pas les robots en pause
  (pause automatique après 60 jours sans activité).
- `tests.yml` à chaque envoi (push) : les tests (site, service worker, pannes).
- Les trois robots partagent le **groupe de concurrence** `maj-site` (jamais deux commits en même temps).

**Ce qui protège le site**
- Source en panne, liste vide, < 30 % du volume habituel, **format des fiches changé** (champs introuvables) :
  c'est une **panne**, jamais « aucun appel d'offres ». Les anciennes annonces sont gardées ; seules les annonces
  dont la date limite est passée disparaissent (calcul fait aussi avec la date du **téléphone du visiteur**).
- Fichier de données illisible, vide ou qui fond de plus de moitié : reprise de `donnees/appels-offres.sauvegarde.json`.
  Sans sauvegarde : le site déjà publié n'est **pas touché**.
- Bandeau daté « La source officielle n'a pas pu être lue depuis le … » dès que la dernière lecture réussie
  a **2 jours ou plus** (vérifié dans la page ET par le JavaScript selon la date du visiteur). La pastille
  « Mis à jour le … » donne toujours la date de la dernière lecture réussie.
- Textes de la source échappés, liens non officiels remplacés par le lien HAICOP de la fiche.
- **Ventes aux enchères (Douane)** : page injoignable, tableau introuvable, < 30 % des lignes d'avant = panne ; anciennes
  ventes gardées (les expirées disparaissent), bandeau daté sur la page enchères après 2 jours sans lecture, « échec » au journal.
- **Entreprises privées** : CSV injoignable, vide, corrompu ou colonnes changées = les publications déjà acceptées sont
  gardées. Les réponses refusées ne sont jamais publiées (seule la raison est gardée, sans leur contenu).
- **Telegram** : secrets absents = rien ; Telegram en erreur = « échec » au journal, le site n'est pas touché, et les
  messages non partis repartent au passage suivant (jamais deux fois le même appel d'offres).
- **Réglages mal écrits** (`robot/reglages.py`) : ignorés, bouton caché, « échec » au journal.
- **Sécurité** : robots.txt (moteurs de recherche oui, robots d'IA et aspirateurs non), `noai`, CSP stricte en balise meta,
  anti-iframe, protection légère contre la copie (numéros Tender, liens et champs restent copiables), aucun secret dans le
  dépôt (vérifié par le test). Limite : un site GitHub Pages en sous-dossier n'a pas son propre robots.txt pour les robots
  (seul `ah6259.github.io/robots.txt` compte) → le copier dans un dépôt `Ah6259.github.io`, ou plus tard avec un nom de domaine.
  Ce qu'un visiteur voit peut toujours être recopié : la vraie protection = © + preuves datées.

- **Installation sur le téléphone** : `sw.js` (service worker) = **réseau d'abord** pour les pages et les données (le cache
  ne sert que hors connexion : jamais une vieille liste quand Internet marche) ; CSS/JS versionnés (?v=) = cache puis mise à jour.
  Si un téléphone garde une vieille version : changer `CACHE_VERSION` dans `sw.js`.

**Ce qui alerte**
- Une **issue GitHub** « Source HAICOP en panne depuis le … » s'ouvre au premier échec (GitHub envoie un e-mail),
  reçoit un commentaire à chaque jour de panne, et **se ferme toute seule** quand la lecture remarche.
- Le mot « échec » apparaît dans les journaux des robots (onglet Actions) : toujours les lire.
- Si les tests échouent, le robot s'arrête en rouge (e-mail de GitHub) et ne publie rien.
- État lisible par tous : `donnees/etat-source.json`.

**Quoi faire si une alerte arrive**
1. Ouvrir le journal indiqué dans l'issue (lien « Journal ») et lire les lignes « échec ».
2. Ouvrir https://www.marchespublics.gov.tn/fr/appels-doffres dans un navigateur :
   - le portail est en panne → rien à faire, le site attend et l'issue se fermera seule ;
   - le portail marche mais a changé d'aspect (« format des fiches changé ») → demander à Claude d'adapter
     `lire_fiche()` dans `robot/lire_haicop.py`, puis relancer les deux tests ;
   - le portail bloque les robots (code 403, page « humain ») → **ne jamais contourner** : écrire à la HAICOP
     pour demander l'autorisation.
3. Relancer à la main : onglet Actions → `maj-appels-offres` → « Run workflow »
   (ou `gh workflow run maj.yml -R Ah6259/appels-offres-tunisie`).

## Droits
LICENSE « tous droits réservés ». Les annonces viennent du portail officiel de la HAICOP ; chaque carte renvoie
à la fiche officielle, seule à faire foi.

## Nouveautés
- 05/10/2026 : nouvelle icône (mégaphone) et « consultation gratuite » dans les titres Google.
- 06/10/2026 : partie payante « Alertes Pro » (page abonnement, conditions, bouton doré, dépôt privé des abonnés).
