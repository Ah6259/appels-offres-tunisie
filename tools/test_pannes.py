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
    # ventes aux enchères lues normalement (sinon leur avertissement se mêlerait aux scénarios HAICOP)
    ecrire_json(os.path.join(dest, "donnees", "encheres.json"),
                {"ventes": {}, "derniere_lecture_reussie": f"{JOUR} 06:00", "statut_source": {"etat": "ok"}})
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

# =========================================================== C. glossaire (résumé traduit)
print("\nC. Résumé traduit (glossaire maison, vrais objets)")
import glossaire as G  # noqa: E402

check(f"glossaire : au moins 150 entrées arabe -> français ({G.NB_ENTREES}) et 150 français -> arabe ({len(G.GLOSSAIRE_FR)})",
      G.NB_ENTREES >= 150 and len(G.GLOSSAIRE_AR) >= 150 and len(G.GLOSSAIRE_FR) >= 150)
r = G.resumer("مشروع تهيئة مركز رعاية المسنين بقرمبالية")
check("« مشروع تهيئة مركز رعاية المسنين بقرمبالية » -> « Aménagement — centre pour personnes âgées — Grombalia »",
      r and r["langue"] == "fr" and r["texte"] == "Aménagement — centre pour personnes âgées — Grombalia")
r = G.resumer("Travaux d'entretien d'étanchéité Complexe Culturel à Carthage Dermech")
check("français -> arabe : « Travaux d'entretien… Carthage » -> résumé arabe avec أشغال, صيانة, قرطاج",
      r and r["langue"] == "ar" and all(m in r["texte"] for m in ("أشغال", "صيانة", "قرطاج")))
check("jamais inventer : texte inconnu (latin ou arabe) -> rien",
      G.resumer("Lorem ipsum dolor sit amet consectetur adipiscing") is None and G.resumer("كلام غامض جدا هنا بلا معنى واضح") is None
      and G.resumer("") is None)
with open(os.path.join(SITE, "donnees", "appels-offres.json"), encoding="utf-8") as f:
    VRAIS = list(json.load(f)["appels_offres"].values())
rare = next((a["objet"] for a in VRAIS if a["numero"] == "Tender-104043"), "")
check("moins de la moitié des mots reconnus -> rien (vrai objet long et rare, Tender-104043)", bool(rare) and G.resumer(rare) is None)


def compose(phrase, connus):
    """Vrai si la phrase est une suite de textes du glossaire (rien d'inventé)."""
    mots = phrase.split(" ")
    ok = [True] + [False] * len(mots)
    for i in range(1, len(mots) + 1):
        # « و » (et) peut être collé devant un mot arabe du glossaire
        ok[i] = any(ok[j] and (" ".join(mots[j:i]) in connus or (mots[j].startswith("و") and " ".join([mots[j][1:]] + mots[j + 1:i]) in connus))
                    for j in range(i))
    return ok[-1]
affichables = G.mots_affichables()
ok_vrais, n_res = True, 0
for a in VRAIS:
    r = G.resumer(a["objet"])
    if not r:
        continue
    n_res += 1
    morceaux = [m.strip(" …") for m in re.split(r" — |, |، | et ", r["texte"]) if m.strip(" …")]
    if r["taux"] < 0.5 or not all(compose(m, affichables) or compose(m[:1].lower() + m[1:], affichables) for m in morceaux):
        ok_vrais = False
        print("   inventé ou trop peu reconnu :", a["numero"], r)
