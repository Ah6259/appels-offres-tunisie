# -*- coding: utf-8 -*-
"""
Robot « ventes aux enchères publiques » : lit UNE page officielle par jour, celle de la Douane tunisienne
https://www.douane.gov.tn/ventes-aux-encheres-publiques/  (robots.txt : tous les robots autorisés ;
preuves datées dans « preuves conditions d'utilisation/2026-10-05 », hors du dépôt).

Écrit donnees/encheres.json : seulement les FAITS de chaque avis (date, bureau des douanes, objet, échéance)
et le lien vers l'avis officiel (PDF). Les PDF ne sont pas téléchargés.

Pannes (jamais « aucune vente ») : page injoignable, tableau introuvable (format changé), moins de 30 % du
nombre de lignes de la fois précédente -> anciennes ventes gardées, statut « panne », code de sortie 1.

    python robot/lire_douane.py
"""
import datetime as dt
import hashlib
import html
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from lire_haicop import trouver_gouvernorats   # noqa: E402

URL = "https://www.douane.gov.tn/ventes-aux-encheres-publiques/"
PREFIXE = "https://www.douane.gov.tn/"
UA = "Mozilla/5.0 (compatible; alertes-ao-tunisie; robot lent, 1 page par jour)"
FICHIER = os.path.join(os.path.dirname(ICI), "donnees", "encheres.json")
GARDER_JOURS = 60          # ventes dont l'échéance est passée depuis plus de 60 jours : oubliées
SEUIL_CHUTE = 0.3

# Bureaux des douanes -> gouvernorat (quand le nom du gouvernorat n'apparaît pas dans le nom du bureau)
VILLES = {
    "menzel bourguiba": "Bizerte", "dehiba": "Tataouine", "ras jedir": "Médenine", "ben guerdane": "Médenine",
    "djerba": "Médenine", "zarzis": "Médenine", "hazoua": "Tozeur", "nefta": "Tozeur", "tunis-carthage": "Tunis",
    "carthage": "Tunis", "goulette": "Tunis", "kalaat senan": "Le Kef", "kalaa khasba": "Le Kef", "sidi youssef": "Le Kef", "mednine": "Médenine", "mehdia": "Mahdia",
    "gahr dimaou": "Jendouba", "ghar dimaou": "Jendouba", "hidra": "Kasserine", "rades": "Ben Arous", "radès": "Ben Arous", "ghardimaou": "Jendouba",
    "tabarka": "Jendouba", "melloula": "Jendouba", "babouch": "Jendouba", "sakiet sidi youssef": "Le Kef",
    "bou chebka": "Kasserine", "skhira": "Sfax", "enfidha": "Sousse", "jebel jelloud": "Tunis", "ventes de tunis": "Tunis",
}


