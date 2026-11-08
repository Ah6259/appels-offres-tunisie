# -*- coding: utf-8 -*-
"""UNE ADRESSE PAR LANGUE (08/11/2026, plan SEO d'Ahmed, phase 2 point 7 ; copie adaptée de robot/langues.py de l'Immobilier et de Concours).

Avant : chaque page contenait tout le texte en français ET en arabe (spans data-l, l'autre langue cachée par le style), avec lang="fr".
Google voyait une page « française » à moitié arabe et ne l'indexait pas.
Maintenant, à partir de la page bilingue fabriquée par page() :
  - <chemin> (français) : sans les textes arabes ;
  - ar/<chemin> (arabe) : sans les textes français, lang="ar" dir="rtl", titre (H1 arabe) et description (1er paragraphe arabe) en arabe,
    fichiers (style, scripts, images, données) pris à la racine du site, pages restant dans ar/ ;
  - les deux pages se citent (hreflang fr / ar / x-default = fr) et ont chacune leur canonical ;
  - data-langue-fixe : la langue est celle de l'adresse ; le bouton de langue mène à l'autre adresse (assets/page.js).
"""
import html as H
import re

URL_SITE = "https://appels-offres.clicvia.com/"
NOM_AR = "طلبات العروض تونس"
BALISE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b([^>]*?)(/?)>", re.S)
VIDES = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def titre_seo(t, maxi=70, suffixes=(" | Alertes appels d'offres", " | Alertes appels d'offres Tunisie", " | " + NOM_AR)):
    """SEO (08/11/2026, règle commune § 56) : titre <= 70 caractères. Un suffixe « | nom du site » saute s'il fait dépasser (le suffixe
    arabe est gardé et la base coupée) ; puis coupe à un séparateur s'il reste au moins 38 caractères, sinon au dernier mot + « … »."""
    t = " ".join(str(t).split())
    if len(t) <= maxi:
        return t
    suffixe = ""
    for sfx in suffixes:
        if t.endswith(sfx):
            t, suffixe = t[:-len(sfx)].rstrip(), (sfx if sfx.endswith(NOM_AR) else "")
            break
    place = maxi - len(suffixe)
    if len(t) <= place:
        return t + suffixe
    for sep in (" : ", " — ", " (", " – ", " · ", ", "):
        i = t.rfind(sep, 0, place)
        if i >= 38:
            return t[:i].rstrip(" ,;:—-·") + suffixe
    return t[:place - 1].rsplit(" ", 1)[0].rstrip(" ,;:—-·(") + "…" + suffixe


def desc_seo(d, maxi=165):
    """Description <= 165 caractères : coupée à la fin de la dernière phrase entière, sinon au dernier mot + « … »."""
    d = " ".join(str(d).split())
    if len(d) <= maxi:
        return d
    coupe = d[:maxi]
    i = max(coupe.rfind(". "), coupe.rfind(" ! "), coupe.rfind(" ? "), coupe.rfind("؟ "), coupe.rfind("۔ "))
    if i >= 60:
        return coupe[:i + 1].strip()
    return coupe[:maxi - 1].rsplit(" ", 1)[0].rstrip(" ,;:—-(،") + "…"


def retirer_langue(page, autre):
    """Enlève chaque élément data-l="<autre>" (et tout ce qu'il contient), sauf dans les cartes d'annonces."""
    sortie, i, carte, saut = [], 0, 0, 0   # carte = profondeur des <article> depuis le début d'une carte d'annonce
    for m in BALISE.finditer(page):
        if m.start() < max(i, saut):
            continue
        ferme, nom, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if nom in ("script", "style") and not ferme:          # jamais de balise cherchée dans un script ou un style
            fin = page.find(f"</{nom}", m.end())
            saut = len(page) if fin < 0 else fin
            continue
        if nom == "article":
            if not ferme and (carte or re.search(r'class="annonce\b', attrs)):
                carte += 1
            elif ferme and carte:
                carte -= 1
            continue
        if ferme or carte or f'data-l="{autre}"' not in attrs:
            continue
        sortie.append(page[i:m.start()])
        if nom in VIDES or m.group(4):
            j = m.end()
        else:
            prof, j = 1, m.end()                               # fin de l'élément : même nom de balise, en comptant l'imbrication
            for n in BALISE.finditer(page, m.end()):
                if n.group(2).lower() != nom or n.group(4):
                    continue
                prof += -1 if n.group(1) else 1
                if prof == 0:
                    j = n.end()
                    break
            else:
                j = len(page)
        # un espace à la place de l'élément retiré : deux mots voisins ne se collent pas dans le texte lu (« civil » + « Kairouan »,
        # vu par la recherche au son) ; pas d'espace juste après une balise ouvrante ni juste avant la fermeture d'un titre
        # (<h1><span data-l="ar">…</span></h1> reste propre)
        avant = "".join(sortie)[-80:]
        suite = page[j:j + 4]
        if (suite and not suite[0].isspace() and not re.match(r"</h[1-6]", suite) and not re.match(r"</title", suite)
                and not re.search(r"<[a-zA-Z][^>]*>$", avant) and avant and not avant[-1].isspace()):
            sortie.append(" ")
        i = j
    sortie.append(page[i:])
    return "".join(sortie)


