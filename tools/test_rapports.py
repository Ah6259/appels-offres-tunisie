# -*- coding: utf-8 -*-
"""
Test des « Rapports du mois » (18/10/2026, règle commune § 25) — à relancer après toute modification :
    python tools/test_rapports.py

1. Le site de ce dossier : pages présentes, chiffres = données (donnees/appels-offres.json et historique
   donnees/rapports.json), mêmes métiers / gouvernorats que les autres pages du site, sous-pages ≥ minimum,
   plan du site avec la date des chiffres, lien dans le pied de page.
2. Scénarios dans une COPIE temporaire (le vrai site n'est jamais modifié) : premier mois sans fausse évolution,
   mois fini figé (plus jamais modifié), évolution seulement si le mois précédent est complet (même période),
   minimum pour une sous-page et pour un classement, pas de rapport créé après coup, données vides.
"""
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(ICI)
sys.path.insert(0, os.path.join(SITE, "robot"))
import rapports as R  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
URL = "https://appels-offres.clicvia.com/"
erreurs = total = 0


def check(desc, cond):
    global erreurs, total
    total += 1
    print(("OK   " if cond else "FAIL ") + desc)
    if not cond:
        erreurs += 1


def lire(racine, chemin):
    with open(os.path.join(racine, chemin), encoding="utf-8") as f:
        return f.read()


def lignes(html, attr):
    """{clé: nombre} des lignes de tableau data-<attr>="…" data-n="…" (une seule section : la première trouvée)."""
    return {k: int(n) for k, n in re.findall(rf'<tr data-{attr}="([^"]*)" data-n="(\d+)">', html)}


def section(html, ident):
    m = re.search(rf'<section class="carte[^"]*" id="{ident}">(.*?)</section>', html, re.S)
    return m.group(1) if m else ""


def compter(recs, cle):
    c = {}
    for r in recs:
        c[r[cle]] = c.get(r[cle], 0) + 1
    return c


# ============================================================ 1. le site de ce dossier
print("1. Site de ce dossier")
sys.path.insert(0, os.path.join(SITE, "robot"))
import construire_site as CS  # noqa: E402
hist = json.load(open(os.path.join(SITE, "donnees", "rapports.json"), encoding="utf-8"))
donnees = json.load(open(os.path.join(SITE, "donnees", "appels-offres.json"), encoding="utf-8"))
aos = CS.nettoyer(list(donnees["appels_offres"].values()))
etat = json.load(open(os.path.join(SITE, "donnees", "etat-source.json"), encoding="utf-8"))
mois = sorted(hist["mois"])
check(f"historique : au moins un mois ({', '.join(mois)})", len(mois) >= 1)
check("page rapports/ (liste des mois) présente, chaque mois listé avec son lien",
      os.path.exists(os.path.join(SITE, "rapports", "index.html"))
      and all(f'<li data-mois="{m}"><a href="{m}/">' in lire(SITE, "rapports/index.html") for m in mois))