check(f"vrais objets : {n_res}/{len(VRAIS)} résumés, chacun ≥ 50 % de mots reconnus et fait UNIQUEMENT de mots du glossaire",
      ok_vrais and n_res >= len(VRAIS) // 2)

# =========================================================== D. Telegram
print("\nD. Alerte Telegram (Telegram simulé, rien n'est envoyé)")
import telegram as TG  # noqa: E402


def lancer_telegram(dossier, aos, jour=JOUR, secrets=True, reponse=(True, "")):
    envois = []

    def faux(jeton, canal, texte):
        envois.append(texte)
        return reponse(texte) if callable(reponse) else reponse
    TG.envoyer = faux
    ecrire_json(os.path.join(dossier, "ao.json"), donnees(aos))
    ancien = {k: os.environ.pop(k, None) for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CANAL")}
    if secrets:
        os.environ.update({"TELEGRAM_BOT_TOKEN": "123:faux", "TELEGRAM_CANAL": "@essai"})
    sortie = io.StringIO()
    try:
        with contextlib.redirect_stdout(sortie):
            code = TG.main(["--donnees", os.path.join(dossier, "ao.json"), "--memoire", os.path.join(dossier, "mem.json"),
                            "--aujourdhui", jour])
    finally:
        for k, v in ancien.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
    mem = json.load(open(os.path.join(dossier, "mem.json"), encoding="utf-8")) if os.path.exists(os.path.join(dossier, "mem.json")) else None
    return code, envois, mem, sortie.getvalue()


tmp = tempfile.mkdtemp(prefix="ao-telegram-")
try:
    du_jour = [fiche(107000 + k, pub=JOUR, limite=plus(JOUR, 20 + k)) for k in range(3)] + \
              [fiche(107010, objet="مشروع تهيئة مركز رعاية المسنين بقرمبالية", pub=plus(JOUR, -1), limite=plus(JOUR, 30),
                     metier="Études / conseil", gouv="Nabeul")]
    j2 = fiche(107020, objet="Acquisition de matériel informatique", pub=plus(JOUR, -9), limite=plus(JOUR, 2), metier="Informatique")
    vieux = fiche(107030, pub=plus(JOUR, -20), limite=plus(JOUR, 15))
    tous = du_jour + [j2, vieux]
    code, envois, mem, log = lancer_telegram(tmp, tous, secrets=False)
    check("Telegram absent (pas de secrets) : rien envoyé, pas d'échec (code 0), pas de mémoire",
          code == 0 and not envois and mem is None and "pas encore configuré" in log)
    code, envois, mem, log = lancer_telegram(tmp, tous)
    msg = "\n".join(envois)
    check("Telegram : UN message groupé par métier (titres en gras), lien vers la page du site ET la fiche officielle",
          code == 0 and len(envois) == 1 and "<b>BTP / génie civil</b> (3)" in msg and "<b>Études / conseil</b> (1)" in msg
          and "https://ah6259.github.io/appels-offres-tunisie/metier/btp-genie-civil/#Tender-107000" in msg
          and "https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-107000" in msg)
    check("Telegram : résumé traduit des objets arabes dans le message", "≈ Aménagement — centre pour personnes âgées — Grombalia" in msg)
    check("Telegram : rubrique « ⏰ Clôturent dans 2 jours » avec l'appel d'offres J-2",
          "⏰ <b>Clôturent dans 2 jours</b>" in msg and msg.split("Clôturent dans 2 jours")[1].count("Tender-107020") >= 1)
    check("Telegram : appel d'offres trop ancien pour être « nouveau » (20 jours) : pas annoncé, mais noté",
          "Tender-107030" not in msg and "Tender-107030" in mem["envoyes"])
    code, envois, mem, log = lancer_telegram(tmp, tous)
    check("Telegram : 2e passage le même jour -> rien n'est renvoyé (mémoire)", code == 0 and not envois and "rien de nouveau" in log)
    nouveau = fiche(107040, pub=JOUR, limite=plus(JOUR, 25))
    code, envois, mem, log = lancer_telegram(tmp, tous + [nouveau], reponse=(False, "Bad Request: chat not found"))
    check("Telegram en erreur : pas d'échec du robot (code 0), « échec » au journal, appel d'offres PAS noté comme envoyé",
          code == 0 and len(envois) == 1 and "échec" in log and "Tender-107040" not in mem["envoyes"])
    code, envois, mem, log = lancer_telegram(tmp, tous + [nouveau])
    check("Telegram revenu : l'appel d'offres manqué part au passage suivant, une seule fois",
          len(envois) == 1 and "Tender-107040" in envois[0] and "Tender-107000" not in envois[0] and "Tender-107040" in mem["envoyes"])
    shutil.rmtree(tmp); os.makedirs(tmp)
    longs = [fiche(108000 + k, objet="Travaux d'aménagement et de construction " + "d'un bâtiment administratif régional " * 3,
                   pub=JOUR, limite=plus(JOUR, 20)) for k in range(70)]
    code, envois, mem, log = lancer_telegram(tmp, longs)
    tous_ids = re.findall(r"#(Tender-\d+)", "\n".join(envois))
    check(f"Telegram : message trop long découpé ({len(envois)} messages, chacun < 4096 caractères, chaque appel d'offres une seule fois)",
          len(envois) >= 2 and all(len(t) < 4096 for t in envois) and sorted(tous_ids) == sorted(a["numero"] for a in longs))
    shutil.rmtree(tmp); os.makedirs(tmp)
    code, envois, mem, log = lancer_telegram(tmp, longs, reponse=lambda t: (False, "Too Many Requests") if "Tender-1080" + "69" in t else (True, ""))
    partis = set(re.findall(r"#(Tender-\d+)", "\n".join(envois[:-1])))
    check("Telegram : erreur au milieu -> seuls les messages partis sont notés", set(mem["envoyes"]) == partis and "échec" in log)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# =========================================================== E. Entreprises privées (Google Forms -> CSV)
print("\nE. Publications des entreprises privées (CSV simulé)")
ENTETE = ["Horodateur", "Nom de l'entreprise", "Objet de l'appel d'offres", "Description (facultatif)", "Métier",
          "Gouvernorat", "Date limite de réception des offres", "Contact pour les candidats (e-mail ou téléphone de l'entreprise)",
          "Je certifie que ces informations sont exactes et j'accepte leur publication"]


def ligne_csv(entreprise="Société Alpha Bâtiment", objet="Construction d'un dépôt de stockage à Sfax", desc="Lot unique.",
              metier="BTP / génie civil", gouv="Sfax", limite="20/10/2026", contact="contact@alpha-batiment.tn",
              heure="05/10/2026 08:00:00", cert="Oui"):
    return [heure, entreprise, objet, desc, metier, gouv, limite, contact, cert]


def csv_texte(lignes, entete=ENTETE):
    import csv as _csv
    s = io.StringIO()
    w = _csv.writer(s)
    w.writerow(entete)
    for l in lignes:
        w.writerow(l)
    return s.getvalue()


def lancer_prives(site, contenu=None, jour=JOUR):
    args = [sys.executable, os.path.join(site, "robot", "prives.py"), "--aujourdhui", jour]
    if contenu is not None:
        chemin = os.path.join(site, "reponses.csv")
        with open(chemin, "w", encoding="utf-8", newline="") as f:
            f.write(contenu)
        args += ["--csv", chemin]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    p = os.path.join(site, "donnees", "prives.json")
    return r.returncode, (json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None), r.stdout + r.stderr


with copie_site() as s:
    ecrire_json(os.path.join(s, "donnees", "appels-offres.json"), donnees(NORMALES))
    code, d, log = lancer_prives(s)
    check("formulaire pas encore configuré (CSV vide dans reglages.py) : rien à faire, code 0", code == 0 and d is None and "pas encore configuré" in log)
    bonnes = [ligne_csv(), ligne_csv(entreprise="شركة النور للخدمات", objet="اقتناء مواد تنظيف لفائدة المصنع بصفاقس", metier="Nettoyage / gardiennage",
                                     gouv="Sfax", contact="+216 74 000 000", limite="2026-10-25")]
    mauvaises = [
        ligne_csv(entreprise="Promo", objet="Construction rapide visitez www.exemple-promo.com maintenant"),          # lien
        ligne_csv(entreprise="Beta", objet="Fourniture de câbles <script>alert(1)</script> divers"),                  # HTML
        ligne_csv(entreprise="Gamma", objet="Gagnez au casino en ligne avec notre offre spéciale"),                  # spam
        ligne_csv(entreprise="Delta", objet="Construction d'un hangar métallique à Gabès", limite="01/10/2026"),     # date passée
        ligne_csv(entreprise="", objet="Construction d'un hangar métallique à Gabès"),                               # champ vide
        ligne_csv(),                                                                                                  # doublon
        ligne_csv(entreprise="Epsilon", objet="Achat " + "de matériel " * 40),                                       # trop long
        ligne_csv(entreprise="Zeta", objet="Fourniture de pièces de rechange pour engins", contact="appelez-moi"),   # contact
        ligne_csv(entreprise="Eta", objet="Fourniture de pièces de rechange pour engins", metier="Astrologie"),      # métier inconnu
        ligne_csv(entreprise="Theta", objet="Fourniture de pièces de rechange pour camions", cert=""),              # non certifié
        ligne_csv(entreprise="Iota", objet="Fourniture de pièces de rechange pour bus", limite="2027-12-31"),       # trop lointaine
    ]
    code, d, log = lancer_prives(s, csv_texte(bonnes + mauvaises))
    raisons = " | ".join(r["raison"] for r in d["refuses"])
    check(f"CSV normal : 2 publiées, {len(mauvaises)} refusées (lien, HTML, spam, date passée, champ vide, doublon, trop long, contact, métier, certification, date lointaine)",
          code == 0 and len(d["publies"]) == 2 and len(d["refuses"]) == len(mauvaises)
          and all(x in raisons for x in ("lien", "HTML", "publicité", "passée", "obligatoire", "doublon", "trop long", "contact", "inconnu", "lointaine")))
    brut = json.dumps(d, ensure_ascii=False)
    check("refusées : leur contenu n'est jamais enregistré (seulement la raison)", "exemple-promo" not in brut and "casino" not in brut and "<script" not in brut)
    code_b, log_b = construire(s)
    h = lire(s)
    check("site : les 2 publications sur l'accueil et la page « Publier », mention « non vérifié par HAICOP », métier/gouvernorat corrects",
          h.count('class="ao prive"') == 2 and h.count("non vérifié par HAICOP") >= 2 and 'data-metier="nettoyage-gardiennage" data-gouv="sfax"' in h
          and lire(s, "publier/index.html").count('class="ao prive"') == 2)
    check("site : publications privées hors des listes officielles HAICOP (pas dans #liste)",
          "Prive-" not in h.split('<div class="liste" id="liste">')[1].split('<button type="button" class="plus"')[0])
    avant = d["publies"]
    code, d, log = lancer_prives(s, "")
    check("CSV vide : panne, publications déjà acceptées gardées, « échec » au journal", code == 1 and d["publies"] == avant and "échec" in log)
    code, d, log = lancer_prives(s, "<!DOCTYPE html><html><body>Connexion Google</body></html>")
    check("CSV corrompu (page HTML reçue) : publications gardées", code == 1 and d["publies"] == avant and d["statut"]["etat"] == "panne")
    code, d, log = lancer_prives(s, csv_texte(bonnes, entete=["A", "B", "C"]))
    check("CSV avec colonnes inconnues (formulaire modifié) : publications gardées, raison « colonnes »",
          code == 1 and d["publies"] == avant and "colonnes" in d["statut"]["raison"])
    code, d, log = lancer_prives(s, csv_texte([]))
    check("CSV avec seulement les titres (aucune réponse) : liste vide acceptée (ligne supprimée par Ahmed = retirée)", code == 0 and d["publies"] == [])
    lancer_prives(s, csv_texte(bonnes))
    construire(s, jour="2026-10-21")
    check("publication dont la date limite est passée : retirée du site", lire(s).count('class="ao prive"') == 1)

# =========================================================== F. Ventes aux enchères (Douane)
print("\nF. Ventes aux enchères (page de la Douane simulée)")
import lire_douane as D  # noqa: E402


def page_douane(lignes, entete=True):
    tete = ('<thead><tr class="row-1"><th class="column-1">Date publication</th><th class="column-2">Recette des Douanes</th>'
            '<th class="column-3">Objet</th><th class="column-4">Échéance</th><th class="column-5">PDF</th>'
            '<th class="column-6">Informations complémentaires</th></tr></thead>') if entete else ""
    corps = "".join(
        f'<tr class="row-{k + 2}"><td class="column-1"><strong>{p}</strong></td><td class="column-2">{b}</td><td class="column-3">{o}</td>'
        f'<td class="column-4">{e}</td><td class="column-5"><a href="{lien}" target="_blank">PDF</a></td>'
        f'<td class="column-6">{c}</td></tr>' for k, (p, b, o, e, lien, c) in enumerate(lignes))
    return f'<html><body><table id="tablepress-14" class="tablepress tablepress-id-14">{tete}<tbody>{corps}</tbody></table></body></html>'


def vente(n, limite=plus(JOUR, 10), bureau="Bureau régional des douanes de Zaghouan", lien=None, cahier=""):
    return (dfr_(plus(JOUR, -3)), bureau, f"Avis de vente aux enchères sous plis fermés N°{n:02d}/2026 de diverses marchandises.", limite,
            lien or f"https://www.douane.gov.tn/wp-content/uploads/2026/10/avis-{n}.pdf", cahier)


def dfr_(d):
    return f"{d[8:10]}-{d[5:7]}-{d[0:4]}"


def lancer_douane(dossier, mode, lignes=None):
    def tel(url):
        if mode == "injoignable":
            return 503, ""
        if mode == "exception":
            raise OSError("délai dépassé")
        if mode == "format":
            return 200, "<html><body>" + "<div>Nouveau portail de la douane</div>" * 500 + "</body></html>"
        return 200, page_douane(lignes)
    D.telecharger = tel
    D.FICHIER = os.path.join(dossier, "encheres.json")
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        code = D.main()
    return code, json.load(open(D.FICHIER, encoding="utf-8")), sortie.getvalue()


with copie_site() as s:
    dd = os.path.join(s, "donnees")
    ecrire_json(os.path.join(dd, "appels-offres.json"), donnees(NORMALES))
    lignes = [vente(k) for k in range(1, 10)] + [
        vente(20, limite=plus(JOUR, 3) + "    13 h00", bureau="Bureau frontalier des douanes de Dehiba",
              cahier='<p><a href="https://www.douane.gov.tn/wp-content/uploads/2026/10/avis-20_cahier.pdf">Télécharger Cahier des charges</a></p>'),
        vente(21, limite=plus(JOUR, -5)),                                                  # expirée
        vente(22, lien="javascript:alert(1)"),                                             # lien douteux
        vente(23, limite="Date de la vente : " + plus(JOUR, 6)),
    ]
    code, d, log = lancer_douane(dd, "normal", lignes)
    v = {x["objet"][:52][-8:]: x for x in d["ventes"].values()}
    v20 = next(x for x in d["ventes"].values() if "N°20/" in x["objet"])
    check("enchères : lecture normale (13 lignes), source OK, code 0", code == 0 and d["lignes_lues"] == 13 and d["statut_source"]["etat"] == "ok")
    check("enchères : échéance + heure « 13 h00 », bureau de Dehiba rangé à Tataouine, cahier des charges gardé",
          v20["date_limite"] == plus(JOUR, 3) and v20["heure"] == "13:00" and v20["gouvernorat"] == "Tataouine" and v20["lien_cahier"].endswith("_cahier.pdf"))
    v22 = next(x for x in d["ventes"].values() if "N°22/" in x["objet"])
    check("enchères : lien douteux remplacé par la page officielle de la Douane", v22["lien_avis"] == D.URL)
    check("enchères : « Date de la vente : … » comprise", any("N°23/" in x["objet"] and x["date_limite"] == plus(JOUR, 6) for x in d["ventes"].values()))
    construire(s)
    h = lire(s, "encheres/index.html")
    c = re.findall(r'<article class="ao enchere[^"]*" id="(Vente-[0-9a-f]+)"', h)
    check("page enchères : 12 ventes ouvertes, l'expirée masquée, aucun lien javascript:, pas d'avertissement",
          len(c) == 12 and "javascript:" not in h and not bandeau(h) and "N°21/" not in h)
    avant = d["ventes"]
    code, d, log = lancer_douane(dd, "format")
    check("enchères : format de la page changé -> panne « format », anciennes ventes gardées, code 1",
          code == 1 and "format" in d["statut_source"]["raison"] and d["ventes"] == avant and "échec" in log)
    depuis = d["statut_source"]["depuis"]
    code, d, log = lancer_douane(dd, "injoignable")
    check("enchères : page injoignable (503) -> panne, date « depuis » conservée", code == 1 and d["statut_source"]["depuis"] == depuis and d["ventes"] == avant)
    code, d, log = lancer_douane(dd, "exception")
    check("enchères : erreur réseau -> panne, pas de plantage", code == 1 and d["statut_source"]["etat"] == "panne")
    code, d, log = lancer_douane(dd, "normal", lignes[:2])
    check("enchères : chute brutale (2 lignes au lieu de 13) -> panne, rien perdu", code == 1 and "lignes" in d["statut_source"]["raison"] and d["ventes"] == avant)
    d["derniere_lecture_reussie"] = f"{plus(JOUR, -4)} 06:00"
    ecrire_json(os.path.join(dd, "encheres.json"), d)
    construire(s)
    check("enchères : dernière lecture il y a 4 jours -> bandeau daté sur la page enchères (ventes ouvertes gardées)",
          bandeau(lire(s, "encheres/index.html")) and "depuis le 01/10/2026" in lire(s, "encheres/index.html"))
    code, d, log = lancer_douane(dd, "normal", lignes)
    check("enchères : retour à la normale", code == 0 and d["statut_source"]["etat"] == "ok")

# =========================================================== G. Réglages (canal Telegram, formulaire) et photos
print("\nG. Réglages d'Ahmed (un seul fichier) et preuves des photos")


def avec_reglages(site, **valeurs):
    p = os.path.join(site, "robot", "reglages.py")
    t = open(p, encoding="utf-8").read()
    for k, v in valeurs.items():
        t = re.sub(rf'^{k} = ".*"$', f'{k} = "{v}"', t, flags=re.M)
    open(p, "w", encoding="utf-8").write(t)


with copie_site() as s:
    ecrire_json(os.path.join(s, "donnees", "appels-offres.json"), donnees(NORMALES))
    construire(s)
    check("canal Telegram non réglé : aucun bouton Telegram sur le site", "btn-telegram" not in lire(s) and "t.me/" not in lire(s))
    avec_reglages(s, TELEGRAM_CANAL_URL="https://t.me/alertesao_essai", FORMULAIRE_PRIVES_URL="https://forms.gle/Essai1234")
    code, log = construire(s)
    check("canal Telegram réglé : bouton « Recevoir les alertes sur Telegram » vers le canal",
          'class="btn-alerte btn-telegram" href="https://t.me/alertesao_essai"' in lire(s) and "Recevoir les alertes sur Telegram" in lire(s))
    check("formulaire réglé : bouton vers Google Forms sur la page « Publier »", 'href="https://forms.gle/Essai1234"' in lire(s, "publier/index.html")
          and "Bientôt" not in lire(s, "publier/index.html").split('id="btn-publier"')[0][-200:])
    avec_reglages(s, TELEGRAM_CANAL_URL='javascript:alert(1)', FORMULAIRE_PRIVES_URL="http://pirate.example/form")
    code, log = construire(s)
    check("réglage mal écrit (javascript:, adresse non Google) : ignoré, bouton caché, « échec » au journal",
          "btn-telegram" not in lire(s) and "javascript:" not in lire(s) and "pirate.example" not in lire(s, "publier/index.html") and "échec" in log)
    # Alertes Pro : nom du robot Telegram des abonnés (TELEGRAM_ROBOT_ALERTES)
    avec_reglages(s, TELEGRAM_ROBOT_ALERTES="AlertesAOEssaiBot")
    code, log = construire(s)
    ab = lire(s, "abonnement/index.html")
    check("Alertes Pro : robot réglé -> lien t.me/AlertesAOEssaiBot + « /start » sur la page abonnement (pas sur l'accueil)",
          'href="https://t.me/AlertesAOEssaiBot"' in ab and "/start" in ab and "t.me/" not in lire(s))
    avec_reglages(s, TELEGRAM_ROBOT_ALERTES="javascript:alert(1)")
    code, log = construire(s)
    ab = lire(s, "abonnement/index.html")
    check("Alertes Pro : nom de robot mal écrit -> ignoré, « le lien Telegram vous est envoyé à l'activation », « échec » au journal",
          "javascript:" not in ab and "t.me/" not in ab and "envoyé à l'activation" in ab and "échec" in log)

import construire_site as CS  # noqa: E402
PREUVES = os.path.join(os.path.dirname(SITE), "preuves conditions d'utilisation")
for ph in CS.PHOTOS:
    check(f"photo {ph['fichier']} : fichier présent, auteur + licence + source renseignés",
          os.path.exists(os.path.join(SITE, ph["fichier"])) and ph["auteur"] and ph["licence"].startswith("CC")
          and ph["source_url"].startswith("https://commons.wikimedia.org/"))
    if os.path.isdir(PREUVES):
        dossier = os.path.join(PREUVES, ph["preuve"])
        lisez = os.path.join(dossier, "LISEZ-MOI.md")
        texte_l = open(lisez, encoding="utf-8").read() if os.path.exists(lisez) else ""
        check(f"photo {ph['fichier']} : preuve de licence sauvegardée (LISEZ-MOI avec auteur/licence/adresse, page HTML, SHA-256)",
              ph["auteur"] in texte_l and ph["licence"] in texte_l and ph["source_url"] in texte_l
              and os.path.exists(os.path.join(dossier, "empreintes-sha256.txt"))
              and any(f.endswith(".html") for f in os.listdir(dossier)))
    else:
        print(f"   (preuves hors dépôt absentes sur cette machine : vérification sautée pour {ph['fichier']})")

print(f"\n{total - erreurs}/{total} scénarios réussis" + (f" — {erreurs} ÉCHEC(S) : ne pas publier." if erreurs else " — tout est bon."))
sys.exit(1 if erreurs else 0)
