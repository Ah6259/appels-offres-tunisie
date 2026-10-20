# -*- coding: utf-8 -*-
"""VISITEUR SIMULÉ commun à tous les sites d'Ahmed (règle générale du 18/10/2026 : « le visiteur simulé doit signaler les problèmes
AVANT le visiteur réel, sur tous les sites »). Copie identique dans chaque dépôt (tools/visiteur_simule.py + tools/visiteur_simule.html).

1. Sans navigateur, sur TOUTES les pages du site : liens et images internes morts (fichier absent).
2. Dans un vrai navigateur (Chromium sans écran), téléphone de 390 px, sur les pages du plan du site (échantillon) : page plus large que
   l'écran (et l'élément qui déborde), image cassée, mot qui trahit un bug (« NaN », « undefined », « [object Object] », « Infinity »),
   page presque vide, page qui ne charge pas.
3. Scénarios du site (tools/scenarios-visiteur.json, facultatif) : le robot remplit les formulaires comme un visiteur, lit le résultat
   AFFICHÉ et vérifie qu'il contient un nombre ; dans un même « groupe » à « croissant: true », le résultat doit monter avec « ordre »
   (ex. un salaire brut plus haut donne un salaire net plus haut).
Rouge (exit 1) si une anomalie est trouvée : à corriger avant que le visiteur réel la voie. Utilisation :
    python3 tools/visiteur_simule.py            (CHROME=chemin du navigateur ; MAX_PAGES=40 ; SANS_NAVIGATEUR=1 : seulement le point 1)
"""
import functools
import html
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import urllib.parse

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
MAX_PAGES = int(os.environ.get("MAX_PAGES", "40"))
IGNORE = re.compile(r"^(https?:|mailto:|tel:|data:|javascript:|#|//|whatsapp:|sms:)", re.I)


