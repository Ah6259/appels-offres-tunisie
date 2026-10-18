# -*- coding: utf-8 -*-
"""
« Rapports du mois » (demande d'Ahmed du 18/10/2026, règle commune § 25) : articles AUTOMATIQUES mais VRAIS,
écrits uniquement à partir des données déjà publiées GRATUITEMENT sur le site (appels d'offres HAICOP relevés
par le robot + ventes aux enchères de la Douane). Rien de la partie payante (Alertes Pro).

Chaque phrase est un chiffre tiré des données ; aucune estimation, aucun texte inventé.

Pages produites (appelé par construire_site.py) :
  rapports/                                  liste des mois
  rapports/AAAA-MM/                          bilan du mois
  rapports/AAAA-MM/gouvernorat/<slug>/       un gouvernorat (seulement s'il a au moins MIN_SOUS_PAGE appels d'offres)
  rapports/AAAA-MM/metier/<slug>/            un métier (idem) — au plus MAX_SOUS_PAGES sous-pages par mois

Historique : donnees/rapports.json  {"robot_depuis": date, "mois": {"AAAA-MM": {...}}}
  - le mois en cours est recalculé à chaque passage (« chiffres au <date> ») ;
  - un mois terminé est FIGÉ à partir du JOUR_FIGE du mois suivant (petit délai : un appel d'offres publié le
    dernier jour est souvent lu le lendemain), puis n'est plus JAMAIS modifié ;
  - les fiches du mois y sont gardées (forme courte), pour que les chiffres ne dépendent pas des fiches encore en mémoire.
"""
import datetime as dt
import json
import os
import re
import statistics

MIN_CLASSEMENT = 3     # un élément n'entre dans un classement qu'avec au moins 3 appels d'offres
MIN_LIGNES = 3         # un classement n'est montré que s'il a au moins 3 lignes (jamais de classement sur 1 ou 2 éléments)
MIN_MEDIANE = 5        # une médiane n'est donnée qu'avec au moins 5 valeurs
MIN_SOUS_PAGE = 10     # sous-page d'un gouvernorat / d'un métier : au moins 10 appels d'offres dans le mois
MAX_SOUS_PAGES = 25    # au plus 25 sous-pages par mois (pas de pages presque vides)
JOUR_FIGE = 3          # un mois est figé à partir du 3 du mois suivant
SPECIAUX_G = ("Plusieurs gouvernorats", "National / non précisé")
SPECIAUX_M = ("Autres",)

MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
MOIS_AR = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ------------------------------------------------------------------ petites fonctions
def mois_fr(m):
    return f"{MOIS_FR[int(m[5:7]) - 1]} {m[:4]}"


def mois_ar(m):
    return f"{MOIS_AR[int(m[5:7]) - 1]} {m[:4]}"


def mois_suivant(m):
    a, n = int(m[:4]), int(m[5:7])
    return f"{a + (n == 12)}-{1 if n == 12 else n + 1:02d}"


def mois_precedent(m):
    a, n = int(m[:4]), int(m[5:7])
    return f"{a - (n == 1)}-{12 if n == 1 else n - 1:02d}"


def fin_mois(m):
    return (dt.date.fromisoformat(mois_suivant(m) + "-01") - dt.timedelta(days=1)).isoformat()


def date_figeage(m):
    return f"{mois_suivant(m)}-{JOUR_FIGE:02d}"


def nb(n):
    return f"{n:,}".replace(",", " ")


def pct(n, total):
    return round(100 * n / total) if total else 0


def compte(records, cle):
    c = {}
    for r in records:
        c[r[cle]] = c.get(r[cle], 0) + 1
    return sorted(c.items(), key=lambda x: (-x[1], x[0]))


def classement(records, cle, exclus=()):
    """Lignes (nom, nombre) d'au moins MIN_CLASSEMENT ; [] si moins de MIN_LIGNES lignes (pas de classement)."""
    lignes = [(k, n) for k, n in compte(records, cle) if n >= MIN_CLASSEMENT and k not in exclus]
    return lignes if len(lignes) >= MIN_LIGNES else []


def premiers(lignes, n=10, plafond=15):
    """Les n premiers, sans couper une égalité : toute la dernière égalité si le total reste ≤ plafond, sinon aucune."""
    if len(lignes) <= n:
        return lignes
    seuil = lignes[n - 1][1]
    avec = [x for x in lignes if x[1] >= seuil]
    return avec if len(avec) <= plafond else [x for x in lignes if x[1] > seuil]


def delais(records):
    res = []
    for r in records:
        if r["date_publication"] and r["date_limite"] and r["date_limite"] >= r["date_publication"]:
            res.append((dt.date.fromisoformat(r["date_limite"]) - dt.date.fromisoformat(r["date_publication"])).days)
    return res


def mediane(valeurs):
    return statistics.median_low(valeurs) if len(valeurs) >= MIN_MEDIANE else None


# ------------------------------------------------------------------ historique
def court_ao(a):
    return {"numero": a["numero"], "objet": a["objet"][:300], "acheteur": str(a.get("acheteur") or "").strip()[:200],
            "metier": a["metier"], "gouvernorat": a["gouvernorat"], "procedure": str(a.get("procedure") or "").strip()[:80],
            "date_publication": a["date_publication"], "date_limite": a["date_limite"],
            "caution": a.get("cautionnement_total_dt"), "lien": a["lien"]}


