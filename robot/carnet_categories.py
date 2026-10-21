# -*- coding: utf-8 -*-
"""Carnet de ce qu'un robot n'a su ranger dans AUCUNE catégorie (outil COMMUN, règle commune § 40, 21/10/2026).

Copie IDENTIQUE dans chaque site (l'audit commun le vérifie) : ne pas la modifier dans un site, mais dans
« outils communs/carnet-categories/ » du dépôt projets-ahmed, puis la recopier partout.

Principe : rien n'est rangé en silence dans « Autres » ou jeté. Le robot note chaque élément non classé ;
une routine (Claude dans le nuage) lit le carnet et ajoute des mots-clés ou une nouvelle catégorie.

    import carnet_categories as CC
    CC.noter("donnees/sans-metier.json", [{"cle": "…", "texte": "…", "source": "…"}, …], "2026-10-21")

Chaque élément : « cle » (unique : lien, numéro…), « texte » (ce qu'il faudrait ranger) et d'autres champs libres.
Le carnet garde, par clé : premier et dernier jour vus ; il oublie ce qui n'a pas été revu depuis 120 jours (1000 au plus).
"""
import datetime as dt
import json
import os

GARDE_JOURS = 120
MAXI = 1000


def lire(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("elements"), list):
            return d
    except (OSError, ValueError):
        pass
    return {"elements": []}


def noter(chemin, elements, jour, explication=""):
    """Ajoute les éléments non classés du jour au carnet ; renvoie le nombre d'éléments gardés."""
    par_cle = {e["cle"]: e for e in lire(chemin)["elements"] if isinstance(e, dict) and e.get("cle")}
    for e in elements:
        if not isinstance(e, dict) or not e.get("cle"):
            continue
        vieux = par_cle.get(e["cle"]) or {}
        par_cle[e["cle"]] = {**e, "premier_vu": vieux.get("premier_vu") or jour, "dernier_vu": jour}
    limite = (dt.date.fromisoformat(jour) - dt.timedelta(days=GARDE_JOURS)).isoformat()
    garde = sorted((e for e in par_cle.values() if (e.get("dernier_vu") or "") >= limite),
                   key=lambda e: (e["dernier_vu"], e["cle"]), reverse=True)[:MAXI]
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"maj": jour, "explication": explication or "Éléments lus par le robot mais rangés dans aucune catégorie "
                   "(gardés 120 jours) : une routine y cherche les thèmes qui reviennent (règle commune § 40).",
                   "nombre": len(garde), "elements": garde}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, chemin)
    return len(garde)


if __name__ == "__main__":   # essai rapide : python carnet_categories.py
    import tempfile
    d = tempfile.mkdtemp()
    c = os.path.join(d, "donnees", "sans-x.json")
    assert noter(c, [{"cle": "a", "texte": "A"}, {"cle": "b", "texte": "B"}], "2026-10-01") == 2
    assert noter(c, [{"cle": "a", "texte": "A"}], "2026-10-05") == 2
    e = {x["cle"]: x for x in lire(c)["elements"]}
    assert e["a"]["premier_vu"] == "2026-10-01" and e["a"]["dernier_vu"] == "2026-10-05"
    assert noter(c, [{"cle": "a", "texte": "A"}], "2027-02-10") == 1    # « b » oublié après 120 jours
    print("carnet_categories : tout est bon")