def _texte(fragment):
    t = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", H.unescape(t)).replace("⁦", "").replace("⁩", "").strip()


def textes_arabes(page):
    """Titre et description arabes tirés de la page : le H1 et le premier paragraphe arabe qui suit."""
    h1 = re.search(r"<h1\b[^>]*>(.*?)</h1>", page, re.S)
    titre = ""
    if h1 and 'data-l="ar"' in h1.group(1):                    # le H1 entier, sans sa partie française
        titre = _texte(retirer_langue(h1.group(1), "fr"))
    desc = ""
    explicite = re.search(r'<meta name="description-ar" content="([^"]*)">', page)
    if explicite:
        return titre, H.unescape(explicite.group(1))
    debut = h1.end() if h1 else 0
    for m in re.finditer(r'<(p|span|div)\b[^>]*data-l="ar"[^>]*>(.*?)</\1>', page[debut:], re.S):
        t = _texte(m.group(2))
        if len(t) >= 40 and "clicvia.com" not in t and not re.match(r"^[^\w\u0600-\u06FF]", t):
            desc = t
            break
    if len(desc) > 158:
        desc = desc[:155].rsplit(" ", 1)[0] + "…"
    return titre, desc


MIROIR = set()        # chemins des pages fabriquées à ce passage (elles existent en arabe) ; rempli par construire_site.py


def _plus_un_niveau(url, chemin):
    """Adresse relative d'une page arabe (un dossier plus bas) : une page fabriquée à ce passage reste dans ar/ ; tout le reste
    (style, scripts, données, images, anciennes pages de concours plus dans les données, PDF…) est pris à la racine du site."""
    if not url or re.match(r"^([a-z][a-z0-9+.-]*:|//|/|#|\?)", url, re.I):
        return url
    p = url.split("#")[0].split("?")[0]
    if p == "" or p.endswith("/") or p in (".", ".."):
        if _resoudre(chemin, p) in MIROIR:
            return url
    return "../" + url


def _resoudre(chemin, rel):
    parts = [x for x in chemin.split("/")[:-1] if x]        # dossier de la page
    for x in rel.split("/"):
        if x in ("", "."):
            continue
        if x == "..":
            if parts:
                parts.pop()
        else:
            parts.append(x)
    return "/".join(parts) + ("/" if parts and (rel.endswith("/") or rel in ("", ".", "..")) else "")


def _reecrire_liens(page, chemin):
    def attr(m):
        nom, val = m.group(1), m.group(2)
        if nom == "srcset":
            morceaux = [s.strip() for s in val.split(",")]
            val = ", ".join(" ".join([_plus_un_niveau(s.split()[0], chemin)] + s.split()[1:]) for s in morceaux if s)
        else:
            val = _plus_un_niveau(val, chemin)
        return f'{nom}="{val}"'
    # attributs d'adresse hors des scripts JSON-LD (adresses absolues de toute façon)
    return re.sub(r'\b(href|src|srcset|action|poster)="([^"]*)"', attr, page)


def tete_langues(chemin):
    fr, ar = URL_SITE + chemin, URL_SITE + "ar/" + chemin
    return (f'<link rel="alternate" hreflang="fr" href="{fr}">\n<link rel="alternate" hreflang="ar" href="{ar}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{fr}">')


