# -*- coding: utf-8 -*-
"""
Résumé court, dans l'autre langue, de l'objet d'un appel d'offres (arabe -> français, français -> arabe).
SANS service payant ni clé : un glossaire maison du vocabulaire des marchés publics tunisiens.

    resumer("مشروع تهيئة مركز رعاية المسنين بقرمبالية")
        -> {"langue": "fr", "texte": "Aménagement — centre pour personnes âgées — Grombalia", "taux": 1.0}

Règle d'honnêteté : on ne traduit QUE les mots du glossaire, on n'invente jamais. Si moins de la moitié
des mots importants de l'objet sont reconnus, resumer() renvoie None (rien n'est affiché).
Le site affiche le résumé avec la mention « traduction automatique approximative ».
"""
import re
import unicodedata

# Une ligne par entrée :  arabe (variantes |) ; français affiché ; variantes françaises (|) ; catégorie
#   A = action (début du résumé)   O = objet   J = adjectif (suit l'objet)   L = lieu
#   S = mot connu mais non affiché (projet, lot, année…)
# Le premier mot arabe est celui écrit dans les résumés en arabe. Les mots de plusieurs mots sont reconnus d'abord.
TABLE = """
تهيئة ; aménagement ; amenagement|amenagements ; A
إعادة تهيئة ; réaménagement ; reamenagement|reamenagements ; A
بناء ; construction ; construction|constructions ; A
إعادة بناء ; reconstruction ; reconstruction ; A
تشييد ; construction ; edification ; A
صيانة ; maintenance ; maintenance|entretien ; A
اقتناء|شراء|اشتراء ; acquisition ; acquisition|acquisitions|achat|achats|aquisition ; A
تزويد|توريد|التزود ; fourniture ; fourniture|approvisionnement ; A
دراسة|دراسات ; étude ; etude|etudes ; A
هدم ; démolition ; demolition ; A
ترميم ; restauration ; restaurer|refection|refections ; A
تشغيل ; mise en marche ; mise en marche|mise en service ; A
تعليب ; conditionnement ; conditionnement ; A
فرقة ; brigade ; brigade ; O
تدخل ; intervention ; intervention ; O
تجهيزات طبية ; équipements médicaux ; equipements medicaux ; O
تأهيل|إعادة تأهيل ; réhabilitation ; rehabilitation ; A
تعبيد ; bitumage ; bitumage|revetement ; A
تبليط ; dallage ; dallage|carrelage ; A
توسعة|توسيع ; extension ; extension|agrandissement ; A
إنجاز ; réalisation ; realisation ; A
تركيز ; installation ; installation|mise en place ; A
تركيب ; montage ; montage|pose ; A
تجديد ; renouvellement ; renouvellement|renovation ; A
إصلاح ; réparation ; reparation|reparations ; A
تنظيف ; nettoyage ; nettoyage ; A
حراسة ; gardiennage ; gardiennage ; A
إطعام|تغذية|تغدية ; restauration ; restauration ; A
نقل ; transport ; transport|transports ; A
تكوين ; formation ; formation|formations ; A
كراء|تسويغ ; location ; location ; A
تأمين ; assurance ; assurance|assurances ; A
مراقبة ; contrôle ; controle|surveillance ; A
تدقيق ; audit ; audit ; A
استغلال ; exploitation ; exploitation ; A
إحداث ; création ; creation ; A
تطهير ; assainissement ; assainissement ; A
تصريف ; évacuation ; evacuation|drainage ; A
تجهيز ; équipement ; equiper ; A
جمع|رفع ; collecte ; collecte|ramassage ; A
معالجة ; traitement ; traitement ; A
طلاء|دهن ; peinture ; peinture|peintures ; A
عزل ; isolation ; isolation ; A
عزل مائي ; étanchéité ; etancheite ; A
حفر ; forage ; forage|forages|creusement ; A
تشجير ; plantation ; plantation|plantations|reboisement ; A
ربط ; raccordement ; raccordement|branchement|branchements ; A
إيواء ; hébergement ; hebergement ; A
طباعة|طبع ; impression ; impression ; A
تصميم ; conception ; conception ; A
متابعة ; suivi ; suivi ; A
مساعدة فنية ; assistance technique ; assistance technique ; A
اختيار ; choix ; choix|selection ; A
تعيين ; désignation ; designation ; A
بيع ; vente ; vente|ventes ; A
بيع بالمزاد|بيع بالمزاد العلني ; vente aux enchères ; vente aux encheres|ventes aux encheres|vente encheres ; A
مزاد ; enchères ; encheres|enchere ; S
قطع سيارات ; pièces automobiles ; pieces automobiles|pieces auto ; O
وسائل نقل ; moyens de transport ; moyens de transport ; O
ملابس جاهزة ; vêtements confectionnés ; vetements confectionnes ; O
حبوب ; graines ; graine|graines|cereales ; O
أقمشة ; tissus ; tissu|tissus ; O
دراجات نارية ; motos ; moto|motos ; O
أجهزة ; appareils ; appareil|appareils ; O
مكيفات ; climatiseurs ; climatiseur|climatiseurs ; O
أشغال ; travaux ; travaux ; A
استكمال|إتمام ; achèvement ; achevement|parachevement ; A
جرد ; inventaire ; inventaire ; A
إيداع ; dépôt ; depot ; A
إعداد ; élaboration ; elaboration|preparation ; A
مد ; pose ; ; A
تكييف ; climatisation ; climatisation ; O
إنارة|تنوير ; éclairage ; eclairage ; O
إنارة عمومية ; éclairage public ; eclairage public ; O
كهرباء ; électricité ; electricite ; O
مركز ; centre ; centre|centres ; O
مركز رعاية المسنين ; centre pour personnes âgées ; ; O
مسنين ; personnes âgées ; personnes agees ; O
رعاية ; soins ; soins ; O
مدرسة ; école ; ecole|ecoles ; O
مدرسة إعدادية ; collège ; college|colleges ; O
مدرسة ابتدائية ; école primaire ; ecole primaire ; O
معهد ; lycée ; lycee|lycees|institut|instituts ; O
معهد ثانوي ; lycée secondaire ; lycee secondaire ; O
كلية ; faculté ; faculte ; O
جامعة ; université ; universite ; O
مبيت ; foyer ; foyer|internat ; O
مطعم ; restaurant ; restaurant|restaurants ; O
مطعم جامعي ; restaurant universitaire ; restaurant universitaire ; O
مستشفى ; hôpital ; hopital|hopitaux ; O
مستوصف ; dispensaire ; dispensaire ; O
مركز صحة أساسية ; centre de santé de base ; centre de sante de base ; O
محطة استشفائية ; station thermale ; station thermale ; O
مخبر ; laboratoire ; laboratoire|laboratoires ; O
طريق ; route ; route ; O
طرقات|طرق ; routes ; routes|voirie|chaussee|chaussees ; O
مسالك|مسلك ; pistes ; piste|pistes ; O
أرصفة|رصيف ; trottoirs ; trottoir|trottoirs ; O
جسر ; pont ; pont|ponts ; O
معبر ; ouvrage de franchissement ; ouvrage de franchissement ; O
وادي|واد ; oued ; oued ; O
سد ; barrage ; barrage|barrages ; O
بئر|آبار ; puits ; puits ; O
شبكة ; réseau ; reseau|reseaux ; O
قنوات ; canalisations ; canalisation|canalisations|conduites ; O
مياه|ماء ; eau ; eau|eaux ; O
مياه مستعملة ; eaux usées ; eaux usees ; O
ماء صالح للشرب ; eau potable ; eau potable ; O
ري ; irrigation ; irrigation ; O
منطقة سقوية ; zone d'irrigation ; zone irrigation|perimetre irrigue ; O
مربض|مرابض|مأوى ; parking ; parking|parkings ; O
مربض للسيارات|مأوى سيارات ; parking ; parc de stationnement ; O
ساحة ; esplanade ; esplanade|cour|place ; O
فضاء|فضاءات ; espaces ; espace|espaces ; O
قاعة ; salle ; salle|salles ; O
قاعة رياضة|قاعة رياضية ; salle de sport ; salle de sport|salle sport|salle omnisport ; O
ملعب ; stade ; stade|stades|terrain ; O
مركب ; complexe ; complexe ; O
مركب ثقافي ; complexe culturel ; complexe culturel ; O
دار الشباب ; maison des jeunes ; maison des jeunes ; O
دار الثقافة ; maison de la culture ; maison de la culture ; O
مقر ; siège ; siege ; O
مندوبية جهوية ; délégation régionale ; delegation regionale ; O
مندوبية ; délégation ; ; O
مندوبية جهوية للمرأة والأسرة ; délégation régionale de la femme et de la famille ; ; O
بلدية ; municipalité ; municipalite|commune ; O
إدارة ; administration ; administration|direction ; O
مكتب ; bureau ; bureau|bureaux ; O
مكاتب دراسات|مكتب دراسات ; bureaux d'études ; bureau etudes|bureaux etudes|bureau d etudes ; O
مهندسين معماريين|مهندس معماري ; architectes ; architecte|architectes ; O
مهندسين|مهندس ; ingénieurs ; ingenieur|ingenieurs ; O
مستشارين|مستشار ; conseils ; conseil|conseils|consultant|consultants ; O
ملفات|ملف ; dossiers ; dossier|dossiers ; O
عرض|عروض ; offres ; offre|offres ; O
عرض خدمات ; offre de services ; offre de services ; O
خدمات|خدمة ; services ; service|services|prestation|prestations ; O
إطارات ; cadres ; cadres ; O
أعوان ; agents ; agent|agents|personnel ; O
شركة ; société ; societe|societes|compagnie ; O
شركة جهوية للنقل ; société régionale de transport ; societe regionale de transport ; O
حرس وطني ; garde nationale ; garde nationale|garde national ; O
مركز الحرس الوطني ; poste de la garde nationale ; poste de la garde nationale|poste garde nationale ; O
أمن ; sécurité ; securite ; O
أكاديمية ; académie ; academie ; O
علوم أمنية ; sciences de la sécurité ; ; O
مغسلة ; buanderie ; buanderie ; O
مشربة ; cafétéria ; cafeteria|buvette ; O
مصحة ; infirmerie ; infirmerie|clinique ; O
مرأة ; femme ; femme|femmes ; O
أسرة ; famille ; famille|familles ; O
طفولة ; enfance ; enfance ; O
روضة ; jardin d'enfants ; jardin enfants|jardin d enfants ; O
مسجد|جامع ; mosquée ; mosquee ; O
سوق ; marché ; marche municipal ; O
مسلخ ; abattoir ; abattoir ; O
مقبرة ; cimetière ; cimetiere ; O
حديقة|منتزه ; jardin ; jardin|parc ; O
سياج ; clôture ; cloture|clotures ; O
حائط|جدار ; mur ; mur|murs ; O
سقف|أسقف ; toiture ; toiture|toitures ; O
بناية|مبنى|مباني ; bâtiment ; batiment|batiments|immeuble ; O
مساكن|مسكن ; logements ; logement|logements ; O
شقق|شقة ; appartements ; appartement|appartements ; O
تقسيم ; lotissement ; lotissement ; O
حي ; cité ; cite|quartier ; O
مدينة ; ville ; ville ; O
قرية ; village ; village ; O
محطة ; station ; station|gare ; O
ميناء ; port ; port ; O
مطار ; aéroport ; aeroport ; O
سكة حديدية ; voie ferrée ; voie ferree ; O
معدات ; équipements ; equipement|equipements|materiel|materiels ; O
تجهيزات ; équipements ; ; O
مواد ; produits ; produit|produits|matieres ; O
مواد تنظيف ; produits de nettoyage ; produits de nettoyage|produits nettoyage ; O
مواد غذائية ; denrées alimentaires ; denrees alimentaires|produits alimentaires|denrees ; O
لوازم ; fournitures ; fournitures ; O
لوازم مكتبية|أدوات مكتبية ; fournitures de bureau ; fournitures de bureau ; O
ورق ; papier ; papier ; O
أثاث ; mobilier ; mobilier|meubles|meuble ; O
رفوف ; rayonnage ; rayonnage|rayonnages|etageres ; O
حواسيب|حاسوب ; ordinateurs ; ordinateur|ordinateurs ; O
معدات إعلامية ; matériel informatique ; materiel informatique ; O
منظومة ; système ; systeme|application ; O
برمجيات ; logiciels ; logiciel|logiciels ; O
قاعدة بيانات ; base de données ; base de donnees|base donnees ; O
طابعات ; imprimantes ; imprimante|imprimantes ; O
أدوية ; médicaments ; medicament|medicaments ; O
كواشف ; réactifs ; reactif|reactifs ; O
مستلزمات طبية ; consommables médicaux ; consommables medicaux ; O
مستلزمات ; consommables ; consommable|consommables ; O
لحوم ; viandes ; viande|viandes ; O
خبز ; pain ; pain ; O
حليب ; lait ; lait ; O
خضر|خضروات ; légumes ; legume|legumes ; O
غلال ; fruits ; fruit|fruits ; O
أرز ; riz ; riz ; O
سميد ; semoule ; semoule ; O
زيت ; huile ; huile ; O
سكر ; sucre ; sucre ; O
مرطبات ; pâtisseries ; patisserie|patisseries ; O
أغذية|غذاء ; nourriture ; nourriture|alimentation ; O
مولد كهربائي ; groupe électrogène ; groupe electrogene ; O
محولات|محول ; transformateurs ; transformateur|transformateurs ; O
عوازل ; isolateurs ; isolateur|isolateurs ; O
كوابل|أسلاك ; câbles ; cable|cables ; O
عربات|عربة ; véhicules ; vehicule|vehicules ; O
سيارات|سيارة ; voitures ; voiture|voitures ; O
شاحنات|شاحنة ; camions ; camion|camions ; O
حافلات|حافلة ; bus ; bus|autobus ; O
آليات ; engins ; engin|engins ; O
قطع غيار ; pièces de rechange ; pieces de rechange|pieces rechange ; O
محروقات ; carburant ; carburant|carburants ; O
إطارات مطاطية ; pneus ; pneu|pneus|pneumatiques ; O
محركات|محرك ; moteurs ; moteur|moteurs ; O
مضخات|مضخة ; pompes ; pompe|pompes ; O
نفايات|فضلات ; déchets ; dechet|dechets|ordures ; O
بضائع ; marchandises ; marchandise|marchandises ; O
مواشي ; bétail ; betail ; O
أغنام ; moutons ; moutons|ovins ; O
أبقار ; bovins ; bovins|vaches ; O
هواتف ; téléphones ; telephone|telephones ; O
ملابس ; vêtements ; vetement|vetements ; O
أحذية ; chaussures ; chaussure|chaussures ; O
محامي|محام ; avocat ; avocat|avocats|avoact ; O
محاكم|محكمة ; tribunaux ; tribunal|tribunaux ; O
هيئات قضائية ; instances judiciaires ; instance judiciaire|instances judiciaires ; O
مسبح ; piscine ; piscine ; O
مكتبة ; bibliothèque ; bibliotheque ; O
متحف ; musée ; musee ; O
سجن ; prison ; prison ; O
ثكنة ; caserne ; caserne ; O
مستودع|مخزن|مخازن ; entrepôt ; entrepot|entrepots|magasin|magasins ; O
مخزون ; stocks ; stock|stocks ; O
محلي ; local ; local|locale|locaux ; J
جهوي ; régional ; regional|regionale|regionaux ; J
وطني ; national ; national|nationale ; J
جامعي ; universitaire ; universitaire|universitaires ; J
ريفي ; rural ; rural|rurale|rurales|ruraux ; J
غابي ; forestier ; forestier|forestiere|forestieres|forestiers ; J
فلاحي ; agricole ; agricole|agricoles ; J
خارجي ; extérieur ; exterieur|exterieure|exterieurs ; J
داخلي ; intérieur ; interieur|interieure|interieurs ; J
عمومي ; public ; public|publique|publics ; J
رياضي ; sportif ; sportif|sportive|sportifs ; J
ثقافي ; culturel ; culturel|culturelle|culturels ; J
صحي ; sanitaire ; sanitaire|sanitaires ; J
فني|تقني ; technique ; technique|techniques ; J
كهربائي ; électrique ; electrique|electriques ; J
مائي ; hydraulique ; hydraulique|hydrauliques ; J
مستعمل ; usagé ; usage|usages|usagee|usagees|occasion ; J
جديد ; neuf ; neuf|neufs|neuve|nouveau|nouvelle ; J
مختلف|متعدد ; divers ; divers|diverse|diverses ; S
رئيسي ; principal ; principal|principaux|principale ; J
ثانوي ; secondaire ; secondaire|secondaires ; J
إعدادي ; préparatoire ; preparatoire ; J
ابتدائي ; primaire ; primaire ; J
صناعي ; industriel ; industriel|industrielle|industriels ; J
سياحي ; touristique ; touristique ; J
أمني ; de sécurité ; ; J
إعلامي ; informatique ; informatique|informatiques ; J
طبي ; médical ; medical|medicale|medicaux|medicales ; J
غذائي ; alimentaire ; alimentaire|alimentaires ; J
مكتبي ; de bureau ; ; J
مشروع ; projet ; projet|projets ; S
لفائدة|لحساب ; au profit de ; profit ; S
بعنوان ; au titre de ; titre ; S
سنة ; année ; annee ; S
عدد|رقم ; numéro ; numero ; S
قسط|أقساط|قسطا ; lot ; lot|lots ; S
طلب عروض ; appel d'offres ; appel offres|appel d offres ; S
استشارة ; consultation ; consultation ; S
إعلان ; avis ; avis ; S
كلم ; km ; km ; S
مستوى ; niveau ; niveau ; S
معتمدية ; délégation ; delegation ; S
ولاية ; gouvernorat ; gouvernorat ; S
كمية ; quantité ; quantite ; S
مجموعة ; ensemble ; ensemble|groupe|groupes ; S
لأوفر عارض|أوفر عارض ; au plus offrant ; plus offrant ; S
ظروف مغلقة ; plis fermés ; plis fermes ; S
أريانة ; Ariana ; ariana ; L
باجة ; Béja ; beja ; L
بن عروس ; Ben Arous ; ben arous ; L
بنزرت ; Bizerte ; bizerte ; L
قابس ; Gabès ; gabes ; L
قفصة ; Gafsa ; gafsa ; L
جندوبة ; Jendouba ; jendouba ; L
القيروان ; Kairouan ; kairouan ; L
القصرين ; Kasserine ; kasserine ; L
قبلي ; Kébili ; kebili ; L
الكاف ; Le Kef ; kef|le kef ; L
المهدية ; Mahdia ; mahdia ; L
منوبة ; La Manouba ; manouba|la manouba ; L
مدنين ; Médenine ; medenine ; L
المنستير ; Monastir ; monastir ; L
نابل ; Nabeul ; nabeul ; L
صفاقس ; Sfax ; sfax ; L
سيدي بوزيد ; Sidi Bouzid ; sidi bouzid ; L
سليانة ; Siliana ; siliana ; L
سوسة ; Sousse ; sousse ; L
تطاوين ; Tataouine ; tataouine ; L
توزر ; Tozeur ; tozeur ; L
تونس ; Tunis ; tunis ; L
زغوان ; Zaghouan ; zaghouan ; L
قرمبالية ; Grombalia ; grombalia ; L
منزل بوزلفة ; Menzel Bouzelfa ; menzel bouzelfa ; L
الحمامات ; Hammamet ; hammamet ; L
حمام بنت الجديدي ; Hammam Bent Jedidi ; hammam bent jedidi ; L
سيدي الجديدي ; Sidi Jedidi ; sidi jedidi ; L
بنقردان|بن قردان ; Ben Guerdane ; ben guerdane|benguerdane ; L
فوشانة ; Fouchana ; fouchana ; L
مرناق ; Mornag ; mornag ; L
المغيرة ; El Mghira ; mghira|el mghira ; L
النفيضة ; Enfidha ; enfidha|nfidha ; L
منزل بورقيبة ; Menzel Bourguiba ; menzel bourguiba ; L
جربة ; Djerba ; djerba|jerba ; L
جرجيس ; Zarzis ; zarzis ; L
ذهيبة ; Dehiba ; dehiba ; L
حزوة ; Hazoua ; hazoua ; L
رادس ; Radès ; rades ; L
حلق الوادي ; La Goulette ; goulette|la goulette ; L
قرطاج ; Carthage ; carthage ; L
درمش ; Dermech ; dermech ; L
بيرصا ; Byrsa ; byrsa ; L
المرسى ; La Marsa ; marsa|la marsa ; L
باردو ; Le Bardo ; bardo|le bardo ; L
حمام الشط ; Hammam Chott ; hammam chott|hammam chatt ; L
حمام الأنف ; Hammam Lif ; hammam lif ; L
قليبية ; Kélibia ; kelibia ; L
منزل تميم ; Menzel Temime ; menzel temime ; L
سليمان ; Soliman ; soliman ; L
الصخيرة ; La Skhira ; skhira|la skhira ; L
قرقنة ; Kerkennah ; kerkennah ; L
المكنين ; Moknine ; moknine ; L
قصر هلال ; Ksar Hellal ; ksar hellal ; L
الحامة ; El Hamma ; el hamma ; L
طبرقة ; Tabarka ; tabarka ; L
عين دراهم ; Aïn Draham ; ain draham|ain drahem ; L
غار الدماء ; Ghardimaou ; ghardimaou ; L
ماطر ; Mateur ; mateur ; L
تستور ; Testour ; testour ; L
مجاز الباب ; Medjez el-Bab ; medjez el bab ; L
الفحص ; El Fahs ; el fahs ; L
نفطة ; Nefta ; nefta ; L
دوز ; Douz ; douz ; L
المتلوي ; Métlaoui ; metlaoui ; L
سبيطلة ; Sbeïtla ; sbeitla ; L
الجم ; El Jem ; el jem ; L
القلعة الكبرى ; Kalâa Kebira ; kalaa kebira ; L
قلعة الأندلس ; Kalaat el-Andalous ; kalaat andalous|kalaat landalous|kalaat el andalous ; L
سكرة ; La Soukra ; soukra|la soukra ; L
طبربة ; Tebourba ; tebourba ; L
ماتلين ; Metline ; metline ; L
برج العامري ; Borj El Amri ; borj el amri ; L
سيدي سالم ; Sidi Salem ; sidi salem ; L
بنقردان ; Ben Guerdane ; ; L
"""