def telecharger(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr,ar;q=0.8"})
    try:
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            # Le site de la Douane envoie une chaîne de certificats incomplète : refusée sur GitHub (Linux),
            # acceptée par les navigateurs. Lecture publique d'UNE page, rien n'est envoyé : on réessaie
            # sans vérification du certificat, uniquement pour ce domaine (même méthode que Géant pour le site de l'eau).
            if "CERTIFICATE_VERIFY_FAILED" not in str(e) or not url.startswith(PREFIXE):
                raise
            print("  (certificat incomplet chez douane.gov.tn : nouvel essai sans vérification)")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def texte(fragment):
    t = re.sub(r"<br\s*/?>", " ", fragment)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def gouvernorat(bureau):
    g = trouver_gouvernorats(bureau)
    if len(g) == 1:
        return g[0]
    b = bureau.lower()
    for ville, gv in VILLES.items():
        if ville in b:
            return gv
    return "Plusieurs gouvernorats" if len(g) > 1 else "National / non précisé"


def lire_tableau(page):
    """Liste des ventes du tableau officiel, ou None si le tableau est introuvable (format changé)."""
    m = re.search(r'<table[^>]*class="[^"]*tablepress[^"]*"[^>]*>(.*?)</table>', page, re.S)
    if not m:
        return None
    entete = texte(" ".join(re.findall(r"<th[^>]*>(.*?)</th>", m.group(1), re.S))).lower()
    if not ("objet" in entete and "chéance" in entete):
        return None
    ventes = []
    for ligne in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S):
        cellules = dict(re.findall(r'<td[^>]*class="column-(\d)"[^>]*>(.*?)</td>', ligne, re.S))
        if not cellules:
            continue
        pub = re.search(r"(\d{2})-(\d{2})-(\d{4})", texte(cellules.get("1", "")))
        ech_txt = texte(cellules.get("4", ""))
        ech = re.search(r"(\d{4})-(\d{2})-(\d{2})", ech_txt) or re.search(r"(\d{2})[-/](\d{2})[-/](\d{4})", ech_txt)
        heure = re.search(r"(\d{1,2})\s*h\s*(\d{2})", ech_txt)
        bureau = texte(cellules.get("2", ""))[:200]
        objet = texte(cellules.get("3", ""))[:600]
        liens = re.findall(r'href="([^"]+)"', cellules.get("5", "") + " " + cellules.get("6", ""))
        avis = next((u for u in re.findall(r'href="([^"]+)"', cellules.get("5", ""))), "")
        cahier = next((u for u in liens if "cahier" in u.lower()), "")
        if not objet or not ech:
            continue
        g = ech.groups()
        limite = f"{g[0]}-{g[1]}-{g[2]}" if len(g[0]) == 4 else f"{g[2]}-{g[1]}-{g[0]}"
        propre = lambda u: u if u.startswith(PREFIXE) and not any(c in u for c in "\"'<> ") else ""
        avis, cahier = propre(avis), propre(cahier)
        cle = avis or f"{bureau}|{objet}|{limite}"
        ventes.append({
            "id": "Vente-" + hashlib.sha1(cle.encode("utf-8")).hexdigest()[:10],
            "date_publication": f"{pub.group(3)}-{pub.group(2)}-{pub.group(1)}" if pub else "",
            "bureau": bureau, "objet": objet,
            "date_limite": limite, "heure": f"{int(heure.group(1)):02d}:{heure.group(2)}" if heure else "",
            "lien_avis": avis or URL, "lien_cahier": cahier,
            "gouvernorat": gouvernorat(bureau), "source": "Douane tunisienne",
        })
    return ventes


def charger():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d.get("ventes"), dict):
            return d
    except (OSError, ValueError, AttributeError):
        pass
    return {"source": "Douane tunisienne - " + URL, "ventes": {}}


def sauver(d):
    os.makedirs(os.path.dirname(FICHIER), exist_ok=True)
    tmp = FICHIER + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FICHIER)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = charger()
    maintenant = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    precedent = int(d.get("lignes_lues") or 0)
    print("Ventes aux enchères (Douane tunisienne)…")
    raison = ""
    try:
        code, page = telecharger(URL)
    except Exception as e:     # réseau coupé, délai… : panne, jamais un plantage
        code, page, raison = 0, "", f"page injoignable ({e})"
    ventes = None
    if not raison:
        if code != 200:
            raison = f"page injoignable (code HTTP {code})"
        else:
            ventes = lire_tableau(page)
            if ventes is None:
                raison = "format de la page changé (tableau introuvable)"
            elif not ventes:
                raison = "tableau vide"
            elif precedent and len(ventes) < SEUIL_CHUTE * precedent:
                raison = f"seulement {len(ventes)} lignes contre {precedent} avant"
    if raison:
        ancien = d.get("statut_source") or {}
        depuis = ancien.get("depuis") if ancien.get("etat") == "panne" else maintenant
        d["statut_source"] = {"etat": "panne", "depuis": depuis, "raison": raison}
        sauver(d)
        print(f"  ! échec : {raison} — anciennes ventes gardées ({len(d['ventes'])})")
        return 1
    oubli = (dt.date.today() - dt.timedelta(days=GARDER_JOURS)).isoformat()
    connues = d["ventes"]
    nouvelles = 0
    for v in ventes:
        if v["date_limite"] < oubli:
            continue
        if v["id"] not in connues:
            nouvelles += 1
            v["lu_le"] = maintenant
            connues[v["id"]] = v
        else:
            connues[v["id"]].update({k: v[k] for k in v if k != "lu_le"})
    d["ventes"] = {k: x for k, x in connues.items() if x.get("date_limite", "") >= oubli}
    d["lignes_lues"] = len(ventes)
    d["derniere_lecture_reussie"] = maintenant
    d["statut_source"] = {"etat": "ok", "depuis": maintenant, "raison": ""}
    sauver(d)
    ouvertes = sum(1 for x in d["ventes"].values() if x["date_limite"] >= dt.date.today().isoformat())
    print(f"  {len(ventes)} lignes lues, {nouvelles} nouvelles, {ouvertes} ventes encore ouvertes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
