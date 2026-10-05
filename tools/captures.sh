#!/bin/bash
# Captures mobiles (Chrome sans écran) : cadres de 340 et 390 px, en français et en arabe.
#   bash tools/captures.sh            -> site/captures/*.png
cd "$(dirname "$0")/.." || exit 1
CH="/c/Program Files/Google/Chrome/Application/chrome.exe"
SITE=$(cygpath -m "$PWD")
PROFIL=$(cygpath -m "${TEMP:-/tmp}/chrome-captures-ao")
# chemin:nom:hauteur (accueil-complet = toute la page, pour voir la carte de la Tunisie en bas)
for page in "index.html:accueil:2400" "index.html:accueil-complet:7600" "metier/btp-genie-civil/index.html:metier:2400"             "gouvernorat/sfax/index.html:gouvernorat:2400" "a-propos/index.html:a-propos:2400" "encheres/index.html:encheres:2400" "publier/index.html:publier:1800"; do
  IFS=: read -r chemin nom H <<< "$page"
  for lang in fr ar; do
    cat > captures/cadre.html <<HTML
<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#888;display:flex;gap:20px;padding:20px;align-items:flex-start}
iframe{border:0;background:#fff;height:${H}px}</style></head><body>
<iframe src="file:///$SITE/$chemin?lang=$lang" width="340"></iframe>
<iframe src="file:///$SITE/$chemin?lang=$lang" width="390"></iframe></body></html>
HTML
    "$CH" --headless=new --allow-file-access-from-files --hide-scrollbars --user-data-dir="$PROFIL" \
      --virtual-time-budget=10000 --window-size=790,$((H + 40)) \
      --screenshot="$SITE/captures/$nom-$lang.png" "file:///$SITE/captures/cadre.html" 2>/dev/null | grep -o "written.*" 
  done
done
rm -f captures/cadre.html
