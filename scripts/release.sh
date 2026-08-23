#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <version>   (e.g. $0 0.2.0)" >&2
    exit 1
fi

VERSION="$1"
TAG="v$VERSION"

if ! git diff-index --quiet HEAD --; then
    echo "error: working tree not clean, commit or stash first" >&2
    exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" != "main" ]; then
    echo "error: releases are cut from main (current: $BRANCH)" >&2
    exit 1
fi

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    echo "error: tag $TAG already exists" >&2
    exit 1
fi

ORIGIN_URL="$(git remote get-url origin 2>/dev/null || true)"
if [ -z "$ORIGIN_URL" ]; then
    echo "error: no 'origin' remote configured" >&2
    exit 1
fi
REPO_SLUG="$(printf '%s' "$ORIGIN_URL" | sed -E 's#.*[:/]([^/]+/[^/.]+)(\.git)?$#\1#')"

echo "== lint =="
uv run ruff check .

echo "== unit tests =="
uv run pytest -q -m "not integration"

echo "== bumping version to $VERSION =="
uv version "$VERSION"
git add pyproject.toml uv.lock
git diff --cached --quiet || git commit -m "chore(release): $TAG"

git tag "$TAG"

echo "== pushing =="
git push origin main "$TAG"

echo "== creating github release =="
gh release delete "$TAG" --yes --cleanup-tag 2>/dev/null || true
gh release create "$TAG" --title "$TAG" --generate-notes

ACTIONS_URL="https://github.com/$REPO_SLUG/actions"
PYPI_URL="https://pypi.org/pypi/copysec/$VERSION/json"
echo ""
echo "$TAG pushed, workflow running: $ACTIONS_URL"
echo "waiting for $VERSION to appear on PyPI..."

for i in $(seq 1 30); do
    HTTP_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' "$PYPI_URL")"
    if [ "$HTTP_STATUS" = "200" ]; then
        echo "+ $VERSION is live: https://pypi.org/project/copysec/$VERSION/"
        exit 0
    fi
    echo "  not available yet (HTTP $HTTP_STATUS). retrying in 5s [$i/30]"
    sleep 5
done

echo "error: $VERSION not found on PyPI after 30 attempts; check $ACTIONS_URL" >&2
exit 1