def charger_historique(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            h = json.load(f)
        if isinstance(h, dict) and isinstance(h.get("mois"), dict):
            return h
    except (OSError, ValueError):
        pass
    return {"robot_depuis": "", "mois": {}}


def mettre_a_jour(hist, aos, ventes, jour, date_chiffres, cs):
    """Ajoute les fiches des mois NON figés, puis fige les mois terminés. Un mois figé n'est jamais touché."""
    mois = hist["mois"]
    lus = [str(a.get("lu_le") or "")[:10] for a in aos if DATE.match(str(a.get("lu_le") or "")[:10])]
    if lus:
        debut = min(lus)
        if not hist.get("robot_depuis") or debut < hist["robot_depuis"]:
            hist["robot_depuis"] = debut
    for a in aos:
        m = a["date_publication"][:7]
        if not a["date_publication"] or m > jour[:7]:
            continue
        if m in mois and mois[m].get("fige"):
            continue
        if m not in mois:
            if jour >= date_figeage(m):
                continue     # mois déjà terminé avant le premier passage : on ne crée pas un rapport après coup
            mois[m] = {"premier_jour": m + "-01", "cree_le": jour, "derniere_date": "", "fige": False,
                       "appels_offres": {}, "ventes": {}}
        mois[m]["appels_offres"][a["numero"]] = court_ao(a)
    for v in ventes:
        m = v["date_publication"][:7]
        if m in mois and not mois[m].get("fige"):
            mois[m]["ventes"][v["id"]] = {"id": v["id"], "gouvernorat": v["gouvernorat"],
                                          "date_publication": v["date_publication"]}
    for m, e in mois.items():
        if e.get("fige"):
            continue
        e["chiffres"] = chiffres(list(e["appels_offres"].values()), list(e["ventes"].values()))
        e["derniere_date"] = min(max(date_chiffres, e["chiffres"]["derniere_publication"]), fin_mois(m))
        e["complet"] = bool(hist.get("robot_depuis")) and hist["robot_depuis"] <= e["premier_jour"]
        if jour >= date_figeage(m):
            e["fige"], e["fige_le"] = True, jour
    return hist


def ecrire_historique(chemin, hist):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(hist, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, chemin)


def chiffres(aos, ventes):
    """Les chiffres du mois (gardés dans l'historique ; ce sont eux que la page affiche)."""
    d = delais(aos)
    cautions = [r["caution"] for r in aos if isinstance(r.get("caution"), int) and r["caution"] > 0]
    jours = compte(aos, "date_publication")
    jours = [j for j in jours if j[0]]
    return {
        "appels_offres": len(aos),
        "premiere_publication": min((r["date_publication"] for r in aos), default=""),
        "derniere_publication": max((r["date_publication"] for r in aos), default=""),
        "par_metier": dict(compte(aos, "metier")),
        "par_gouvernorat": dict(compte(aos, "gouvernorat")),
        "par_procedure": dict(compte(aos, "procedure")),
        "acheteurs": dict(premiers(classement(aos, "acheteur"))),
        "jours_de_publication": len(jours),
        "jour_max": list(jours[0]) if jours else None,
        "avec_delai": len(d), "delai_median": mediane(d),
        "avec_caution": len(cautions), "caution_mediane": mediane(cautions),
        "ventes": len(ventes),
        "ventes_par_gouvernorat": dict(compte(ventes, "gouvernorat")),
    }


# ------------------------------------------------------------------ morceaux de page
def tableau(cs, entetes, lignes, attr):
    """lignes : [(cle, libelle_html, n, part)] ; attr = nom de l'attribut data- (pour les tests)."""
    th = "".join('<th scope="col"' + (' class="n"' if k else "") + f">{h}</th>" for k, h in enumerate(entetes))
    corps = "".join(f'<tr data-{attr}="{cs.E(c)}" data-n="{n}"><td>{lib}</td><td class="n">{cs.ISO(nb(n))}</td>'
                    f'<td class="n">{cs.ISO(str(p) + " %")}</td></tr>' for c, lib, n, p in lignes)
    return f'<div class="rap-defile"><table class="rap-table"><thead><tr>{th}</tr></thead><tbody>{corps}</tbody></table></div>'


def fil_rapport(cs, racine, niveaux):
    """niveaux : [(lien ou "", fr, ar)]"""
    morceaux = [f'<a href="{racine}">{cs.L("Accueil", "الرئيسية")}</a>']
    for lien, fr, ar in niveaux:
        morceaux.append(f'<a href="{lien}">{cs.L(fr, ar)}</a>' if lien else cs.L(fr, ar))
    return '    <p class="fil">' + " › ".join(morceaux) + "</p>"


def jsonld(cs, url, titre, e, fil_items, faq):
    blocs = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": k + 1, "name": n, "item": u} for k, (n, u) in enumerate(fil_items)]},
        {"@context": "https://schema.org", "@type": "Article", "headline": titre, "inLanguage": ["fr", "ar"],
         "datePublished": e.get("cree_le") or e["derniere_date"], "dateModified": e["derniere_date"], "url": url,
         "author": {"@type": "Organization", "name": "Alertes appels d'offres Tunisie", "url": cs.URL_SITE},
         "publisher": {"@type": "Organization", "name": "Alertes appels d'offres Tunisie", "url": cs.URL_SITE},
         "image": cs.URL_SITE + "assets/og-image-v6.jpg"}]
    if faq:
        blocs.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in faq]})
    return "".join('<script type="application/ld+json">' + json.dumps(b, ensure_ascii=False).replace("</", "<\\/")
                   + "</script>\n" for b in blocs)


def statut_html(cs, m, e):
    if e.get("fige"):
        return cs.L(f"Mois terminé : chiffres définitifs (figés le {cs.dfr(e['fige_le'])}).",
                    f"شهر منتهٍ: أرقام نهائية (ثُبّتت يوم {cs.ISO(cs.dfr(e['fige_le']))}).")
    return cs.L(f"Chiffres au {cs.dfr(e['derniere_date'])}, recalculés chaque jour ; ils seront figés le {cs.dfr(date_figeage(m))}.",
                f"أرقام إلى غاية {cs.ISO(cs.dfr(e['derniere_date']))}، تُحيَّن كل يوم، وتُثبَّت يوم {cs.ISO(cs.dfr(date_figeage(m)))}.")


