# -*- coding: utf-8 -*-
"""
Construit le site statique « Alertes appels d'offres Tunisie » à partir de
donnees/appels-offres.json (rempli par lire_haicop.py).

Pages produites dans site/ (racine du dépôt) :
  index.html                      accueil (tous les appels d'offres ouverts, filtres)
  metier/<métier>/index.html      une page par métier
  gouvernorat/<gouv>/index.html   une page par gouvernorat
  a-propos/index.html             à propos, méthode et sources
  sitemap.xml

Robustesse (règles communes à tous les sites) :
  - fichier de données illisible ou vide  -> on reprend la dernière sauvegarde
    (donnees/appels-offres.sauvegarde.json) et on affiche un avertissement daté ;
  - sans sauvegarde et site déjà construit -> on NE touche PAS au site (code 1) ;
  - beaucoup moins de fiches qu'avant (< 50 %) -> données suspectes : sauvegarde ;
  - source marquée « en panne » par lire_haicop.py (statut_source) -> état gardé dans
    donnees/etat-source.json (lu par le robot GitHub qui ouvre/ferme l'issue d'alerte) ;
  - dernière lecture réussie vieille de 2 jours ou plus -> bandeau d'avertissement daté
    (le JavaScript refait ce calcul avec la date du téléphone du visiteur) ;
  - appels d'offres expirés masqués, doublons fusionnés, textes échappés.

Utilisation :
    python construire_site.py
    python construire_site.py --donnees X.json --sortie dossier --aujourdhui 2026-10-05   (tests)
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import glossaire   # noqa: E402  résumé traduit des objets (glossaire maison)
import reglages    # noqa: E402  adresses à remplir par Ahmed (canal Telegram, formulaire…)

RACINE_SITE = os.path.dirname(ICI)          # le dossier site/ (= racine du dépôt GitHub)
URL_SITE = "https://ah6259.github.io/appels-offres-tunisie/"
URL_HAICOP = "https://www.marchespublics.gov.tn/fr/appels-doffres"
PREFIXE_FICHE = "https://www.marchespublics.gov.tn/"
SEUIL_CHUTE = 0.5          # moins de 50 % des fiches de la sauvegarde -> suspect
JOURS_SANS_DATE = 30       # fiche sans date limite : montrée 30 jours après publication
AGE_AVERTISSEMENT = 2      # jours sans lecture réussie avant l'avertissement

# (nom donné par le robot, adresse, français, arabe)
METIERS = [
    ("BTP / génie civil", "btp-genie-civil", "BTP / génie civil", "البناء والأشغال العامة"),
    ("Électricité", "electricite", "Électricité", "الكهرباء"),
    ("Informatique", "informatique", "Informatique", "الإعلامية"),
    ("Fournitures de bureau", "fournitures-bureau", "Fournitures et mobilier", "اللوازم والأثاث"),
    ("Nettoyage / gardiennage", "nettoyage-gardiennage", "Nettoyage / gardiennage", "التنظيف والحراسة"),
    ("Alimentation", "alimentation", "Alimentation", "المواد الغذائية"),
    ("Médical", "medical", "Médical / pharmacie", "الطبي والصيدلي"),
    ("Transport / véhicules", "transport-vehicules", "Transport / véhicules", "النقل والعربات"),
    ("Études / conseil", "etudes-conseil", "Études / conseil", "الدراسات والاستشارات"),
    ("Autres", "autres", "Autres", "أخرى"),
]
GOUVERNORATS = [
    ("Ariana", "ariana", "أريانة"), ("Béja", "beja", "باجة"), ("Ben Arous", "ben-arous", "بن عروس"),
    ("Bizerte", "bizerte", "بنزرت"), ("Gabès", "gabes", "قابس"), ("Gafsa", "gafsa", "قفصة"),
    ("Jendouba", "jendouba", "جندوبة"), ("Kairouan", "kairouan", "القيروان"), ("Kasserine", "kasserine", "القصرين"),
    ("Kébili", "kebili", "قبلي"), ("Le Kef", "le-kef", "الكاف"), ("Mahdia", "mahdia", "المهدية"),
    ("La Manouba", "la-manouba", "منوبة"), ("Médenine", "medenine", "مدنين"), ("Monastir", "monastir", "المنستير"),
    ("Nabeul", "nabeul", "نابل"), ("Sfax", "sfax", "صفاقس"), ("Sidi Bouzid", "sidi-bouzid", "سيدي بوزيد"),
    ("Siliana", "siliana", "سليانة"), ("Sousse", "sousse", "سوسة"), ("Tataouine", "tataouine", "تطاوين"),
    ("Tozeur", "tozeur", "توزر"), ("Tunis", "tunis", "تونس"), ("Zaghouan", "zaghouan", "زغوان"),
    ("Plusieurs gouvernorats", "plusieurs", "عدة ولايات"),
    ("National / non précisé", "national", "وطني / غير محدد"),
]
M_PAR_NOM = {m[0]: m for m in METIERS}
G_PAR_NOM = {g[0]: g for g in GOUVERNORATS}
TYPES_AR = {"travaux": "أشغال", "biens": "اقتناء مواد", "services": "خدمات", "etudes": "دراسات", "études": "دراسات"}
PROCEDURES_AR = [("ouvert", "طلب عروض مفتوح"), ("restreint", "طلب عروض مضيّق"), ("concours", "طلب عروض مع مناظرة"),
                 ("consultation", "استشارة"), ("négocié", "تفاوض مباشر"), ("negocie", "تفاوض مباشر")]

E = lambda t: html.escape(str(t or ""), quote=True)
ISO = lambda t: "⁦" + str(t) + "⁩"     # isole un nombre dans un texte arabe
ARABE = re.compile(r"[؀-ۿ]")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def reglage(nom, motif):
    """Adresse lue dans robot/reglages.py ; "" si vide ou mal écrite (le site cache alors le bouton)."""
    v = str(getattr(reglages, nom, "") or "").strip()
    if v and not re.fullmatch(motif, v):
        print(f"  ! échec : réglage {nom} mal écrit ({v[:60]}) -> ignoré")
        return ""
    return v


def adresses():
    return {
        "telegram": reglage("TELEGRAM_CANAL_URL", r"https://t\.me/[A-Za-z0-9_]{4,64}"),
        "whatsapp": reglage("WHATSAPP_CANAL_URL", r"https://(www\.)?whatsapp\.com/channel/[A-Za-z0-9_-]{8,64}"),
        "formulaire": reglage("FORMULAIRE_PRIVES_URL", r"https://(forms\.gle/[A-Za-z0-9_-]{4,64}|docs\.google\.com/forms/[A-Za-z0-9_/=?&.-]{8,200})"),
        # nom d'utilisateur du robot Telegram des Alertes Pro (sans @), ex. AlertesAOTunisieBot
        "robot": reglage("TELEGRAM_ROBOT_ALERTES", r"@?[A-Za-z][A-Za-z0-9_]{1,28}[Bb][Oo][Tt]").lstrip("@"),
    }


def resume_trad(objet):
    """Paragraphe « ≈ résumé dans l'autre langue — traduction automatique approximative » (ou "")."""
    r = glossaire.resumer(objet)
    if not r:
        return ""
    if r["langue"] == "fr":
        return (f'<p class="trad" lang="fr" dir="ltr"><span class="trad-t">≈ {E(r["texte"])}</span> '
                f'<small>{L("traduction automatique approximative", "ترجمة آلية تقريبية")}</small></p>')
    return (f'<p class="trad" lang="ar" dir="rtl"><span class="trad-t">≈ {E(r["texte"])}</span> '
            f'<small>{L("traduction automatique approximative", "ترجمة آلية تقريبية")}</small></p>')


def dfr(d):
    return f"{d[8:10]}/{d[5:7]}/{d[0:4]}" if d else ""


def montant(n):
    return f"{n:,}".replace(",", " ") + " DT"


def numero(tid):
    m = re.search(r"(\d+)$", tid or "")
    return int(m.group(1)) if m else 0


def L(fr, ar):
    """Texte bilingue (le bon s'affiche selon la langue de la page)."""
    return f'<span data-l="fr">{fr}</span><span data-l="ar">{ar}</span>'


# ------------------------------------------------------------ données
def charger(chemin):
    """Renvoie (dictionnaire, liste propre) ou (None, []) si le fichier est absent ou illisible."""
    try:
        with open(chemin, encoding="utf-8") as f:
            brut = json.load(f)
        aos = brut["appels_offres"]
    except (OSError, ValueError, KeyError, TypeError):
        return None, []
    if isinstance(aos, dict):
        aos = list(aos.values())
    if not isinstance(aos, list):
        return None, []
    return brut, nettoyer(aos)


def nettoyer(aos):
    """Garde les fiches valides, fusionne les doublons (même numéro), sécurise les champs."""
    propres = {}
    for a in aos:
        if not isinstance(a, dict):
            continue
        tid = str(a.get("numero") or "").strip()
        m = re.fullmatch(r"(?i)tender-(\d+)", tid)
        objet = str(a.get("objet") or "").strip()
        if not m or not objet:
            continue
        tid = "Tender-" + m.group(1)
        f = dict(a)
        f["numero"] = tid
        f["objet"] = re.sub(r"\s+", " ", objet)
        for k in ("date_publication", "date_limite"):
            v = str(f.get(k) or "")
            f[k] = v if DATE.match(v) else ""
        h = str(f.get("heure_limite") or "")
        f["heure_limite"] = h if re.fullmatch(r"\d{1,2}[:h]\d{2}", h) else ""
        c = f.get("cautionnement_total_dt")
        f["cautionnement_total_dt"] = c if isinstance(c, int) and 0 < c < 10**9 else None
        lien = str(f.get("lien") or "")
        if not lien.startswith(PREFIXE_FICHE) or any(x in lien for x in "\"'<> "):
            lien = f"{URL_HAICOP}/{tid}"     # lien officiel reconstruit, jamais un lien douteux
        f["lien"] = lien
        if f.get("metier") not in M_PAR_NOM:
            f["metier"] = "Autres"
        if f.get("gouvernorat") not in G_PAR_NOM:
            f["gouvernorat"] = "National / non précisé"
        ancien = propres.get(tid)
        if ancien is None or str(f.get("lu_le", "")) >= str(ancien.get("lu_le", "")):
            propres[tid] = f
    return list(propres.values())


def ouvertes(aos, jour):
    """Appels d'offres encore ouverts le jour donné (les expirés sont masqués)."""
    limite_sans_date = (dt.date.fromisoformat(jour) - dt.timedelta(days=JOURS_SANS_DATE)).isoformat()
    res = []
    for a in aos:
        if a["date_limite"]:
            if a["date_limite"] >= jour:
                res.append(a)
        elif a["date_publication"] and a["date_publication"] >= limite_sans_date:
            res.append(a)
    res.sort(key=lambda a: (a["date_limite"] or "9999", -numero(a["numero"])))
    return res


# ------------------------------------------------------------ morceaux de page
ICONE_LIEU = '<svg viewBox="0 0 24 24"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>'
ICONE_LIEN = '<svg viewBox="0 0 24 24"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>'



# ------------------------------------------------------------ images (SVG faits maison)
# Icône de chaque métier (trait 24 × 24, même style que les badges) et sa couleur
ICONES_METIER = {
    "btp-genie-civil": ('<path d="M3 19h18"/><path d="M5 19v-2.5a7 7 0 0 1 14 0V19"/><path d="M10 10V6.5h4V10"/><path d="M12 10v3"/>', "#B7791F"),
    "electricite": ('<path d="M13 2.5 5 13.5h6l-1 8 8-11h-6z"/>', "#C98A1B"),
    "informatique": ('<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19.5h20"/><path d="M9 9.5l-2 1.5 2 1.5M15 9.5l2 1.5-2 1.5"/>', "#2F6FB3"),
    "fournitures-bureau": ('<path d="M5 20l1.2-4.4L16.5 5.3a2 2 0 0 1 2.9 2.9L9.1 18.6z"/><path d="M14.5 7.3l2.9 2.9"/><path d="M13 20h7"/>', "#6B5BB5"),
    "nettoyage-gardiennage": ('<path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6z"/><path d="M12 8.5l.9 2 2.1.3-1.5 1.5.4 2.1-1.9-1-1.9 1 .4-2.1-1.5-1.5 2.1-.3z"/>', "#0E8A8A"),
    "alimentation": ('<path d="M7 3v7a2 2 0 0 0 4 0V3"/><path d="M9 3v18"/><path d="M17 21V3c-2.2 1.6-3 4.5-3 7.5 0 1.4.9 2.5 3 2.5"/>', "#2E8B57"),
    "medical": ('<rect x="3.5" y="3.5" width="17" height="17" rx="4"/><path d="M12 8v8M8 12h8"/>', "#C2412F"),
    "transport-vehicules": ('<path d="M2.5 6.5h11v9.5h-11z"/><path d="M13.5 10h4l3 3.2V16h-7"/><circle cx="6.5" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>', "#3D6A99"),
    "etudes-conseil": ('<path d="M9 3.5h6v3H9z"/><path d="M7 5H5v15.5h14V5h-2"/><path d="M9 16.5v-3M12 16.5v-6M15 16.5v-4"/>', "#8A6A2F"),
    "autres": ('<rect x="4" y="4" width="6.5" height="6.5" rx="1.6"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.6"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.6"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.6"/>', "#5A6878"),
}
SPRITE = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>'
          + "".join(f'<symbol id="i-{k}" viewBox="0 0 24 24">{v[0]}</symbol>' for k, v in ICONES_METIER.items())
          + "</defs></svg>")
