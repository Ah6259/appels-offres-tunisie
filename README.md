# Alertes appels d'offres Tunisie

Site gratuit, sans inscription : chaque jour, les nouveaux **appels d'offres publics tunisiens**,
triés **par métier** et **par gouvernorat**, avec la date limite (en rouge à moins de 7 jours),
la caution provisoire et le lien vers la **fiche officielle**. Français + arabe (`?lang=ar`).

- Adresse prévue : https://ah6259.github.io/appels-offres-tunisie/
- Source unique : portail officiel de la **HAICOP** (Haute Instance de la Commande Publique,
  www.marchespublics.gov.tn). Le cahier des charges se retire sur **TUNEPS**. Ce site n'est pas officiel.

## Comment ça marche
| Étape | Fichier | Rôle |
|---|---|---|
| 1 | `robot/lire_haicop.py` | lit **lentement** les nouvelles fiches (1 page / 2,5 s), les classe par métier et gouvernorat → `donnees/appels-offres.json` |
| 2 | `robot/construire_site.py` | fabrique les 38 pages : accueil, 10 pages métier, 26 pages gouvernorat, à propos, `sitemap.xml` |
| 3 | `tools/test_site.mjs` + `tools/test_pannes.py` | tests (le robot ne publie rien si un test échoue) |
| 4 | `.github/workflows/maj.yml` | fait 1 → 2 → 3 chaque jour à 6h05 (heure de Tunis) puis commit ; GitHub Pages republie |

Pages : `index.html`, `metier/<métier>/`, `gouvernorat/<gouvernorat>/`, `a-propos/`.
Fichiers à la main : `assets/style.css`, `assets/page.js` (langue, en-tête, pied), `assets/app.js` (filtres, tri,
dates selon le téléphone du visiteur), `assets/logo.svg`, `assets/og-image-v1.png` (source : `tools/og-image.html`).
Images faites maison en SVG : illustration du bandeau (`assets/illustration-accueil.svg`, écrite par le constructeur),
une icône par métier, carte schématique de la Tunisie (une bulle par gouvernorat).

## Lancer à la main (PC)
```
python robot/lire_haicop.py --max 40
python robot/construire_site.py
npm install --no-save --no-package-lock jsdom     (une fois par PC)
node tools/test_site.mjs
python tools/test_pannes.py
bash tools/captures.sh                             (captures téléphone 340/390 px, FR + AR, dans captures/)
```

## Plan de continuité
Objectif : le site reste **en vie et honnête** même si la source tombe en panne ou si personne ne s'en occupe.

**Ce qui tourne tout seul**
- `maj.yml` chaque jour : lecture HAICOP → construction → tests → commit. Le `?v=` des fichiers CSS/JS est
  calculé automatiquement (empreinte des fichiers) : les téléphones ne gardent jamais un ancien style.
- `battement-de-coeur.yml` le 1er du mois : petit commit pour que GitHub ne mette pas les robots en pause
  (pause automatique après 60 jours sans activité).
- `tests.yml` à chaque envoi (push) : les deux tests.
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
