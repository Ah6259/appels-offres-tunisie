# -*- coding: utf-8 -*-
"""
Appels d'offres publiés GRATUITEMENT par les entreprises privées (Google Forms -> feuille publiée en CSV).

Lit le CSV dont l'adresse est dans robot/reglages.py (CSV_PRIVES_URL), contrôle chaque réponse
AUTOMATIQUEMENT et écrit donnees/prives.json (lu par construire_site.py) :
  - champs obligatoires présents, métier et gouvernorat connus, case « je certifie » cochée ;
  - date limite à venir (au plus 180 jours) ;
  - pas de lien Internet ni d'adresse de site, pas de HTML, pas de mots de publicité ;
  - longueurs raisonnables, contact = e-mail ou téléphone ;
  - pas de doublon (même entreprise + même objet), au plus 3 publications par entreprise et par jour.
Les réponses refusées ne sont JAMAIS publiées (seulement la raison, sans leur contenu).

Pannes : CSV injoignable, vide, corrompu ou colonnes introuvables -> les publications déjà acceptées
sont gardées (jamais « aucun appel d'offres »), « échec » au journal, code 1.
La feuille Google reste la référence : une ligne supprimée par Ahmed disparaît du site au passage suivant.

    python robot/prives.py
    python robot/prives.py --csv fichier.csv --aujourdhui 2026-10-05     (tests)
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import reglages   # noqa: E402

FICHIER = os.path.join(os.path.dirname(ICI), "donnees", "prives.json")
UA = "Mozilla/5.0 (compatible; alertes-ao-tunisie)"
MAX_JOURS = 180
MAX_PAR_ENTREPRISE = 3

# Choix proposés dans le formulaire -> adresse de la page (mêmes listes que construire_site.py)
METIERS = {
    "btp / genie civil": "btp-genie-civil", "electricite": "electricite", "informatique": "informatique",
    "fournitures et mobilier": "fournitures-bureau", "nettoyage / gardiennage": "nettoyage-gardiennage",
    "alimentation": "alimentation", "medical / pharmacie": "medical", "transport / vehicules": "transport-vehicules",
    "etudes / conseil": "etudes-conseil", "autres": "autres",
}
GOUVERNORATS = {
    "ariana": "ariana", "beja": "beja", "ben arous": "ben-arous", "bizerte": "bizerte", "gabes": "gabes", "gafsa": "gafsa",
    "jendouba": "jendouba", "kairouan": "kairouan", "kasserine": "kasserine", "kebili": "kebili", "le kef": "le-kef",
    "mahdia": "mahdia", "la manouba": "la-manouba", "medenine": "medenine", "monastir": "monastir", "nabeul": "nabeul",
    "sfax": "sfax", "sidi bouzid": "sidi-bouzid", "siliana": "siliana", "sousse": "sousse", "tataouine": "tataouine",
    "tozeur": "tozeur", "tunis": "tunis", "zaghouan": "zaghouan", "plusieurs gouvernorats": "plusieurs",
    "toute la tunisie": "national",
}
# En-têtes des colonnes du CSV (mots cherchés dans l'intitulé de la question, sans accents)
COLONNES = {
    "horodatage": ("horodat", "timestamp", "date et heure"),
    "entreprise": ("entreprise", "societe"),
    "objet": ("objet",),
    "description": ("description", "details"),
    "metier": ("metier", "domaine"),
    "gouvernorat": ("gouvernorat",),
    "date_limite": ("date limite",),
    "contact": ("contact",),
    "certification": ("certifie",),
}
OBLIGATOIRES = ("entreprise", "objet", "metier", "gouvernorat", "date_limite", "contact", "certification")
LIEN = re.compile(r"(https?:|www\.|://|\b[a-z0-9-]+\.(com|net|org|info|biz|xyz|top|click|io|me|ly|ru|tk|ml|site|online|shop|tn|fr)\b"
                  r"|\bt\.me\b|\bwa\.me\b|bit\.ly)", re.I)
HTML = re.compile(r"<\s*/?\s*[a-z!]|&#?\w+;|javascript:", re.I)
PUB = re.compile(r"\b(casino|crypto|bitcoin|forex|viagra|porn|sexe?|xxx|pret rapide|credit rapide|gagnez|gagner de l'argent|"
                 r"investissement garanti|loterie|lottery|betting|paris sportifs|followers|promo code)\b", re.I)
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def sans_accents(t):
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip()


def lire_date(t):
    t = str(t or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t) or re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if not m:
        return ""
    a, b, c = m.groups()
    try:
        return (dt.date(int(a), int(b), int(c)) if len(a) == 4 else dt.date(int(c), int(b), int(a))).isoformat()
    except ValueError:
        return ""


def colonnes(entetes):
    pos = {}
    for i, e in enumerate(entetes):
        e = sans_accents(e)
        for cle, mots in COLONNES.items():
            if cle not in pos and any(m in e for m in mots):
                pos[cle] = i
                break
    return pos


def controler(r, jour, deja, par_entreprise):
    """Renvoie (publication, None) ou (None, raison du refus)."""
    for k in OBLIGATOIRES:
        if not r.get(k, "").strip():
            return None, f"champ obligatoire vide : {k}"
    texte = " ".join(r.get(k, "") for k in ("entreprise", "objet", "description", "metier", "gouvernorat"))
    contact = r["contact"].strip()
    if HTML.search(texte + " " + contact):
        return None, "HTML ou code interdit"
    sans_mail = EMAIL.sub("", contact) if EMAIL.match(contact) else contact
    if LIEN.search(texte) or LIEN.search(sans_mail):
        return None, "lien Internet interdit"
    if PUB.search(sans_accents(texte)):
        return None, "publicité / spam"
    if not 2 <= len(r["entreprise"].strip()) <= 120:
        return None, "nom d'entreprise trop court ou trop long"
    if not 15 <= len(r["objet"].strip()) <= 300:
        return None, "objet trop court (15 caractères min.) ou trop long (300 max.)"
    if len(r.get("description", "")) > 1500:
        return None, "description trop longue (1500 caractères max.)"
    if re.search(r"(.)\1{7,}", texte):
        return None, "texte suspect (caractère répété)"
    chiffres = re.sub(r"\D", "", contact)
    if not (EMAIL.match(contact) or (8 <= len(chiffres) <= 15 and re.fullmatch(r"[\d +().-]+", contact))):
        return None, "contact invalide (e-mail ou téléphone)"
    metier = METIERS.get(sans_accents(r["metier"]))
    gouv = GOUVERNORATS.get(sans_accents(r["gouvernorat"]))
    if not metier or not gouv:
        return None, "métier ou gouvernorat inconnu"
    limite = lire_date(r["date_limite"])
    if not limite:
        return None, "date limite illisible"
    if limite <= jour:
        return None, "date limite passée ou aujourd'hui"
    if limite > (dt.date.fromisoformat(jour) + dt.timedelta(days=MAX_JOURS)).isoformat():
        return None, "date limite trop lointaine"
    ent = sans_accents(r["entreprise"])
    cle = ent + "|" + sans_accents(r["objet"])
    if cle in deja:
        return None, "doublon"
    recu = r.get("horodatage", "")
    jour_recu = recu.split(" ")[0]
    if par_entreprise.get((ent, jour_recu), 0) >= MAX_PAR_ENTREPRISE:
        return None, "trop de publications le même jour pour cette entreprise"
    deja.add(cle)
    par_entreprise[(ent, jour_recu)] = par_entreprise.get((ent, jour_recu), 0) + 1
    nettoie = lambda t, n: re.sub(r"\s+", " ", str(t or "")).strip()[:n]
    return {
        "id": "Prive-" + hashlib.sha1((recu + "|" + cle).encode("utf-8")).hexdigest()[:10],
        "entreprise": nettoie(r["entreprise"], 120), "objet": nettoie(r["objet"], 300),
        "description": nettoie(r.get("description"), 1500), "metier": metier, "gouvernorat": gouv,
        "date_limite": limite, "contact": nettoie(contact, 120), "recu_le": recu[:40],
        "mention": "Publié par l'entreprise — non vérifié par HAICOP",
    }, None


def analyser(texte_csv, jour):
    """(publications, refus) ou lève ValueError si le CSV est vide, corrompu ou sans les bonnes colonnes."""
    if not texte_csv or not texte_csv.strip():
        raise ValueError("CSV vide")
    if texte_csv.lstrip()[:1] == "<":
        raise ValueError("ce n'est pas un CSV (page HTML reçue)")
    try:
        lignes = list(csv.reader(io.StringIO(texte_csv.lstrip("﻿"))))
    except csv.Error as e:
        raise ValueError(f"CSV corrompu ({e})")
    if not lignes:
        raise ValueError("CSV vide")
    pos = colonnes(lignes[0])
    manquantes = [k for k in OBLIGATOIRES if k not in pos]
    if manquantes:
        raise ValueError("colonnes introuvables : " + ", ".join(manquantes))
    pubs, refus, deja, par_ent = [], [], set(), {}
    for ligne in lignes[1:]:
        if not any(c.strip() for c in ligne):
            continue
        r = {k: (ligne[i] if i < len(ligne) else "") for k, i in pos.items()}
        p, raison = controler(r, jour, deja, par_ent)
        if p:
            pubs.append(p)
        else:
            refus.append({"recu_le": str(r.get("horodatage", ""))[:40], "raison": raison})
    return pubs, refus


def telecharger(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        if r.status != 200:
            raise ValueError(f"code HTTP {r.status}")
        return r.read().decode("utf-8", errors="replace")


def charger_ancien():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def sauver(d):
    os.makedirs(os.path.dirname(FICHIER), exist_ok=True)
    tmp = FICHIER + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FICHIER)


def main():
    p = argparse.ArgumentParser(description="Publications des entreprises privées (Google Forms -> CSV).")
    p.add_argument("--csv", help="fichier CSV local (tests) au lieu de l'adresse de reglages.py")
    p.add_argument("--aujourdhui", default=dt.date.today().isoformat())
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    url = str(getattr(reglages, "CSV_PRIVES_URL", "") or "").strip()
    print("Appels d'offres des entreprises privées…")
    if not a.csv and not url:
        print("  formulaire pas encore configuré (CSV_PRIVES_URL vide dans robot/reglages.py) : rien à faire")
        return 0
    if not a.csv and not re.fullmatch(r"https://docs\.google\.com/spreadsheets/[A-Za-z0-9_/=?&.-]{10,300}", url):
        print("  ! échec : CSV_PRIVES_URL mal écrite (doit commencer par https://docs.google.com/spreadsheets/) : rien changé")
        return 1
    ancien = charger_ancien()
    maintenant = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        if a.csv:
            with open(a.csv, encoding="utf-8", errors="replace") as f:
                brut = f.read()
        else:
            brut = telecharger(url)
        pubs, refus = analyser(brut, a.aujourdhui)
    except Exception as e:     # réseau, CSV vide ou corrompu : on garde les publications déjà acceptées
        ancien["statut"] = {"etat": "panne", "depuis": (ancien.get("statut") or {}).get("depuis") if (ancien.get("statut") or {}).get("etat") == "panne" else maintenant,
                            "raison": str(e)[:200]}
        ancien.setdefault("publies", [])
        sauver(ancien)
        print(f"  ! échec : {e} — {len(ancien['publies'])} publications déjà acceptées gardées")
        return 1
    sauver({"publies": pubs, "refuses": refus[-200:], "derniere_lecture": maintenant,
            "statut": {"etat": "ok", "depuis": maintenant, "raison": ""}})
    print(f"  {len(pubs)} publiées, {len(refus)} refusées" + "".join(f"\n   refus : {r['raison']}" for r in refus[-10:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