def evolution(cs, hist, m, e, filtre=None, quoi=("appels d'offres", "طلب عروض")):
    """Phrase d'évolution, SEULEMENT si le mois précédent existe et a été lu dès son 1er jour ; sinon dit pourquoi."""
    p = mois_precedent(m)
    prec = hist["mois"].get(p)
    if not prec:
        return ("premier", cs.L("Premier rapport : pas encore de mois précédent pour comparer.",
                                "أول تقرير: لا يوجد بعد شهر سابق للمقارنة."))
    if not prec.get("complet"):
        return ("incomplet", cs.L(f"Pas d'évolution affichée : en {mois_fr(p)}, notre robot n'a pas lu le portail dès le 1er jour du mois (comparaison faussée).",
                                  f"لا مقارنة: في {mois_ar(p)} لم يقرأ برنامجنا البوابة منذ أول يوم في الشهر (المقارنة غير دقيقة)."))
    def sel(recs):
        return [r for r in recs if filtre is None or filtre(r)]
    actuel = len(sel(e["appels_offres"].values()))
    if e.get("fige"):
        avant = len(sel(prec["appels_offres"].values()))
        ref_fr, ref_ar = f"en {mois_fr(p)} (mois complet)", f"في {mois_ar(p)} (شهر كامل)"
    else:
        jourm = min(int(e["derniere_date"][8:10]), int(fin_mois(p)[8:10]))
        limite = f"{p}-{jourm:02d}"
        avant = len([r for r in sel(prec["appels_offres"].values()) if r["date_publication"] <= limite])
        ref_fr = f"du 1er au {jourm} {mois_fr(p)} (même période)"
        ref_ar = f"من {cs.ISO(1)} إلى {cs.ISO(jourm)} {mois_ar(p)} (نفس الفترة)"
    diff = actuel - avant
    signe = "+" if diff > 0 else ("−" if diff < 0 else "")
    part = f" ({signe}{abs(pct(diff, avant))} %)" if avant else ""
    return ("ok", cs.L(f"Évolution : {nb(actuel)} {quoi[0]} contre {nb(avant)} {ref_fr}, soit {signe}{nb(abs(diff))}{part}.",
                       f"التطور: {cs.ISO(nb(actuel))} {quoi[1]} مقابل {cs.ISO(nb(avant))} {ref_ar}، أي {cs.ISO(signe + nb(abs(diff)) + part)}."))


def liste_bref(bref, genre_evo):
    """La dernière ligne (évolution) porte id="evolution" ou id="premier-rapport" (vérifié par les tests)."""
    ident = {"ok": ' id="evolution"', "premier": ' id="premier-rapport"', "incomplet": ' id="sans-evolution"'}[genre_evo]
    return "".join(f"<li{ident if k == len(bref) - 1 else ''}>{x}</li>" for k, x in enumerate(bref))


def liste_fiches(cs, recs):
    recs = sorted(recs, key=lambda r: (r["date_publication"], r["numero"]), reverse=True)
    lis = "".join(f'<li data-numero="{cs.E(r["numero"])}"><a href="{cs.E(r["lien"])}" rel="noopener"><bdi>{cs.E(r["objet"])}</bdi></a>'
                  f'<span class="rap-meta">{cs.E(r["acheteur"])} · {cs.L("publié le", "نُشر يوم")} {cs.ISO(cs.dfr(r["date_publication"]))}'
                  + (f' · {cs.L("date limite", "آخر أجل")} {cs.ISO(cs.dfr(r["date_limite"]))}' if r["date_limite"] else "")
                  + "</span></li>" for r in recs)
    return f'<ol class="rap-fiches">{lis}</ol>'


def methode(cs):
    return f"""<section class="carte rap-methode" id="methode">
  <h2>{cs.L("Comment ces chiffres sont calculés", "كيف تُحسب هذه الأرقام")}</h2>
  <ul class="sources" data-l="fr">
    <li>Ce sont les appels d'offres publiés sur le portail officiel de la <b>HAICOP</b> et <b>relevés par notre robot</b> (il lit chaque jour jusqu'à 40 nouvelles fiches). Ce n'est donc pas le total officiel du portail.</li>
    <li>Le mois est celui de la <b>date de publication</b> écrite sur la fiche officielle. Le métier et le gouvernorat sont ceux du classement du site (mêmes pages « Par métier » et « Par gouvernorat ») : quelques erreurs de classement sont possibles.</li>
    <li>Un métier, un gouvernorat ou un acheteur n'entre dans un classement qu'avec au moins <b>{MIN_CLASSEMENT} appels d'offres</b>, et un classement n'est montré qu'avec au moins <b>{MIN_LIGNES} lignes</b>. Une médiane n'est donnée qu'avec au moins <b>{MIN_MEDIANE} valeurs</b> (la moitié des valeurs est au-dessus, l'autre moitié au-dessous). Un gouvernorat ou un métier n'a sa propre page qu'avec au moins <b>{MIN_SOUS_PAGE} appels d'offres</b> dans le mois.</li>
    <li>Le mois en cours est recalculé chaque jour. Un mois terminé est figé le {JOUR_FIGE} du mois suivant et n'est plus jamais modifié. L'évolution compare seulement avec un mois que notre robot a lu dès son 1er jour, sur la même période.</li>
    <li>Ventes aux enchères : avis publiés sur la page officielle de la <b>Douane tunisienne</b> pendant le mois, relevés par notre robot.</li>
    <li>Aucune estimation : chaque chiffre est un simple comptage (ou une médiane) des annonces affichées gratuitement sur ce site.</li>
  </ul>
  <ul class="sources" data-l="ar">
    <li>هي طلبات العروض المنشورة في البوابة الرسمية <b>للهيئة العليا للطلب العمومي</b> والتي <b>رصدها برنامجنا</b> (يقرأ كل يوم إلى حدود {cs.ISO(40)} بطاقة جديدة). ليست إذن العدد الرسمي الكامل للبوابة.</li>
    <li>الشهر هو شهر <b>تاريخ النشر</b> المكتوب في البطاقة الرسمية. الاختصاص والولاية حسب ترتيب الموقع (نفس صفحات «حسب الاختصاص» و«حسب الولاية»): أخطاء قليلة ممكنة.</li>
    <li>لا يدخل اختصاص أو ولاية أو مشترٍ في الترتيب إلا بـ<b>{cs.ISO(MIN_CLASSEMENT)} طلبات عروض</b> على الأقل، ولا يظهر الترتيب إلا بـ<b>{cs.ISO(MIN_LIGNES)} أسطر</b> على الأقل. لا يُعطى الوسيط إلا بـ<b>{cs.ISO(MIN_MEDIANE)} قيم</b> على الأقل. لا تكون للولاية أو للاختصاص صفحة خاصة إلا بـ<b>{cs.ISO(MIN_SOUS_PAGE)} طلبات عروض</b> على الأقل في الشهر.</li>
    <li>يُعاد حساب الشهر الجاري كل يوم. يُثبَّت الشهر المنتهي يوم {cs.ISO(JOUR_FIGE)} من الشهر الموالي ولا يتغيّر بعد ذلك أبدًا. لا تُحسب المقارنة إلا مع شهر قرأه برنامجنا منذ أول يوم، وعلى نفس الفترة.</li>
    <li>البيوعات بالمزاد: إعلانات منشورة في الصفحة الرسمية <b>للديوانة التونسية</b> خلال الشهر، رصدها برنامجنا.</li>
    <li>لا يوجد أي تقدير: كل رقم عدّ بسيط (أو وسيط) للإعلانات المعروضة مجانًا في هذا الموقع.</li>
  </ul>
</section>"""


