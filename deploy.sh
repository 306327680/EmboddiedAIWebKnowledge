#!/usr/bin/env bash
#
# Build the static site from docs/*.md and deploy it to Cloudflare Pages.
#
#   ./deploy.sh            build + deploy
#   ./deploy.sh --build    build only, no deploy (then open docs/site/index.html)
#   ./deploy.sh --verify   build + deploy + byte-compare every page against the live site
#
set -euo pipefail

cd "$(dirname "$0")"

PROJECT="vla-model-architecture"
# The Pages production branch is `main`. It is NOT tied to the local git branch —
# omitting --branch, or passing anything else, lands the deploy in the Preview
# environment and the live site does not change.
PAGES_BRANCH="main"
DOMAIN="https://vla.yilong-zhu.com"
SITE_DIR="docs/site"

MODE="${1:-deploy}"

echo "==> Building site"
python3 docs/build_site.py

if [ "$MODE" = "--build" ]; then
    echo
    echo "Build only. Open $SITE_DIR/index.html to preview locally."
    exit 0
fi

echo
echo "==> Deploying to Cloudflare Pages (project=$PROJECT, branch=$PAGES_BRANCH)"
npx wrangler pages deploy "$SITE_DIR" \
    --project-name "$PROJECT" \
    --branch "$PAGES_BRANCH" \
    --commit-dirty=true

if [ "$MODE" != "--verify" ]; then
    echo
    echo "Done. Live at $DOMAIN"
    exit 0
fi

echo
echo "==> Waiting 45s for the edge to pick up the new deployment"
sleep 45

echo "==> Byte-comparing every page against $DOMAIN"
# Cloudflare Pages 308-redirects /foo.html -> /foo, so compare against the
# extensionless URL and follow redirects; without -L curl returns an empty body
# and every page looks like a mismatch.
fail=0
for f in "$SITE_DIR"/*.html; do
    base="$(basename "$f" .html)"
    url="$DOMAIN/$base"
    [ "$base" = "index" ] && url="$DOMAIN/"
    local_md5="$(md5sum "$f" | cut -d' ' -f1)"
    live_md5="$(curl -sL --compressed --max-time 45 "$url" | md5sum | cut -d' ' -f1)"
    if [ "$local_md5" = "$live_md5" ]; then
        echo "  ok   $base"
    else
        echo "  DIFF $base  (local=$local_md5 live=$live_md5)"
        fail=$((fail + 1))
    fi
done

echo
if [ "$fail" -eq 0 ]; then
    echo "All pages match the live site."
else
    echo "$fail page(s) differ from the live site."
    exit 1
fi
