# -*- coding: utf-8 -*-
"""Date HONNÊTE de chaque adresse du plan du site (<lastmod>), 25/11/2026 (plan Google B.2).

Avant : toutes les pages portaient la date du jour chaque nuit (Google n'y croit plus). Maintenant la date d'une page
ne change que si son CONTENU UTILE change : empreinte (sha1) du HTML sans les dates (« Prix relevés le 25/11/2026 »,
2026-11-25…), sans les ?v= et sans les espaces ; mémoire dans data/lastmod.json {chemin: {"empreinte", "date"}}.

Page inconnue de la mémoire : on remonte l'historique git du fichier (dernier commit dont le contenu utile est le même)
pour retrouver la vraie date ; fichier jamais enregistré = page nouvelle = date du jour. Rien n'est jamais inventé.
"""
import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path

MOIS = ("janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre|"
        "جانفي|فيفري|مارس|أفريل|ماي|جوان|جويلية|أوت|سبتمبر|أكتوبر|نوفمبر|ديسمبر|يناير|فبراير|أبريل|مايو|يونيو|يوليو|أغسطس")
_DATES = [
    re.compile(r"\?v=[\w.-]+"),
    re.compile(r"\d{4}-\d{2}-\d{2}(?:T[\d:.]+(?:Z|[+-]\d{2}:?\d{2})?)?"),
    re.compile(r"\d{1,2}/\d{1,2}/\d{4}"),
    re.compile(r"(?<![\d,.])\d{1,2}:\d{2}(?::\d{2})?(?![\d,.])"),        # heure du relevé (« 16:42 »)
    re.compile(r"\d{1,2}(?:er)?(?:\s|&nbsp;| )+(?:" + MOIS + r")(?:\s|&nbsp;| )+\d{4}", re.I),
]


VERSION = 2   # à augmenter si la façon de calculer l'empreinte change : la mémoire est alors refaite depuis git, jamais « aujourd'hui »


def empreinte(html, ignorer=()):
    """Empreinte du contenu utile d'une page : sans dates, sans ?v=, sans espaces, sans les textes propres au site qui
    changent chaque jour sans que la page change (ignorer = expressions régulières, ex. compte à rebours « encore 3 jours »)."""
    for r in list(ignorer) + _DATES:
        html = r.sub("", html)
    return hashlib.sha1(re.sub(r"\s+", "", html).encode("utf-8")).hexdigest()[:16]


def _date_git(racine, fichier, emp, ignorer=()):
    """Date du plus ancien commit d'une suite ininterrompue de commits où le fichier a cette même empreinte."""
    try:
        log = subprocess.run(["git", "-C", str(racine), "log", "--format=%H %cs", "--", fichier],
                             capture_output=True, text=True, timeout=60).stdout.split("\n")
    except Exception:
        return None
    trouve = None
    for ligne in filter(None, log):
        h, d = ligne.split()
        try:
            contenu = subprocess.run(["git", "-C", str(racine), "show", f"{h}:{fichier}"],
                                     capture_output=True, text=True, timeout=60).stdout
        except Exception:
            break
        if empreinte(contenu, ignorer) != emp:
            break
        trouve = d
    return trouve


def dates(racine, chemins, aujourd_hui=None, memoire="donnees/lastmod.json", ignorer=()):
    """chemins = fichiers HTML relatifs à la racine (ex. « gouvernorat/tunis/index.html »).
    Renvoie {chemin: date ISO} et réécrit la mémoire (seulement les chemins donnés : une page retirée est oubliée)."""
    racine = Path(racine)
    jour = aujourd_hui or date.today().isoformat()
    f = racine / memoire
    try:
        mem = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        mem = {}
    if mem.pop("_version", 1) != VERSION:
        mem = {c: {"date": x.get("date")} for c, x in mem.items() if isinstance(x, dict)}   # empreintes à refaire
    neuf, res = {}, {}
    for c in chemins:
        p = racine / c
        if not p.exists():
            continue
        emp = empreinte(p.read_text(encoding="utf-8"), ignorer)
        ancien = mem.get(c)
        if ancien and ancien.get("empreinte") == emp:
            d = ancien["date"]                     # contenu inchangé : la date reste
        elif ancien and "empreinte" in ancien:
            d = jour                               # contenu changé : date du jour
        else:
            d = _date_git(racine, c, emp, ignorer) or jour  # page inconnue : sa vraie date dans git, sinon nouvelle
        neuf[c] = {"empreinte": emp, "date": d}
        res[c] = d
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"_version": VERSION, **dict(sorted(neuf.items()))}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return res