def citer(cs, url, titre_fr, e):
    date = cs.dfr(e["fige_le"] if e.get("fige") else e["derniere_date"])
    return f"""<section class="carte rap-citer" id="citer">
  <h2>{cs.L("Citer ces chiffres", "الاستشهاد بهذه الأرقام")}</h2>
  <p>{cs.L("Journalistes, blogs, organismes : vous pouvez reprendre ces chiffres en citant la source et le lien ci-dessous.",
           "صحفيون، مدونات، هياكل: يمكنكم نقل هذه الأرقام مع ذكر المصدر والرابط أسفله.")}</p>
  <blockquote class="rap-citation"><bdi>Alertes appels d'offres Tunisie, « {cs.E(titre_fr)} », chiffres au {date}, d'après le portail officiel HAICOP — {url}</bdi></blockquote>
</section>"""


# ------------------------------------------------------------------ partage et signature (demande d'Ahmed, 18/10/2026)
NOM_SITE_FR = "Alertes appels d'offres Tunisie"
NOM_SITE_AR = "تنبيهات طلبات العروض تونس"
DOMAINE = "appels-offres.clicvia.com"
ICONE_PARTAGE = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>'
                 '<circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>')


def description_rapport(desc):
    """La description (aperçu Facebook / WhatsApp / Google) dit d'abord de quel site vient le rapport."""
    return f"{NOM_SITE_FR} — rapport du mois. {desc}"


def signature(cs):
    return ('    <p class="rp-signature">' + cs.L(f"Un rapport de <b>{cs.E(NOM_SITE_FR)}</b> · {DOMAINE}",
                                                 f"تقرير من <b>{NOM_SITE_AR}</b> · <bdi>{DOMAINE}</bdi>") + "</p>")


def bloc_partage(cs, url, titre_fr, titre_ar, haut):
    """UN seul bouton « Partager ce rapport » (menu de partage du téléphone : Facebook, WhatsApp, LinkedIn…).
    Le code est dans assets/page.js (écouteur sur button[data-partage-rapport]) : la CSP interdit les scripts en ligne."""
    return (f'<div class="rp-partage{" rp-partage-haut" if haut else " rp-partage-bas"}">'
            f'<button class="rp-partager" type="button" data-partage-rapport data-url="{cs.E(url)}" '
            f'data-titre-fr="{cs.E(titre_fr)}" data-titre-ar="{cs.E(titre_ar)}">{ICONE_PARTAGE}'
            f'<span>{cs.L("Partager ce rapport", "شارك هذا التقرير")}</span></button>'
            f'<p class="rp-copie" role="status" hidden></p></div>')


# ------------------------------------------------------------------ pages
def construire_rapports(cs, hist, v, etat):
    """Renvoie [(chemin, html, lastmod)] pour rapports/ et chaque mois de l'historique."""
    pages = []
    mois = sorted(hist["mois"], reverse=True)
    for m in mois:
        pages += pages_mois(cs, hist, m, v, etat)
    pages.insert(0, ("rapports/", page_liste(cs, hist, mois, v, etat), max((hist["mois"][m]["derniere_date"] for m in mois), default="") or None))
    return pages


def page_liste(cs, hist, mois, v, etat):
    racine = "../"
    url = cs.URL_SITE + "rapports/"
    titre_fr = "Rapports du mois : appels d'offres publics en Tunisie en chiffres"
    titre_ar = "تقارير الشهر: طلبات العروض العمومية في تونس بالأرقام"
    if mois:
        lis = "".join(
            f'<li data-mois="{m}"><a href="{m}/">{cs.L(mois_fr(m).capitalize(), mois_ar(m))}</a> — '
            + cs.L(f"{nb(hist['mois'][m]['chiffres']['appels_offres'])} appels d'offres relevés, "
                   + (f"chiffres définitifs" if hist["mois"][m].get("fige") else f"chiffres au {cs.dfr(hist['mois'][m]['derniere_date'])} (mois en cours)"),
                   f"{cs.ISO(nb(hist['mois'][m]['chiffres']['appels_offres']))} طلب عروض مرصود، "
                   + ("أرقام نهائية" if hist["mois"][m].get("fige") else f"أرقام إلى غاية {cs.ISO(cs.dfr(hist['mois'][m]['derniere_date']))} (شهر جارٍ)"))
            + "</li>" for m in mois)
        corps = f'<ul class="rap-mois">{lis}</ul>'
    else:
        corps = f'<p>{cs.L("Pas encore de rapport : le premier sera publié dès que des appels d’offres seront relevés.", "لا يوجد تقرير بعد.")}</p>'
    hero = f"""{fil_rapport(cs, racine, [("", "Rapports du mois", "تقارير الشهر")])}
    <h1>{cs.L("Rapports du mois", "تقارير الشهر")}</h1>
{signature(cs)}
    <p class="intro">{cs.L("Chaque mois, le bilan des appels d'offres publics tunisiens relevés par notre robot : par métier, par gouvernorat, par acheteur public. Uniquement des chiffres tirés des annonces du site.",
                           "كل شهر، حصيلة طلبات العروض العمومية التونسية التي رصدها برنامجنا: حسب الاختصاص والولاية والمشتري العمومي. أرقام مأخوذة فقط من إعلانات الموقع.")}</p>
    {bloc_partage(cs, url, titre_fr, titre_ar, True)}"""
    contenu = f"""<section class="carte">
  <h2>{cs.L("Tous les mois", "كل الأشهر")}</h2>
  {corps}
</section>
{methode(cs)}
{bloc_partage(cs, url, titre_fr, titre_ar, False)}"""
    titre = "Rapports du mois : appels d'offres publics en Tunisie en chiffres | Alertes appels d'offres"
    desc = ("Bilan mensuel des appels d'offres publics tunisiens relevés sur le portail officiel HAICOP : nombre par métier, par gouvernorat "
            "et par acheteur public. Chiffres vérifiables, gratuit. تقارير شهرية لطلبات العروض.")
    return cs.page("rapports/", racine, titre, description_rapport(desc), hero, contenu, v, etat)


