# -*- coding: utf-8 -*-
"""
Alerte quotidienne sur le canal Telegram : UN message court groupé
  - « Nouveaux appels d'offres » du jour, par métier (lien vers la page du site + fiche officielle HAICOP) ;
  - « ⏰ Clôturent dans 2 jours ».
Découpé en plusieurs messages si le texte dépasse la limite de Telegram (4096 caractères).

Ne fait RIEN (et ne sonne pas en échec) si les secrets TELEGRAM_BOT_TOKEN et TELEGRAM_CANAL n'existent pas.
Ne renvoie JAMAIS deux fois le même appel d'offres : mémoire dans donnees/telegram-envoyes.json
(seuls les messages vraiment partis sont notés ; en cas d'erreur, ils repartiront au passage suivant).

    TELEGRAM_BOT_TOKEN=… TELEGRAM_CANAL=@moncanal python robot/telegram.py
    python robot/telegram.py --essai          (affiche le message sans rien envoyer)
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import construire_site as C   # noqa: E402  (métiers, gouvernorats, adresse du site, nettoyage des données)
import glossaire              # noqa: E402

DONNEES = os.path.join(os.path.dirname(ICI), "donnees")
LIMITE = 4096          # limite de Telegram pour un message
MARGE = 3900           # on coupe avant, par prudence
FRAIS_JOURS = 3        # au premier passage : seuls les appels d'offres publiés ces 3 derniers jours sont « nouveaux »
OUBLI_JOURS = 150      # la mémoire oublie les numéros plus vieux que 150 jours
RAPPEL_JOURS = 2

H = lambda t: html.escape(str(t or ""), quote=False)   # liens déjà vérifiés par construire_site.charger()


def court(t, n=110):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"


def dfr(d):
    return f"{d[8:10]}/{d[5:7]}" if d else "?"


def charger_memoire(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            m = json.load(f)
        if isinstance(m.get("envoyes"), dict) and isinstance(m.get("rappels"), dict):
            return m
    except (OSError, ValueError, AttributeError):
        pass
    return {"envoyes": {}, "rappels": {}}


def sauver_memoire(chemin, m, jour):
    oubli = (dt.date.fromisoformat(jour) - dt.timedelta(days=OUBLI_JOURS)).isoformat()
    for k in ("envoyes", "rappels"):
        m[k] = {t: d for t, d in m[k].items() if d >= oubli}
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, chemin)


def ligne_ao(a, avec_resume=True):
    m = C.M_PAR_NOM[a["metier"]]
    g = C.G_PAR_NOM[a["gouvernorat"]]
    page = f"{C.URL_SITE}metier/{m[1]}/#{a['numero']}"
    lignes = [f"• {H(court(a['objet']))}"]
    r = glossaire.resumer(a["objet"]) if avec_resume else None
    if r and r["langue"] == "fr":
        lignes.append(f"  <i>≈ {H(r['texte'])}</i>")
    lignes.append(f"  📍 {H(g[0])} · ⏳ {dfr(a['date_limite'])} · <a href=\"{H(page)}\">Site</a> · "
                  f"<a href=\"{H(a['lien'])}\">Fiche officielle</a>")
    return "\n".join(lignes)


def preparer(aos, memoire, jour):
    """Renvoie la liste des blocs [(texte, [numéros nouveaux], [numéros rappel])] et les numéros oubliés d'office."""
    ouverts = C.ouvertes(aos, jour)
    frais = (dt.date.fromisoformat(jour) - dt.timedelta(days=FRAIS_JOURS)).isoformat()
    nouveaux, anciens = [], []
    for a in ouverts:
        if a["numero"] in memoire["envoyes"]:
            continue
        (nouveaux if (a["date_publication"] or jour) >= frais else anciens).append(a)
    cible = (dt.date.fromisoformat(jour) + dt.timedelta(days=RAPPEL_JOURS)).isoformat()
    rappels = [a for a in ouverts if a["date_limite"] == cible and a["numero"] not in memoire["rappels"]]
    blocs = []
    if nouveaux:
        blocs.append((f"📢 <b>Nouveaux appels d'offres — {dfr(jour)}/{jour[:4]}</b> ({len(nouveaux)})", [], []))
        ordre = [m[0] for m in C.METIERS]
        for nom in ordre:
            sel = sorted((a for a in nouveaux if a["metier"] == nom), key=lambda a: (a["date_limite"] or "9999", a["numero"]))
            if not sel:
                continue
            blocs.append((f"\n<b>{H(C.M_PAR_NOM[nom][2])}</b> ({len(sel)})", [], []))
            for a in sel:
                blocs.append((ligne_ao(a), [a["numero"]], []))
    if rappels:
        blocs.append((f"\n⏰ <b>Clôturent dans 2 jours</b> ({len(rappels)})", [], []))
        for a in sorted(rappels, key=lambda a: a["numero"]):
            blocs.append((ligne_ao(a, avec_resume=False), [], [a["numero"]]))
    if blocs:
        blocs.append((f"\nSource : HAICOP. Seule la fiche officielle fait foi. Tous les appels d'offres : {C.URL_SITE}", [], []))
    return blocs, [a["numero"] for a in anciens]


