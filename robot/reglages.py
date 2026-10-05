# -*- coding: utf-8 -*-
"""
Réglages à remplir par Ahmed — UN SEUL fichier (voir README, « Ce qu'Ahmed doit faire »).
Laisser "" tant que ce n'est pas prêt : le site cache alors le bouton ou affiche « Bientôt ».
Après une modification : python robot/construire_site.py (ou attendre le passage du robot quotidien).

Rien de secret ici (dépôt public) : le JETON du robot Telegram va dans les Secrets GitHub
(TELEGRAM_BOT_TOKEN), jamais dans ce fichier.
"""

# Adresse PUBLIQUE du canal Telegram, ex. "https://t.me/alertesaotunisie".
# Vide -> le bouton « Recevoir les alertes sur Telegram » n'apparaît pas.
TELEGRAM_CANAL_URL = ""

# Plus tard : adresse du canal WhatsApp, ex. "https://whatsapp.com/channel/XXXXXXXX".
WHATSAPP_CANAL_URL = ""

# Google Forms « Publier un appel d'offres » : lien à donner aux entreprises
# (bouton « Envoyer » du formulaire -> lien, ex. "https://forms.gle/XXXX").
# Vide -> la page « Publier un appel d'offres » affiche « Bientôt ».
FORMULAIRE_PRIVES_URL = ""

# Feuille des réponses publiée en CSV (Fichier -> Partager -> Publier sur le Web -> CSV),
# ex. "https://docs.google.com/spreadsheets/d/e/XXXX/pub?output=csv".
# Vide -> robot/prives.py ne fait rien.
CSV_PRIVES_URL = ""
