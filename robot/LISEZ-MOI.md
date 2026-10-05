# Robot « appels d'offres Tunisie » — mode d'emploi

> Depuis le 05/10/2026, les dossiers `robot\` et `donnees\` sont DANS `site\` (le futur dépôt GitHub).
> Le site se construit ensuite avec `python robot\construire_site.py` (voir README du site).

## Ce que fait le robot
`lire_haicop.py` lit les **appels d'offres publics tunisiens** sur le portail officiel de la
**HAICOP** (https://www.marchespublics.gov.tn/fr/appels-doffres). Il n'utilise **pas** TUNEPS.

1. Il demande au portail la **liste des appels d'offres les plus récents**
   (la même liste que celle affichée sur la page, mais sous forme de données).
2. Il ouvre **chaque fiche** (ex. `.../appels-doffres/Tender-104049`) **lentement** :
   une page toutes les 2,5 secondes, avec un nom de robot honnête (« alertes-ao-tunisie »).
3. Il recopie l'essentiel : numéro, objet, acheteur public, type de commande, procédure,
   région d'exécution, date de publication, **date limite + heure**, cautionnement provisoire,
   spécialité / catégorie, nombre de lots, **lien vers la fiche officielle**.
4. Il range chaque appel d'offres :
   - par **métier** : BTP / génie civil, électricité, informatique, fournitures de bureau,
     nettoyage / gardiennage, alimentation, médical, transport / véhicules, études / conseil, autres ;
   - par **gouvernorat** (les 24), ou « Plusieurs gouvernorats » / « National / non précisé ».
5. Il écrit deux fichiers dans le dossier `donnees\` :
   - `appels-offres.json` : la **mémoire** du robot. Une fiche déjà lue n'est **jamais relue**.
   - `du-jour.md` : la **liste lisible** des appels d'offres récents encore ouverts,
     triée par métier puis par gouvernorat, avec la date limite, le lien et « source : HAICOP ».

## Comment le lancer
Ouvrir un terminal dans le dossier `robot` puis :

```
python lire_haicop.py              (lit les 30 derniers appels d'offres)
python lire_haicop.py --max 10     (seulement 10 fiches)
python lire_haicop.py --jours 3    (du-jour.md : publiés ces 3 derniers jours, par défaut)
```

Rien à installer : Python suffit. Compter environ **1 minute 30 pour 30 fiches** (c'est voulu : lecture lente).
Environ 14 nouveaux appels d'offres paraissent chaque jour : `--max 30` une ou deux fois par jour suffit.

Si les règles de classement sont améliorées, le robot **reclasse tout seul** les appels d'offres déjà en
mémoire, sans relire le site.

## Résultat du premier essai (04/10/2026, depuis le PC)
- 30 fiches lues, 0 échec (Tender-104009 à Tender-104049, publiées les 02 et 03/10/2026).
- Classement : 13 BTP, 4 études, 3 alimentation, 2 fournitures, 2 transport, 1 informatique,
  1 nettoyage, 1 électricité, 3 autres.

## Test « GitHub peut-il lire le site ? » (04/10/2026)
Fait avec le robot manuel `tester-source.yml` du dépôt `prix-eaux-tunisie` (aucune modification de ce dépôt).

| Adresse testée | Code HTTP | Taille | Blocage anti-robot |
|---|---|---|---|
| Fiche `Tender-104049` | **200** | 68 Ko (page complète) | aucun |
| Page liste `appels-doffres` | **200** | 370 Ko | aucun |

`robots.txt` vu depuis GitHub : `User-agent: *` / `Disallow:` → tous les robots autorisés.
**Conclusion : les serveurs GitHub peuvent lire le site** ; le robot pourra tourner automatiquement sur GitHub.

À noter : la liste des numéros récents est demandée « comme le fait la page » (données JSON) ;
ce test-là n'a pas pu être fait depuis GitHub (le robot de test n'envoie pas les mêmes en-têtes),
mais c'est la même adresse que la page liste, qui passe. Si un jour la liste ne répond plus,
le robot a un **plan B** : il essaie les numéros qui suivent le dernier connu (Tender-N+1, N+2…).

## Pannes (ajouté le 05/10/2026)
Chaque passage écrit dans `appels-offres.json` :
- `statut_source` : `ok` ou `panne` (avec la date « depuis » et la raison) ;
- `derniere_lecture_reussie` : date de la dernière lecture correcte.

Sont des **pannes** (jamais « aucun appel d'offres ») : portail injoignable, liste vide ou < 30 % du volume
demandé sans fiche lisible derrière, **format changé** (page reçue mais champs introuvables), 3 fiches injoignables
ou plus. Les anciennes fiches sont toujours gardées. Code de sortie 1 en cas de panne.

## Limites connues
- Le classement par métier se fait par **mots-clés** (français + arabe) et par le « type de commande »
  officiel : quelques erreurs sont possibles (ex. un achat déclaré « Matériels électriques » par un restaurant).
- Les objets sont souvent **en arabe** : ils sont recopiés tels quels.
- Seule la fiche officielle fait foi ; le cahier des charges reste à retirer sur TUNEPS.