en_cours = [m for m in mois if not hist["mois"][m].get("fige")]
for m in mois:
    e = hist["mois"][m]
    h = lire(SITE, f"rapports/{m}/index.html")
    recs = list(e["appels_offres"].values())
    c = e["chiffres"]
    check(f"{m} : chiffres de l'historique = fiches gardées ({len(recs)})", c["appels_offres"] == len(recs)
          and c["par_metier"] == compter(recs, "metier") and c["par_gouvernorat"] == compter(recs, "gouvernorat"))
    check(f"{m} : le total affiché = l'historique ({c['appels_offres']})", f"<b>{R.nb(c['appels_offres'])}</b> appels d’offres publiés en" in h)
    tm, tg = lignes(section(h, "par-metier"), "metier"), lignes(section(h, "par-gouvernorat"), "gouvernorat")
    check(f"{m} : tableau par métier = chiffres (≥ {R.MIN_CLASSEMENT} chacun)",
          tm == {CS.M_PAR_NOM[k][1]: n for k, n in c["par_metier"].items() if n >= R.MIN_CLASSEMENT} or (not tm and "Pas de classement" in section(h, "par-metier")))
    check(f"{m} : tableau par gouvernorat = chiffres (≥ {R.MIN_CLASSEMENT} chacun)",
          tg == {CS.G_PAR_NOM[k][1]: n for k, n in c["par_gouvernorat"].items() if n >= R.MIN_CLASSEMENT} or (not tg and "Pas de classement" in section(h, "par-gouvernorat")))
    ta = lignes(section(h, "acheteurs"), "acheteur")
    check(f"{m} : acheteurs = chiffres, chacun ≥ {R.MIN_CLASSEMENT}, jamais un classement de 1 ou 2 lignes",
          {CS.html.unescape(k): n for k, n in ta.items()} == c["acheteurs"] and all(n >= R.MIN_CLASSEMENT for n in ta.values())
          and (len(ta) == 0 or len(ta) >= R.MIN_LIGNES))
    check(f"{m} : JSON-LD Article + FAQ + fil d'Ariane, bloc « Citer ces chiffres », méthode",
          '"@type": "Article"' in h and '"@type": "FAQPage"' in h and '"@type": "BreadcrumbList"' in h
          and 'id="citer"' in h and 'id="methode"' in h and f"{URL}rapports/{m}/" in section(h, "citer"))
    if m in en_cours:
        # données du site : toute fiche du mois encore en mémoire est dans l'historique, avec le même classement
        du_mois = [a for a in aos if a["date_publication"][:7] == m]
        check(f"{m} (en cours) : les {len(du_mois)} fiches du mois dans les données sont toutes dans le rapport, même métier et même gouvernorat",
              all(a["numero"] in e["appels_offres"] and e["appels_offres"][a["numero"]]["metier"] == a["metier"]
                  and e["appels_offres"][a["numero"]]["gouvernorat"] == a["gouvernorat"] for a in du_mois))
        if len(du_mois) == len(recs):
            check(f"{m} (en cours) : total, métiers et gouvernorats recalculés directement depuis donnees/appels-offres.json",
                  c["appels_offres"] == len(du_mois) and c["par_metier"] == compter(du_mois, "metier")
                  and c["par_gouvernorat"] == compter(du_mois, "gouvernorat"))
        check(f"{m} (en cours) : « chiffres au {e['derniere_date']} » affiché", f"Chiffres au {CS.dfr(e['derniere_date'])}" in h)
    # sous-pages : minimum, plafond, mêmes fiches que les pages métier / gouvernorat du site
    sous = [os.path.join(t, s) for t in ("gouvernorat", "metier") if os.path.isdir(os.path.join(SITE, "rapports", m, t))
            for s in os.listdir(os.path.join(SITE, "rapports", m, t))]
    check(f"{m} : {len(sous)} sous-pages (au plus {R.MAX_SOUS_PAGES})", len(sous) <= R.MAX_SOUS_PAGES)
    ok_min, ok_meme, ok_liste = True, True, True
    for sp in sous:
        t, slug = sp.replace("\\", "/").split("/")
        nom = (CS.G_PAR_SLUG if t == "gouvernorat" else CS.M_PAR_SLUG)[slug][0]
        sel = [r for r in recs if r[t] == nom]
        hs = lire(SITE, f"rapports/{m}/{t}/{slug}/index.html")
        listes = re.findall(r'<li data-numero="(Tender-\d+)">', hs)
        if len(sel) < R.MIN_SOUS_PAGE or nom in R.SPECIAUX_G + R.SPECIAUX_M:
            ok_min = False
        if sorted(listes) != sorted(r["numero"] for r in sel) or f"<b>{R.nb(len(sel))}</b> appels d’offres publiés en" not in hs:
            ok_liste = False
        # mêmes classements que la page du site (pour les appels d'offres encore ouverts)
        page_site = lire(SITE, f"{t}/{slug}/index.html")
        cartes = set(re.findall(r'<article class="ao[^"]*" id="(Tender-\d+)"', page_site))
        ouverts = [r["numero"] for r in sel if r["date_limite"] and r["date_limite"] >= etat["construit_le"]]
        if not all(n in cartes for n in ouverts):
            ok_meme = False
            print("   pas sur la page du site :", sp, [n for n in ouverts if n not in cartes][:5])
    check(f"{m} : chaque sous-page a au moins {R.MIN_SOUS_PAGE} appels d'offres (jamais « Plusieurs », « National », « Autres »)", ok_min)
    check(f"{m} : chaque sous-page liste exactement les fiches du mois de son gouvernorat / métier", ok_liste)
    check(f"{m} : les fiches encore ouvertes d'une sous-page sont aussi sur la page gouvernorat / métier du site (mêmes chiffres partout)", ok_meme)
# plan du site : toutes les pages des rapports, avec la date de leurs chiffres
sitemap = lire(SITE, "sitemap.xml")
pages_r = []
for dossier, _, fichiers in os.walk(os.path.join(SITE, "rapports")):
    if "index.html" in fichiers:
        pages_r.append(os.path.relpath(dossier, SITE).replace("\\", "/") + "/")