def candidats_sous_pages(cs, recs):
    c = []
    for nom, n in compte(recs, "gouvernorat"):
        if n >= MIN_SOUS_PAGE and nom not in SPECIAUX_G:
            g = cs.G_PAR_NOM[nom]
            c.append(("gouvernorat", nom, g[1], n, nom, g[2]))
    for nom, n in compte(recs, "metier"):
        if n >= MIN_SOUS_PAGE and nom not in SPECIAUX_M:
            mm = cs.M_PAR_NOM[nom]
            c.append(("metier", nom, mm[1], n, mm[2], mm[3]))
    c.sort(key=lambda x: (-x[3], x[0], x[2]))
    return c[:MAX_SOUS_PAGES]


def lignes_tableau(cs, comptes, total, genre, exclus=()):
    """Tableau d'une répartition (métier ou gouvernorat) : lignes d'au moins MIN_CLASSEMENT, le reste regroupé."""
    lignes, reste, n_reste = [], 0, 0
    for nom, n in sorted(comptes.items(), key=lambda x: (-x[1], x[0])):
        if n >= MIN_CLASSEMENT and nom not in exclus:
            if genre == "metier":
                mm = cs.M_PAR_NOM.get(nom, (nom, nom, nom, nom))
                lib, cle = cs.L(cs.E(mm[2]), mm[3]), mm[1]
            else:
                g = cs.G_PAR_NOM.get(nom, (nom, nom, nom))
                lib, cle = cs.L(cs.E(nom), g[2]), g[1]
            lignes.append((cle, lib, n, pct(n, total)))
        else:
            reste += n
            n_reste += 1
    return lignes, reste, n_reste


def bloc_repartition(cs, titre_fr, titre_ar, comptes, total, genre, ident):
    lignes, reste, n_reste = lignes_tableau(cs, comptes, total, genre)
    if len(lignes) < MIN_LIGNES:
        return (f'<section class="carte" id="{ident}"><h2>{cs.L(titre_fr, titre_ar)}</h2>'
                f'<p>{cs.L(f"Pas de classement : moins de {MIN_LIGNES} lignes d’au moins {MIN_CLASSEMENT} appels d’offres.", f"لا ترتيب: أقل من {cs.ISO(MIN_LIGNES)} أسطر بـ{cs.ISO(MIN_CLASSEMENT)} طلبات عروض على الأقل.")}</p></section>')
    col = ("Métier", "الاختصاص") if genre == "metier" else ("Gouvernorat", "الولاية")
    t = tableau(cs, [cs.L(*col), cs.L("Appels d'offres", "طلبات العروض"), cs.L("Part", "النسبة")], lignes, genre)
    mot = ("métiers", "اختصاصات") if genre == "metier" else ("gouvernorats", "ولايات")
    note = (f'<p class="rap-note">{cs.L(f"Regroupés ({n_reste} {mot[0]} avec moins de {MIN_CLASSEMENT} appels d’offres chacun) : {nb(reste)} appels d’offres au total.", f"مجمّعة ({cs.ISO(n_reste)} {mot[1]} بأقل من {cs.ISO(MIN_CLASSEMENT)} طلبات عروض لكل منها): {cs.ISO(nb(reste))} طلب عروض في المجموع.")}</p>'
            if reste else "")
    return f'<section class="carte" id="{ident}"><h2>{cs.L(titre_fr, titre_ar)}</h2>{t}{note}</section>'


def bloc_acheteurs(cs, recs, total):
    lignes = premiers(classement(recs, "acheteur"))
    titre = cs.L("Acheteurs publics les plus actifs", "المشترون العموميون الأكثر نشاطًا")
    if not lignes:
        return (f'<section class="carte" id="acheteurs"><h2>{titre}</h2><p>{cs.L(f"Pas de classement : moins de {MIN_LIGNES} acheteurs avec au moins {MIN_CLASSEMENT} appels d’offres.", f"لا ترتيب: أقل من {cs.ISO(MIN_LIGNES)} مشترين بـ{cs.ISO(MIN_CLASSEMENT)} طلبات عروض على الأقل.")}</p></section>')
    t = tableau(cs, [cs.L("Acheteur public", "المشتري العمومي"), cs.L("Appels d'offres", "طلبات العروض"), cs.L("Part", "النسبة")],
                [(a, f"<bdi>{cs.E(a)}</bdi>", n, pct(n, total)) for a, n in lignes], "acheteur")
    return f'<section class="carte" id="acheteurs"><h2>{titre}</h2>{t}<p class="rap-note">{cs.L(f"Au moins {MIN_CLASSEMENT} appels d’offres chacun ; les 10 premiers (ex æquo compris).", f"{cs.ISO(MIN_CLASSEMENT)} طلبات عروض على الأقل لكل منهم؛ العشرة الأوائل (مع المتساوين).")}</p></section>'


def bloc_delais(cs, c):
    lis = []
    if c["delai_median"] is not None:
        lis.append(cs.L(f"Délai médian entre la publication et la date limite : <b>{c['delai_median']} jours</b> (sur {nb(c['avec_delai'])} appels d’offres avec une date limite).",
                        f"المدة الوسيطة بين النشر وآخر أجل: <b>{cs.ISO(c['delai_median'])} يومًا</b> (من {cs.ISO(nb(c['avec_delai']))} طلب عروض بآخر أجل)."))
    if c["caution_mediane"] is not None:
        lis.append(cs.L(f"Caution provisoire médiane : <b>{nb(c['caution_mediane'])} DT</b> (sur {nb(c['avec_caution'])} appels d’offres qui en demandent une).",
                        f"الضمان الوقتي الوسيط: <b>{cs.ISO(nb(c['caution_mediane']))} دينار</b> (من {cs.ISO(nb(c['avec_caution']))} طلب عروض يطلب ضمانًا)."))
    if not lis:
        return ""
    return (f'<section class="carte" id="delais"><h2>{cs.L("Délais et cautions", "الآجال والضمانات")}</h2>'
            f'<ul class="rap-bref">{"".join(f"<li>{x}</li>" for x in lis)}</ul></section>')