def decouper(blocs, marge=MARGE):
    """Regroupe les blocs en messages de moins de `marge` caractères (un bloc n'est jamais coupé en deux)."""
    messages, texte, ids, rap = [], "", [], []
    for t, n, r in blocs:
        if len(t) > marge:
            t = t[:marge - 1] + "…"
        if texte and len(texte) + 1 + len(t) > marge:
            messages.append((texte, ids, rap))
            texte, ids, rap = "", [], []
        texte = (texte + "\n" + t) if texte else t.lstrip("\n")
        ids, rap = ids + n, rap + r
    if texte:
        messages.append((texte, ids, rap))
    return messages


def envoyer(jeton, canal, texte):
    """Envoie un message ; renvoie (True, "") ou (False, raison). Remplacée par une fausse fonction dans les tests."""
    donnees = urllib.parse.urlencode({"chat_id": canal, "text": texte, "parse_mode": "HTML",
                                      "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{jeton}/sendMessage", data=donnees)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            rep = json.loads(r.read().decode("utf-8", errors="replace"))
            return (True, "") if rep.get("ok") else (False, str(rep.get("description"))[:200])
    except urllib.error.HTTPError as e:
        try:
            return False, f"code {e.code} : " + str(json.loads(e.read().decode()).get("description"))[:200]
        except Exception:
            return False, f"code {e.code}"
    except Exception as e:   # réseau coupé, délai…
        return False, str(e)[:200]


def main(argv=None):
    p = argparse.ArgumentParser(description="Alerte quotidienne Telegram.")
    p.add_argument("--donnees", default=os.path.join(DONNEES, "appels-offres.json"))
    p.add_argument("--memoire", default=os.path.join(DONNEES, "telegram-envoyes.json"))
    p.add_argument("--aujourdhui", default=dt.date.today().isoformat())
    p.add_argument("--essai", action="store_true", help="affiche le message sans l'envoyer")
    a = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    jeton = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    canal = os.environ.get("TELEGRAM_CANAL", "").strip()
    print("Alerte Telegram…")
    if not a.essai and not (jeton and canal):
        print("  Telegram pas encore configuré (secrets TELEGRAM_BOT_TOKEN / TELEGRAM_CANAL absents) : rien envoyé")
        return 0
    _, aos = C.charger(a.donnees)
    if not aos:
        print("  ! échec : données illisibles : rien envoyé")
        return 0
    memoire = charger_memoire(a.memoire)
    blocs, anciens = preparer(aos, memoire, a.aujourdhui)
    messages = decouper(blocs)
    if a.essai:
        for t, _, _ in messages:
            print(t, "\n" + "-" * 40)
        print(f"  (essai) {len(messages)} message(s), rien envoyé")
        return 0
    for t in anciens:                       # trop anciens pour être annoncés : notés sans envoi
        memoire["envoyes"][t] = a.aujourdhui
    envoyes = 0
    for texte, ids, rap in messages:
        ok, raison = envoyer(jeton, canal, texte)
        if not ok:
            print(f"  ! échec : Telegram a refusé le message ({raison}) — il repartira au prochain passage")
            break
        envoyes += 1
        for t in ids:
            memoire["envoyes"][t] = a.aujourdhui
        for t in rap:
            memoire["rappels"][t] = a.aujourdhui
    sauver_memoire(a.memoire, memoire, a.aujourdhui)
    print(f"  {envoyes}/{len(messages)} message(s) envoyé(s)" if messages else "  rien de nouveau aujourd'hui : aucun message")
    return 0


if __name__ == "__main__":
    sys.exit(main())
