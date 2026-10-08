#!/bin/bash
# Push vers GitHub avec le jeton stocké dans .github_token (jamais commité).
cd "$(dirname "$0")"
TOKEN=$(tr -d ' \n\r' < .github_token) || { echo "NO_TOKEN"; exit 2; }
for f in .git/*.lock .git/objects/*.lock; do [ -e "$f" ] && mv -n "$f" ".git/stale-$(basename $f)-$RANDOM"; done
git -c credential.helper= push "https://x-access-token:${TOKEN}@github.com/BenjaminH7/citations-carrousels.git" HEAD:main 2>&1 | sed "s/${TOKEN}/***/g"
for f in .git/*.lock .git/objects/*.lock; do [ -e "$f" ] && mv -n "$f" ".git/stale-$(basename $f)-$RANDOM"; done
git rev-parse HEAD