STYLE_ICONES = "<style>" + "".join(f".ic-{k}{{--c:{v[1]}}}" for k, v in ICONES_METIER.items()) + "</style>"


def icone(slug, cls="ic-m"):
    return f'<span class="{cls} ic-{slug}" aria-hidden="true"><svg><use href="#i-{slug}"/></svg></span>'


# Contour simplifié de la Tunisie (longitude, latitude) et chef-lieu de chaque gouvernorat.
# Les gouvernorats du Grand Tunis sont un peu écartés pour rester lisibles (carte schématique).
CONTOUR_TN = [(8.62, 36.94), (9.0, 37.12), (9.2, 37.23), (9.6, 37.33), (9.87, 37.34), (10.05, 37.27), (10.25, 37.18),
              (10.17, 37.0), (10.25, 36.83), (10.33, 36.78), (10.5, 36.7), (10.8, 36.9), (11.0, 37.06), (11.1, 36.87),
              (10.95, 36.65), (10.75, 36.45), (10.58, 36.38), (10.5, 36.08), (10.64, 35.83), (10.83, 35.78), (10.88, 35.66),
              (11.07, 35.5), (11.12, 35.23), (10.95, 34.95), (10.77, 34.73), (10.5, 34.52), (10.07, 34.3), (10.1, 33.88),
              (10.45, 33.6), (10.75, 33.62), (11.12, 33.5), (11.25, 33.3), (11.56, 33.17), (11.48, 32.62), (11.0, 32.35),
              (10.7, 31.98), (10.3, 31.6), (10.15, 31.0), (9.55, 30.23), (9.3, 30.9), (9.05, 31.9), (8.35, 32.5),
              (7.85, 33.2), (7.5, 33.8), (7.75, 34.2), (8.25, 34.65), (8.4, 35.2), (8.3, 35.7), (8.4, 36.0), (8.42, 36.45),
              (8.2, 36.55)]
POSITIONS_TN = {
    "bizerte": (9.62, 37.1), "ariana": (10.08, 37.08), "tunis": (10.55, 36.98), "la-manouba": (9.72, 36.72),
    "ben-arous": (10.2, 36.6), "nabeul": (10.9, 36.62), "zaghouan": (10.0, 36.2), "beja": (9.08, 36.72),
    "jendouba": (8.72, 36.55), "le-kef": (8.75, 36.1), "siliana": (9.37, 35.95), "kairouan": (9.95, 35.62),
    "sousse": (10.42, 35.9), "monastir": (10.88, 35.62), "mahdia": (10.9, 35.22), "kasserine": (8.85, 35.2),
    "sidi-bouzid": (9.5, 35.0), "sfax": (10.45, 34.8), "gafsa": (8.75, 34.42), "tozeur": (8.13, 33.95),
    "kebili": (8.95, 33.55), "gabes": (9.85, 33.85), "medenine": (10.75, 33.3), "tataouine": (10.15, 32.55),
}


def _proj(lon, lat):
    import math
    return round((lon - 7.3) * 62 * math.cos(math.radians(34)), 1), round((37.5 - lat) * 62, 1)


def _contour():
    return "M" + " L".join(f"{x},{y}" for x, y in (_proj(*p) for p in CONTOUR_TN)) + "Z"


def carte_tunisie(comptes, racine):
    """Carte schématique : une bulle par gouvernorat, taille selon le nombre d'appels d'offres ouverts."""
    dj = _proj(10.9, 33.8)
    bulles = []
    for nom, slug, ar in GOUVERNORATS:
        if slug not in POSITIONS_TN:
            continue
        x, y = _proj(*POSITIONS_TN[slug])
        n = comptes.get(slug, 0)
        r = round(min(18, 7.5 + 2.2 * n ** 0.5), 1) if n else 4.5
        bulles.append(
            f'<a href="{racine}gouvernorat/{slug}/" class="tn-b{" vide" if not n else ""}" data-gouv="{slug}">'
            f'<title>{E(nom)} · {ar} : {n}</title><circle cx="{x}" cy="{y}" r="{r}"/>'
            + (f'<text x="{x}" y="{y}">{n}</text>' if n else "") + "</a>")
    return (f'<svg class="carte-tn" viewBox="0 0 232 462" role="img" aria-label="Carte de la Tunisie : appels d\'offres ouverts par gouvernorat">'
            f'<path class="tn-terre" d="{_contour()}"/><ellipse class="tn-terre" cx="{dj[0]}" cy="{dj[1]}" rx="9" ry="6.5"/>'
            + "".join(bulles) + "</svg>")