def bloc_procedures(cs, c):
    total = c["appels_offres"]
    if not total:
        return ""
    lis = "".join(f'<li data-procedure="{cs.E(p)}" data-n="{n}">{cs.L(cs.E(p or "Non précisée"), cs.procedure_ar(p) or cs.E(p or "غير محدد"))} : {cs.ISO(nb(n))}</li>'
                  for p, n in sorted(c["par_procedure"].items(), key=lambda x: (-x[1], x[0])))
    return f'<section class="carte" id="procedures"><h2>{cs.L("Procédures", "الإجراءات")}</h2><ul class="rap-bref">{lis}</ul></section>'


def bloc_ventes(cs, c, racine, mois):
    if not c["ventes"]:
        return ""
    lignes, reste, n_reste = lignes_tableau(cs, c["ventes_par_gouvernorat"], c["ventes"], "gouvernorat")
    t, nv = "", nb(c["ventes"])
    if len(lignes) >= MIN_LIGNES:
        t = tableau(cs, [cs.L("Gouvernorat", "الولاية"), cs.L("Ventes", "البيوعات"), cs.L("Part", "النسبة")], lignes, "vente-gouv")
        if reste:
            t += f'<p class="rap-note">{cs.L(f"Regroupés ({n_reste} gouvernorats avec moins de {MIN_CLASSEMENT} ventes chacun) : {nb(reste)} ventes au total.", f"مجمّعة ({cs.ISO(n_reste)} ولايات بأقل من {cs.ISO(MIN_CLASSEMENT)} بيوعات لكل منها): {cs.ISO(nb(reste))} بيوعات في المجموع.")}</p>'
    return (f'<section class="carte" id="ventes"><h2>{cs.L("Ventes aux enchères de la Douane", "بيوعات الديوانة بالمزاد")}</h2>'
            + "<p>" + cs.L(f"<b>{nv}</b> avis de vente aux enchères publiés en {mois_fr(mois)} par la Douane tunisienne ont été relevés.", f"تم رصد <b>{cs.ISO(nv)}</b> إعلان بيع بالمزاد نشرته الديوانة التونسية في {mois_ar(mois)}.") + " "
            + f'<a href="{racine}encheres/">{cs.L("Voir les ventes encore ouvertes", "البيوعات المفتوحة")}</a></p>{t}</section>')