ok_sm = True
for p in pages_r:
    m = re.match(r"rapports/(\d{4}-\d{2})/", p)
    attendu = hist["mois"][m.group(1)]["derniere_date"] if m else max(hist["mois"][x]["derniere_date"] for x in mois)
    if f"<loc>{URL}{p}</loc><lastmod>{attendu}</lastmod>" not in sitemap:
        ok_sm = False
        print("   absente du plan du site ou mauvaise date :", p)
check(f"plan du site : les {len(pages_r)} pages des rapports, lastmod = date de leurs chiffres", ok_sm and len(pages_r) >= 2)
check("pied de page : lien « Rapports du mois » (FR + AR)", '${racine}rapports/">${T("Rapports du mois", "تقارير الشهر")}' in lire(SITE, "assets/page.js"))
check("robot GitHub : les pages rapports/ sont enregistrées par maj.yml et ce test y est lancé",
      re.search(r"git add [^\n]*\brapports\b", lire(SITE, ".github/workflows/maj.yml")) is not None
      and "tools/test_rapports.py" in lire(SITE, ".github/workflows/maj.yml") and "tools/test_rapports.py" in lire(SITE, ".github/workflows/tests.yml"))
check("rien de la partie payante dans les rapports (pas d'abonnés, pas de chat_id)",
      not any(re.search(r"abonne|chat_?id", lire(SITE, p + "index.html")) for p in pages_r))


# bouton « Partager ce rapport » (demande d'Ahmed, 18/10/2026) : UN seul bouton en haut + un en bas, sur TOUTES les pages des rapports
ok_btn, ok_res, ok_sig, ok_desc, ok_og = True, True, True, True, True
for p in pages_r:
    h = lire(SITE, p + "index.html")
    url_p = URL + p
    boutons = re.findall(r'<button class="rp-partager" type="button" data-partage-rapport data-url="([^"]*)"', h)
    haut, bas = h.find("rp-partage-haut"), h.find("rp-partage-bas")
    if not (boutons == [url_p, url_p] and 0 < h.find("<h1") < haut < h.find('<main') < bas and h.count("rp-aide") == 2
            and "Facebook, WhatsApp, LinkedIn… : le menu de votre téléphone s’ouvre." in h and 'class="rp-copie" role="status" hidden' in h):
        ok_btn = False; print("   bouton :", p, boutons)
    if re.search(r"facebook\.com/sharer|wa\.me/|linkedin\.com/share|twitter\.com/intent|onclick=", h) or "data-reseau=" in h:
        ok_res = False; print("   lien séparé :", p)
    if not ('<p class="rp-signature"><span data-l="fr">Un rapport de <b>Alertes appels d&#x27;offres Tunisie</b> · appels-offres.clicvia.com</span>' in h
            and h.find("<h1") < h.find("rp-signature") < haut):
        ok_sig = False; print("   signature :", p)
    desc = re.search(r'<meta name="description" content="([^"]*)"', h)
    ogd = re.search(r'<meta property="og:description" content="([^"]*)"', h)
    if not (desc and ogd and desc.group(1).startswith("Alertes appels d&#x27;offres Tunisie — rapport du mois. ") and ogd.group(1) == desc.group(1)):
        ok_desc = False; print("   description :", p)
    if not (f'<meta property="og:url" content="{url_p}">' in h and re.search(r'<meta property="og:title" content="[^"|]{10,}">', h)
            and f'<meta property="og:image" content="{URL}assets/og-image-v6.jpg">' in h and os.path.exists(os.path.join(SITE, "assets", "og-image-v6.jpg"))):
        ok_og = False; print("   og :", p)
check(f"partage : les {len(pages_r)} pages des rapports ont UN bouton « Partager ce rapport » en haut (sous le titre) et un en bas, avec leur adresse", ok_btn)
check("partage : aucun lien Facebook / WhatsApp / LinkedIn séparé dans les rapports (le menu du téléphone propose tout)", ok_res)
check("partage : signature « Un rapport de Alertes appels d'offres Tunisie · appels-offres.clicvia.com » sous le titre", ok_sig)
check("partage : la description (et og:description) commence par « Alertes appels d'offres Tunisie — rapport du mois. »", ok_desc)
check("partage : og:title, og:url (= adresse de la page) et og:image (image avec le nom du site) présents", ok_og)
js = lire(SITE, "assets/page.js")
check("partage : code du bouton dans assets/page.js (button[data-partage-rapport], navigator.share, presse-papiers, prompt, GoatCounter)",
      all(x in js for x in ('closest("button[data-partage-rapport]")', "navigator.share(", "navigator.clipboard.writeText(", "window.prompt(",
                            '"partage" + location.pathname', "Lien copié ✓ — collez-le où vous voulez", "Rapport du mois d’")))