ILLUSTRATION = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 200" role="img" aria-label="Avis d’appel d’offres avec cachet des marchés publics et carte de la Tunisie">
<path d="{contour}" transform="translate(132 4) scale(.42)" fill="#fff" fill-opacity=".12" stroke="#fff" stroke-opacity=".4" stroke-width="2.5"/>
<g transform="translate(176 30)"><circle r="4.5" fill="#7CF0BE"/><circle r="10" fill="none" stroke="#7CF0BE" stroke-opacity=".55" stroke-width="2"/></g>
<g transform="translate(206 70)"><circle r="3.5" fill="#7CF0BE" fill-opacity=".8"/></g>
<!-- document administratif sérieux, SANS armoiries ni croissant/étoile (le site n'est pas officiel) -->
<g transform="rotate(-4 100 104)">
 <rect x="40" y="30" width="122" height="156" rx="4" fill="#0F2236" fill-opacity=".35" transform="translate(5 6)"/>
 <rect x="34" y="20" width="122" height="156" rx="4" fill="#FFFDF7"/>
 <rect x="34" y="20" width="122" height="8" fill="#C8102E"/><rect x="34" y="28" width="122" height="2.5" fill="#fff"/><rect x="34" y="30.5" width="122" height="1.6" fill="#C8102E"/>
 <text x="95" y="46" text-anchor="middle" font-family="Noto Kufi Arabic,Tahoma,Arial,sans-serif" font-size="9.5" font-weight="700" fill="#14273D">إعلان طلب عروض</text>
 <text x="95" y="59" text-anchor="middle" font-family="Georgia,Times New Roman,serif" font-size="7.3" font-weight="700" letter-spacing=".3" fill="#14273D">AVIS D'APPEL D'OFFRES</text>
 <rect x="62" y="64" width="66" height="1.2" fill="#14273D"/>
 <text x="44" y="77" font-family="Georgia,Times New Roman,serif" font-size="6.4" fill="#4A5B6E">N° 2026/  —  Procédure ouverte</text>
 <g fill="#C9D3DF">
  <rect x="44" y="84" width="102" height="3.4" rx="1.7"/><rect x="44" y="91" width="96" height="3.4" rx="1.7"/>
  <rect x="44" y="98" width="100" height="3.4" rx="1.7"/><rect x="44" y="105" width="88" height="3.4" rx="1.7"/>
  <rect x="44" y="112" width="98" height="3.4" rx="1.7"/><rect x="44" y="119" width="70" height="3.4" rx="1.7"/>
 </g>
 <rect x="44" y="128" width="54" height="15" rx="2" fill="#FBEAE7" stroke="#C8102E" stroke-width=".8"/>
 <text x="48" y="134" font-family="Arial,sans-serif" font-size="4.6" font-weight="700" fill="#C8102E">DATE LIMITE</text>
 <text x="48" y="140.5" font-family="Arial,sans-serif" font-size="5.6" font-weight="700" fill="#14273D">10/11 · 10:00</text>
 <rect x="44" y="160" width="40" height="1" fill="#8A97A6"/><text x="44" y="167" font-family="Arial,sans-serif" font-size="4.6" fill="#8A97A6">Signature</text>
 <!-- cachet à l'encre : bâtiment public générique -->
 <g transform="translate(124 146) rotate(-14)" opacity=".86">
  <circle r="21" fill="none" stroke="#1F4FA0" stroke-width="2"/><circle r="16" fill="none" stroke="#1F4FA0" stroke-width=".9"/>
  <path id="arc" d="M-18.5 0a18.5 18.5 0 1 1 37 0" fill="none"/>
  <text font-family="Arial,sans-serif" font-size="4.4" font-weight="700" fill="#1F4FA0" letter-spacing=".5"><textPath href="#arc" startOffset="50%" text-anchor="middle">MARCHÉS PUBLICS</textPath></text>
  <g fill="#1F4FA0"><path d="M-8 -2l8-5 8 5z"/><rect x="-7" y="-1" width="2" height="7"/><rect x="-3" y="-1" width="2" height="7"/><rect x="1" y="-1" width="2" height="7"/><rect x="5" y="-1" width="2" height="7"/><rect x="-9" y="6.5" width="18" height="2"/></g>
  <text y="14" text-anchor="middle" font-family="Arial,sans-serif" font-size="4" font-weight="700" fill="#1F4FA0">TUNISIE</text>
 </g>
</g>
<!-- stylo plume -->
<g transform="translate(176 108) rotate(38)">
 <rect x="-4.5" y="-46" width="9" height="56" rx="4.5" fill="#14273D"/><rect x="-4.5" y="-30" width="9" height="4" fill="#D9B44A"/>
 <path d="M-4.5 10h9l-4.5 16z" fill="#D9B44A"/><path d="M0 12v10" stroke="#14273D" stroke-width=".9"/>
</g>
</svg>
"""


# Vraies photos libres de droits (Wikimedia Commons). Pour CHAQUE photo : crédit + licence affichés sous la photo
# et dans « À propos », preuve de la licence dans « preuves conditions d'utilisation/<date>/photos/ » (hors dépôt).
# Bandeau de l'accueil = MOSAÏQUE de 4 vraies photos prises en Tunisie (tous les marchés publics, pas seulement le BTP),
# assemblée en une seule image (recadrées). Une entrée par photo : chacune est créditée.
# Deux mises en page des MÊMES 4 photos : 4 côte à côte (ordinateur) et 2 x 2 (téléphone), choisies dans style.css.
MOSAIQUE = "assets/photos/marches-publics-mosaique.jpg"
MOSAIQUE_MOBILE = "assets/photos/marches-publics-mosaique-carre.jpg"
PHOTOS = [{
    "fichier": MOSAIQUE, "tuile": "en haut à gauche",
    "sujet_fr": "Travaux et BTP : chantier de construction à Monastir", "sujet_ar": "أشغال وبناء: حضيرة في المنستير",
    "auteur": "Habib M'henni", "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/deed.fr",
    "source_url": "https://commons.wikimedia.org/wiki/File:Chantier_de_construction,_Monastir,_Tunisie_-_1.jpg",
    "preuve": "2026-10-05/photos",
}, {
    "fichier": MOSAIQUE, "tuile": "en haut à droite",
    "sujet_fr": "Informatique : ordinateur portable (atelier MedinaPedia, Tunis)", "sujet_ar": "إعلامية: حاسوب محمول (ورشة مدينة بيديا، تونس)",
    "auteur": "Touzrimounir", "licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/deed.fr",
    "source_url": "https://commons.wikimedia.org/wiki/File:MedinaPedia_workshop_3.jpg",
    "preuve": "2026-10-05/photos",
}, {
    "fichier": MOSAIQUE, "tuile": "en bas à gauche",
    "sujet_fr": "Santé : chambre d'une clinique en Tunisie", "sujet_ar": "صحة: غرفة في مصحة بتونس",
    "auteur": "Habib M'henni", "licence": "CC BY-SA 3.0", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/deed.fr",
    "source_url": "https://commons.wikimedia.org/wiki/File:Chambre_clinique_priv%C3%A9e_en_Tunisie,_janvier_2014.jpg",
    "preuve": "2026-10-05/photos",
}, {
    "fichier": MOSAIQUE, "tuile": "en bas à droite",
    "sujet_fr": "Fournitures et transport : conteneurs au port de Radès", "sujet_ar": "توريدات ونقل: حاويات في ميناء رادس",
    "auteur": "M. Rais", "licence": "CC BY-SA 3.0", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/deed.fr",
    "source_url": "https://commons.wikimedia.org/wiki/File:Port_Rades_01.JPG",
    "preuve": "2026-10-05/photos",
}]


def credit_photos(photos):
    """Petit crédit sous le titre du bandeau : CHAQUE photo de la mosaïque (auteur -> page source, licence -> texte)."""
    morceaux = " · ".join(
        f'<a href="{E(ph["source_url"])}" target="_blank" rel="noopener">{E(ph["auteur"])}</a> '
        f'<a href="{E(ph["licence_url"])}" target="_blank" rel="noopener license">{E(ph["licence"])}</a>' for ph in photos)
    return (f'    <p class="credit-photo" data-photo="{E(MOSAIQUE)} {E(MOSAIQUE_MOBILE)}">{L("Photos", "صور")} '
            f'<bdi dir="ltr">(Wikimedia Commons) : {morceaux}</bdi></p>')


def ecrire_illustration(sortie):
    ecrire(sortie, "assets/illustration-accueil.svg", ILLUSTRATION.replace("{contour}", _contour()))


def type_ar(a):
    t = (a.get("type_commande") or "").split("/")[0].strip().lower()
    return TYPES_AR.get(t, "")


def procedure_ar(p):
    pl = (p or "").lower()
    for mot, ar in PROCEDURES_AR:
        if mot in pl:
            return ar
    return ""


def carte(a, racine, jour):
    m = M_PAR_NOM[a["metier"]]
    g = G_PAR_NOM[a["gouvernorat"]]
    lim = a["date_limite"]
    reste = (dt.date.fromisoformat(lim) - dt.date.fromisoformat(jour)).days if lim else None
    urgent = reste is not None and 0 <= reste < 7
    heure = a["heure_limite"]
    if lim:
        lim_fr = dfr(lim) + (f" · {heure}" if heure else "")
        lim_ar = ISO(dfr(lim) + (f" · {heure}" if heure else ""))
        reste_fr = "aujourd'hui !" if reste == 0 else "demain !" if reste == 1 else f"dans {reste} jours"
    else:
        lim_fr, lim_ar, reste_fr = "non indiquée", "غير مذكور", "voir la fiche"
    c = a["cautionnement_total_dt"]
    caution = L(montant(c), ISO(montant(c))) if c else L("non indiquée", "غير مذكور")
    objet = a["objet"]
    sens = 'dir="rtl" lang="ar"' if ARABE.search(objet) else 'dir="ltr" lang="fr"'
    infos_fr = [E(a.get("type_commande")), E(a.get("procedure"))]
    infos_ar = [type_ar(a) or E(a.get("type_commande")), procedure_ar(a.get("procedure")) or E(a.get("procedure"))]
    lots = str(a.get("nombre_lots") or "").strip()
    if lots.isdigit() and int(lots) > 1:
        infos_fr.append(f"{lots} lots")
        infos_ar.append(f"{ISO(lots)} أقساط")
    infos_fr.append(f"N° {E(a['numero'])}")
    infos_ar.append(f"عدد {ISO(E(a['numero']))}")
    infos_fr = " · ".join(x for x in infos_fr if x)
    infos_ar = " · ".join(x for x in infos_ar if x)
    return f"""<article class="ao{' urgent' if urgent else ''}" id="{E(a['numero'])}" data-num="{numero(a['numero'])}" data-metier="{m[1]}" data-gouv="{g[1]}" data-limite="{lim}" data-pub="{a['date_publication']}">
 <div class="ao-haut">{icone(m[1])}<a class="pastille" href="{racine}metier/{m[1]}/">{L(E(m[2]), m[3])}</a><a class="pastille gouv" href="{racine}gouvernorat/{g[1]}/">{ICONE_LIEU}{L(E(g[0]), g[2])}</a><span class="nouveau" hidden>{L("Nouveau", "جديد")}</span><span class="rappel" hidden></span></div>
 <h3 {sens}>{E(objet)}</h3>
 {resume_trad(objet)}
 <p class="acheteur">{E(a.get("acheteur") or "")}</p>
 <div class="ao-infos">
  <div class="limite"><span>{L("Date limite", "آخر أجل")}</span><b>{L(lim_fr, lim_ar)}</b><small class="reste">{reste_fr}</small></div>
  <div><span>{L("Caution provisoire", "الضمان الوقتي")}</span><b>{caution}</b></div>
 </div>
 <p class="ao-type">{L(infos_fr, infos_ar)}</p>
 <a class="officiel" href="{E(a['lien'])}" target="_blank" rel="noopener">{L("Voir la fiche officielle <small>(HAICOP)</small>", "البطاقة الرسمية <small>(الهيئة العليا)</small>")}{ICONE_LIEN}</a>
</article>"""


def options(liste, cle_slug, cle_fr, cle_ar, tous_fr, tous_ar, compte):
    o = [f'<option value="" data-fr="{tous_fr}" data-ar="{tous_ar}">{tous_fr} ({sum(compte.values())})</option>']
    for x in liste:
        o.append(f'<option value="{x[cle_slug]}" data-fr="{E(x[cle_fr])}" data-ar="{x[cle_ar]}">{E(x[cle_fr])} ({compte.get(x[cle_slug], 0)})</option>')
    return "\n".join(o)


def recherche_seule():
    """Champ de recherche seul (pages sans filtres métier/gouvernorat, ex. ventes aux enchères)."""
    return (f'<section class="carte filtres un"><div class="f-q"><label for="f-q">{L("Rechercher", "بحث")}</label>'
            '<input id="f-q" type="search" enterkeyhint="search" autocomplete="off" placeholder="Mot-clé, bureau des douanes, ville…" '
            'data-fr="Mot-clé, bureau des douanes, ville…" data-ar="كلمة، مكتب الديوانة، مدينة…"></div></section>')


def filtres(aos, avec_metier=True, avec_gouv=True):
    cm, cg = {}, {}
    for a in aos:
        cm[M_PAR_NOM[a["metier"]][1]] = cm.get(M_PAR_NOM[a["metier"]][1], 0) + 1
        cg[G_PAR_NOM[a["gouvernorat"]][1]] = cg.get(G_PAR_NOM[a["gouvernorat"]][1], 0) + 1
    blocs = [f'<div class="f-q"><label for="f-q">{L("Rechercher", "بحث")}</label>'
             '<input id="f-q" type="search" enterkeyhint="search" autocomplete="off" '
             'placeholder="Mot-clé, acheteur, n° Tender-…" data-fr="Mot-clé, acheteur, n° Tender-…" '
             'data-ar="كلمة، مشترٍ، رقم ⁦Tender-…⁩"></div>']
    if avec_metier:
        blocs.append(f'<div><label for="f-metier">{L("Métier", "الاختصاص")}</label><select id="f-metier">'
                     f'{options(METIERS, 1, 2, 3, "Tous les métiers", "كل الاختصاصات", cm)}</select></div>')
    if avec_gouv:
        blocs.append(f'<div><label for="f-gouv">{L("Gouvernorat", "الولاية")}</label><select id="f-gouv">'
                     f'{options(GOUVERNORATS, 1, 0, 2, "Toute la Tunisie", "كل الولايات", cg)}</select></div>')
    blocs.append(f'<div class="f-tri"><label for="f-tri">{L("Trier par", "الترتيب حسب")}</label><select id="f-tri">'
                 '<option value="limite" data-fr="Date limite la plus proche" data-ar="أقرب آخر أجل">Date limite la plus proche</option>'
                 '<option value="recent" data-fr="Plus récents d\'abord" data-ar="الأحدث أولاً">Plus récents d\'abord</option></select></div>')
    if not (avec_metier and avec_gouv):
        return f'<section class="carte filtres deux">{"".join(blocs)}</section>'
    return f'<section class="carte filtres">{"".join(blocs)}</section>'


def liste_html(aos, racine, jour, vide_fr, vide_ar, unite=None, cartes_html=None):
    """Liste filtrable. unite = (singulier FR, pluriel FR, arabe) pour le compteur (défaut : appels d'offres)."""
    cartes = cartes_html if cartes_html is not None else "\n".join(carte(a, racine, jour) for a in aos)
    n = len(aos)
    if unite:
        u1, un, uar = unite
        return f"""<p class="compte" id="compte" aria-live="polite" data-un="{E(u1)}" data-pl="{E(un)}" data-ar="{E(uar)}"><span>{n} {E(u1 if n <= 1 else un)}</span></p>
<div class="liste" id="liste">
{cartes}
</div>
<button type="button" class="plus" id="plus" hidden>Afficher plus</button>
<p class="carte vide" id="vide"{' hidden' if aos else ''}>{L(vide_fr, vide_ar)}</p>"""
    return f"""<p class="compte" id="compte" aria-live="polite"><span>{n} appel{'s' if n > 1 else ''} d'offres ouvert{'s' if n > 1 else ''}</span></p>
<div class="liste" id="liste">
{cartes}
</div>
<button type="button" class="plus" id="plus" hidden>Afficher plus</button>
<p class="carte vide" id="vide"{' hidden' if aos else ''}>{L(vide_fr, vide_ar)}</p>"""


def grille(items, actuel, racine, dossier, comptes, ident, icones=False):
    liens = []
    for slug, fr, ar in items:
        n = comptes.get(slug, 0)
        cl = " ".join(x for x in ("zero" if not n else "", "ici" if slug == actuel else "") if x)
        liens.append(f'<a href="{racine}{dossier}/{slug}/"{f" class={chr(34)}{cl}{chr(34)}" if cl else ""}>{icone(slug, "ic-p") if icones else ""}<span>{L(E(fr), ar)}</span><span class="n">{n}</span></a>')
    return f'<div class="grille" id="{ident}">{"".join(liens)}</div>'


# (05-06/10/2026) Rangée de badges « Source officielle / Gratuit / Mis à jour » supprimée à la demande d'Ahmed :
# des cartes avec icône qui ressemblaient à des boutons mais ne faisaient rien. L'info est dans le texte d'intro.


# Sécurité (balises meta, GitHub Pages ne permet pas d'en-têtes) : scripts du site seulement, polices Google,
# formulaires envoyés seulement au site ou à Google Forms ; aucun cadre, aucun plugin.
# GoatCounter (statistiques de visite anonymes, sans cookies) : script gc.zgo.at, envoi vers le compteur.
COMPTEUR = "https://prix-eaux-tunisie.goatcounter.com"
# « Votre avis » (règle d'Ahmed du 05/10/2026 : sur chacun de ses sites) : envoi au clic vers Formspree (assets/avis.js)
FORMSPREE = "https://formspree.io"
CSP = ("default-src 'self'; script-src 'self' https://gc.zgo.at; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       f"font-src 'self' https://fonts.gstatic.com; img-src 'self' data: {COMPTEUR}; connect-src 'self' {COMPTEUR} {FORMSPREE}; "
       f"form-action 'self' https://docs.google.com {FORMSPREE}; frame-src 'none'; object-src 'none'; base-uri 'self'")


# Section « Votre avis » de l'accueil (envoi par assets/avis.js, champs cachés site + page)
AVIS = """<section class="carte avis" id="avis" aria-labelledby="avis-titre">
  <h2 id="avis-titre"><span data-l="fr">Votre avis</span><span data-l="ar">رأيك يهمّنا</span></h2>
  <p class="avis-intro"><span data-l="fr">Une remarque, une erreur, une idée ? Écrivez-nous : chaque message est lu.</span><span data-l="ar">ملاحظة، خطأ، فكرة؟ اكتب لنا: كل رسالة تُقرأ.</span></p>
  <form id="avis-form" action="https://formspree.io/f/mwlpakqj" method="POST">
    <fieldset>
      <legend><span data-l="fr">Votre note (facultatif)</span><span data-l="ar">تقييمك (اختياري)</span></legend>
      <div class="avis-notes">
        <label><input type="radio" name="note" value="😀 Très bien"><span class="emoji" aria-hidden="true">😀</span><span class="avis-cache"><span data-l="fr">Très bien</span><span data-l="ar">ممتاز</span></span></label>
        <label><input type="radio" name="note" value="🙂 Bien"><span class="emoji" aria-hidden="true">🙂</span><span class="avis-cache"><span data-l="fr">Bien</span><span data-l="ar">جيد</span></span></label>
        <label><input type="radio" name="note" value="😐 Moyen"><span class="emoji" aria-hidden="true">😐</span><span class="avis-cache"><span data-l="fr">Moyen</span><span data-l="ar">متوسط</span></span></label>
        <label><input type="radio" name="note" value="🙁 Pas bien"><span class="emoji" aria-hidden="true">🙁</span><span class="avis-cache"><span data-l="fr">Pas bien</span><span data-l="ar">سيئ</span></span></label>
      </div>
    </fieldset>
    <label class="avis-etiquette" for="avis-message"><span data-l="fr">Votre message</span><span data-l="ar">رسالتك</span></label>
    <textarea id="avis-message" name="message" required maxlength="1000" rows="4" data-ph-fr="Ce qui vous plaît, ce qui manque, une erreur à corriger…" data-ph-ar="ما يعجبك، ما ينقص، خطأ يجب تصحيحه…"></textarea>
    <span class="avis-compte" id="avis-compte" aria-live="off">0 / 1000</span>
    <label class="avis-etiquette" for="avis-email"><span data-l="fr">Votre e-mail (facultatif, pour vous répondre)</span><span data-l="ar">بريدك الإلكتروني (اختياري، للرد عليك)</span></label>
    <input type="email" id="avis-email" name="email" autocomplete="email" maxlength="200" data-ph-fr="nom@example.com" data-ph-ar="nom@example.com">
    <input type="hidden" name="site" value="Alertes appels d&#39;offres Tunisie">
    <input type="hidden" name="page" value="">
    <input type="hidden" name="_subject" value="Avis — Alertes appels d&#39;offres Tunisie">
    <input type="text" name="_gotcha" class="avis-piege" tabindex="-1" autocomplete="off" aria-hidden="true">
    <div class="avis-actions">
      <button type="submit" class="avis-envoyer"><span data-l="fr">Envoyer</span><span data-l="ar">إرسال</span></button>
      <span id="avis-status" role="status" aria-live="polite"></span>
    </div>
    <p class="avis-mention"><span data-l="fr">Votre avis est envoyé au créateur du site (service Formspree). Rien n&#39;est envoyé sans clic sur « Envoyer ».</span><span data-l="ar">يُرسل رأيك إلى صاحب الموقع (خدمة ⁨Formspree⁩). لا يُرسل أي شيء دون الضغط على «إرسال».</span></p>
  </form>
</section>"""


def page(chemin, racine, titre, description, hero, contenu, v, etat, jsonld="", classe_hero="", scripts=()):
    canon = URL_SITE + chemin
    return f"""<!doctype html>
<html lang="fr" dir="ltr" translate="no" data-racine="{racine}">
<head>
<meta charset="utf-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="robots" content="noai, noimageai">
<title>{E(titre)}</title>
<meta name="description" content="{E(description)}">
<link rel="canonical" href="{canon}">
<link rel="icon" href="{racine}assets/logo.svg" type="image/svg+xml">
<link rel="icon" href="{racine}favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="{racine}assets/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Appels d'offres">
<link rel="manifest" href="{racine}manifest.webmanifest">
<meta name="theme-color" content="#24476B">
<meta property="og:title" content="{E(titre.split(' | ')[0])}">
<meta property="og:description" content="{E(description)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{URL_SITE}assets/og-image-v6.jpg">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_TN"><meta property="og:locale:alternate" content="ar_TN">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;700;800&family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{racine}assets/style.css?v={v}">
{STYLE_ICONES}
{jsonld}<script src="{racine}assets/page.js?v={v}"></script>
<script src="{racine}assets/app.js?v={v}"></script>
<script src="{racine}assets/avis.js?v={v}"></script>
{"".join(f'<script src="{racine}assets/{s}?v={v}"></script>{chr(10)}' for s in scripts)}</head>
<body data-maj="{etat['maj']}" data-maj-texte="{etat['maj_texte']}" data-panne="{'1' if etat['panne'] else '0'}">
{SPRITE}
<header class="entete" id="entete"></header>
<section class="hero{classe_hero}">
  <div class="wrap">
{hero}
    <span class="maj">{L("Mis à jour le", "تحيين")}&nbsp;{ISO(etat['maj_texte']) if etat['maj_texte'] else '—'}</span>
  </div>
</section>
<main class="wrap chevauche">
<div class="alerte-panne{' on' if etat['panne'] else ''}" id="alerte-panne" role="status">{E(etat['message'])}</div>
{contenu}
</main>
<footer id="pied"><div class="wrap"><p>Source : HAICOP (marchespublics.gov.tn) · © 2026 Alertes appels d'offres Tunisie — tous droits réservés.</p></div></footer>
<script data-goatcounter="{COMPTEUR}/count" async src="https://gc.zgo.at/count.js"></script>
</body>
</html>
"""


def fil(racine, fr, ar):
    return f'    <p class="fil"><a href="{racine}">{L("Accueil", "الرئيسية")}</a> › {L(fr, ar)}</p>'


# ------------------------------------------------------------ alertes, entreprises privées, enchères
ICONE_TELEGRAM = '<svg viewBox="0 0 24 24"><path d="M21 4.5 2.8 11.4c-.9.4-.9 1.6.1 1.9l4.5 1.4 1.7 5.3c.3.8 1.3 1 1.9.4l2.5-2.4 4.6 3.4c.7.5 1.7.1 1.9-.7L23 5.8c.2-1-.9-1.8-2-1.3z"/><path d="m8 14.6 9.5-6.6"/></svg>'
ICONE_MARTEAU = '<svg viewBox="0 0 24 24"><path d="m14 4 6 6M11.5 6.5l6 6M13 5l-6 6 3 3 6-6"/><path d="m8.5 12.5-6 6 2 2 6-6"/><path d="M13 21h8"/></svg>'


def bouton_alertes(adr):
    """Boutons « Recevoir les alertes » : rien du tout tant que l'adresse du canal n'est pas réglée."""
    b = []
    if adr["telegram"]:
        b.append(f'<a class="btn-alerte btn-telegram" href="{E(adr["telegram"])}" target="_blank" rel="noopener">{ICONE_TELEGRAM}'
                 f'{L("Recevoir les alertes sur Telegram", "تلقَّ التنبيهات على تيليغرام")}</a>')
    if adr["whatsapp"]:
        b.append(f'<a class="btn-alerte btn-whatsapp" href="{E(adr["whatsapp"])}" target="_blank" rel="noopener">'
                 f'{L("Recevoir les alertes sur WhatsApp", "تلقَّ التنبيهات على واتساب")}</a>')
    return f'<div class="alertes-btn">{"".join(b)}</div>' if b else ""


M_PAR_SLUG = {m[1]: m for m in METIERS}
G_PAR_SLUG = {g[1]: g for g in GOUVERNORATS}


def charger_prives(chemin, jour):
    """Appels d'offres publiés par les entreprises (donnees/prives.json, écrit par prives.py), encore ouverts."""
    try:
        with open(chemin, encoding="utf-8") as f:
            pub = json.load(f).get("publies") or []
    except (OSError, ValueError, AttributeError):
        return []
    res = []
    for p in pub if isinstance(pub, list) else []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "")
        lim = str(p.get("date_limite") or "")
        if not re.fullmatch(r"Prive-[0-9a-f]{10}", pid) or not DATE.match(lim) or lim < jour:
            continue
        if p.get("metier") not in M_PAR_SLUG or p.get("gouvernorat") not in G_PAR_SLUG:
            continue
        if not str(p.get("objet") or "").strip() or not str(p.get("entreprise") or "").strip():
            continue
        res.append(p)
    res.sort(key=lambda p: (p["date_limite"], p["id"]))
    return res


def carte_prive(p, racine):
    m, g = M_PAR_SLUG[p["metier"]], G_PAR_SLUG[p["gouvernorat"]]
    objet = str(p["objet"])
    sens = 'dir="rtl" lang="ar"' if ARABE.search(objet) else 'dir="ltr" lang="fr"'
    desc = str(p.get("description") or "")
    if len(desc) > 300:
        desc = desc[:297].rsplit(" ", 1)[0] + "…"
    pub = str(p.get("recu_le") or "")[:10]
    return f"""<article class="ao prive" id="{E(p['id'])}" data-num="0" data-metier="{m[1]}" data-gouv="{g[1]}" data-limite="{p['date_limite']}" data-pub="{pub if DATE.match(pub) else ''}">
 <div class="ao-haut">{icone(m[1])}<a class="pastille" href="{racine}metier/{m[1]}/">{L(E(m[2]), m[3])}</a><a class="pastille gouv" href="{racine}gouvernorat/{g[1]}/">{ICONE_LIEU}{L(E(g[0]), g[2])}</a><span class="badge-prive">{L("Entreprise privée", "مؤسسة خاصة")}</span><span class="rappel" hidden></span></div>
 <h3 {sens}>{E(objet)}</h3>
 {resume_trad(objet)}
 <p class="acheteur">{E(p['entreprise'])}</p>
 {f'<p class="desc">{E(desc)}</p>' if desc else ''}
 <div class="ao-infos">
  <div class="limite"><span>{L("Date limite", "آخر أجل")}</span><b>{L(dfr(p['date_limite']), ISO(dfr(p['date_limite'])))}</b><small class="reste"></small></div>
  <div><span>{L("Contact", "الاتصال")}</span><b class="contact">{E(p.get('contact'))}</b></div>
 </div>
 <p class="non-verifie">{L("Publié par l'entreprise — non vérifié par HAICOP", "نشرته المؤسسة — لم تتحقق منه الهيئة العليا للطلب العمومي")}</p>
</article>"""


def section_prives(prives, racine):
    cartes = "\n".join(carte_prive(p, racine) for p in prives)
    return f"""<section class="bloc-prives" id="prives"{'' if prives else ' hidden'}>
<h2 class="titre-section">{L("Appels d'offres d'entreprises privées", "طلبات عروض المؤسسات الخاصة")}</h2>
<p class="sous-titre">{L("Publiés gratuitement par les entreprises elles-mêmes, contrôlés automatiquement mais <b>non vérifiés par HAICOP</b>.", "نشرتها المؤسسات نفسها مجانًا، مع مراقبة آلية، لكن <b>لم تتحقق منها الهيئة العليا للطلب العمومي</b>.")}
 <a href="{racine}publier/">{L("Publier le vôtre", "انشر طلبك")}</a></p>
<div class="liste" id="liste-prives">
{cartes}
</div>
</section>"""


def charger_encheres(chemin, jour):
    """Ventes aux enchères de la Douane (donnees/encheres.json, écrit par lire_douane.py) -> (ventes ouvertes, état)."""
    try:
        with open(chemin, encoding="utf-8") as f:
            brut = json.load(f)
        ventes = brut.get("ventes") or {}
    except (OSError, ValueError, AttributeError):
        brut, ventes = {}, {}
    if isinstance(ventes, dict):
        ventes = list(ventes.values())
    res = []
    for v in ventes if isinstance(ventes, list) else []:
        if not isinstance(v, dict):
            continue
        lim = str(v.get("date_limite") or "")
        if not re.fullmatch(r"Vente-[0-9a-f]{10}", str(v.get("id") or "")) or not DATE.match(lim) or lim < jour:
            continue
        if not str(v.get("objet") or "").strip():
            continue
        lien = str(v.get("lien_avis") or "")
        if not lien.startswith(lire_douane_prefixe()) or any(x in lien for x in "\"'<> "):
            lien = URL_DOUANE
        cahier = str(v.get("lien_cahier") or "")
        if not cahier.startswith(lire_douane_prefixe()) or any(x in cahier for x in "\"'<> "):
            cahier = ""
        res.append(dict(v, lien_avis=lien, lien_cahier=cahier,
                        gouvernorat=v.get("gouvernorat") if v.get("gouvernorat") in G_PAR_NOM else "National / non précisé"))
    res.sort(key=lambda v: (v["date_limite"], str(v.get("heure") or ""), v["id"]))
    statut = (brut.get("statut_source") or {}) if isinstance(brut, dict) else {}
    maj = str(brut.get("derniere_lecture_reussie") or "") if isinstance(brut, dict) else ""
    if not re.match(r"^\d{4}-\d{2}-\d{2}", maj):
        maj = ""
    age = (dt.date.fromisoformat(jour) - dt.date.fromisoformat(maj[:10])).days if maj else None
    panne = age is None or age >= AGE_AVERTISSEMENT
    if statut.get("etat") == "panne" or panne:
        print(f"  ! échec : ventes aux enchères (Douane) — {statut.get('raison') or 'lecture ancienne ou absente'}"
              f" (dernière lecture réussie : {maj or 'jamais'})")
    maj_texte = (dfr(maj[:10]) + (" " + maj[11:16] if len(maj) >= 16 else "")) if maj else ""
    message = (f"⚠️ La page officielle de la Douane n'a pas pu être lue depuis le {dfr(maj[:10])} : la liste peut être incomplète."
               if maj else "⚠️ Ventes aux enchères pas encore lues : consultez le portail de la Douane.") if panne else ""
    return res, {"maj": maj, "maj_texte": maj_texte, "panne": panne, "message": message}


URL_DOUANE = "https://www.douane.gov.tn/ventes-aux-encheres-publiques/"


def lire_douane_prefixe():
    return "https://www.douane.gov.tn/"


def carte_enchere(v, racine):
    g = G_PAR_NOM[v["gouvernorat"]]
    objet = str(v["objet"])
    sens = 'dir="rtl" lang="ar"' if ARABE.search(objet) else 'dir="ltr" lang="fr"'
    heure = str(v.get("heure") or "")
    heure = heure if re.fullmatch(r"\d{1,2}[:h]\d{2}", heure) else ""
    lim = dfr(v["date_limite"]) + (f" · {heure}" if heure else "")
    pub = str(v.get("date_publication") or "")
    pub = pub if DATE.match(pub) else ""
    cahier = (f'<a class="cahier" href="{E(v["lien_cahier"])}" target="_blank" rel="noopener">{L("Cahier des charges (PDF)", "كراس الشروط")}</a>'
              if v.get("lien_cahier") else "")
    return f"""<article class="ao enchere" id="{E(v['id'])}" data-num="0" data-metier="" data-gouv="{g[1]}" data-limite="{v['date_limite']}" data-pub="{pub}">
 <div class="ao-haut"><span class="ic-m ic-enchere" aria-hidden="true">{ICONE_MARTEAU}</span><a class="pastille gouv" href="{racine}gouvernorat/{g[1]}/">{ICONE_LIEU}{L(E(g[0]), g[2])}</a><span class="nouveau" hidden>{L("Nouveau", "جديد")}</span><span class="rappel" hidden></span></div>
 <h3 {sens}>{E(objet)}</h3>
 {resume_trad(objet)}
 <p class="acheteur">{E(v.get('bureau') or '')}</p>
 <div class="ao-infos">
  <div class="limite"><span>{L("Échéance", "آخر أجل")}</span><b>{L(lim, ISO(lim))}</b><small class="reste"></small></div>
  <div><span>{L("Publié le", "تاريخ النشر")}</span><b>{L(dfr(pub) or "—", ISO(dfr(pub)) if pub else "—")}</b></div>
 </div>
 <a class="officiel" href="{E(v['lien_avis'])}" target="_blank" rel="noopener">{L("Avis officiel <small>(PDF, Douane)</small>", "الإعلان الرسمي <small>(الديوانة)</small>")}{ICONE_LIEN}</a>
 {cahier}
</article>"""


# ------------------------------------------------------------ Alertes Pro (abonnement payant, accord d'Ahmed du 06/10/2026)
# La CONSULTATION du site reste gratuite. Payant : alertes personnalisées (métiers + gouvernorats) chaque matin sur Telegram.
# Les abonnés (données personnelles) sont dans le dépôt PRIVÉ Ah6259/appels-offres-abonnes, jamais ici.
ABO = {
    "prix_mois": 25, "prix_an": 199, "essai_jours": 14, "rappel_jours": 3,
    "numero": "24 321 390",                         # D17, IZI, Wafacash
    "whatsapp": "21624321390",                      # preuve de paiement
    "paiements": ["D17", "IZI", "Wafacash"],
    "formspree": "https://formspree.io/f/mwlpakqj",
}
TEXTE_PREUVE = ("Bonjour, voici la preuve de paiement de mon abonnement Alertes Pro "
                "(Alertes appels d'offres Tunisie). Entreprise : ")
ICONE_CLOCHE = '<svg viewBox="0 0 24 24"><path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.8 1.8H4.2z"/><path d="M10 20.5a2 2 0 0 0 4 0"/></svg>'
ICONE_WA = '<svg viewBox="0 0 24 24"><path d="M4 20l1.3-4A8 8 0 1 1 8.4 19z"/><path d="M9 8.6c0 3.4 2.9 6.4 6.4 6.4l1-1.4-2-1-1 .9c-1-.4-2.1-1.5-2.5-2.5l.9-1-1-2z"/></svg>'


def prix_abo():
    m, a = ABO["prix_mois"], ABO["prix_an"]
    return L(f"{m} DT / mois <small>ou {a} DT / an</small>",
             f"{ISO(m)} دينار / شهر <small>أو {ISO(a)} دينار / سنة</small>")


def lien_preuve(ident="abo-preuve"):
    import urllib.parse
    url = f"https://wa.me/{ABO['whatsapp']}?text={urllib.parse.quote(TEXTE_PREUVE)}"
    return (f'<a class="btn-wa" id="{ident}" href="{E(url)}" data-texte="{E(TEXTE_PREUVE)}" target="_blank" rel="noopener">{ICONE_WA}'
            + L("Envoyer la preuve de paiement par WhatsApp", "أرسل إثبات الدفع عبر واتساب") + "</a>")


def liste_paiements():
    modes = "".join(f'<dt>{m}</dt><dd><bdi dir="ltr">{ABO["numero"]}</bdi></dd>' for m in ABO["paiements"])
    return (f'<dl class="paie">{modes}'
            f'<dt>{L("Montant", "المبلغ")}</dt><dd>{prix_abo()}</dd>'
            f'<dt>{L("Motif", "سبب الدفع")}</dt><dd>{L("le nom de votre entreprise", "اسم مؤسستك")}</dd></dl>')


def texte_telegram(robot):
    """Instructions Telegram après l'inscription (le code est donné par Ahmed à l'activation)."""
    if robot:
        lien = f'<a href="https://t.me/{E(robot)}" target="_blank" rel="noopener"><bdi dir="ltr">@{E(robot)}</bdi></a>'
        return L(f"Ouvrez notre robot {lien} dans Telegram et envoyez <b>/start</b> suivi de votre code "
                 "(exemple : <code>/start AB12CD</code>). Le code vous est donné à l'activation.",
                 f"افتح برنامجنا {lien} في تيليغرام وأرسل <b><bdi dir=\"ltr\">/start</bdi></b> متبوعًا برمزك "
                 "(مثال: <code dir=\"ltr\">/start AB12CD</code>). يُعطى لك الرمز عند التفعيل.")
    return L("Le lien Telegram vous est envoyé à l'activation, avec votre code personnel : il suffira d'ouvrir notre robot "
             "et d'envoyer <b>/start</b> suivi de votre code.",
             "يُرسل إليك رابط تيليغرام عند التفعيل مع رمزك الشخصي: يكفي أن تفتح برنامجنا وترسل "
             "<b><bdi dir=\"ltr\">/start</bdi></b> متبوعًا برمزك.")


def bouton_pro_accueil(racine=""):
    """Gros bouton doré en haut de l'accueil -> page abonnement/."""
    n = ABO["essai_jours"]
    titre = L("Alertes Pro : vos appels d'offres chaque matin sur Telegram", "تنبيهات Pro: طلبات عروضك كل صباح على تيليغرام")
    sous = L(f"{n} jours d'essai gratuit · seulement vos métiers et vos gouvernorats",
             f"تجربة مجانية {ISO(n)} يومًا · اختصاصاتك وولاياتك فقط")
    return (f'    <a class="btn-pro-grand" id="btn-pro-accueil" href="{racine}abonnement/">{ICONE_CLOCHE}'
            f'<span>{titre}<small>{sous}</small></span></a>')


def pages_abonnement(adr, v, etat):
    """Page abonnement/ (prix, avantages, paiement, inscription) et abonnement/conditions/."""
    essai = ABO["essai_jours"]
    pm, pa, rj = ABO["prix_mois"], ABO["prix_an"], ABO["rappel_jours"]
    cases_m = "".join(f'<label class="case"><input type="checkbox" name="metiers" value="{slug}"> {icone(slug, "ic-p")}<span>{L(E(fr), ar)}</span></label>'
                      for _, slug, fr, ar in METIERS)
    cases_g = (f'<label class="case tous"><input type="checkbox" name="gouvernorats" value="tous" id="g-tous"> <span><b>{L("Toute la Tunisie", "كل الولايات")}</b></span></label>'
               + "".join(f'<label class="case"><input type="checkbox" name="gouvernorats" value="{slug}"> <span>{L(E(nom), ar)}</span></label>'
                         for nom, slug, ar in GOUVERNORATS if slug not in ("plusieurs", "national")))
    accepte = L('J\'accepte les <a href="conditions/">conditions de l\'abonnement</a>.', 'أوافق على <a href="conditions/">شروط الاشتراك</a>.')
    hero = f"""{fil("../", "Alertes Pro", "تنبيهات Pro")}
    <h1>{L("Alertes Pro sur Telegram", "تنبيهات Pro على تيليغرام")}</h1>
    <p class="intro">{L("Chaque matin, seulement les nouveaux appels d'offres de VOS métiers et de VOS gouvernorats, directement sur votre téléphone. La consultation du site reste gratuite.",
                        "كل صباح، طلبات العروض الجديدة في اختصاصاتك وولاياتك فقط، مباشرة على هاتفك. تصفح الموقع يبقى مجانيًا.")}</p>"""
    contenu = f"""<section class="offre-pro" id="offre">
  <p class="ruban">{L(f"{essai} jours d'essai gratuit", f"تجربة مجانية {ISO(essai)} يومًا")}</p>
  <h2>{L("Abonnement Alertes Pro", "اشتراك تنبيهات Pro")}</h2>
  <p class="prix" id="abo-prix">{prix_abo()}</p>
  <ul class="avantages">
    <li>{L("Un message chaque matin sur <b>Telegram</b> : seulement les nouveaux appels d'offres de vos métiers et de vos gouvernorats", "رسالة كل صباح على <b>تيليغرام</b>: طلبات العروض الجديدة في اختصاصاتك وولاياتك فقط")}</li>
    <li>{L("Plusieurs métiers et gouvernorats au choix, ou toute la Tunisie", "عدة اختصاصات وولايات حسب اختيارك، أو كل الولايات")}</li>
    <li>{L("Pour chaque annonce : date limite et lien vers la fiche officielle HAICOP", "لكل إعلان: آخر أجل ورابط البطاقة الرسمية")}</li>
    <li>{L("Jamais deux fois le même appel d'offres", "لا يُرسل نفس طلب العروض مرتين")}</li>
    <li>{L(f"Pas de renouvellement automatique : rappel {rj} jours avant la fin, puis l'alerte s'arrête simplement", f"لا تجديد آلي: تذكير قبل النهاية بـ{ISO(rj)} أيام، ثم يتوقف التنبيه ببساطة")}</li>
    <li><strong>{L("Sans engagement au-delà d'un an", "دون التزام بعد السنة")}</strong></li>
  </ul>
  <p class="petit">{L(f"{essai} jours d'essai gratuit, sans paiement. Ensuite, paiement par D17, IZI ou Wafacash (bouton « Paiement »). Une facture vous est adressée.",
                      f"تجربة مجانية لمدة {ISO(essai)} يومًا دون دفع. بعدها، الدفع عبر ⁨D17⁩ أو ⁨IZI⁩ أو ⁨Wafacash⁩ (زر «الدفع»). تُرسل إليك فاتورة.")}</p>
  <details class="paiement" id="paiement"><summary class="btn-clair">{L("Paiement", "الدفع")}</summary>
    {liste_paiements()}
    {lien_preuve()}
    <p class="petit">{L("Payez après l'essai gratuit (ou tout de suite si vous préférez), avec pour motif le nom de votre entreprise, puis envoyez la preuve par WhatsApp. Une facture vous est adressée.",
                        "ادفع بعد التجربة المجانية (أو فورًا إن أردت) مع ذكر اسم مؤسستك كسبب للدفع، ثم أرسل الإثبات عبر واتساب. تُرسل إليك فاتورة.")}</p>
  </details>
  <a class="btn-pro" href="#inscription">{L(f"Je m'inscris : {essai} jours gratuits", f"أسجّل: {ISO(essai)} يومًا مجانًا")}</a>
</section>
<section class="carte">
  <h2>{L("Comment ça marche ?", "كيف يعمل؟")}</h2>
  <ol class="etapes" data-l="fr">
    <li>Vous choisissez vos <b>métiers</b> et vos <b>gouvernorats</b> dans le formulaire ci-dessous.</li>
    <li>Nous activons votre abonnement (en général sous 24 heures) et vous envoyons votre <b>code personnel</b>.</li>
    <li>Dans Telegram, vous ouvrez notre robot et envoyez <b>/start</b> suivi de votre code.</li>
    <li>Chaque matin, vous recevez les nouveaux appels d'offres qui vous concernent (y compris ceux « national » ou « plusieurs gouvernorats » de vos métiers).</li>
  </ol>
  <ol class="etapes" data-l="ar">
    <li>تختار <b>اختصاصاتك</b> و<b>ولاياتك</b> في الاستمارة أسفله.</li>
    <li>نفعّل اشتراكك (عادة في غضون ⁦24⁩ ساعة) ونرسل إليك <b>رمزك الشخصي</b>.</li>
    <li>في تيليغرام، تفتح برنامجنا وترسل <b><bdi dir="ltr">/start</bdi></b> متبوعًا برمزك.</li>
    <li>كل صباح، تصلك طلبات العروض الجديدة التي تهمّك (ومنها «الوطنية» أو «لعدة ولايات» في اختصاصاتك).</li>
  </ol>
</section>
<section class="carte abo" id="inscription" aria-labelledby="abo-titre">
  <h2 id="abo-titre">{L("Inscription", "التسجيل")}</h2>
  <form id="abo-form" action="{ABO['formspree']}" method="POST" novalidate>
    <label class="abo-etiquette" for="abo-nom">{L("Votre nom", "اسمك")}</label>
    <input id="abo-nom" name="nom" required maxlength="100" autocomplete="name">
    <label class="abo-etiquette" for="abo-entreprise">{L("Entreprise (motif du paiement et facture)", "المؤسسة (سبب الدفع والفاتورة)")}</label>
    <input id="abo-entreprise" name="entreprise" required maxlength="120" autocomplete="organization">
    <label class="abo-etiquette" for="abo-tel">{L("Téléphone (8 chiffres)", "الهاتف (⁦8⁩ أرقام)")}</label>
    <input id="abo-tel" name="telephone" required inputmode="tel" pattern="[0-9 ]{{8,11}}" maxlength="11" autocomplete="tel">
    <label class="abo-etiquette" for="abo-email">{L("E-mail (pour la confirmation et la facture)", "البريد الإلكتروني (للتأكيد والفاتورة)")}</label>
    <input id="abo-email" type="email" name="email" required maxlength="200" autocomplete="email">
    <fieldset class="abo-choix" id="abo-metiers">
      <legend>{L("Vos métiers (un ou plusieurs)", "اختصاصاتك (واحد أو أكثر)")}</legend>
      <div class="cases">{cases_m}</div>
    </fieldset>
    <fieldset class="abo-choix" id="abo-gouv">
      <legend>{L("Vos gouvernorats (un ou plusieurs)", "ولاياتك (واحدة أو أكثر)")}</legend>
      <div class="cases">{cases_g}</div>
    </fieldset>
    <fieldset class="abo-choix" id="abo-formule">
      <legend>{L("Votre formule", "صيغتك")}</legend>
      <label class="case"><input type="radio" name="formule" value="essai {essai} jours" checked> <span>{L(f"<b>{essai} jours d'essai gratuit</b>, je paierai ensuite si je suis satisfait", f"<b>تجربة مجانية {ISO(essai)} يومًا</b>، وأدفع بعدها إن كنت راضيًا")}</span></label>
      <label class="case"><input type="radio" name="formule" value="je paie directement"> <span>{L(f"Je paie directement ({pm} DT / mois ou {pa} DT / an)", f"أدفع مباشرة ({ISO(pm)} دينار / شهر أو {ISO(pa)} دينار / سنة)")}</span></label>
    </fieldset>
    <label class="case"><input type="checkbox" name="conditions" value="oui" required id="abo-conditions"> <span>{accepte}</span></label>
    <input type="hidden" name="site" value="Alertes appels d&#39;offres Tunisie">
    <input type="hidden" name="page" value="">
    <input type="hidden" name="_subject" value="Abonnement Alertes Pro — Alertes appels d&#39;offres Tunisie">
    <input type="text" name="_gotcha" class="abo-piege" tabindex="-1" autocomplete="off" aria-hidden="true">
    <button type="submit" class="btn-pro">{L("Envoyer mon inscription", "أرسل تسجيلي")}</button>
    <p id="abo-status" role="status" aria-live="polite"></p>
    <p class="petit">{L("Vos coordonnées servent seulement à l'abonnement et à la facture : elles ne sont jamais publiées ni vendues (envoi par le service Formspree). Rien n'est envoyé sans clic sur « Envoyer ».",
                        "تُستعمل بياناتك للاشتراك والفاتورة فقط: لا تُنشر ولا تُباع أبدًا (إرسال عبر خدمة ⁨Formspree⁩). لا يُرسل أي شيء دون الضغط على «أرسل».")}</p>
  </form>
  <div class="apres-abo" id="apres-abo" hidden>
    <h3>{L("Merci, votre inscription est bien reçue", "شكرًا، وصلنا تسجيلك")}</h3>
    <p>{L(f"Nous activons votre abonnement, en général sous 24 heures. Vos {essai} jours d'essai gratuit commencent à l'activation.", f"نفعّل اشتراكك عادة في غضون ⁦24⁩ ساعة. تبدأ أيامك المجانية الـ{ISO(essai)} عند التفعيل.")}</p>
    <h3>{L("Recevoir les alertes sur Telegram", "تلقي التنبيهات على تيليغرام")}</h3>
    <p id="abo-telegram">{texte_telegram(adr["robot"])}</p>
    <p class="petit">{L("Installez Telegram (gratuit) sur votre téléphone si ce n'est pas déjà fait.", "ثبّت تيليغرام (مجاني) على هاتفك إن لم يكن مثبتًا.")}</p>
    <h3>{L("Paiement", "الدفع")}</h3>
    <p>{L("Après l'essai (ou tout de suite si vous avez choisi de payer directement), payez par D17, IZI ou Wafacash, avec pour motif le nom de votre entreprise :", "بعد التجربة (أو فورًا إن اخترت الدفع مباشرة)، ادفع عبر ⁨D17⁩ أو ⁨IZI⁩ أو ⁨Wafacash⁩ مع ذكر اسم مؤسستك كسبب للدفع:")}</p>
    {liste_paiements()}
    {lien_preuve("abo-preuve-apres")}
    <p class="petit">{L(f"Une facture vous est adressée. Pas de renouvellement automatique : nous vous prévenons {rj} jours avant la fin.", f"تُرسل إليك فاتورة. لا تجديد آلي: نعلمك قبل النهاية بـ{ISO(rj)} أيام.")}</p>
  </div>
</section>
<p class="avert">{L("La consultation du site reste <b>gratuite, sans inscription</b> : toutes les annonces restent visibles par métier et par gouvernorat. L'abonnement ajoute seulement l'alerte personnalisée sur Telegram.",
                    "تصفح الموقع يبقى <b>مجانيًا ودون تسجيل</b>: كل الإعلانات تبقى ظاهرة حسب الاختصاص والولاية. الاشتراك يضيف فقط التنبيه الشخصي على تيليغرام.")}</p>"""
    titre = f"Alertes Pro : appels d'offres de votre métier sur Telegram — {essai} jours gratuits | Alertes appels d'offres"
    desc = (f"Recevez chaque matin sur Telegram les nouveaux appels d'offres tunisiens de vos métiers et de vos gouvernorats. "
            f"{pm} DT / mois ou {pa} DT / an, {essai} jours d'essai gratuit, sans renouvellement automatique. "
            "تنبيهات طلبات العروض على تيليغرام.")
    res = [("abonnement/", page("abonnement/", "../", titre, desc, hero, contenu, v, etat, scripts=("abonnement.js",)))]

    # ---- conditions de l'abonnement (sobre)
    hero = f"""    <p class="fil"><a href="../../">{L("Accueil", "الرئيسية")}</a> › <a href="../">{L("Alertes Pro", "تنبيهات Pro")}</a> › {L("Conditions", "الشروط")}</p>
    <h1>{L("Conditions de l'abonnement", "شروط الاشتراك")}</h1>
    <p class="intro">{L("Alertes Pro : prix, essai gratuit, paiement, données personnelles, arrêt.", "تنبيهات Pro: السعر، التجربة المجانية، الدفع، المعطيات الشخصية، الإيقاف.")}</p>"""
    num = ABO["numero"]
    sections = [
        ("1. Le service", "1. الخدمة",
         "Alertes Pro envoie chaque matin sur Telegram les nouveaux appels d'offres publics correspondant aux métiers et aux gouvernorats choisis par l'abonné (ainsi que ceux « national » ou « plusieurs gouvernorats » de ses métiers). La consultation du site reste gratuite et sans inscription.",
         "ترسل تنبيهات Pro كل صباح على تيليغرام طلبات العروض العمومية الجديدة المطابقة للاختصاصات والولايات التي اختارها المشترك (وكذلك «الوطنية» أو «لعدة ولايات» في اختصاصاته). تصفح الموقع يبقى مجانيًا ودون تسجيل."),
        ("2. Prix", "2. السعر",
         f"{pm} DT par mois ou {pa} DT par an, en dinars tunisiens. Le prix affiché au moment de l'inscription s'applique à toute la période payée.",
         f"{ISO(pm)} دينار في الشهر أو {ISO(pa)} دينار في السنة. السعر المعروض عند التسجيل يُطبَّق على كامل المدة المدفوعة."),
        ("3. Essai gratuit", "3. التجربة المجانية",
         f"Les {essai} premiers jours sont gratuits, sans paiement et sans engagement. Sans paiement à la fin de l'essai, l'alerte s'arrête simplement.",
         f"الأيام الـ{ISO(essai)} الأولى مجانية، دون دفع ودون التزام. إذا لم يتم الدفع في نهاية التجربة، يتوقف التنبيه ببساطة."),
        ("4. Paiement et facture", "4. الدفع والفاتورة",
         f"Paiement par D17, IZI ou Wafacash au {num}, avec pour motif le nom de l'entreprise, puis preuve envoyée par WhatsApp au même numéro. La période payée commence après l'essai gratuit ou après la période déjà payée. Une facture est adressée à l'abonné.",
         f"الدفع عبر ⁨D17⁩ أو ⁨IZI⁩ أو ⁨Wafacash⁩ على الرقم {ISO(num)} مع ذكر اسم المؤسسة، ثم إرسال الإثبات عبر واتساب على نفس الرقم. تبدأ المدة المدفوعة بعد التجربة المجانية أو بعد المدة المدفوعة سابقًا. تُرسل فاتورة إلى المشترك."),
        ("5. Pas de renouvellement automatique", "5. لا تجديد آلي",
         f"Sans engagement au-delà d'un an. Il n'y a aucun renouvellement automatique : un rappel est envoyé {rj} jours avant la fin ; sans nouveau paiement, l'alerte s'arrête simplement à la date de fin.",
         f"دون التزام بعد السنة. لا يوجد أي تجديد آلي: يُرسل تذكير قبل النهاية بـ{ISO(rj)} أيام، ودون دفع جديد يتوقف التنبيه ببساطة في تاريخ النهاية."),
        ("6. Arrêt (résiliation)", "6. الإيقاف (الفسخ)",
         "L'abonné peut arrêter les alertes à tout moment, en envoyant /stop au robot Telegram ou en nous écrivant sur WhatsApp. Pendant l'essai gratuit, rien n'est dû. Une période déjà payée n'est pas renouvelée.",
         "يمكن للمشترك إيقاف التنبيهات في أي وقت بإرسال ⁨/stop⁩ إلى برنامج تيليغرام أو بمراسلتنا عبر واتساب. خلال التجربة المجانية لا يُستحق أي مبلغ. المدة المدفوعة لا تُجدَّد."),
        ("7. Limites", "7. الحدود",
         "Les annonces viennent du portail officiel de la HAICOP. Le classement par métier et par gouvernorat est automatique et peut se tromper ; une annonce peut manquer si la source est en panne. Seule la fiche officielle fait foi : vérifiez-la toujours avant de répondre.",
         "الإعلانات مصدرها البوابة الرسمية للهيئة العليا للطلب العمومي. الترتيب حسب الاختصاص والولاية آلي وقد يخطئ، وقد يغيب إعلان إذا تعطل المصدر. البطاقة الرسمية هي المرجع الوحيد: تثبّت منها دائمًا قبل المشاركة."),
        ("8. Données personnelles", "8. المعطيات الشخصية",
         "Nous gardons seulement : nom, entreprise, téléphone, e-mail, métiers et gouvernorats choisis, dates de l'abonnement et identifiant Telegram. Elles servent uniquement à envoyer les alertes et la facture, sont conservées dans un espace privé, ne sont jamais publiées ni vendues, et sont supprimées sur simple demande (WhatsApp). Le formulaire passe par le service Formspree et les alertes par Telegram.",
         "نحتفظ فقط بـ: الاسم، المؤسسة، الهاتف، البريد الإلكتروني، الاختصاصات والولايات المختارة، تواريخ الاشتراك ومعرّف تيليغرام. تُستعمل فقط لإرسال التنبيهات والفاتورة، وتُحفظ في فضاء خاص، ولا تُنشر ولا تُباع أبدًا، وتُحذف بمجرد الطلب (واتساب). تمر الاستمارة عبر خدمة ⁨Formspree⁩ والتنبيهات عبر تيليغرام."),
        ("9. Contact", "9. الاتصال",
         f"WhatsApp : {num}.",
         f"واتساب: {ISO(num)}."),
    ]
    corps = "\n".join(f"  <h2>{L(t_fr, t_ar)}</h2>\n  <p>{L(p_fr, p_ar)}</p>" for t_fr, t_ar, p_fr, p_ar in sections)
    contenu = f"""<section class="carte conditions">
{corps}
  <p class="avert">{L("Ce site n'est pas officiel et n'est pas lié à la HAICOP ni à TUNEPS.", "هذا الموقع ليس رسميًا ولا علاقة له بالهيئة العليا للطلب العمومي ولا بمنظومة " + ISO("TUNEPS") + ".")}</p>
  <p><a class="btn-pro" href="../#inscription">{L("Retour à l'inscription", "العودة إلى التسجيل")}</a></p>
</section>"""
    titre = "Conditions de l'abonnement Alertes Pro (appels d'offres sur Telegram) | Alertes appels d'offres"
    desc = (f"Conditions d'Alertes Pro : {pm} DT / mois ou {pa} DT / an, {essai} jours d'essai gratuit, "
            "pas de renouvellement automatique, paiement D17, IZI ou Wafacash, données personnelles et arrêt.")
    res.append(("abonnement/conditions/", page("abonnement/conditions/", "../../", titre, desc, hero, contenu, v, etat)))
    return res


# ------------------------------------------------------------ construction
def version_assets(sortie):
    h = hashlib.sha1()
    for f in ("style.css", "page.js", "app.js", "avis.js", "abonnement.js"):
        p = os.path.join(sortie, "assets", f)
        if os.path.exists(p):
            with open(p, "rb") as fh:
                # fins de ligne normalisées : même version sous Windows et sur GitHub (Linux)
                h.update(fh.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:8]


def ecrire(sortie, chemin, contenu):
    p = os.path.join(sortie, chemin)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(contenu)
    os.replace(tmp, p)


def construire(donnees, sortie, jour):
    sauvegarde = donnees.replace(".json", ".sauvegarde.json")
    brut, aos = charger(donnees)
    brut_s, aos_s = charger(sauvegarde)
    panne, raison = False, ""
    repli = False   # True si on a dû reprendre la sauvegarde (données illisibles ou suspectes)
    if not aos:
        if aos_s:
            print(f"  ! échec : {os.path.basename(donnees)} illisible ou vide -> dernière sauvegarde utilisée")
            brut, aos, panne, raison, repli = brut_s, aos_s, True, "données illisibles", True
        elif os.path.exists(os.path.join(sortie, "index.html")):
            print("  ! échec : données illisibles et aucune sauvegarde -> le site existant est gardé tel quel")
            return 1
        else:
            print("  ! échec : aucune donnée -> site construit vide, avec avertissement")
            brut, panne, raison, repli = {}, True, "aucune donnée", True
    elif aos_s and len(aos) < SEUIL_CHUTE * len(aos_s):
        print(f"  ! échec : seulement {len(aos)} fiches contre {len(aos_s)} avant -> données suspectes, sauvegarde utilisée")
        brut, aos, panne, raison, repli = brut_s, aos_s, True, "données suspectes", True
    else:
        tmp = sauvegarde + ".tmp"
        shutil.copyfile(donnees, tmp)
        os.replace(tmp, sauvegarde)

    statut = (brut or {}).get("statut_source") or {}
    passage = (brut or {}).get("dernier_passage") or {}
    source_en_panne = statut.get("etat") == "panne" or passage.get("reussi") is False
    if source_en_panne:
        print(f"  ! échec : source HAICOP en panne depuis {statut.get('depuis') or passage.get('date')} "
              f"({statut.get('raison') or 'lecture ratée'}) — anciennes données gardées")
    maj = str((brut or {}).get("derniere_lecture_reussie") or (brut or {}).get("mis_a_jour") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}", maj):
        maj = ""
    age = (dt.date.fromisoformat(jour) - dt.date.fromisoformat(maj[:10])).days if maj else None
    # Bandeau : données vieilles de 2 jours ou plus (même règle que le JavaScript du visiteur), ou aucune donnée
    panne = panne or age is None or age >= AGE_AVERTISSEMENT
    if panne and not raison:
        raison = "lecture ancienne"
    maj_texte = (dfr(maj[:10]) + (" " + maj[11:16] if len(maj) >= 16 else "")) if maj else ""
    message = (f"⚠️ La source officielle n'a pas pu être lue depuis le {dfr(maj[:10])} : la liste peut être incomplète. "
               "Vérifiez toujours sur le portail de la HAICOP." if maj else
               "⚠️ Données indisponibles : consultez le portail de la HAICOP.") if panne else ""
    ecrire(sortie, "donnees/etat-source.json", json.dumps({
        "source_en_panne": bool(source_en_panne or repli),
        "depuis": statut.get("depuis") or passage.get("date") or "",
        "raison": statut.get("raison") or raison or "",
        "derniere_lecture_reussie": maj, "jours_sans_lecture": age,
        "bandeau_visible": panne, "construit_le": jour}, ensure_ascii=False, indent=1) + "\n")
    etat = {"maj": maj, "maj_texte": maj_texte, "panne": panne, "message": message}

    vis = ouvertes(aos, jour)
    v = version_assets(sortie)
    adr = adresses()
    dossier_donnees = os.path.dirname(os.path.abspath(donnees))
    prives = charger_prives(os.path.join(dossier_donnees, "prives.json"), jour)
    encheres, etat_encheres = charger_encheres(os.path.join(dossier_donnees, "encheres.json"), jour)
    cm, cg = {}, {}
    for a in vis:
        cm[M_PAR_NOM[a["metier"]][1]] = cm.get(M_PAR_NOM[a["metier"]][1], 0) + 1
        cg[G_PAR_NOM[a["gouvernorat"]][1]] = cg.get(G_PAR_NOM[a["gouvernorat"]][1], 0) + 1
    items_m = [(m[1], m[2], m[3]) for m in METIERS]
    items_g = [(g[1], g[0], g[2]) for g in GOUVERNORATS]
    pages = []

    # ---- accueil
    pubs = sorted({a["date_publication"] for a in vis if a["date_publication"]})
    dernier = pubs[-1] if pubs else ""
    n_auj = sum(1 for a in vis if a["date_publication"] == jour)
    n_nouv = n_auj or sum(1 for a in vis if a["date_publication"] == dernier)
    lib_nouv = "nouveaux aujourd'hui" if n_auj else (f"nouveaux le {dfr(dernier)[:5]}" if dernier else "nouveaux")
    n_urg = sum(1 for a in vis if a["date_limite"] and
                0 <= (dt.date.fromisoformat(a["date_limite"]) - dt.date.fromisoformat(jour)).days < 7)
    hero = f"""{credit_photos(PHOTOS)}
    <h1>{L("Appels d'offres publics en Tunisie", "طلبات العروض العمومية في تونس")}</h1>
    <p class="intro">{L("Chaque jour, les nouveaux appels d'offres de l'État, des communes et des entreprises publiques, triés par métier et par gouvernorat. Résumé court, lien vers la fiche officielle. Gratuit, sans inscription.",
                        "كل يوم، طلبات العروض الجديدة للدولة والبلديات والمنشآت العمومية، مرتبة حسب الاختصاص والولاية، مع ملخص قصير ورابط البطاقة الرسمية. مجاني، دون تسجيل.")}</p>
{bouton_pro_accueil()}"""
    faq = [
        ("Où trouver les appels d'offres publics en Tunisie ?",
         "Ils sont publiés sur le portail officiel de la HAICOP (marchespublics.gov.tn) et sur TUNEPS. Ce site reprend chaque jour les nouvelles annonces de la HAICOP, triées par métier et par gouvernorat, avec le lien vers chaque fiche officielle."),
        ("Ce service est-il gratuit ?", "Oui : la consultation des appels d'offres est gratuite et sans inscription. "
         f"Seules les alertes personnalisées sur Telegram (Alertes Pro) sont payantes : {ABO['prix_mois']} DT par mois ou "
         f"{ABO['prix_an']} DT par an, avec {ABO['essai_jours']} jours d'essai gratuit."),
        ("Où retirer le cahier des charges ?",
         "Le cahier des charges se retire sur TUNEPS (www.tuneps.tn), selon les indications de la fiche officielle. Seule la fiche officielle fait foi."),
    ]
    jsonld = ('<script type="application/ld+json">\n' + json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in faq]},
        ensure_ascii=False) + "\n</script>\n")
    contenu = f"""<section class="carte resume" aria-label="Résumé">
  <div class="r-nouveaux" id="r-nouveaux"><b>{n_nouv}</b><span>{lib_nouv}</span></div>
  <div class="r-ouverts" id="r-ouverts"><b>{len(vis)}</b><span>{L("appels d'offres ouverts", "طلبات عروض مفتوحة")}</span></div>
  <div class="r-urgent" id="r-urgent"><b>{n_urg}</b><span>{L("clôturent sous 7 jours", "تنتهي خلال 7 أيام")}</span></div>
</section>
<section class="carte bientot" id="bientot" hidden aria-labelledby="bientot-titre">
  <h2 id="bientot-titre">{L("⏰ Clôturent bientôt", "⏰ تنتهي قريبًا")}</h2>
  <ol class="bientot-liste" id="bientot-liste"></ol>
</section>
{bouton_alertes(adr)}
{filtres(vis)}
{liste_html(vis, "", jour, "Aucun appel d'offres ouvert pour ce choix. Essayez un autre métier ou toute la Tunisie.", "لا يوجد طلب عروض مفتوح لهذا الاختيار. جرّب اختصاصًا آخر أو كل الولايات.")}
{section_prives(prives, "")}
<h2 class="titre-section" id="metiers">{L("Par métier", "حسب الاختصاص")}</h2>
{grille(items_m, None, "", "metier", cm, "grille-metiers", True)}
<h2 class="titre-section" id="gouvernorats">{L("Par gouvernorat", "حسب الولاية")}</h2>
<section class="carte bloc-carte">
  <figure>{carte_tunisie(cg, "")}
  <figcaption>{L("Appels d'offres ouverts par gouvernorat. Touchez une bulle pour voir la liste.", "طلبات العروض المفتوحة حسب الولاية. المس دائرة لعرض القائمة.")}</figcaption></figure>
  {grille(items_g, None, "", "gouvernorat", cg, "grille-gouv")}
</section>
<section class="carte" style="margin-top:18px">
  <h2>{L("Comment ça marche ?", "كيف يعمل الموقع؟")}</h2>
  <ol class="etapes" data-l="fr">
    <li>Chaque jour, un robot lit <b>lentement</b> les nouvelles annonces sur le portail officiel de la <b>HAICOP</b>.</li>
    <li>Chaque appel d'offres est rangé par <b>métier</b> et par <b>gouvernorat</b>.</li>
    <li>Vous ouvrez la <b>fiche officielle</b> pour les détails ; le cahier des charges se retire sur <b>TUNEPS</b>.</li>
  </ol>
  <ol class="etapes" data-l="ar">
    <li>كل يوم، يقرأ برنامج آلي <b>ببطء</b> الإعلانات الجديدة في البوابة الرسمية <b>للهيئة العليا للطلب العمومي</b>.</li>
    <li>يُرتَّب كل طلب عروض حسب <b>الاختصاص</b> و<b>الولاية</b>.</li>
    <li>تفتح <b>البطاقة الرسمية</b> للتفاصيل، ويُسحب كراس الشروط من منظومة <b>{ISO("TUNEPS")}</b>.</li>
  </ol>
  <p class="avert">{L("Ce site n'est pas officiel. Vérifiez toujours la fiche officielle avant de répondre : seule elle fait foi.", "هذا الموقع ليس رسميًا. تثبّت دائمًا من البطاقة الرسمية قبل المشاركة: هي وحدها المرجع.")} <a href="a-propos/">{L("Méthode et sources", "المنهجية والمصادر")}</a></p>
</section>"""
    contenu += "\n" + AVIS
    titre = f"Appels d'offres Tunisie aujourd'hui — {len(vis)} ouverts, consultation gratuite | Alertes appels d'offres"
    desc = ("Les nouveaux appels d'offres publics tunisiens chaque jour (source officielle HAICOP), triés par métier et par gouvernorat, "
            "avec date limite et caution. Gratuit, sans inscription. طلبات العروض العمومية في تونس.")
    pages.append(("", page("", "", titre, desc, hero, contenu, v, etat, jsonld, " hero-photo")))

    # ---- une page par métier
    for nom, slug, fr, ar in METIERS:
        sel = [a for a in vis if a["metier"] == nom]
        hero = f"""{fil("../../", "Métiers", "الاختصاصات")}
    {icone(slug, "hero-ic")}
    <h1>{L(f"Appels d'offres {E(fr)}", f"طلبات العروض: {ar}")}</h1>
    <p class="intro">{L(f"{len(sel)} appel{'s' if len(sel) > 1 else ''} d'offres ouvert{'s' if len(sel) > 1 else ''} en Tunisie, triés par date limite. Source officielle : HAICOP.",
                        f"{ISO(len(sel))} طلب عروض مفتوح في تونس، مرتبة حسب آخر أجل. المصدر الرسمي: الهيئة العليا للطلب العمومي.")}</p>"""
        contenu = f"""{filtres(sel, avec_metier=False)}
{liste_html(sel, "../../", jour, f"Aucun appel d'offres « {E(fr)} » ouvert en ce moment. Revenez demain : la liste est mise à jour chaque jour.", f"لا يوجد حاليًا طلب عروض مفتوح في «{ar}». عُد غدًا: القائمة تُحيَّن يوميًا.")}
<h2 class="titre-section">{L("Autres métiers", "اختصاصات أخرى")}</h2>
{grille(items_m, slug, "../../", "metier", cm, "grille-metiers", True)}"""
        titre = f"Appels d'offres {fr} Tunisie — {len(sel)} ouverts, consultation gratuite | Alertes appels d'offres"
        desc = (f"Appels d'offres publics « {fr} » en Tunisie, encore ouverts, triés par date limite, avec caution et lien vers la fiche officielle HAICOP. Gratuit, sans inscription. "
                f"طلبات العروض: {ar}.")
        pages.append((f"metier/{slug}/", page(f"metier/{slug}/", "../../", titre, desc, hero, contenu, v, etat)))

    # ---- une page par gouvernorat
    for nom, slug, ar in GOUVERNORATS:
        sel = [a for a in vis if a["gouvernorat"] == nom]
        special = slug in ("plusieurs", "national")
        h_fr = f"Appels d'offres : {nom.lower()}" if special else f"Appels d'offres à {nom}"
        h_ar = f"طلبات العروض: {ar}" if special else f"طلبات العروض في ولاية {ar}"
        hero = f"""{fil("../../", "Gouvernorats", "الولايات")}
    <h1>{L(E(h_fr), h_ar)}</h1>
    <p class="intro">{L(f"{len(sel)} appel{'s' if len(sel) > 1 else ''} d'offres ouvert{'s' if len(sel) > 1 else ''}, triés par date limite. Source officielle : HAICOP.",
                        f"{ISO(len(sel))} طلب عروض مفتوح، مرتبة حسب آخر أجل. المصدر الرسمي: الهيئة العليا للطلب العمومي.")}</p>"""
        contenu = f"""{filtres(sel, avec_gouv=False)}
{liste_html(sel, "../../", jour, "Aucun appel d'offres ouvert en ce moment pour ce gouvernorat. Revenez demain : la liste est mise à jour chaque jour.", "لا يوجد حاليًا طلب عروض مفتوح في هذه الولاية. عُد غدًا: القائمة تُحيَّن يوميًا.")}
<h2 class="titre-section">{L("Autres gouvernorats", "ولايات أخرى")}</h2>
{grille(items_g, slug, "../../", "gouvernorat", cg, "grille-gouv")}"""
        titre = f"{h_fr} (Tunisie) — {len(sel)} ouverts, consultation gratuite | Alertes appels d'offres"
        desc = (f"Appels d'offres publics {'— ' + nom.lower() if special else 'dans le gouvernorat de ' + nom}, encore ouverts, triés par date limite, "
                f"avec caution et lien vers la fiche officielle HAICOP. Gratuit, sans inscription. {h_ar}.")
        pages.append((f"gouvernorat/{slug}/", page(f"gouvernorat/{slug}/", "../../", titre, desc, hero, contenu, v, etat)))

    # ---- à propos et sources
    hero = f"""{fil("../", "À propos", "من نحن")}
    <h1>{L("À propos et sources", "من نحن والمصادر")}</h1>
    <p class="intro">{L("D'où viennent les annonces, comment elles sont classées, et leurs limites.", "من أين تأتي الإعلانات، كيف تُرتَّب، وحدودها.")}</p>"""
    contenu = f"""<section class="carte">
  <h2>{L("Ce que fait ce site", "ماذا يقدّم هذا الموقع")}</h2>
  <p data-l="fr">Un service <b>gratuit, sans inscription</b>, qui rassemble chaque jour les nouveaux appels d'offres publics tunisiens, les range par <b>métier</b> et par <b>gouvernorat</b>, et met en avant la <b>date limite</b> et la <b>caution provisoire</b>. Aussi : recherche par mots-clés (français et arabe), résumé traduit des objets, rappels avant la date limite, ventes aux enchères de la Douane, publication gratuite pour les entreprises privées, alertes Telegram (puis WhatsApp). Seules les alertes personnalisées par métier et gouvernorat (<a href="../abonnement/">Alertes Pro</a>) sont payantes.</p>
  <p data-l="ar">خدمة <b>مجانية ودون تسجيل</b> تجمع كل يوم طلبات العروض العمومية الجديدة في تونس، وترتّبها حسب <b>الاختصاص</b> و<b>الولاية</b>، وتُبرز <b>آخر أجل</b> و<b>الضمان الوقتي</b>. وأيضًا: بحث بالكلمات (بالعربية والفرنسية)، ملخص مترجم للمواضيع، تذكير قبل آخر أجل، بيوعات الديوانة بالمزاد، نشر مجاني للمؤسسات الخاصة، وتنبيهات تيليغرام (ثم واتساب). التنبيهات الشخصية حسب الاختصاص والولاية (<a href="../abonnement/">تنبيهات Pro</a>) وحدها بمقابل.</p>
</section>
<section class="carte">
  <h2>{L("Source officielle", "المصدر الرسمي")}</h2>
  <ul class="sources" data-l="fr">
    <li><b>HAICOP — Haute Instance de la Commande Publique</b> : portail <a href="{URL_HAICOP}" rel="noopener">marchespublics.gov.tn</a>. Chaque annonce du site renvoie à sa fiche officielle (« Voir la fiche officielle »).</li>
    <li>Le fichier robots.txt du portail autorise la lecture par les robots. Notre robot lit <b>lentement</b> (une page toutes les 2,5 secondes), une ou deux fois par jour, en se présentant honnêtement.</li>
    <li>Le <b>cahier des charges</b> n'est pas recopié : il se retire sur <a href="https://www.tuneps.tn" rel="noopener">TUNEPS</a>, selon la fiche officielle.</li>
    <li><b>Ventes aux enchères</b> : page officielle de la <b>Douane tunisienne</b> (<a href="{URL_DOUANE}" rel="noopener">douane.gov.tn</a>), robots autorisés, lue une fois par jour ; lien vers chaque avis officiel.</li>
    <li><b>Appels d'offres d'entreprises privées</b> : envoyés par les entreprises elles-mêmes, contrôlés automatiquement, <b>non vérifiés par HAICOP</b>.</li>
  </ul>
  <ul class="sources" data-l="ar">
    <li><b>الهيئة العليا للطلب العمومي</b>: البوابة <a href="https://www.marchespublics.gov.tn/ar/appels-doffres" rel="noopener">{ISO("marchespublics.gov.tn")}</a>. كل إعلان في الموقع مرفق برابط بطاقته الرسمية.</li>
    <li>ملف {ISO("robots.txt")} للبوابة يسمح بالقراءة الآلية. برنامجنا يقرأ <b>ببطء</b> (صفحة كل {ISO("2,5")} ثانية)، مرة أو مرتين في اليوم.</li>
    <li>لا يُنسخ <b>كراس الشروط</b>: يُسحب من منظومة <a href="https://www.tuneps.tn" rel="noopener">{ISO("TUNEPS")}</a> حسب البطاقة الرسمية.</li>
    <li><b>البيوعات بالمزاد</b>: الصفحة الرسمية <b>للديوانة التونسية</b>، تُقرأ مرة في اليوم، مع رابط كل إعلان رسمي.</li>
    <li><b>طلبات عروض المؤسسات الخاصة</b>: ترسلها المؤسسات نفسها، مع مراقبة آلية، <b>دون تحقق من الهيئة العليا للطلب العمومي</b>.</li>
  </ul>
</section>
<section class="carte">
  <h2>{L("Méthode", "المنهجية")}</h2>
  <ol class="etapes" data-l="fr">
    <li>Lecture des nouvelles fiches publiées sur le portail de la HAICOP (objet, acheteur, région, date limite, caution, procédure).</li>
    <li>Classement par <b>métier</b> à partir du type de commande officiel et de mots-clés (français et arabe) : quelques erreurs sont possibles.</li>
    <li>Classement par <b>gouvernorat</b> d'après la région d'exécution, sinon le nom de l'acheteur.</li>
    <li>Les objets sont recopiés <b>dans leur langue d'origine</b> (souvent en arabe), avec un <b>résumé court dans l'autre langue</b> fait par un glossaire maison (traduction automatique approximative, affichée seulement si la plupart des mots sont reconnus).</li>
    <li>Les appels d'offres dont la date limite est passée sont <b>retirés automatiquement</b>.</li>
    <li>Si la source ne répond pas, les annonces déjà connues restent affichées avec un <b>avertissement daté</b>.</li>
  </ol>
  <ol class="etapes" data-l="ar">
    <li>قراءة البطاقات الجديدة المنشورة في بوابة الهيئة العليا للطلب العمومي (الموضوع، المشتري العمومي، الجهة، آخر أجل، الضمان، الإجراء).</li>
    <li>ترتيب حسب <b>الاختصاص</b> انطلاقًا من نوع الطلب الرسمي وكلمات مفتاحية (بالعربية والفرنسية): أخطاء قليلة ممكنة.</li>
    <li>ترتيب حسب <b>الولاية</b> وفق جهة التنفيذ، وإلا فحسب اسم المشتري.</li>
    <li>تُنقل المواضيع <b>بلغتها الأصلية</b>، مع <b>ملخص قصير باللغة الأخرى</b> عبر معجم خاص (ترجمة آلية تقريبية، لا تظهر إلا إذا عُرفت أغلب الكلمات).</li>
    <li>طلبات العروض التي انتهى أجلها <b>تُحذف آليًا</b>.</li>
    <li>إذا لم يستجب المصدر، تبقى الإعلانات المعروفة ظاهرة مع <b>تنبيه مؤرَّخ</b>.</li>
  </ol>
  <p class="avert">{L("<b>Avertissement :</b> ce site n'est pas officiel et n'est pas lié à la HAICOP ni à TUNEPS. Les résumés sont indicatifs : <b>vérifiez toujours la fiche officielle</b> (dates, montants, conditions) avant de répondre à un appel d'offres. Seule la fiche officielle fait foi.",
                        "<b>تنبيه:</b> هذا الموقع ليس رسميًا ولا علاقة له بالهيئة العليا للطلب العمومي ولا بمنظومة " + ISO("TUNEPS") + ". الملخصات للإرشاد فقط: <b>تثبّت دائمًا من البطاقة الرسمية</b> (الآجال، المبالغ، الشروط) قبل المشاركة. البطاقة الرسمية هي المرجع الوحيد.")}</p>
</section>
<section class="carte" id="credits-photos">
  <h2>{L("Crédits des photos", "حقوق الصور")}</h2>
  <ul class="sources">{"".join(f'<li data-photo="{E(MOSAIQUE)} {E(MOSAIQUE_MOBILE)}">{L(E(ph["sujet_fr"]) + " (mosaïque, " + ph["tuile"] + ", recadrée)", ph["sujet_ar"])} — {L("photo", "صورة")} : <b>{E(ph["auteur"])}</b>, {L("licence", "رخصة")} <a href="{E(ph["licence_url"])}" rel="noopener license">{E(ph["licence"])}</a>, <a href="{E(ph["source_url"])}" rel="noopener">Wikimedia Commons</a>.</li>' for ph in PHOTOS)}</ul>
</section>"""
    titre = "À propos et sources — appels d'offres HAICOP | Alertes appels d'offres Tunisie"
    desc = "Service gratuit. D'où viennent les appels d'offres affichés (portail officiel de la HAICOP), comment ils sont classés, et pourquoi vérifier toujours la fiche officielle."
    pages.append(("a-propos/", page("a-propos/", "../", titre, desc, hero, contenu, v, etat)))

    # ---- publier un appel d'offres (entreprises privées, gratuit)
    hero = f"""{fil("../", "Publier un appel d'offres", "نشر طلب عروض")}
    <h1>{L("Publier un appel d'offres", "نشر طلب عروض")}</h1>
    <p class="intro">{L("Entreprise privée ? Publiez gratuitement votre appel d'offres : il apparaît sur le site après un contrôle automatique.", "مؤسسة خاصة؟ انشر طلب العروض مجانًا: يظهر في الموقع بعد مراقبة آلية.")}</p>"""
    if adr["formulaire"]:
        action = (f'<a class="btn-publier" id="btn-publier" href="{E(adr["formulaire"])}" target="_blank" rel="noopener">'
                  f'{L("Remplir le formulaire de publication", "املأ استمارة النشر")}</a>')
    else:
        action = (f'<p class="bientot-pub" id="btn-publier">{L("Bientôt : le formulaire de publication sera ouvert ici.", "قريبًا: ستُفتح استمارة النشر هنا.")}</p>')
    contenu = f"""<section class="carte">
  <h2>{L("Comment ça marche ?", "كيف يعمل؟")}</h2>
  <ol class="etapes" data-l="fr">
    <li>Vous remplissez le formulaire : entreprise, objet, métier, gouvernorat, <b>date limite</b>, contact.</li>
    <li>Un robot contrôle la demande (champs obligatoires, date limite à venir, pas de lien ni de publicité, pas de doublon).</li>
    <li>L'appel d'offres apparaît sur le site (accueil) dans les heures qui suivent, avec la mention <b>« Publié par l'entreprise — non vérifié par HAICOP »</b>, et disparaît après la date limite.</li>
  </ol>
  <ol class="etapes" data-l="ar">
    <li>تملأ الاستمارة: المؤسسة، الموضوع، الاختصاص، الولاية، <b>آخر أجل</b>، وسيلة الاتصال.</li>
    <li>يراقب برنامج آلي الطلب (الخانات الإجبارية، أجل لم يحن بعد، دون روابط أو إشهار، دون تكرار).</li>
    <li>يظهر طلب العروض في الموقع خلال ساعات مع عبارة <b>«نشرته المؤسسة — لم تتحقق منه الهيئة العليا للطلب العمومي»</b>، ويُحذف بعد آخر أجل.</li>
  </ol>
  {action}
  <p class="avert">{L("C'est gratuit. Les informations envoyées (dont le contact de l'entreprise) sont <b>publiées telles quelles</b> : n'indiquez que des coordonnées professionnelles. Les liens Internet ne sont pas acceptés.", "النشر مجاني. المعلومات المرسلة (ومنها وسيلة اتصال المؤسسة) <b>تُنشر كما هي</b>: لا تذكر إلا معطيات مهنية. الروابط غير مقبولة.")}</p>
</section>
{section_prives(prives, "../")}"""
    titre = "Publier gratuitement un appel d'offres privé en Tunisie | Alertes appels d'offres"
    desc = ("Entreprises privées : publiez gratuitement votre appel d'offres en Tunisie. Contrôle automatique, publication rapide, "
            "mention « non vérifié par HAICOP ». نشر طلب عروض مجانًا.")
    pages.append(("publier/", page("publier/", "../", titre, desc, hero, contenu, v, etat)))

    # ---- ventes aux enchères publiques (Douane tunisienne)
    hero = f"""{fil("../", "Ventes aux enchères", "البيوعات بالمزاد")}
    <h1>{L("Ventes aux enchères publiques", "البيوعات بالمزاد العلني")}</h1>
    <p class="intro">{L(f"{len(encheres)} vente{'s' if len(encheres) > 1 else ''} aux enchères de la Douane tunisienne encore ouverte{'s' if len(encheres) > 1 else ''} (marchandises, véhicules, bétail…), triées par échéance. Source officielle : Douane tunisienne.",
                        f"{ISO(len(encheres))} بيع بالمزاد العلني للديوانة التونسية مفتوح (بضائع، عربات، مواشٍ…)، مرتبة حسب آخر أجل. المصدر الرسمي: الديوانة التونسية.")}</p>"""
    cartes_e = "\n".join(carte_enchere(x, "../") for x in encheres)
    contenu = f"""{recherche_seule()}
{liste_html(encheres, "../", jour, "Aucune vente aux enchères ouverte en ce moment. Revenez demain : la liste est mise à jour chaque jour.", "لا يوجد حاليًا بيع بالمزاد مفتوح. عُد غدًا: القائمة تُحيَّن يوميًا.",
            unite=("vente aux enchères ouverte", "ventes aux enchères ouvertes", "بيع بالمزاد مفتوح"), cartes_html=cartes_e)}
<section class="carte" style="margin-top:18px">
  <h2>{L("Source", "المصدر")}</h2>
  <p data-l="fr">Avis publiés par la <b>Douane tunisienne</b> sur sa page officielle <a href="{URL_DOUANE}" rel="noopener">« Ventes aux enchères publiques »</a>, lue une fois par jour. Chaque carte renvoie à l'avis officiel (PDF), seul à faire foi : conditions, lieu, caution et visite des lots y sont indiqués.</p>
  <p data-l="ar">إعلانات نشرتها <b>الديوانة التونسية</b> في صفحتها الرسمية <a href="https://www.douane.gov.tn/ar/ventes-aux-encheres-publiques_ar/" rel="noopener">«البيع بالمزاد العلني»</a>، تُقرأ مرة في اليوم. كل بطاقة مرفقة برابط الإعلان الرسمي، وهو المرجع الوحيد.</p>
  <p class="avert">{L("Ce site n'est pas officiel et n'est pas lié à la Douane. Vérifiez toujours l'avis officiel avant de participer.", "هذا الموقع ليس رسميًا ولا علاقة له بالديوانة. تثبّت دائمًا من الإعلان الرسمي قبل المشاركة.")}</p>
</section>"""
    titre = f"Ventes aux enchères publiques Tunisie (Douane) — {len(encheres)} ouvertes, consultation gratuite | Alertes appels d'offres"
    desc = ("Ventes aux enchères publiques de la Douane tunisienne encore ouvertes : marchandises, véhicules, bétail, avec échéance et lien "
            "vers l'avis officiel. Gratuit, sans inscription. البيوعات بالمزاد العلني للديوانة التونسية.")
    pages.append(("encheres/", page("encheres/", "../", titre, desc, hero, contenu, v, etat_encheres)))

    # ---- Alertes Pro (abonnement payant) et ses conditions
    pages += pages_abonnement(adr, v, etat)

    # ---- écriture
    for chemin, contenu in pages:
        ecrire(sortie, chemin + "index.html", contenu)
    lastmod = jour
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for chemin, _ in pages:
        sitemap.append(f"  <url><loc>{URL_SITE}{chemin}</loc><lastmod>{lastmod}</lastmod></url>")
    sitemap.append("</urlset>")
    ecrire(sortie, "sitemap.xml", "\n".join(sitemap) + "\n")
    print(f"  {len(pages)} pages, {len(vis)} appels d'offres ouverts (sur {len(aos)} en mémoire), "
          f"version {v}{', AVERTISSEMENT : ' + raison if panne else ''}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Construit le site statique des appels d'offres.")
    p.add_argument("--donnees", default=os.path.join(RACINE_SITE, "donnees", "appels-offres.json"))
    p.add_argument("--sortie", default=RACINE_SITE)
    p.add_argument("--aujourdhui", default=dt.date.today().isoformat(), help="date du jour AAAA-MM-JJ (tests)")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not DATE.match(a.aujourdhui):
        print("date invalide"); return 2
    print("Construction du site…")
    return construire(a.donnees, a.sortie, a.aujourdhui)


if __name__ == "__main__":
    sys.exit(main())
