# -*- coding: utf-8 -*-
"""
Robot « alertes appels d'offres Tunisie » : lit les appels d'offres publics
publiés sur le portail de la HAICOP (www.marchespublics.gov.tn).

- Bibliothèque standard Python uniquement (rien à installer).
- Lecture LENTE et polie : au moins 2 secondes entre deux requêtes,
  User-Agent honnête qui dit qui on est.
- Cache : une fiche déjà lue n'est jamais relue.
- TUNEPS (tuneps.tn) n'est PAS utilisé.

Utilisation :
    python lire_haicop.py            (30 derniers appels d'offres)
    python lire_haicop.py --max 10   (10 seulement)
    python lire_haicop.py --jours 3  (du-jour.md = publiés ces 3 derniers jours)
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.marchespublics.gov.tn/fr/appels-doffres"
UA = "Mozilla/5.0 (compatible; alertes-ao-tunisie; robot lent, 1 page / 2 s)"
PAUSE = 2.5  # secondes entre deux requêtes (minimum demandé : 2)

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_DONNEES = os.path.join(os.path.dirname(ICI), "donnees")
FICHIER_JSON = os.path.join(DOSSIER_DONNEES, "appels-offres.json")
FICHIER_MD = os.path.join(DOSSIER_DONNEES, "du-jour.md")

_derniere_requete = [0.0]


# ---------------------------------------------------------------- réseau
def telecharger(url, json_attendu=False):
    """Télécharge une adresse en respectant la pause entre deux requêtes."""
    attente = PAUSE - (time.time() - _derniere_requete[0])
    if attente > 0:
        time.sleep(attente)
    entetes = {"User-Agent": UA, "Accept-Language": "fr,ar;q=0.8"}
    if json_attendu:
        entetes["Accept"] = "application/json"
        entetes["X-Requested-With"] = "XMLHttpRequest"
    req = urllib.request.Request(url, headers=entetes)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    finally:
        _derniere_requete[0] = time.time()


# ------------------------------------------------------- liste récente
def liste_recente(nombre):
    """Numéros des appels d'offres les plus récents (liste officielle, triée
    du plus récent au plus ancien). Renvoie [] si la liste est illisible."""
    params = {
        "draw": "1", "start": "0", "length": str(nombre),
        "columns[0][data]": "id",
        "order[0][column]": "0", "order[0][dir]": "desc",
    }
    try:
        code, texte = telecharger(BASE + "?" + urllib.parse.urlencode(params), json_attendu=True)
    except Exception as e:  # réseau coupé, délai, DNS… : traité comme une panne, jamais un plantage
        print(f"  ! échec : liste injoignable ({e})")
        return []
    if code != 200:
        print(f"  ! liste illisible (code HTTP {code})")
        return []
    try:
        donnees = json.loads(texte)["data"]
        if not isinstance(donnees, list):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        print("  ! liste : réponse inattendue (pas du JSON)")
        return []
    return [d["id"] for d in donnees if isinstance(d, dict) and str(d.get("id", "")).startswith("Tender-")]


def numero(tid):
    m = re.search(r"(\d+)$", tid or "")
    return int(m.group(1)) if m else 0


# ------------------------------------------------------- lecture fiche
def nettoyer(fragment):
    t = re.sub(r"<br\s*/?>", " ", fragment)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def lire_fiche(tid):
    url = f"{BASE}/{tid}"
    code, page = telecharger(url)
    if code != 200:
        return None, code
    if "Numéro A.O" not in page:
        # Page reçue mais sans la fiche : numéro inexistant, ou format du portail changé.
        return None, "format" if len(page) > 20000 else code

    paires = []  # (étiquette, valeur) dans l'ordre de la page
    # Bandeau du haut : <h5>Objet</h5><span>…</span>
    for lab, val in re.findall(r"<h5[^>]*>([^<]*)</h5>\s*<span[^>]*>(.*?)</span>", page, re.S):
        paires.append((nettoyer(lab), nettoyer(val)))
    # Corps : <p><strong>Étiquette :</strong> valeur</p>
    for bloc in re.findall(r"<p[^>]*>\s*(<strong.*?)</p>", page, re.S):
        m = re.match(r"<strong[^>]*>(.*?)</strong>(.*)", bloc, re.S)
        if m:
            paires.append((nettoyer(m.group(1)).rstrip(" :"), nettoyer(m.group(2))))

    def champ(*noms, apres=None):
        debut = 0
        if apres:
            for i, (lab, _) in enumerate(paires):
                if lab.lower().startswith(apres.lower()):
                    debut = i + 1
                    break
        for lab, val in paires[debut:]:
            for n in noms:
                if lab.lower().startswith(n.lower()):
                    return val
        return ""

    specialites = [v for (l, v) in paires if l == "Spécialité"]
    cautions = []  # un montant par lot, en dinars
    for x in re.findall(r"cautionnement provisoire\s*:\s*([0-9][0-9 .,]*)", page):
        chiffres = re.sub(r"[^\d]", "", x.split(",")[0])
        if chiffres:
            cautions.append(int(chiffres))
    regions_lots = [nettoyer(r) for r in re.findall(r"Région\s+d&#039;exécution:\s*(.*?)</span>", page, re.S)]

    ao = {
        "numero": tid,
        "objet": champ("Objet"),
        "descriptif": champ("Descriptif"),
        "acheteur": champ("Acheteur public"),
        "type_commande": champ("Type de commande"),
        "procedure": champ("Procédure de passation"),
        "region_execution": champ("Région d’exécution", "Région d'exécution"),
        "regions_lots": sorted(set(r for r in regions_lots if r)),
        "date_publication": date_iso(champ("Date de publication")),
        "date_limite": date_iso(champ("Date limite de réception des offres")),
        "heure_limite": champ("Heure", apres="Date limite de réception des offres"),
        "date_ouverture": date_iso(champ("Date d’ouverture des offres", "Date d'ouverture des offres")),
        "cautionnement_provisoire_dt": cautions,
        "cautionnement_total_dt": sum(cautions) if cautions else None,
        "specialite": specialites[0] if specialites else "",
        "categorie": champ("Catégorie"),
        "niveau_specialite": specialites[1] if len(specialites) > 1 else "",
        "nombre_lots": champ("Nombre de lots"),
        "etat": champ("Etat"),
        "lien": url,
        "source": "HAICOP",
        "lu_le": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    if not ao["objet"] or not (ao["date_limite"] or ao["acheteur"]):
        return None, "format"   # champs essentiels introuvables : format changé (jamais « aucun appel d'offres »)
    ao["metier"] = classer_metier(ao)
    ao["gouvernorat"] = classer_gouvernorat(ao)
    return ao, code


def date_iso(texte):
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", texte or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


# ------------------------------------------------------- classements
def normaliser(texte):
    """Minuscules, sans accents ; arabe sans voyelles (أإآ→ا, ة→ه, ى→ي)."""
    t = unicodedata.normalize("NFKD", (texte or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub("[ً-ْـ]", "", t)  # harakat + tatweel
    t = t.translate(str.maketrans("أإآٱةى", "ااااهي"))
    return t


METIERS = [
    ("Électricité", ["electricit", "electrique", "eclairage", "groupe electrogene", "climatisation", "hta", "isolateur", "transformateur", "cable electrique",
                     "كهرباء", "كهربائي", "انارة", "تنوير", "مولد", "تكييف", "مكيف"]),
    ("Informatique", ["informatique", "logiciel", "ordinateur", "serveur", "imprimante", "reseau informatique",
                      "numerique", "اعلامي", "حاسوب", "حواسيب", "برمجي", "طابعات", "منظومه معلوماتي",
                      "رقمي", "معدات اعلاميه"]),
    ("Fournitures de bureau", ["fournitures de bureau", "papeterie", "papier", "mobilier de bureau",
                               "consommables", "مكتبي", "ورق", "اثاث", "مطبوعات", "ادوات مكتبيه"]),
    ("Nettoyage / gardiennage", ["nettoyage", "gardiennage", "surveillance", "hygiene", "jardinage",
                                 "تنظيف", "حراسه", "نظافه", "بستنه", "مراقبه", "dechets", "نفايات"]),
    ("Alimentation", ["alimentaire", "denree", "restauration", "restaurant", "تغديه", "viande", "pain", "lait", "legume", "fruit",
                      "مواد غذائيه", "غذائي", "لحوم", "خبز", "حليب", "اطعام", "تغذيه", "خضر", "غلال", "مرطبات",
                      "riz", "nourriture", "sucre", "huile vegetale", "semoule", "farine", "conserve", "ارز", "سميد", "زيت نباتي"]),
    ("Médical", ["medicament", "medical", "medicaux", "reactif", "laboratoire", "pharmac", "dentaire",
                 "ادويه", "طبي", "شبه طبي", "كواشف", "مخبر", "صيدل", "تجهيزات طبيه", "مستلزمات طبيه"]),
    ("Transport / véhicules", ["vehicule", "transport", "pieces de rechange", "carburant", "pneumatique",
                               "camion", "voiture", "engin",
                               "سيارات", "سياره", "نقل", "عربات", "قطع غيار", "محروقات", "اطارات", "شاحن", "اليات"]),
    ("Études / conseil", ["etude", "conseil", "assistance technique", "audit", "formation", "controle technique",
                          "maitrise d'oeuvre", "دراسه", "دراسات", "استشار", "تدقيق", "تكوين", "مراقبه فنيه",
                          "مكتب دراسات", "avocat", "محامي"]),
    ("BTP / génie civil", ["travaux", "genie civil", "batiment", "construction", "amenagement", "route", "voirie",
                           "assainissement", "rehabilitation", "hydraulique", "اشغال", "تهيئه", "بناء", "هدم",
                           "طرقات", "طريق", "مسالك", "تعبيد", "ترميم", "تبليط", "تطهير", "مرابض", "مربض",
                           "تشييد", "توسعه", "جسر", "سياج", "حائط"]),
]


# (motif dans le type de commande normalisé, métier, poids) — le premier qui correspond
TYPES_COMMANDE = [
    (r"^etudes", "Études / conseil", 3),
    (r"informati", "Informatique", 3),
    (r"nourriture|alimenta|restaura", "Alimentation", 3),
    (r"mobilier|fournitures de bureau|papeterie|imprim", "Fournitures de bureau", 3),
    (r"entretien|nettoyage|gardiennage|surveillance", "Nettoyage / gardiennage", 3),
    (r"electri", "Électricité", 3),
    (r"vehicule|transport|engin", "Transport / véhicules", 3),
    (r"medic|pharma|sante", "Médical", 3),
    (r"^travaux", "BTP / génie civil", 1.5),
]


def classer_metier(ao):
    texte = normaliser(" ".join(str(ao.get(k) or "") for k in ("objet", "descriptif", "specialite", "categorie")))
    type_cmd = normaliser(ao.get("type_commande"))
    scores = {}
    for nom, mots in METIERS:
        s = sum(1 for m in mots if normaliser(m) in texte)
        if s:
            scores[nom] = s
    # Le type de commande officiel (ex. « Biens/ Matériels informatiques ») pèse lourd
    for motif, nom, poids in TYPES_COMMANDE:
        if re.search(motif, type_cmd):
            scores[nom] = scores.get(nom, 0) + poids
            break
    spec = normaliser(ao.get("specialite"))
    if "electric" in spec:
        scores["Électricité"] = scores.get("Électricité", 0) + 3
    elif re.search(r"\((b|r|h|vrd|gc)\)", spec) or "batiment" in spec:
        scores["BTP / génie civil"] = scores.get("BTP / génie civil", 0) + 2
    if not scores:
        return "Autres"
    return max(scores, key=scores.get)


GOUVERNORATS = {
    "Ariana": ["ariana", "اريانه"],
    "Béja": ["beja", "باجه"],
    "Ben Arous": ["ben arous", "بن عروس"],
    "Bizerte": ["bizerte", "بنزرت"],
    "Gabès": ["gabes", "قابس"],
    "Gafsa": ["gafsa", "قفصه"],
    "Jendouba": ["jendouba", "جندوبه"],
    "Kairouan": ["kairouan", "القيروان"],
    "Kasserine": ["kasserine", "القصرين"],
    "Kébili": ["kebili", "قبلي"],
    "Le Kef": ["le kef", "kef", "الكاف"],
    "Mahdia": ["mahdia", "المهديه"],
    "La Manouba": ["manouba", "منوبه"],
    "Médenine": ["medenine", "مدنين"],
    "Monastir": ["monastir", "المنستير"],
    "Nabeul": ["nabeul", "نابل"],
    "Sfax": ["sfax", "صفاقس"],
    "Sidi Bouzid": ["sidi bouzid", "سيدي بوزيد"],
    "Siliana": ["siliana", "سليانه"],
    "Sousse": ["sousse", "سوسه"],
    "Tataouine": ["tataouine", "تطاوين"],
    "Tozeur": ["tozeur", "توزر"],
    "Tunis": ["tunis", "تونس"],
    "Zaghouan": ["zaghouan", "زغوان"],
}


def trouver_gouvernorats(texte):
    t = normaliser(texte)
    trouves = []
    for nom, mots in GOUVERNORATS.items():
        for m in mots:
            m = normaliser(m)
            # « tunis » ne doit pas matcher « tunisie », « kef » doit être un mot
            # en arabe, « ب » (à), « و » (et), « ل » (pour) peuvent être collés devant le nom
            if re.search(r"(?<![a-z؀-ۿ])[بول]?" + re.escape(m) + r"(?![a-z؀-ۿ])", t):
                trouves.append(nom)
                break
    return trouves


def classer_gouvernorat(ao):
    # 1) région d'exécution des lots (la plus précise), sinon celle de la fiche
    for regions in (" | ".join(ao.get("regions_lots") or []), ao.get("region_execution") or ""):
        g = trouver_gouvernorats(regions)
        if len(g) == 1:
            return g[0]
        if len(g) > 1:
            return "Plusieurs gouvernorats"
    # 2) sinon : nom de l'acheteur, puis objet
    for texte in (ao.get("acheteur") or "", ao.get("objet") or ""):
        g = trouver_gouvernorats(texte)
        if len(g) == 1:
            return g[0]
    return "National / non précisé"


# ------------------------------------------------------- fichiers
def charger_cache():
    if os.path.exists(FICHIER_JSON):
        with open(FICHIER_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {"source": "HAICOP - www.marchespublics.gov.tn", "appels_offres": {}}


def sauver_cache(cache):
    os.makedirs(DOSSIER_DONNEES, exist_ok=True)
    cache["mis_a_jour"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    tmp = FICHIER_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FICHIER_JSON)


def ecrire_du_jour(cache, jours):
    aos = list(cache["appels_offres"].values())
    if not aos:
        return 0
    aujourd_hui = dt.date.today().isoformat()
    plus_recente = max(a["date_publication"] for a in aos if a.get("date_publication"))
    seuil = (dt.date.fromisoformat(plus_recente) - dt.timedelta(days=jours - 1)).isoformat()
    choisis = [a for a in aos
               if a.get("date_publication", "") >= seuil
               and (not a.get("date_limite") or a["date_limite"] >= aujourd_hui)]
    ordre_metier = [m for m, _ in sorted(METIERS, key=lambda x: normaliser(x[0]))] + ["Autres"]
    choisis.sort(key=lambda a: (ordre_metier.index(a["metier"]) if a["metier"] in ordre_metier else 99,
                                a["gouvernorat"], a.get("date_limite", ""), -numero(a["numero"])))

    def fr(d):
        return f"{d[8:10]}/{d[5:7]}/{d[0:4]}" if d else "?"

    lignes = [
        "# Appels d'offres publics — Tunisie",
        "",
        f"Publiés entre le {fr(seuil)} et le {fr(plus_recente)} · {len(choisis)} appels d'offres encore ouverts"
        f" · mis à jour le {dt.datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        "",
        "_Source : HAICOP (www.marchespublics.gov.tn). Résumé indicatif : seule la fiche officielle fait foi."
        " Cahier des charges à retirer sur TUNEPS._",
        "",
    ]
    metier_courant = gouv_courant = None
    for a in choisis:
        if a["metier"] != metier_courant:
            metier_courant, gouv_courant = a["metier"], None
            n = sum(1 for x in choisis if x["metier"] == metier_courant)
            if lignes[-1] != "":
                lignes.append("")
            lignes += [f"## {metier_courant} ({n})", ""]
        if a["gouvernorat"] != gouv_courant:
            gouv_courant = a["gouvernorat"]
            if lignes[-1] != "":
                lignes.append("")
            lignes += [f"### {gouv_courant}", ""]
        heure = f" {a['heure_limite']}" if a.get("heure_limite") else ""
        caution = (f" · caution {a['cautionnement_total_dt']:,} DT".replace(",", " ")
                   if a.get("cautionnement_total_dt") else "")
        objet = a["objet"].replace("\n", " ").strip() or "(objet non indiqué)"
        if len(objet) > 180:
            objet = objet[:177].rsplit(" ", 1)[0] + "…"
        lignes.append(
            f"- **{objet}** — {a['acheteur']} · {a['type_commande'] or '?'}"
            f" · date limite **{fr(a.get('date_limite', ''))}{heure}**{caution}"
            f" · [{a['numero']}]({a['lien']}) (source : HAICOP)"
        )
    lignes += ["", "---", "Source : HAICOP — Haute Instance de la Commande Publique (www.marchespublics.gov.tn)."]
    with open(FICHIER_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lignes) + "\n")
    return len(choisis)


# ------------------------------------------------------- programme
def main():
    p = argparse.ArgumentParser(description="Lit les appels d'offres récents de la HAICOP.")
    p.add_argument("--max", type=int, default=30, help="nombre maximum de fiches à lire (défaut 30)")
    p.add_argument("--jours", type=int, default=3, help="du-jour.md : publiés ces N derniers jours (défaut 3)")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    cache = charger_cache()
    connus = cache["appels_offres"]
    # Reclasse ce qui est déjà en mémoire (si les règles ont changé) : aucune requête.
    for ao in connus.values():
        ao["metier"] = classer_metier(ao)
        ao["gouvernorat"] = classer_gouvernorat(ao)

    print("1) Liste des appels d'offres récents…")
    ids = ids_liste = liste_recente(max(a.max, 1))
    if len(ids) < max(1, int(0.3 * a.max)) and connus:
        # Plan B : remonter les numéros à partir du plus grand déjà connu
        dernier = max(numero(k) for k in connus)
        print(f"  plan B : on essaie les numéros après Tender-{dernier}")
        ids = list(ids) + [f"Tender-{dernier + i}" for i in range(1, a.max + 1)]
    a_lire = [t for t in ids if t not in connus][: a.max]
    print(f"  {len(ids)} trouvés, {len(ids) - len(a_lire)} déjà connus, {len(a_lire)} à lire")

    print(f"2) Lecture des fiches (une toutes les {PAUSE} s)…")
    lus = echecs = absents = formats = 0
    for i, tid in enumerate(a_lire, 1):
        try:
            ao, code = lire_fiche(tid)
        except Exception as e:  # réseau, délai…
            print(f"  [{i}/{len(a_lire)}] {tid} : échec ({e})")
            echecs += 1
            continue
        if ao is None and code == "format":
            print(f"  [{i}/{len(a_lire)}] {tid} : échec (format de la fiche inconnu : champs introuvables)")
            formats += 1
            if formats >= 3 and not lus:
                break  # inutile d'insister : le portail a changé
            continue
        if ao is None:
            print(f"  [{i}/{len(a_lire)}] {tid} : pas de fiche (code {code})")
            absents += 1
            if absents >= 3 and not lus:
                break  # plan B : plus rien après
            continue
        connus[tid] = ao
        lus += 1
        print(f"  [{i}/{len(a_lire)}] {tid} · {ao['metier']} · {ao['gouvernorat']} · limite {ao['date_limite']}")
        if lus % 10 == 0:
            sauver_cache(cache)

    # État de la source, lu par construire_site.py (avertissement) et par le robot GitHub (issue d'alerte)
    liste_ok = len(ids_liste) >= max(1, int(0.3 * a.max))   # < 30 % du volume demandé = anormal
    raisons = []
    if formats and formats >= lus:
        raisons.append(f"format des fiches changé ({formats} fiches illisibles)")
    if not liste_ok and lus == 0:
        raisons.append("liste des appels d'offres illisible ou presque vide"
                       f" ({len(ids_liste)} numéros au lieu de {a.max})")
    if echecs >= 3 and echecs > lus:
        raisons.append(f"{echecs} fiches injoignables")
    reussi = not raisons
    maintenant = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    ancien = cache.get("statut_source") or {}
    cache["dernier_passage"] = {"date": maintenant, "liste_ok": liste_ok, "lus": lus, "echecs": echecs,
                                "formats_inconnus": formats, "reussi": reussi}
    if reussi:
        cache["derniere_lecture_reussie"] = maintenant
        cache["statut_source"] = {"etat": "ok", "depuis": maintenant, "raison": ""}
    else:
        depuis = ancien.get("depuis") if ancien.get("etat") == "panne" else maintenant
        cache["statut_source"] = {"etat": "panne", "depuis": depuis, "raison": " ; ".join(raisons)}
        print(f"   ! échec : source HAICOP en panne ({' ; '.join(raisons)}) — anciennes données gardées")
    sauver_cache(cache)
    n = ecrire_du_jour(cache, a.jours)
    print(f"3) Terminé : {lus} fiches lues, {echecs} échecs, {formats} formats inconnus, {len(connus)} en mémoire, "
          f"{n} dans du-jour.md")
    print(f"   {FICHIER_JSON}\n   {FICHIER_MD}")
    return 0 if reussi else 1


if __name__ == "__main__":
    sys.exit(main())
