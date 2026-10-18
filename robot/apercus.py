"""Image d'aperçu de CHAQUE rapport du mois (18/10/2026, Ahmed : « quand je partage l'article sur Facebook, l'image est celle
du site ; je veux partager l'ARTICLE »). Modèle repris d'Immobilier Tunisie (robot/apercus.py).
1200 × 630, JPEG : titre de l'article, mois, chiffre clé (tiré des chiffres de la page, jamais inventé), nom et adresse du site.
Pillow (pip install pillow) ; polices DejaVu copiées dans robot/polices/ (licence libre, Bitstream Vera / DejaVu).
Sans Pillow : disponible() = False et la page garde l'image générale du site (rien ne casse)."""
import os

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
NOM_SITE, DOMAINE = "Alertes appels d’offres Tunisie", "appels-offres.clicvia.com"
ICONE = os.path.join(RACINE, "assets", "icons", "icon-192.png")
# couleurs du site (assets/style.css)
PRINCIPALE, ENCRE, FOND, DOUX, LIGNE = (36, 71, 107), (15, 30, 46), (243, 246, 249), (90, 104, 120), (224, 230, 237)   # --bleu #24476B, --texte, --bg, --doux, --ligne


def disponible():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def _police(nom, taille):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(ICI, "polices", nom), taille)


def _lignes(dessin, texte, police, largeur):
    mots, lignes, cur = texte.split(), [], ""
    for m in mots:
        essai = (cur + " " + m).strip()
        if dessin.textlength(essai, font=police) <= largeur:
            cur = essai
        else:
            if cur:
                lignes.append(cur)
            cur = m
    return lignes + ([cur] if cur else [])


def _ajuste(d, texte, nom, taille, mini, largeur):
    """Police réduite jusqu'à ce que le texte tienne sur UNE ligne (jamais de débordement)."""
    while taille > mini and d.textlength(texte, font=_police(nom, taille)) > largeur:
        taille -= 2
    return _police(nom, taille)


def fabriquer(chemin_sortie, titre, mois, chiffre, sous_titre=""):
    """Écrit l'image ; renvoie True, ou False si Pillow manque."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False
    im = Image.new("RGB", (1200, 630), FOND)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1200, 14], fill=PRINCIPALE)
    # ruban « Rapport du mois · octobre 2026 »
    f_ruban = _police("DejaVuSans-Bold.ttf", 30)
    ruban = f"RAPPORT DU MOIS · {mois.upper()}"
    w = d.textlength(ruban, font=f_ruban)
    d.rounded_rectangle([64, 60, 64 + w + 40, 60 + 56], radius=12, fill=PRINCIPALE)
    d.text((84, 70), ruban, font=f_ruban, fill=(255, 255, 255))
    # titre de l'article (3 lignes au plus)
    taille = 66
    while True:
        f_titre = _police("DejaVuSerif-Bold.ttf", taille)
        lignes = _lignes(d, titre, f_titre, 1070)
        if len(lignes) <= 3 or taille <= 40:
            break
        taille -= 4
    y = 150
    for l in lignes[:3]:
        d.text((64, y), l, font=f_titre, fill=ENCRE)
        y += int(taille * 1.18)
    # chiffre clé
    if chiffre:
        f_ch = _ajuste(d, chiffre, "DejaVuSans-Bold.ttf", 40, 24, 1028)
        y += 14
        d.rounded_rectangle([64, y, 64 + d.textlength(chiffre, font=f_ch) + 44, y + 70], radius=14, fill=(255, 255, 255), outline=LIGNE, width=3)
        d.text((86, y + 35), chiffre, font=f_ch, fill=PRINCIPALE, anchor="lm")
        y += 86
    if sous_titre:
        d.text((64, y + 6), sous_titre, font=_ajuste(d, sous_titre, "DejaVuSans.ttf", 28, 18, 1072), fill=DOUX)
    # pied : logo + nom + adresse
    try:
        logo = Image.open(ICONE).convert("RGBA").resize((70, 70))
        im.paste(logo, (64, 528), logo)
    except OSError:
        pass
    d.text((150, 536), NOM_SITE, font=_police("DejaVuSerif-Bold.ttf", 34), fill=ENCRE)
    d.text((150, 578), DOMAINE, font=_police("DejaVuSans-Bold.ttf", 26), fill=PRINCIPALE)
    os.makedirs(os.path.dirname(chemin_sortie), exist_ok=True)
    im.save(chemin_sortie, "JPEG", quality=85, optimize=True)
    return True