def versions(page, chemin):
    """chemin = dossier de la page ("" pour l'accueil, "metier/sante/"…). Renvoie (page française, page arabe)."""
    titre_ar, desc_ar = textes_arabes(page)
    if not titre_ar:
        titre_ar = re.search(r"<title>(.*?)</title>", page, re.S).group(1).split(" | ")[0]
    if not desc_ar:
        desc_ar = titre_ar
    tete = tete_langues(chemin)
    profondeur = chemin.count("/")
    vers_ar = "../" * profondeur + "ar/" + chemin            # bouton de langue : adresse relative de l'autre version
    vers_fr = "../" * (profondeur + 1) + chemin
    m = re.search(r'<html lang="fr" dir="ltr" translate="no" data-racine="([^"]*)">', page)
    if not m:
        raise SystemExit(f"ÉCHEC - {chemin or 'accueil'} : balise <html lang=\"fr\" … data-racine> attendue")
    racine = m.group(1)

    page = re.sub(r'\n?<meta name="description-ar" content="[^"]*">', "", page)
    fr = retirer_langue(page, "ar")
    fr = fr.replace('<link rel="canonical"', tete + '\n<link rel="canonical"', 1)
    fr = fr.replace(m.group(0), f'<html lang="fr" dir="ltr" translate="no" data-racine="{racine}" data-langue-fixe="fr" data-autre-langue="{vers_ar}">', 1)

    ar = retirer_langue(page, "fr")
    ar = _reecrire_liens(ar, chemin)
    ar = ar.replace(m.group(0), f'<html lang="ar" dir="rtl" translate="no" data-racine="../{racine}" data-site="{racine}" data-langue-fixe="ar" data-autre-langue="{vers_fr}">', 1)
    url_ar = URL_SITE + "ar/" + chemin
    ar = re.sub(r'<link rel="canonical" href="[^"]*">', lambda x: tete + f'\n<link rel="canonical" href="{url_ar}">', ar, count=1)
    ar = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url_ar}">', ar, count=1)
    ar = ar.replace('<meta property="og:locale" content="fr_FR"><meta property="og:locale:alternate" content="ar_AR">',
                    '<meta property="og:locale" content="ar_AR"><meta property="og:locale:alternate" content="fr_FR">', 1)
    ar = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", ar, flags=re.S)   # données Google écrites en français : pas sur la page arabe
    t = H.escape(titre_seo(f"{titre_ar} | {NOM_AR}"), quote=False)
    ar = re.sub(r"<title>.*?</title>", lambda x: f"<title>{t}</title>", ar, count=1, flags=re.S)
    ar = re.sub(r'<meta property="og:title" content="[^"]*">', lambda x: f'<meta property="og:title" content="{H.escape(titre_ar)}">', ar, count=1)
    desc_ar = desc_seo(desc_ar)
    ar = re.sub(r'<meta name="description" content="[^"]*">', lambda x: f'<meta name="description" content="{H.escape(desc_ar)}">', ar, count=1)
    ar = re.sub(r'<meta property="og:description" content="[^"]*">', lambda x: f'<meta property="og:description" content="{H.escape(desc_ar)}">', ar, count=1)
    ar = ar.replace('<meta name="apple-mobile-web-app-title" content="Appels d\'offres">', '<meta name="apple-mobile-web-app-title" content="طلبات العروض">', 1)
    return fr, ar


def nettoyer(racine):
    """Retire chaque page arabe ar/<chemin> dont la page française <chemin> n'existe plus (07/11/2026 : un quartier passé
    sous 8 annonces perd sa page française, sa version arabe restait en ligne avec des liens vers une page disparue)."""
    import os
    import shutil
    retirees = []
    base = os.path.join(racine, "ar")
    for dossier, sous, fichiers in os.walk(base, topdown=False):
        if "index.html" in fichiers:
            rel = os.path.relpath(dossier, base)
            fr = os.path.join(racine, "index.html") if rel == "." else os.path.join(racine, rel, "index.html")
            if not os.path.exists(fr):           # 08/11/2026 (leçon de Concours) : seulement si la page française a disparu du disque (une page française gardée hors des pages du jour garde sa page arabe : hreflang et bouton de langue)
                os.remove(os.path.join(dossier, "index.html"))
                retirees.append(rel)
        if dossier != base and not os.listdir(dossier):
            shutil.rmtree(dossier)
    return retirees