css = lire(SITE, "assets/style.css")
check("partage : bouton tactile (au moins 44 px de haut) dans style.css", re.search(r"\.rp-partager\{[^}]*min-height:(4[4-9]|[5-9]\d)px", css) is not None)

# ============================================================ 2. scénarios (copie temporaire)
@contextlib.contextmanager
def copie():
    tmp = tempfile.mkdtemp(prefix="ao-rapports-")
    dest = os.path.join(tmp, "site")
    shutil.copytree(SITE, dest, ignore=shutil.ignore_patterns("node_modules", "captures", ".git", "rapports"))
    for f in os.listdir(os.path.join(dest, "donnees")):
        os.remove(os.path.join(dest, "donnees", f))
    try:
        yield dest
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fiche(num, pub, gouv="Sfax", metier="BTP / génie civil", lu=None, acheteur="Municipalité de Sfax"):
    return {"numero": f"Tender-{num}", "objet": f"Travaux numéro {num}", "acheteur": acheteur, "procedure": "Appel d’offres ouvert",
            "date_publication": pub, "date_limite": "2026-12-30", "cautionnement_total_dt": 1000 + num % 7,
            "lien": f"https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-{num}", "source": "HAICOP",
            "lu_le": (lu or pub) + " 06:00", "metier": metier, "gouvernorat": gouv}


def ecrire(site, aos, jour, ventes=None):
    with open(os.path.join(site, "donnees", "appels-offres.json"), "w", encoding="utf-8") as f:
        json.dump({"source": "HAICOP", "appels_offres": {a["numero"]: a for a in aos}, "mis_a_jour": jour + " 06:00",
                   "derniere_lecture_reussie": jour + " 06:00", "statut_source": {"etat": "ok"}}, f, ensure_ascii=False)
    with open(os.path.join(site, "donnees", "encheres.json"), "w", encoding="utf-8") as f:
        json.dump({"ventes": ventes or {}, "derniere_lecture_reussie": jour + " 06:00", "statut_source": {"etat": "ok"}}, f)