def pages_mois(cs, hist, m, v, etat):
    e = hist["mois"][m]
    c = e["chiffres"]
    recs = list(e["appels_offres"].values())
    racine = "../../"
    url = f"{cs.URL_SITE}rapports/{m}/"
    total = c["appels_offres"]
    mfr, mar = mois_fr(m), mois_ar(m)
    titre_fr = f"Appels d'offres publics en Tunisie : bilan de {mfr}" if mfr[0] not in "aeiouéo" else f"Appels d'offres publics en Tunisie : bilan d'{mfr}"
    titre_ar = f"طلبات العروض العمومية في تونس: حصيلة {mar}"
    sp = candidats_sous_pages(cs, recs)

    # ---- en bref : uniquement des chiffres
    bref = [cs.L(f"<b>{nb(total)}</b> appels d’offres publiés en {mfr} sur le portail HAICOP ont été relevés par notre robot"
                 + (f" (publications du {cs.dfr(c['premiere_publication'])} au {cs.dfr(c['derniere_publication'])}, sur {c['jours_de_publication']} jours de publication)." if total else "."),
                 f"تم رصد <b>{cs.ISO(nb(total))}</b> طلب عروض نُشرت في {mar} على بوابة الهيئة العليا للطلب العمومي"
                 + (f" (من {cs.ISO(cs.dfr(c['premiere_publication']))} إلى {cs.ISO(cs.dfr(c['derniere_publication']))}، على {cs.ISO(c['jours_de_publication'])} أيام)." if total else "."))]
    rm = classement(recs, "metier", SPECIAUX_M)
    if rm:
        mm = cs.M_PAR_NOM[rm[0][0]]
        bref.append(cs.L(f"Métier le plus fréquent : <b>{cs.E(mm[2])}</b> ({nb(rm[0][1])}, soit {pct(rm[0][1], total)} %).",
                         f"الاختصاص الأكثر تكرارًا: <b>{mm[3]}</b> ({cs.ISO(nb(rm[0][1]))}، أي {cs.ISO(str(pct(rm[0][1], total)) + ' %')})."))
    rg = classement(recs, "gouvernorat", SPECIAUX_G)
    if rg:
        g = cs.G_PAR_NOM[rg[0][0]]
        bref.append(cs.L(f"Gouvernorat le plus fréquent : <b>{cs.E(g[0])}</b> ({nb(rg[0][1])}, soit {pct(rg[0][1], total)} %).",
                         f"الولاية الأكثر تكرارًا: <b>{g[2]}</b> ({cs.ISO(nb(rg[0][1]))}، أي {cs.ISO(str(pct(rg[0][1], total)) + ' %')})."))
    ra = classement(recs, "acheteur")
    if ra:
        bref.append(cs.L(f"Acheteur public le plus actif : <b><bdi>{cs.E(ra[0][0])}</bdi></b> ({nb(ra[0][1])} appels d’offres).",
                         f"المشتري العمومي الأكثر نشاطًا: <b><bdi>{cs.E(ra[0][0])}</bdi></b> ({cs.ISO(nb(ra[0][1]))} طلب عروض)."))
    if c["jour_max"] and c["jours_de_publication"] >= MIN_LIGNES:
        bref.append(cs.L(f"Jour le plus chargé : {cs.dfr(c['jour_max'][0])} ({nb(c['jour_max'][1])} appels d’offres publiés).",
                         f"اليوم الأكثر نشرًا: {cs.ISO(cs.dfr(c['jour_max'][0]))} ({cs.ISO(nb(c['jour_max'][1]))} طلب عروض)."))
    if c["ventes"]:
        bref.append(cs.L(f"{nb(c['ventes'])} ventes aux enchères publiées par la Douane ont aussi été relevées.",
                         f"تم رصد {cs.ISO(nb(c['ventes']))} بيوعات بالمزاد نشرتها الديوانة."))
    genre_evo, phrase_evo = evolution(cs, hist, m, e)
    bref.append(phrase_evo)
    avert = ""
    if not e.get("complet") and hist.get("robot_depuis"):
        rd = cs.dfr(hist["robot_depuis"])
        avert = ('<p class="avert" id="partiel">' + cs.L(f"Notre robot lit le portail HAICOP depuis le {rd} : les appels d’offres publiés avant cette date n’ont été relevés qu’en partie.", f"يقرأ برنامجنا بوابة الهيئة منذ {cs.ISO(rd)}: طلبات العروض المنشورة قبل هذا التاريخ رُصدت جزئيًا فقط.") + "</p>")

    liens_sp = ""
    if sp:
        g_l = [x for x in sp if x[0] == "gouvernorat"]
        m_l = [x for x in sp if x[0] == "metier"]
        def ligne(lst, fr, ar):
            if not lst:
                return ""
            return (f'<p><b>{cs.L(fr, ar)}</b> : ' + ", ".join(
                f'<a href="{t}/{s}/">{cs.L(cs.E(lfr), lar)}</a> ({cs.ISO(nb(n))})' for t, nom, s, n, lfr, lar in lst) + "</p>")
        liens_sp = (f'<section class="carte" id="sous-pages"><h2>{cs.L("Le rapport de chaque gouvernorat et de chaque métier", "تقرير كل ولاية وكل اختصاص")}</h2>'
                    + ligne(g_l, "Gouvernorats", "الولايات") + ligne(m_l, "Métiers", "الاختصاصات")
                    + f'<p class="rap-note">{cs.L(f"Seulement ceux qui ont au moins {MIN_SOUS_PAGE} appels d’offres ce mois-ci.", f"فقط ما له {cs.ISO(MIN_SOUS_PAGE)} طلبات عروض على الأقل هذا الشهر.")}</p></section>')

    hero = f"""{fil_rapport(cs, racine, [("../", "Rapports du mois", "تقارير الشهر"), ("", mfr.capitalize(), mar)])}
    <h1>{cs.L(cs.E(titre_fr), titre_ar)}</h1>
{signature(cs)}
    <p class="intro">{statut_html(cs, m, e)}</p>
    {bloc_partage(cs, url, titre_fr, titre_ar, True)}"""
    contenu = f"""<section class="carte rap-bref-carte" id="en-bref">
  <h2>{cs.L("En bref", "باختصار")}</h2>
  <ul class="rap-bref">{liste_bref(bref, genre_evo)}</ul>
  {avert}
</section>
{bloc_repartition(cs, "Par métier", "حسب الاختصاص", c["par_metier"], total, "metier", "par-metier")}
{bloc_repartition(cs, "Par gouvernorat", "حسب الولاية", c["par_gouvernorat"], total, "gouvernorat", "par-gouvernorat")}
{bloc_acheteurs(cs, recs, total)}
{bloc_delais(cs, c)}
{bloc_procedures(cs, c)}
{bloc_ventes(cs, c, racine, m)}
{liens_sp}
<section class="carte" id="plus-loin">
  <h2>{cs.L("Aller plus loin", "للمزيد")}</h2>
  <p><a href="{racine}">{cs.L("Les appels d’offres encore ouverts", "طلبات العروض المفتوحة")}</a> · <a href="{racine}#metiers">{cs.L("Par métier", "حسب الاختصاص")}</a> · <a href="{racine}#gouvernorats">{cs.L("Par gouvernorat", "حسب الولاية")}</a> · <a href="../">{cs.L("Tous les rapports", "كل التقارير")}</a></p>
</section>
{methode(cs)}
{citer(cs, url, titre_fr, e)}
{bloc_partage(cs, url, titre_fr, titre_ar, False)}"""
    faq = []
    if total:
        faq.append((f"Combien d'appels d'offres publics ont été publiés en Tunisie en {mfr} ?",
                    f"Notre robot a relevé {nb(total)} appels d'offres publiés en {mfr} sur le portail officiel HAICOP "
                    + ("(chiffres définitifs)." if e.get("fige") else f"(chiffres au {cs.dfr(e['derniere_date'])}).")))
    if rm:
        faq.append((f"Quel métier a le plus d'appels d'offres en {mfr} ?",
                    f"{cs.M_PAR_NOM[rm[0][0]][2]}, avec {nb(rm[0][1])} appels d'offres sur {nb(total)} relevés."))
    if rg:
        faq.append((f"Quel gouvernorat a le plus d'appels d'offres en {mfr} ?",
                    f"{rg[0][0]}, avec {nb(rg[0][1])} appels d'offres sur {nb(total)} relevés."))
    fil_items = [("Accueil", cs.URL_SITE), ("Rapports du mois", cs.URL_SITE + "rapports/"), (mfr, url)]
    titre = f"{titre_fr} ({nb(total)} relevés) | Alertes appels d'offres"
    desc = (f"Bilan de {mfr} des appels d'offres publics tunisiens relevés sur le portail officiel HAICOP : {nb(total)} appels d'offres, "
            f"par métier, par gouvernorat et par acheteur public. Chiffres vérifiables, gratuit. {titre_ar}.")
    html = cs.page(f"rapports/{m}/", racine, titre, description_rapport(desc), hero, contenu, v, etat, jsonld(cs, url, titre_fr, e, fil_items, faq))
    pages = [(f"rapports/{m}/", html, e["derniere_date"])]
    for t, nom, slug, n, lfr, lar in sp:
        pages.append(page_sous(cs, hist, m, e, t, nom, slug, lfr, lar, v, etat))
    return pages


