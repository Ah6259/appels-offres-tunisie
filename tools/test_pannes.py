# -*- coding: utf-8 -*-
"""
Scénarios de panne — à relancer après toute modification des robots :
    python tools/test_pannes.py

Rien n'est lu sur Internet : le portail HAICOP est simulé. Chaque scénario travaille
dans une COPIE temporaire du site ; le vrai site n'est jamais modifié.

A. Robot de lecture (lire_haicop.py) : source injoignable, liste presque vide,
   format des fiches changé (2 variantes), panne qui dure (date « depuis » gardée),
   retour à la normale.
B. Constructeur (construire_site.py) : source vide, JSON corrompu, chute brutale,
   champs vides, fiche sans date limite, appel d'offres expiré, doublons,
   texte piégé, panne d'un jour, panne de 8 jours, retour à la normale.
"""
import contextlib
import datetime as dt
import io
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
import lire_haicop as R  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JOUR = "2026-10-05"
erreurs = total = 0


def check(desc, cond):
    global erreurs, total
    total += 1
    print(("OK   " if cond else "FAIL ") + desc)
    if not cond:
        erreurs += 1


def plus(d, n):
    return (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()


def fiche(num, objet="Travaux d'aménagement de la route régionale", limite="2026-11-10",
          pub="2026-10-03", gouv="Sfax", metier="BTP / génie civil", **autres):
    a = {"numero": f"Tender-{num}", "objet": objet, "descriptif": "", "acheteur": "Municipalité de Sfax",
         "type_commande": "Travaux/ Routes", "procedure": "Appel d’offres ouvert", "region_execution": "SFAX",
         "regions_lots": ["SFAX"], "date_publication": pub, "date_limite": limite, "heure_limite": "10:00",
         "cautionnement_total_dt": 5000, "lien": f"https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-{num}",
         "source": "HAICOP", "lu_le": "2026-10-04 23:45", "metier": metier, "gouvernorat": gouv}
    a.update(autres)
    return a


def donnees(aos, lecture=f"{JOUR} 06:00", statut=None, passage=None):
    d = {"source": "HAICOP", "appels_offres": {a["numero"]: a for a in aos} if isinstance(aos, list) else aos,
         "mis_a_jour": lecture, "derniere_lecture_reussie": lecture}
    if statut:
        d["statut_source"] = statut
    if passage:
        d["dernier_passage"] = passage
    return d


@contextlib.contextmanager
def copie_site():
    """Copie temporaire du site (sans node_modules ni captures)."""
    tmp = tempfile.mkdtemp(prefix="ao-pannes-")
    dest = os.path.join(tmp, "site")
    shutil.copytree(SITE, dest, ignore=shutil.ignore_patterns("node_modules", "captures", ".git"))
    for f in os.listdir(os.path.join(dest, "donnees")):
        os.remove(os.path.join(dest, "donnees", f))
    try:
        yield dest
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def ecrire_json(chemin, contenu):
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(contenu if isinstance(contenu, str) else json.dumps(contenu, ensure_ascii=False))


def construire(site, jour=JOUR):
    r = subprocess.run([sys.executable, os.path.join(site, "robot", "construire_site.py"),
                        "--donnees", os.path.join(site, "donnees", "appels-offres.json"),
                        "--sortie", site, "--aujourdhui", jour],
                       capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, r.stdout + r.stderr


def lire(site, chemin="index.html"):
    with open(os.path.join(site, chemin), encoding="utf-8") as f:
        return f.read()


def cartes(html):
    return re.findall(r'<article class="ao[^"]*" id="(Tender-\d+)"', html)


def bandeau(html):
    return 'class="alerte-panne on"' in html


def etat(site):
    with open(os.path.join(site, "donnees", "etat-source.json"), encoding="utf-8") as f:
        return json.load(f)


NORMALES = [fiche(104000 + k, pub=plus(JOUR, -1 - k % 3), limite=plus(JOUR, 10 + k)) for k in range(12)]

# =========================================================== B. constructeur
print("B. Constructeur du site")
with copie_site() as s:
    J = os.path.join(s, "donnees", "appels-offres.json")
    ecrire_json(J, donnees(NORMALES))
    code, log = construire(s)
    h = lire(s)
    check("normal : 12 cartes, pas d'avertissement, code 0", code == 0 and len(cartes(h)) == 12 and not bandeau(h))
    check("normal : sauvegarde écrite", os.path.exists(J.replace(".json", ".sauvegarde.json")))
    check("normal : etat-source.json « source OK »", etat(s)["source_en_panne"] is False and etat(s)["bandeau_visible"] is False)

    # source vide -> sauvegarde
    ecrire_json(J, donnees({}))
    code, log = construire(s)
    h = lire(s)
    check("source vide : la sauvegarde est reprise (12 cartes) + avertissement daté", len(cartes(h)) == 12 and bandeau(h) and "depuis le 05/10/2026" in h)
    check("source vide : « échec » écrit dans le journal", "échec" in log)
    check("source vide : signalée en panne dans etat-source.json", etat(s)["source_en_panne"] is True)

    # JSON corrompu -> sauvegarde
    ecrire_json(J, '{"source": "HAICOP", "appels_offres": {"Tender-1": {"numero"')
    code, log = construire(s)
    h = lire(s)
    check("JSON corrompu : la sauvegarde est reprise, le site n'est pas vidé", len(cartes(h)) == 12 and bandeau(h))

    # chute brutale (2 fiches au lieu de 12) -> sauvegarde
    ecrire_json(J, donnees(NORMALES[:2]))
    code, log = construire(s)
    check("chute brutale (< 50 %) : données suspectes, sauvegarde gardée", len(cartes(lire(s))) == 12 and "suspectes" in log)

    # champs vides (format changé côté données) -> sauvegarde
    ecrire_json(J, donnees([fiche(105000 + k, objet="") for k in range(15)]))
    code, log = construire(s)
    check("champs vides partout : traité comme une panne, jamais « aucun appel d'offres »", len(cartes(lire(s))) == 12 and bandeau(lire(s)))

with copie_site() as s:
    J = os.path.join(s, "donnees", "appels-offres.json")
    ecrire_json(J, donnees(NORMALES))
    construire(s)
    avant = lire(s)
    os.remove(J.replace(".json", ".sauvegarde.json"))
    ecrire_json(J, "pas du JSON")
    code, log = construire(s)
    check("JSON corrompu SANS sauvegarde : site existant gardé tel quel (code 1)", code == 1 and lire(s) == avant)

with copie_site() as s:
    J = os.path.join(s, "donnees", "appels-offres.json")
    ecrire_json(J, donnees(NORMALES + [
        fiche(106001, limite="", pub=plus(JOUR, -2)),            # sans date limite, récente -> montrée
        fiche(106002, limite="", pub=plus(JOUR, -45)),           # sans date limite, ancienne -> masquée
        fiche(106003, limite=plus(JOUR, -1)),                    # expirée -> masquée
        fiche(106004, limite=JOUR),                              # se termine aujourd'hui -> montrée, urgente
        fiche(106005, limite="10/11/2026"),                      # date absurde -> traitée comme absente
        fiche(106006, objet='<script>alert("x")</script> Fourniture <b>pain</b>',
              lien="javascript:alert(1)", metier="Inconnu", gouvernorat="Atlantide"),
    ]))
    code, log = construire(s)
    h = lire(s)
    c = cartes(h)
    bloc = re.search(r'<article[^>]*id="Tender-106001".*?</article>', h, re.S)
    check("fiche sans date limite : affichée avec « non indiquée », pas en rouge",
          "Tender-106001" in c and bloc and "non indiquée" in bloc.group(0) and 'class="ao urgent"' not in bloc.group(0))
    check("fiche sans date limite publiée il y a 45 jours : masquée", "Tender-106002" not in c)
    check("appel d'offres expiré : masqué", "Tender-106003" not in c)
    check("date limite aujourd'hui : affiché, en rouge", re.search(r'<article class="ao urgent" id="Tender-106004"', h) is not None)
    check("date limite absurde : pas de plantage, carte « non indiquée »", "Tender-106005" in c)
    piege = re.search(r'<article[^>]*id="Tender-106006".*?</article>', h, re.S).group(0)
    check("texte piégé : balises échappées (aucun <script> injecté)", "<script>alert" not in h and "&lt;script&gt;" in piege)
    check("lien douteux : remplacé par le lien officiel HAICOP",
          'href="https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-106006"' in piege and "javascript:" not in h)
    check("métier / gouvernorat inconnus : rangés dans « Autres » / « National »", 'data-metier="autres"' in piege and 'data-gouv="national"' in piege)
    check("tri : la date limite la plus proche en premier", c[0] == "Tender-106004")

with copie_site() as s:
    J = os.path.join(s, "donnees", "appels-offres.json")
    liste = NORMALES[:5] + [dict(NORMALES[0], lu_le="2026-10-05 06:00", objet="Version plus récente"),
                            dict(NORMALES[1], numero="tender-104001")]
    ecrire_json(J, {"source": "HAICOP", "appels_offres": liste, "derniere_lecture_reussie": f"{JOUR} 06:00"})
    code, log = construire(s)
    c = cartes(lire(s))
    check("doublons (même numéro, casse différente) : une seule carte chacun", len(c) == 5 and len(set(c)) == 5)
    check("doublons : la version la plus récente est gardée", "Version plus récente" in lire(s))

with copie_site() as s:
    J = os.path.join(s, "donnees", "appels-offres.json")
    panne = {"etat": "panne", "depuis": f"{plus(JOUR, -1)} 06:00", "raison": "liste illisible"}
    ecrire_json(J, donnees(NORMALES, lecture=f"{plus(JOUR, -1)} 06:00", statut=panne, passage={"reussi": False}))
    code, log = construire(s)
    h, e = lire(s), etat(s)
    check("panne d'1 jour : site intact (12 cartes), pas encore de bandeau", len(cartes(h)) == 12 and not bandeau(h))
    check("panne d'1 jour : « en panne » dans etat-source.json (alerte GitHub) + « échec » au journal",
          e["source_en_panne"] is True and e["bandeau_visible"] is False and "échec" in log)

    panne = {"etat": "panne", "depuis": f"{plus(JOUR, -8)} 06:00", "raison": "format des fiches changé"}
    ecrire_json(J, donnees(NORMALES, lecture=f"{plus(JOUR, -8)} 06:00", statut=panne, passage={"reussi": False}))
    code, log = construire(s)
    h, e = lire(s), etat(s)
    check("panne de 8 jours : bandeau daté visible « depuis le 27/09/2026 »", bandeau(h) and "depuis le 27/09/2026" in h)
    check("panne de 8 jours : les appels d'offres encore ouverts restent affichés", len(cartes(h)) == 12)
    check("panne de 8 jours : etat-source.json (8 jours, bandeau, raison)",
          e["jours_sans_lecture"] == 8 and e["bandeau_visible"] is True and "format" in e["raison"])

    ecrire_json(J, donnees(NORMALES, statut={"etat": "ok", "depuis": f"{JOUR} 06:00", "raison": ""}, passage={"reussi": True}))
    code, log = construire(s)
    h, e = lire(s), etat(s)
    check("retour à la normale : bandeau retiré, source OK", not bandeau(h) and e["source_en_panne"] is False and code == 0)

# =========================================================== A. robot de lecture
print("\nA. Robot de lecture HAICOP (portail simulé)")
with open(os.path.join(ICI, "exemples", "fiche-Tender-104049.html"), encoding="utf-8") as f:
    FICHE = f.read()
GRANDE_PAGE_SANS_FICHE = "<html><body>" + "<div>Nouveau portail</div>" * 2000 + "</body></html>"


def portail(mode):
    """Faux réseau : renvoie (code HTTP, texte) comme R.telecharger."""
    def telecharger(url, json_attendu=False):
        if mode == "injoignable":
            return 503, ""
        if mode == "exception":
            raise OSError("délai dépassé")
        if json_attendu:
            if mode == "liste-vide":
                return 200, json.dumps({"data": []})
            return 200, json.dumps({"data": [{"id": f"Tender-{n}"} for n in (104052, 104051, 104050)]})
        tid = url.rsplit("/", 1)[1]
        if mode == "liste-vide":
            return 404, ""
        if mode == "format":
            return 200, GRANDE_PAGE_SANS_FICHE
        if mode == "format-champs":
            return 200, re.sub(r"<h5[^>]*>Objet</h5>", "<h6>Sujet</h6>", FICHE).replace(
                "Date limite de réception des offres", "Fin").replace("Acheteur public", "Organisme")
        return 200, FICHE.replace("Tender-104049", tid)
    return telecharger


def lancer_robot(dossier, mode):
    R.telecharger = portail(mode)
    R.PAUSE = 0
    R.DOSSIER_DONNEES = dossier
    R.FICHIER_JSON = os.path.join(dossier, "appels-offres.json")
    R.FICHIER_MD = os.path.join(dossier, "du-jour.md")
    sys.argv = ["lire_haicop.py", "--max", "3"]
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        code = R.main()
    with open(R.FICHIER_JSON, encoding="utf-8") as f:
        return code, json.load(f), sortie.getvalue()


tmp = tempfile.mkdtemp(prefix="ao-robot-")
try:
    ecrire_json(os.path.join(tmp, "appels-offres.json"), donnees(NORMALES))
    code, d, log = lancer_robot(tmp, "normal")
    check("robot normal : 3 fiches lues, source OK, code 0",
          code == 0 and len(d["appels_offres"]) == 15 and d["statut_source"]["etat"] == "ok")
    check("robot normal : la fiche d'exemple est bien comprise (objet, date limite, caution, Nabeul)",
          d["appels_offres"]["Tender-104052"]["date_limite"] == "2026-11-10"
          and d["appels_offres"]["Tender-104052"]["cautionnement_total_dt"] == 17000
          and d["appels_offres"]["Tender-104052"]["gouvernorat"] == "Nabeul")

    ecrire_json(os.path.join(tmp, "appels-offres.json"), donnees(NORMALES))
    code, d, log = lancer_robot(tmp, "injoignable")
    depuis = d["statut_source"].get("depuis")
    check("source injoignable : panne enregistrée, anciennes fiches gardées, code 1",
          code == 1 and d["statut_source"]["etat"] == "panne" and len(d["appels_offres"]) == 12 and "échec" in log)
    check("source injoignable : la date de dernière lecture réussie n'avance pas",
          d["derniere_lecture_reussie"] == f"{JOUR} 06:00")

    d["statut_source"]["depuis"] = "2026-09-27 06:00"     # la panne dure depuis 8 jours
    ecrire_json(os.path.join(tmp, "appels-offres.json"), d)
    code, d, log = lancer_robot(tmp, "exception")
    check("panne qui dure (erreurs réseau) : date « depuis » conservée (27/09)",
          d["statut_source"]["etat"] == "panne" and d["statut_source"]["depuis"] == "2026-09-27 06:00")

    ecrire_json(os.path.join(tmp, "appels-offres.json"), donnees(NORMALES))
    code, d, log = lancer_robot(tmp, "liste-vide")
    check("liste vide (< 30 % du volume) et rien derrière : panne, pas « aucun appel d'offres »",
          code == 1 and d["statut_source"]["etat"] == "panne" and len(d["appels_offres"]) == 12)

    ecrire_json(os.path.join(tmp, "appels-offres.json"), donnees(NORMALES))
    code, d, log = lancer_robot(tmp, "format")
    check("format du portail changé (page sans fiche) : panne « format », rien d'ajouté",
          code == 1 and "format" in d["statut_source"]["raison"] and len(d["appels_offres"]) == 12)

    ecrire_json(os.path.join(tmp, "appels-offres.json"), donnees(NORMALES))
    code, d, log = lancer_robot(tmp, "format-champs")
    check("format changé (champs introuvables) : panne « format », aucune fiche vide enregistrée",
          code == 1 and "format" in d["statut_source"]["raison"] and len(d["appels_offres"]) == 12)

    code, d, log = lancer_robot(tmp, "normal")
    check("retour à la normale : source OK, fiches ajoutées, dernière lecture mise à jour",
          code == 0 and d["statut_source"]["etat"] == "ok" and len(d["appels_offres"]) == 15
          and d["derniere_lecture_reussie"] != f"{JOUR} 06:00")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{total - erreurs}/{total} scénarios réussis" + (f" — {erreurs} ÉCHEC(S) : ne pas publier." if erreurs else " — tout est bon."))
sys.exit(1 if erreurs else 0)