def construire(site, jour):
    r = subprocess.run([sys.executable, os.path.join(site, "robot", "construire_site.py"), "--donnees",
                        os.path.join(site, "donnees", "appels-offres.json"), "--sortie", site, "--aujourdhui", jour],
                       capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode:
        print(r.stdout + r.stderr)
    return r.returncode


def historique(site):
    return json.load(open(os.path.join(site, "donnees", "rapports.json"), encoding="utf-8"))


print("\n2. Scénarios")
# Octobre lu depuis le 04/10 (incomplet) : 12 à Tunis (BTP), 9 à Sfax (Informatique), 4 à Sousse (Électricité)
OCT = ([fiche(1000 + k, f"2026-10-{4 + k % 10:02d}", "Tunis", acheteur=f"Acheteur {k % 4}") for k in range(12)]
       + [fiche(2000 + k, f"2026-10-{5 + k:02d}", "Sfax", "Informatique") for k in range(9)]
       + [fiche(3000 + k, f"2026-10-{6 + k:02d}", "Sousse", "Électricité") for k in range(4)])
with copie() as s:
    ecrire(s, OCT, "2026-10-20")
    check("premier mois : construction sans erreur", construire(s, "2026-10-20") == 0)
    h = lire(s, "rapports/2026-10/index.html")
    check("premier mois : « Premier rapport », aucune évolution affichée", 'id="premier-rapport"' in h and 'id="evolution"' not in h and "Évolution :" not in h)
    check("premier mois : avertissement « relevés en partie » (robot lancé le 04/10, après le 1er du mois)", 'id="partiel"' in h and "04/10/2026" in section(h, "en-bref"))
    check("premier mois : 25 appels d'offres affichés, tableau par gouvernorat Tunis 12 / Sfax 9 / Sousse 4",
          "<b>25</b> appels d’offres publiés en octobre 2026" in h and lignes(section(h, "par-gouvernorat"), "gouvernorat") == {"tunis": 12, "sfax": 9, "sousse": 4})
    check(f"sous-page seulement à partir de {R.MIN_SOUS_PAGE} appels d'offres : Tunis (12) oui, Sfax (9) non, métier BTP (12) oui",
          os.path.exists(os.path.join(s, "rapports/2026-10/gouvernorat/tunis/index.html"))
          and not os.path.exists(os.path.join(s, "rapports/2026-10/gouvernorat/sfax/index.html"))
          and os.path.exists(os.path.join(s, "rapports/2026-10/metier/btp-genie-civil/index.html"))
          and not os.path.exists(os.path.join(s, "rapports/2026-10/metier/informatique/index.html")))
    ht = lire(s, "rapports/2026-10/gouvernorat/tunis/index.html")
    check("sous-page Tunis : 4 acheteurs à 3 appels d'offres = classement (≥ 3 lignes de ≥ 3)", lignes(section(ht, "acheteurs"), "acheteur") == {f"Acheteur {k}": 3 for k in range(4)})
    check("sous-page Tunis : un seul métier -> « Pas de classement » (jamais de classement sur 1 ou 2 lignes)", "Pas de classement" in section(ht, "par-metier") and not lignes(section(ht, "par-metier"), "metier"))
    sm = lire(s, "sitemap.xml")
    check("plan du site : rapport du mois et sous-pages avec lastmod = 2026-10-20 (date des chiffres)",
          f"<loc>{URL}rapports/2026-10/</loc><lastmod>2026-10-20</lastmod>" in sm and f"<loc>{URL}rapports/2026-10/gouvernorat/tunis/</loc><lastmod>2026-10-20</lastmod>" in sm
          and f"<loc>{URL}rapports/</loc>" in sm)

    # fin du mois : encore recalculé le 02/11, figé le 03/11
    OCT2 = OCT + [fiche(4000, "2026-10-31", "Sfax", "Informatique", lu="2026-11-01")]
    NOV = [fiche(5000 + k, f"2026-11-{2 + k % 8:02d}", "Tunis") for k in range(6)]
    ecrire(s, OCT2 + NOV[:1], "2026-11-02")
    construire(s, "2026-11-02")
    e = historique(s)["mois"]["2026-10"]
    check("le 02/11 : octobre pas encore figé, fiche du 31/10 lue le 01/11 comptée (26), chiffres au 31/10",
          not e["fige"] and e["chiffres"]["appels_offres"] == 26 and e["derniere_date"] == "2026-10-31")
    ecrire(s, OCT2 + NOV, "2026-11-03")
    construire(s, "2026-11-03")
    e = historique(s)["mois"]["2026-10"]
    gele = json.dumps(e, sort_keys=True)
    check("le 03/11 : octobre figé (fige_le 2026-11-03)", e["fige"] and e["fige_le"] == "2026-11-03")
    h_avant = section(lire(s, "rapports/2026-10/index.html"), "en-bref")
    # données qui changent ensuite : une fiche d'octobre ajoutée, une autre reclassée -> le mois figé ne bouge pas
    OCT3 = [dict(a, gouvernorat="Bizerte") if a["numero"] == "Tender-1000" else a for a in OCT2] + [fiche(4001, "2026-10-30", "Gabès")]
    ecrire(s, OCT3 + NOV, "2026-11-10")
    construire(s, "2026-11-10")
    e2 = historique(s)["mois"]["2026-10"]
    h = lire(s, "rapports/2026-10/index.html")
    check("mois figé : historique identique malgré des données modifiées (fiche ajoutée, fiche reclassée)", json.dumps(e2, sort_keys=True) == gele)
    check("mois figé : page avec les mêmes chiffres (« chiffres définitifs »), lastmod gardé au 31/10",
          section(h, "en-bref") == h_avant and "chiffres définitifs" in h
          and f"<loc>{URL}rapports/2026-10/</loc><lastmod>2026-10-31</lastmod>" in lire(s, "sitemap.xml"))
    hn = lire(s, "rapports/2026-11/index.html")
    check("novembre : octobre incomplet (robot lancé le 04/10) -> pas d'évolution, et on dit pourquoi",
          'id="sans-evolution"' in hn and 'id="evolution"' not in hn and "Évolution :" not in hn)
    check("novembre : pas d'avertissement « relevés en partie » (robot déjà en marche le 01/11)", 'id="partiel"' not in hn)
    check("liste des mois : novembre puis octobre", lire(s, "rapports/index.html").find('data-mois="2026-11"') < lire(s, "rapports/index.html").find('data-mois="2026-10"'))

with copie() as s:
    # robot en marche dès le 30/09 -> octobre complet -> évolution en novembre, sur la même période
    SEP = [fiche(900, "2026-09-30", lu="2026-09-30")]
    OCTC = [fiche(1100 + k, f"2026-10-{1 + k:02d}") for k in range(20)]       # 1 par jour du 01 au 20/10
    ecrire(s, SEP + OCTC, "2026-10-21")
    construire(s, "2026-10-21")
    hs = historique(s)
    check("robot en marche le 30/09 : octobre « complet » ; septembre déjà fini au 1er passage (21/10) : pas de rapport après coup",
          hs["mois"]["2026-10"]["complet"] and "2026-09" not in hs["mois"])
    h = lire(s, "rapports/2026-10/index.html")
    check("octobre : pas de mois précédent -> « Premier rapport », pas d'évolution, pas d'avertissement « en partie »",
          'id="premier-rapport"' in h and "Évolution :" not in h and 'id="partiel"' not in h)
    NOVC = [fiche(5100 + k, f"2026-11-{2 + k:02d}") for k in range(8)]          # du 02 au 09/11
    ecrire(s, SEP + OCTC + NOVC, "2026-11-09")
    construire(s, "2026-11-09")
    h = lire(s, "rapports/2026-11/index.html")
    evo = re.search(r'<li id="evolution">(.*?)</li>', h, re.S)
    check("novembre en cours : évolution comparée à la MÊME période (8 contre 9 du 1er au 9 octobre, soit −1)",
          evo is not None and "Évolution : 8 appels d'offres contre 9 du 1er au 9 octobre 2026 (même période), soit −1 (−11 %)." in evo.group(1))
    ecrire(s, SEP + OCTC + NOVC, "2026-12-05")
    construire(s, "2026-12-05")
    h = lire(s, "rapports/2026-11/index.html")
    evo = re.search(r'<li id="evolution">(.*?)</li>', h, re.S)
    check("novembre figé : évolution mois complet contre mois complet (8 contre 20)",
          evo is not None and "Évolution : 8 appels d'offres contre 20 en octobre 2026 (mois complet), soit −12 (−60 %)." in evo.group(1))
    ht = lire(s, "rapports/2026-11/gouvernorat/sfax/index.html") if os.path.exists(os.path.join(s, "rapports/2026-11/gouvernorat/sfax/index.html")) else ""
    check("pas de sous-page sous le minimum (Sfax : 8 en novembre)", ht == "")

with copie() as s:
    # mois déjà terminé avant le premier passage du robot : aucun rapport créé après coup
    ecrire(s, [fiche(700 + k, "2026-08-1" + str(k)) for k in range(5)] + OCT, "2026-10-20")
    construire(s, "2026-10-20")
    check("août (terminé avant le premier passage) : aucun rapport créé après coup", "2026-08" not in historique(s)["mois"]
          and not os.path.exists(os.path.join(s, "rapports/2026-08")))
    # ventes aux enchères du mois : comptées seulement pour un mois qui a un rapport
    ventes = {f"Vente-{k:010x}": {"id": f"Vente-{k:010x}", "date_publication": f"2026-{'10' if k < 4 else '09'}-1{k}", "gouvernorat": "Tunis",
                                  "objet": "Avis de vente", "date_limite": "2026-12-01"} for k in range(6)}
    ecrire(s, OCT, "2026-10-20", ventes)
    construire(s, "2026-10-20")
    e = historique(s)["mois"]["2026-10"]
    check("ventes aux enchères : les 4 d'octobre comptées, celles de septembre ignorées (pas de rapport de septembre)",
          e["chiffres"]["ventes"] == 4 and "2026-09" not in historique(s)["mois"]
          and "<b>4</b> avis de vente aux enchères publiés en octobre 2026" in lire(s, "rapports/2026-10/index.html"))

with copie() as s:
    ecrire(s, [fiche(1, "", lu="2026-10-20")], "2026-10-20")      # une fiche sans date de publication : jamais rangée dans un mois
    code = construire(s, "2026-10-20")
    check("aucune fiche datée : construction OK, la page rapports/ existe et dit « Pas encore de rapport »", code == 0 and os.path.exists(os.path.join(s, "rapports/index.html"))
          and "Pas encore de rapport" in lire(s, "rapports/index.html"))

print(f"\n{total - erreurs}/{total} vérifications réussies" + (f" — {erreurs} ÉCHEC(S) : ne pas publier." if erreurs else " — tout est bon."))
sys.exit(1 if erreurs else 0)