# Mots outils : ni comptés, ni affichés
STOP_AR = set("""من في على إلى الى عن مع أو او ثم التي الذي الذين هذا هذه ذلك تلك كل بين حول لدى عند خلال ضمن حسب
و ب ل ف ك ال لـ بـ وـ قصد بها به لها له ما لا ان أن إن""".split())
STOP_FR = set("""de du des la le les l d a au aux et en pour sur dans par avec un une ou sous son sa ses leur leurs qui que
ce cette ces cet n no nos notre votre se s y il elle ils lors entre chez vers apres avant pendant durant selon tout tous
toute toutes autre autres meme plus moins tres bien al el qu j c m t afin dont
deux trois quatre cinq six sept huit neuf dix simple double""".split())

PREFIXES_AR = ("و", "ف")          # et, alors
PREP_AR = ("ب", "ل", "ك")         # à/dans, pour, comme


def normaliser(texte):
    """Minuscules, sans accents ; arabe sans voyelles ni tatweel (أإآٱ→ا, ة→ه, ى→ي)."""
    t = unicodedata.normalize("NFKD", (texte or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub("[ً-ْـٰ]", "", t)
    t = t.translate(str.maketrans("أإآٱةى’`", "ااااهي''"))
    return t


def _formes_ar(mot):
    """Formes possibles d'un mot arabe sans ses préfixes (و، ف، ب، ل، ك، ال، لل), la forme entière d'abord."""
    formes = [mot]
    bases = [mot]
    if mot[:1] in PREFIXES_AR and len(mot) > 3:
        bases.append(mot[1:])
    for b in list(bases):
        if b[:1] in PREP_AR and len(b) > 3:
            bases.append(b[1:])
    for b in bases:
        formes.append(b)
        if b.startswith("ال") and len(b) > 3:
            formes.append(b[2:])
        if b.startswith("ل") and b[1:].startswith("ل") and len(b) > 3:   # لل = ل + ال
            formes.append(b[2:])
    vus, res = set(), []
    for f in formes:
        if f and f not in vus:
            vus.add(f)
            res.append(f)
    return res


def _sans_al(mot):
    return mot[2:] if mot.startswith("ال") and len(mot) > 3 else mot


def _charger():
    ar, fr = {}, {}          # clé (tuple de mots normalisés) -> (affichage dans l'autre langue, catégorie)
    entrees = 0
    for ligne in TABLE.strip().splitlines():
        if not ligne.strip():
            continue
        p = [x.strip() for x in ligne.split(";")]
        if len(p) != 4:
            raise ValueError("ligne du glossaire mal écrite : " + ligne)
        ars, fr_aff, frs, cat = p
        ars = [a.strip() for a in ars.split("|") if a.strip()]
        entrees += 1
        for a in ars:
            cle = tuple(_sans_al(normaliser(m)) for m in a.split())
            ar.setdefault(cle, (fr_aff, cat))
        for f in [f.strip() for f in frs.split("|") if f.strip()]:
            cle = tuple(m for m in re.split(r"[^a-z0-9]+", normaliser(f)) if m)
            fr.setdefault(cle, (ars[0], cat))
    return ar, fr, entrees


GLOSSAIRE_AR, GLOSSAIRE_FR, NB_ENTREES = _charger()
LONGUEUR_MAX_AR = max(len(k) for k in GLOSSAIRE_AR)
LONGUEUR_MAX_FR = max(len(k) for k in GLOSSAIRE_FR)
ARABE = re.compile(r"[؀-ۿ]")


def _mots_ar(texte):
    t = normaliser(texte)
    return [m for m in re.split(r"[^ء-ي0-9]+", t) if m]


def _mots_fr(texte):
    t = normaliser(texte)
    return [m for m in re.split(r"[^a-z0-9]+", t) if m]


def _chercher_ar(mots, i):
    """Plus longue entrée du glossaire qui commence au mot i. Renvoie (longueur, (affichage, cat), préfixé)."""
    for n in range(min(LONGUEUR_MAX_AR, len(mots) - i), 0, -1):
        formes = [_formes_ar(mots[i + k]) for k in range(n)]
        # premier mot : préfixes permis ; mots suivants : seul « ال » / « لل » / « و » peut être collé
        def essais(k):
            return [_sans_al(f) for f in formes[k]] if k == 0 else [_sans_al(f) for f in formes[k][:4]]
        cles = [()]
        for k in range(n):
            cles = [c + (f,) for c in cles for f in dict.fromkeys(essais(k))][:64]
        for c in cles:
            if c in GLOSSAIRE_AR:
                prefixe = mots[i][:1] in PREFIXES_AR + PREP_AR and _sans_al(mots[i]) != c[0]
                return n, GLOSSAIRE_AR[c], prefixe
    return 0, None, False


def _chercher_fr(mots, i):
    for n in range(min(LONGUEUR_MAX_FR, len(mots) - i), 0, -1):
        bloc = mots[i:i + n]
        variantes = [tuple(bloc)]
        if n == 1 and len(bloc[0]) > 3 and bloc[0][-1] in "sx":
            variantes.append((bloc[0][:-1],))
        for v in variantes:
            if v in GLOSSAIRE_FR:
                return n, GLOSSAIRE_FR[v]
    return 0, None


def _assembler(elements, langue):
    """elements : liste de (catégorie, texte, coupure) -> « Actions — objets — lieux »."""
    actions, objets, lieux = [], [], []
    phrase, liaison = [], False
    sep = "، " if langue == "ar" else ", "
    et = " و" if langue == "ar" else " et "

    def fermer():
        if phrase:
            objets.append(" ".join(phrase))
            phrase.clear()

    for cat, txt, coupure in elements:
        if cat == "A":
            fermer()
            if txt not in actions:
                actions.append(txt)
        elif cat == "L":
            fermer()
            if txt not in lieux:
                lieux.append(txt)
        elif cat in ("O", "J"):
            if cat == "J" and not phrase and objets and liaison:
                objets[-1] = objets[-1] + et + txt          # « pistes forestières et rurales »
            elif cat == "J" and not phrase and not objets:
                continue                                      # adjectif sans nom : ignoré
            else:
                if coupure and phrase:
                    fermer()
                phrase.append(txt)
        else:   # S, mot outil, mot inconnu : fin de la phrase en cours
            fermer()
        liaison = cat == "ET"
    fermer()
    vus, obj = set(), []
    for o in objets:
        if o not in vus:
            vus.add(o)
            obj.append(o)
    morceaux = []
    if actions:
        morceaux.append(sep.join(actions[:3]))
    if obj:
        morceaux.append(sep.join(obj[:5]))
    if lieux:
        morceaux.append(sep.join(lieux[:3]))
    if not (actions or obj):
        return ""
    texte = " — ".join(morceaux)
    if langue == "fr":
        texte = texte[:1].upper() + texte[1:]
    if len(texte) > 150:
        texte = texte[:147].rsplit(" ", 1)[0].rstrip(",،—- ") + "…"
    return texte


def resumer(objet):
    """Résumé dans l'autre langue, ou None si l'objet est trop peu reconnu (on n'invente jamais)."""
    objet = str(objet or "")
    if not objet.strip():
        return None
    elements, importants, reconnus = [], 0, 0
    if len(ARABE.findall(objet)) >= max(3, len(re.findall(r"[A-Za-zÀ-ÿ]", objet))):
        langue = "fr"               # objet en arabe -> résumé en français
        mots = _mots_ar(objet)
        i = 0
        while i < len(mots):
            m = mots[i]
            if m in STOP_AR or m.isdigit() or len(m) < 2:
                elements.append(("ET" if m == "و" else "-", "", False))
                i += 1
                continue
            n, trouve, prefixe = _chercher_ar(mots, i)
            if trouve:
                importants += n
                reconnus += n
                if m[:1] == "و" and trouve[1] == "J":
                    elements.append(("ET", "", False))
                elements.append((trouve[1], trouve[0], prefixe))
                i += n
            else:
                importants += 1
                elements.append(("?", m, False))
                i += 1
    else:
        langue = "ar"               # objet en français -> résumé en arabe
        mots = _mots_fr(objet)
        i = 0
        while i < len(mots):
            m = mots[i]
            n, trouve = _chercher_fr(mots, i)
            if trouve:
                importants += n - sum(1 for x in mots[i:i + n] if x in STOP_FR)
                reconnus += n - sum(1 for x in mots[i:i + n] if x in STOP_FR)
                elements.append((trouve[1], trouve[0], False))
                i += n
                continue
            if m in STOP_FR or m.isdigit() or len(m) < 2:
                elements.append(("ET" if m == "et" else "-", "", m in ("de", "du", "des", "pour", "a", "au", "aux")))
                i += 1
                continue
            importants += 1
            elements.append(("?", m, False))
            i += 1
        # en français la coupure de phrase se fait après « de / pour / à » : un objet par complément
        elements = [(c, t, (k > 0 and elements[k - 1][0] == "-" and elements[k - 1][2])) if c in ("O", "J") else (c, t, x)
                    for k, (c, t, x) in enumerate(elements)]
    if not importants:
        return None
    taux = reconnus / importants
    if taux < 0.5:
        return None
    texte = _assembler(elements, langue)
    if not texte:
        return None
    if importants >= 4 and len(texte.split()) <= 1:
        return None        # un seul mot pour un long objet : n'aide pas le lecteur
    return {"langue": langue, "texte": texte, "taux": round(taux, 2)}


def mots_affichables():
    """Tous les textes que le glossaire peut écrire (pour vérifier qu'un résumé n'invente rien)."""
    return {v[0] for v in GLOSSAIRE_AR.values()} | {v[0] for v in GLOSSAIRE_FR.values()}


if __name__ == "__main__":
    import json
    import os
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ici = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(os.path.dirname(ici), "donnees", "appels-offres.json"), encoding="utf-8") as f:
        aos = json.load(f)["appels_offres"]
    n = 0
    for a in (aos.values() if isinstance(aos, dict) else aos):
        r = resumer(a.get("objet"))
        n += bool(r)
        print(a.get("numero"), "|", a.get("objet", "")[:90], "\n   ->", r)
    print(f"{NB_ENTREES} entrées ; {n} résumés sur {len(aos)} objets")
