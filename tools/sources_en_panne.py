"""Alerte « ventes aux enchères en panne » (15/10/2026, règle commune § 17 : aucun robot vert qui ne fait rien).

La source HAICOP a déjà son alerte (issue GitHub ouverte et fermée par maj.yml). La page de la DOUANE, elle, ne prévenait
personne : l'étape affichait « échec » et le robot restait vert (seul un bandeau prévenait les visiteurs).
Lancé APRÈS l'enregistrement par maj.yml : dernière lecture réussie de plus de JOURS jours -> échec (GitHub prévient Ahmed
par e-mail). Les autres données sont déjà enregistrées. Même chose pour la feuille des publications des entreprises,
dès qu'elle est branchée (reglages.CSV_PRIVES_URL).
"""
import datetime as dt
import json
import os
import re
import sys

JOURS = 2
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SOMMEIL AUTOMATIQUE (06/11/2026, règle commune § 55, Ahmed : « si le problème se reproduit, il est réglé automatiquement ») :
# une source dont le SITE refuse la connexion (refus, délai, 403/429/5xx, adresse introuvable : rien à réparer chez nous, jamais
# de contournement) est réessayée à chaque passage et revient seule ; pas d'échec pendant SOMMEIL_MAX_JOURS après sa dernière
# lecture réussie (ligne « SOMMEIL »), puis l'alarme sonne (décider de la retirer). Une erreur de lecture CHEZ NOUS (page
# changée, liste trop courte…) sonne toujours après JOURS jours.
SOMMEIL_MAX_JOURS = 30
EXTERNE = re.compile(r"refused|reset by peer|timed? ?out|Errno (101|104|110|111|113)|HTTP Error (403|429|5\d\d)|injoignable|"
                     r"Temporary failure|Name or service not known|unreachable|No route to host|Cloudflare", re.I)


def en_sommeil(derniere, raison, jour):
    """Date de fin du sommeil si la panne vient du site lui-même et dure depuis moins de SOMMEIL_MAX_JOURS, sinon None."""
    if not derniere or not raison or not EXTERNE.search(raison):
        return None
    fin = (dt.date.fromisoformat(str(derniere)[:10]) + dt.timedelta(days=SOMMEIL_MAX_JOURS)).isoformat()
    return fin if jour <= fin else None


def en_panne(encheres, jour, prives=None, csv_prives=""):
    """prives / csv_prives : publications des entreprises (formulaire Google) — surveillées seulement si la feuille est branchée."""
    lim = (dt.date.fromisoformat(jour) - dt.timedelta(days=JOURS)).isoformat()
    d = str(encheres.get("derniere_lecture_reussie") or "")[:10]
    raison = (encheres.get("statut_source") or {}).get("raison") or ""
    out = [("ventes aux enchères (Douane)", d, raison)] if d < lim else []
    dp = str((prives or {}).get("derniere_lecture") or "")[:10]
    if csv_prives and dp < lim:
        out.append(("publications des entreprises (feuille Google)", dp, "feuille illisible ou débranchée"))
    return out


if __name__ == "__main__":
    for _f in (sys.stdout, sys.stderr):
        if hasattr(_f, "reconfigure"):
            _f.reconfigure(encoding="utf-8", errors="replace")
    lire = lambda n: json.load(open(os.path.join(RACINE, "donnees", n), encoding="utf-8")) if os.path.exists(os.path.join(RACINE, "donnees", n)) else {}
    sys.path.insert(0, os.path.join(RACINE, "robot"))
    import reglages
    p = en_panne(lire("encheres.json"), dt.date.today().isoformat(), lire("prives.json"), getattr(reglages, "CSV_PRIVES_URL", ""))
    auj = dt.date.today().isoformat()
    dors = [x for x in p if en_sommeil(x[1], x[2], auj)]
    p = [x for x in p if x not in dors]
    for s, d, r in dors:
        print(f"SOMMEIL source {s} : son site refuse la connexion depuis le {d} ({r}) — réessayée à chaque passage, revient seule ; "
              f"alarme après le {en_sommeil(d, r, auj)} (décider alors de la retirer)")
    for s, d, r in p:
        print(f"ÉCHEC source {s} : dernière lecture réussie le {d or 'jamais'} ({r}) — à réparer")
    sys.exit(1 if p else 0)