def page_sous(cs, hist, m, e, t, nom, slug, lfr, lar, v, etat):
    racine = "../../../../"
    chemin = f"rapports/{m}/{t}/{slug}/"
    url = cs.URL_SITE + chemin
    mfr, mar = mois_fr(m), mois_ar(m)
    tous = list(e["appels_offres"].values())
    recs = [r for r in tous if r[t] == nom]
    n, total = len(recs), len(tous)
    if t == "gouvernorat":
        titre_fr, titre_ar = f"Appels d'offres à {lfr} : {mfr}", f"طلبات العروض في ولاية {lar}: {mar}"
        part_fr = f"soit {pct(n, total)} % des {nb(total)} relevés dans toute la Tunisie"
        part_ar = f"أي {cs.ISO(str(pct(n, total)) + ' %')} من {cs.ISO(nb(total))} مرصودة في كامل تونس"
        rep = bloc_repartition(cs, "Par métier", "حسب الاختصاص", dict(compte(recs, "metier")), n, "metier", "par-metier")
        lien_site = f"{racine}gouvernorat/{slug}/"
    else:
        titre_fr, titre_ar = f"Appels d'offres {lfr} : {mfr}", f"طلبات العروض ({lar}): {mar}"
        part_fr = f"soit {pct(n, total)} % des {nb(total)} relevés tous métiers confondus"
        part_ar = f"أي {cs.ISO(str(pct(n, total)) + ' %')} من {cs.ISO(nb(total))} مرصودة في كل الاختصاصات"
        rep = bloc_repartition(cs, "Par gouvernorat", "حسب الولاية", dict(compte(recs, "gouvernorat")), n, "gouvernorat", "par-gouvernorat")
        lien_site = f"{racine}metier/{slug}/"
    c = chiffres(recs, [])
    bref = [cs.L(f"<b>{nb(n)}</b> appels d’offres publiés en {mfr} relevés ({part_fr}).",
                 f"<b>{cs.ISO(nb(n))}</b> طلب عروض نُشرت في {mar} ({part_ar}).")]
    ra = classement(recs, "acheteur")
    if ra:
        bref.append(cs.L(f"Acheteur public le plus actif : <b><bdi>{cs.E(ra[0][0])}</bdi></b> ({nb(ra[0][1])} appels d’offres).",
                         f"المشتري العمومي الأكثر نشاطًا: <b><bdi>{cs.E(ra[0][0])}</bdi></b> ({cs.ISO(nb(ra[0][1]))} طلب عروض)."))
    genre_evo, phrase_evo = evolution(cs, hist, m, e, filtre=lambda r: r[t] == nom)
    bref.append(phrase_evo)
    hero = f"""{fil_rapport(cs, racine, [("../../../", "Rapports du mois", "تقارير الشهر"), ("../../", mfr.capitalize(), mar), ("", lfr, lar)])}
    <h1>{cs.L(cs.E(titre_fr), titre_ar)}</h1>
{signature(cs)}
    <p class="intro">{statut_html(cs, m, e)}</p>
    {bloc_partage(cs, url, titre_fr, titre_ar, True)}"""
    contenu = f"""<section class="carte rap-bref-carte" id="en-bref">
  <h2>{cs.L("En bref", "باختصار")}</h2>
  <ul class="rap-bref">{liste_bref(bref, genre_evo)}</ul>
</section>
{rep}
{bloc_acheteurs(cs, recs, n)}
{bloc_delais(cs, c)}
<section class="carte" id="fiches">
  <h2>{cs.L(f"Les {nb(n)} appels d’offres du mois", f"طلبات العروض الـ{cs.ISO(nb(n))} لهذا الشهر")}</h2>
  <p class="rap-note">{cs.L("Chaque titre ouvre la fiche officielle de la HAICOP (seule elle fait foi).", "كل عنوان يفتح البطاقة الرسمية للهيئة (هي وحدها المرجع).")}</p>
  {liste_fiches(cs, recs)}
</section>
<section class="carte" id="plus-loin">
  <h2>{cs.L("Aller plus loin", "للمزيد")}</h2>
  <p><a href="{lien_site}">{cs.L(f"Les appels d’offres encore ouverts : {cs.E(lfr)}", f"طلبات العروض المفتوحة: {lar}")}</a> · <a href="../../">{cs.L(f"Bilan national de {mfr}", f"الحصيلة الوطنية لشهر {mar}")}</a> · <a href="../../../">{cs.L("Tous les rapports", "كل التقارير")}</a></p>
</section>
{methode(cs)}
{citer(cs, url, titre_fr, e)}
{bloc_partage(cs, url, titre_fr, titre_ar, False)}"""
    faq = [(f"Combien d'appels d'offres {('à ' + lfr) if t == 'gouvernorat' else '« ' + lfr + ' »'} en {mfr} ?",
            f"Notre robot a relevé {nb(n)} appels d'offres publiés en {mfr} sur le portail officiel HAICOP "
            + ("(chiffres définitifs)." if e.get("fige") else f"(chiffres au {cs.dfr(e['derniere_date'])})."))]
    fil_items = [("Accueil", cs.URL_SITE), ("Rapports du mois", cs.URL_SITE + "rapports/"), (mfr, f"{cs.URL_SITE}rapports/{m}/"), (lfr, url)]
    titre = f"{titre_fr} ({nb(n)} relevés) | Alertes appels d'offres"
    desc = (f"{titre_fr} : {nb(n)} appels d'offres publics relevés sur le portail officiel HAICOP, par acheteur, avec la liste et le lien "
            f"vers chaque fiche officielle. Chiffres vérifiables, gratuit. {titre_ar}.")
    html = cs.page(chemin, racine, titre, description_rapport(desc), hero, contenu, v, etat, jsonld(cs, url, titre_fr, e, fil_items, faq))
    return (chemin, html, e["derniere_date"])


def charger_ventes(chemin, cs):
    """Toutes les ventes aux enchères connues (ouvertes ou non), champs vérifiés."""
    try:
        with open(chemin, encoding="utf-8") as f:
            ventes = (json.load(f) or {}).get("ventes") or {}
    except (OSError, ValueError, AttributeError):
        ventes = {}
    if isinstance(ventes, dict):
        ventes = list(ventes.values())
    res = []
    for v in ventes if isinstance(ventes, list) else []:
        if not isinstance(v, dict) or not re.fullmatch(r"Vente-[0-9a-f]{10}", str(v.get("id") or "")):
            continue
        pub = str(v.get("date_publication") or "")
        if not DATE.match(pub):
            continue
        res.append({"id": v["id"], "date_publication": pub,
                    "gouvernorat": v.get("gouvernorat") if v.get("gouvernorat") in cs.G_PAR_NOM else "National / non précisé"})
    return res