def chrome():
    for c in (os.environ.get("CHROME"), "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", shutil.which("google-chrome"),
              shutil.which("chromium"), shutil.which("chromium-browser"),
              # PC Windows (20/10/2026 : le visiteur ne trouvait pas Chrome sur le PC et ne faisait que la moitié du contrôle)
              r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if c and os.path.exists(c):
            return c
    return None


def pages_html():
    # seulement les pages PUBLIÉES (suivies par Git) : un dossier exclu (.gitignore) qui n'existe que sur le PC, ex. les copies de
    # conditions d'utilisation gardées en preuve, n'est pas une page du site (20/10/2026 : 970 « anomalies » sur le PC pour rien)
    try:
        r = subprocess.run(["git", "ls-files", "-z", "--", "*.html"], cwd=RACINE, capture_output=True, timeout=60)
        if r.returncode == 0 and r.stdout:
            exclus = ("node_modules", "tools", "robot", "data-brut", "preuves")
            return sorted(f for f in r.stdout.decode("utf-8", "replace").split("\0")
                          if f.endswith(".html") and not any(p.startswith((".", "_")) or p in exclus for p in f.split("/")[:-1])
                          and not f.split("/")[-1].startswith("_"))
    except (OSError, subprocess.SubprocessError):
        pass
    out = []
    for d, dirs, fs in os.walk(RACINE):
        dirs[:] = [x for x in dirs if not x.startswith((".", "_")) and x not in ("node_modules", "tools", "robot", "data-brut", "preuves")]
        for f in fs:
            if f.endswith(".html") and not f.startswith("_"):
                out.append(os.path.relpath(os.path.join(d, f), RACINE).replace(os.sep, "/"))
    return sorted(out)


def domaine():
    try:
        return open(os.path.join(RACINE, "CNAME"), encoding="utf-8").read().strip()
    except OSError:
        return ""


def liens_morts(pages):
    dom, morts = domaine(), []
    for p in pages:
        h = open(os.path.join(RACINE, p), encoding="utf-8", errors="ignore").read()
        h = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", h)          # liens fabriqués par le JavaScript : vérifiés par le navigateur
        for m in re.finditer(r'(?:href|src)="([^"]+)"', h):
            u = html.unescape(m.group(1)).strip()
            if dom and u.startswith(("https://" + dom, "http://" + dom)):
                u = u.split(dom, 1)[1] or "/"
            if not u or IGNORE.match(u) or "{" in u:
                continue
            u = urllib.parse.unquote(u.split("#")[0].split("?")[0])
            if not u:
                continue
            cible = os.path.normpath(os.path.join(RACINE, u.lstrip("/")) if u.startswith("/") else os.path.join(RACINE, os.path.dirname(p), u))
            if not cible.startswith(RACINE):
                continue
            if os.path.isdir(cible):
                cible = os.path.join(cible, "index.html")
            if not os.path.exists(cible):
                morts.append(f"{p} : lien ou image vers « {m.group(1)[:80]} » introuvable")
    return sorted(set(morts))


def echantillon(pages):
    plan = os.path.join(RACINE, "sitemap.xml")
    urls = []
    if os.path.exists(plan):
        for loc in re.findall(r"<loc>([^<]+)</loc>", open(plan, encoding="utf-8").read()):
            chemin = urllib.parse.urlparse(loc).path
            urls.append(chemin if chemin.endswith((".html", "/")) else chemin + "/")
    if not urls:
        urls = ["/" + p.replace("index.html", "") for p in pages]
    urls = list(dict.fromkeys(["/"] + urls))
    if len(urls) > MAX_PAGES:                                     # toujours les premières (pages principales), puis un échantillon régulier
        tete, reste = urls[:15], urls[15:]
        pas = max(1, len(reste) // (MAX_PAGES - 15))
        urls = tete + reste[::pas][:MAX_PAGES - 15]
    return urls


def serveur():
    class Muet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass
    h = functools.partial(Muet, directory=RACINE)

    class Serveur(socketserver.ThreadingTCPServer):
        daemon_threads = True

        def handle_error(self, *a):          # navigateur qui coupe une connexion (vidéo) : sans importance, pas de message
            pass
    s = Serveur(("127.0.0.1", 0), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, s.server_address[1]


PC = 1280                                  # largeur d'un écran d'ordinateur (19/10/2026)
N_PC = 12                                  # pages revues aussi sur PC (accueil d'abord)


def visiter(port, liste, nav, largeur=390):
    shutil.copy(os.path.join(ICI, "visiteur_simule.html"), os.path.join(RACINE, "_visiteur_simule.html"))
    try:
        u = f"http://127.0.0.1:{port}/_visiteur_simule.html?w={largeur}&l=" + urllib.parse.quote(json.dumps(liste))
        r = subprocess.run([nav, "--headless", "--no-sandbox", "--disable-gpu", f"--window-size={largeur + 10},1400", "--hide-scrollbars",
                            f"--virtual-time-budget={20000 + 4000 * len(liste)}", "--dump-dom", u], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=900).stdout or ""   # UTF-8 : sous Windows, la sortie était lue en cp1252 et perdue (20/10/2026)
        t = re.search(r"<title>R(.*?)</title>", r, re.S)
        return json.loads(html.unescape(t.group(1))) if t else []
    finally:
        os.remove(os.path.join(RACINE, "_visiteur_simule.html"))


def nombre(texte):
    m = re.search(r"-?\d[\d\s  .]*(?:,\d+)?", texte or "")
    if not m:
        return None
    try:
        return float(re.sub(r"[\s  .]", "", m.group(0)).replace(",", "."))
    except ValueError:
        return None


def main():
    pages = pages_html()
    anomalies = liens_morts(pages)
    nav = None if os.environ.get("SANS_NAVIGATEUR") else chrome()
    n_vis, lentes = 0, []
    if nav:
        s, port = serveur()
        try:
            urls = echantillon(pages)
            base = f"http://127.0.0.1:{port}"
            res = []
            for i in range(0, len(urls), 20):
                res += visiter(port, [{"u": base + u} for u in urls[i:i + 20]], nav)
            sc = []
            fs = os.path.join(ICI, "scenarios-visiteur.json")
            if os.path.exists(fs):
                sc = json.load(open(fs, encoding="utf-8"))
                for i in range(0, len(sc), 20):
                    paquet = sc[i:i + 20]
                    res_sc = visiter(port, [{"u": base + "/" + x["page"].lstrip("/"), "s": x.get("nom"), "etapes": x.get("etapes"), "lire": x.get("lire"),
                                             "attente": x.get("attente"), "apres": x.get("apres")} for x in paquet], nav)
                    for x, r in zip(paquet, res_sc):
                        r["scenario"] = x
                    res += res_sc
            # 19/10/2026 (capture d'Ahmed : accueil cassé sur PC, jamais vu à 390 px) : les premières pages aussi sur un écran d'ordinateur
            for r in visiter(port, [{"u": base + u} for u in urls[:N_PC]], nav, PC):
                r["pc"] = True
                res.append(r)
            n_vis = len(res)
            if len(res) < len(urls) + len(sc) + min(N_PC, len(urls)):
                anomalies.append(f"seulement {len(res)} visites sur {len(urls) + len(sc) + min(N_PC, len(urls))} (navigateur arrêté trop tôt ?)")
            groupes = {}
            lentes += [(r.get("s") or r["u"].replace(base, "")) for r in res if r.get("lent")]
            for r in res:
                nom = (r.get("s") or r["u"].replace(base, "")) + (" (PC 1280 px)" if r.get("pc") else "")
                if r.get("err"):
                    anomalies.append(f"{nom} : {r['err']}")
                    continue
                if (r.get("largeur") or 0) > (PC if r.get("pc") else 390) + 2:
                    anomalies.append(f"{nom} : page plus large que l'écran ({r['largeur']} px ; {', '.join(r.get('deborde') or [])})")
                for e in r.get("chevauche") or []:   # 19/10/2026 : un élément caché par son voisin
                    anomalies.append(f"{nom} : {e}")
                for im in r.get("images") or []:
                    anomalies.append(f"{nom} : image cassée « {im} »")
                if r.get("mot"):
                    anomalies.append(f"{nom} : texte « {r['mot']} »")
                if r.get("vide") and not r.get("scenario"):
                    anomalies.append(f"{nom} : page presque vide")
                for e in r.get("espaces") or []:     # § 29 : espaces vus comme un œil (éléments qui se touchent, espaces inégaux)
                    anomalies.append(f"{nom} : {e}")
                for m in r.get("manque") or []:
                    anomalies.append(f"{nom} : élément « {m} » introuvable (scénario à mettre à jour ?)")
                x = r.get("scenario")
                if x and x.get("lire"):
                    v = nombre(r.get("lu"))
                    if v is None:
                        anomalies.append(f"{nom} : pas de nombre dans le résultat affiché (« {(r.get('lu') or '')[:80]} »)")
                    elif x.get("groupe"):
                        groupes.setdefault(x["groupe"], []).append((x.get("ordre", 0), v, nom, x.get("croissant")))
            for g, l in groupes.items():
                l.sort()
                if any(c for *_, c in l):
                    for (o1, v1, n1, _), (o2, v2, n2, _) in zip(l, l[1:]):
                        if v2 < v1:
                            anomalies.append(f"groupe {g} : « {n2} » ({v2:g}) plus petit que « {n1} » ({v1:g}) — illogique")
        finally:
            s.shutdown()
    else:
        print("(navigateur absent : seulement les liens et images des pages)")
    print(f"Visiteur simulé : {len(pages)} pages relues, {n_vis} visites dans le navigateur (390 px, et {N_PC} pages sur PC {PC} px)")
    if lentes:
        print("  (pages lentes, contenu affiché après plus de 8 s : " + ", ".join(lentes[:10]) + ")")
    anomalies = list(dict.fromkeys(anomalies))
    for a in anomalies[:60]:
        print("  - " + a)
    print(f"ANOMALIES {len(anomalies)}")
    return 1 if anomalies else 0


if __name__ == "__main__":
    sys.exit(main())
