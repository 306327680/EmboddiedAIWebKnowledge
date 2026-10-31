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
case "$MODE" in
    deploy|--build|--verify) ;;
    *)
        echo "Usage: $0 [--build|--verify]" >&2
        exit 2
        ;;
esac

sha256_file() {
    python3 -c 'import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' "$1"
}

sha256_stdin() {
    python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
}

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
VERIFY_WAIT_SECONDS="${VERIFY_WAIT_SECONDS:-45}"
echo "==> Waiting ${VERIFY_WAIT_SECONDS}s for the edge to pick up the new deployment"
sleep "$VERIFY_WAIT_SECONDS"

echo "==> Byte-comparing every page against $DOMAIN"
# Cloudflare Pages 308-redirects /foo.html -> /foo, so compare against the
# extensionless URL and follow redirects; without -L curl returns an empty body
# and every page looks like a mismatch.
fail=0
for f in "$SITE_DIR"/*.html; do
    base="$(basename "$f" .html)"
    url="$DOMAIN/$base"
    [ "$base" = "index" ] && url="$DOMAIN/"
    local_sha256="$(sha256_file "$f")"
    live_sha256="$(curl --fail --silent --show-error --location --compressed --max-time 45 "$url" | sha256_stdin)"
    if [ "$local_sha256" = "$live_sha256" ]; then
        echo "  ok   $base"
    else
        echo "  DIFF $base  (local=$local_sha256 live=$live_sha256)"
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
