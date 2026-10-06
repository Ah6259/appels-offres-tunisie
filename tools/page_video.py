"""Page(s) vidéo du site (video/…) : fabriquées à partir de la page À propos déjà construite, pour garder EXACTEMENT le
même en-tête, pied de page, CSP, sécurité et numéros ?v= que le reste du site. Même travail que tools/page_video.mjs
(version Python pour les robots de construction en Python). Copié par l'outil vidéos d'Ahmed (dossier privé « videos (outil) »).
Réglages : tools/page_video.json. Ajoute aussi les pages au sitemap.xml.
Usage : from page_video import pages_video ; pages_video(dossier_du_site)    ou    python tools/page_video.py"""
import html, json, os, re


def _esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def _txt(o, d):
    return "".join(f' data-v{l}="{_esc(t)}"' for l, t in o.items()) + ">" + _esc(o.get(d, o.get("fr")))


def pages_video(root, cfg=None):
    if cfg is None:
        with open(os.path.join(root, "tools", "page_video.json"), encoding="utf-8") as f: cfg = json.load(f)
    with open(os.path.join(root, cfg.get("modele", "a-propos/index.html")), encoding="utf-8") as f: modele = f.read()
    D = cfg.get("defaut", "fr"); fait = []
    for p in cfg["pages"]:
        url = cfg["site"] + p["chemin"]; mp4 = cfg["site"] + "assets/video/" + p["video"] + ".mp4"
        titre = p["titre"].get(D, p["titre"]["fr"]); nom = cfg["nom"].get(D, cfg["nom"]["fr"]); desc = p["description"].get(D, p["description"]["fr"])
        og = (f'<link rel="canonical" href="{url}">\n<meta property="og:type" content="video.other">\n'
              f'<meta property="og:site_name" content="{_esc(nom)}">\n<meta property="og:title" content="{_esc(titre + " — " + nom)}">\n'
              f'<meta property="og:description" content="{_esc(desc)}">\n<meta property="og:url" content="{url}">\n'
              f'<meta property="og:image" content="{cfg["site"]}assets/video/{p["apercu"]}">\n<meta property="og:image:type" content="image/jpeg">\n'
              f'<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
              f'<meta property="og:video" content="{mp4}">\n<meta property="og:video:secure_url" content="{mp4}">\n'
              f'<meta property="og:video:type" content="video/mp4">\n<meta property="og:video:width" content="1080">\n'
              f'<meta property="og:video:height" content="1920">\n<meta name="twitter:card" content="summary_large_image">\n')
        h = re.sub(r'<script type="application/ld\+json">[\s\S]*?</script>\s*', "", modele)
        h = re.sub(r'<link rel="canonical"[^>]*>\s*', "", h)
        h = re.sub(r'<meta (property="og:[^"]*"|name="twitter:[^"]*")[^>]*>\s*', "", h)
        h = re.sub(r"<title>[\s\S]*?</title>", lambda m: f"<title>{_esc(titre)} | {_esc(nom)}</title>", h, count=1)
        h = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + _esc(desc) + m.group(2), h, count=1)
        h = h.replace("</head>", og + "</head>", 1)
        h = re.sub(r'(<body[^>]*\sdata-page=")[^"]*(")', r"\g<1>video\g<2>", h, count=1)
        # contenu remplacé : (bandeau +) <main>…</main> ; sans <main>, tout ce qui est entre </header> et <footer
        m = re.search(r"<main[\s>]", h); s = h.find('<section class="hero')
        if m:
            debut = s if 0 <= s < m.start() else m.start(); fin = h.find("</main>") + len("</main>")
        else:
            debut = h.find("</header>") + len("</header>") if "</header>" in h else -1
            f2 = re.search(r"<footer[\s>]", h); fin = f2.start() if f2 else -1
        if debut < 0 or fin < debut: raise SystemExit("page modèle sans <main>")
        r = "../" * len([x for x in p["chemin"].split("/") if x])
        src = "".join(f' data-src-{l}="{r}assets/video/{v}.mp4" data-poster-{l}="{r}assets/video/{v.replace("presentation", "couverture")}.jpg"' for l, v in p.get("sources", {}).items())
        corps = (f'<main class="wrap video-main">\n<section class="video-page" id="video">\n'
                 '  <div class="video-tete">' + (f'<img src="{r}{cfg["logo"]}" alt="" width="52" height="52">' if cfg.get("logo") else "")
                 + f'<p class="video-nom"{_txt(cfg["nom"], D)}</p></div>\n'
                 f'  <h1{_txt(p["titre"], D)}</h1>\n'
                 f'  <video class="video-lecteur" controls playsinline preload="metadata" width="1080" height="1920" poster="{r}assets/video/{p["couverture"]}" src="{r}assets/video/{p["video"]}.mp4"{src}></video>\n'
                 f'  <a class="btn-video-site" href="{r}{p["site"]}"{_txt(p["bouton"], D)}</a>\n'
                 f'  <button class="btn-video-partager" type="button" data-partager-video{_txt(cfg["partager"], D)}</button>\n'
                 f'</section>\n</main>')
        h = h[:debut] + corps + h[fin:]
        os.makedirs(os.path.join(root, p["chemin"]), exist_ok=True)
        with open(os.path.join(root, p["chemin"], "index.html"), "w", encoding="utf-8", newline="\n") as f: f.write(h)
        fait.append(p["chemin"])
    sm = os.path.join(root, "sitemap.xml")
    if os.path.exists(sm):
        with open(sm, encoding="utf-8") as f: s = f.read()
        ajout = [cfg["site"] + p["chemin"] for p in cfg["pages"] if f"<loc>{cfg['site'] + p['chemin']}</loc>" not in s]
        if ajout:
            s = s.replace("</urlset>", "".join(f"  <url><loc>{u}</loc></url>\n" for u in ajout) + "</urlset>")
            with open(sm, "w", encoding="utf-8", newline="\n") as f: f.write(s)
    return fait


if __name__ == "__main__":
    print("Pages vidéo :", ", ".join(pages_video(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))))
