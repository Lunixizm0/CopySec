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

echo "== lint =="
uv run ruff check .

echo "== unit tests =="
uv run pytest -q -m "not integration"

echo "== bumping version to $VERSION =="
uv version "$VERSION"
git add pyproject.toml uv.lock
git commit -m "chore(release): $TAG"
git tag "$TAG"

echo
echo "done. now run:"
echo "  git push origin main && git push origin $TAG"
echo "  gh release create $TAG --generate-notes --title $TAG"
