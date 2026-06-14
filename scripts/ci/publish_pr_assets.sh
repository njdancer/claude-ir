#!/usr/bin/env bash
# Publish a PR's board renders to the long-lived `pr-assets` orphan branch so
# they can be embedded (raw.githubusercontent.com) in the sticky PR comment.
# GitHub markdown can't inline workflow artifacts or data URIs, so a public
# branch is the cheapest reliable host. Each PR owns the pr-<N>/ subdir, which
# is overwritten every run — only the latest renders per open PR are kept.
#
# Inputs (env): GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, SHA, RENDER_DIR
# Output: writes `renders_url=<raw base>` to $GITHUB_OUTPUT when renders were
# published; emits nothing (exit 0) if the renders are missing, so the
# comment job degrades to a no-image report instead of failing.
set -euo pipefail

BRANCH=pr-assets
DEST="pr-${PR_NUMBER}"
RENDER_DIR="${RENDER_DIR:-renders}"

for f in top bottom iso; do
  if [ ! -f "${RENDER_DIR}/${f}.png" ]; then
    echo "publish_pr_assets: ${RENDER_DIR}/${f}.png missing — skipping image publish"
    exit 0
  fi
done

URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
WORK="$(mktemp -d)"

if git clone --depth 1 --branch "$BRANCH" "$URL" "$WORK" 2>/dev/null; then
  echo "publish_pr_assets: cloned existing $BRANCH"
else
  echo "publish_pr_assets: $BRANCH does not exist — creating orphan"
  git init -q "$WORK"
  git -C "$WORK" checkout -q -b "$BRANCH"
  git -C "$WORK" remote add origin "$URL"
fi

rm -rf "${WORK:?}/${DEST}"
mkdir -p "${WORK}/${DEST}"
cp "${RENDER_DIR}"/top.png "${RENDER_DIR}"/bottom.png "${RENDER_DIR}"/iso.png \
   "${WORK}/${DEST}/"

git -C "$WORK" config user.name "github-actions[bot]"
git -C "$WORK" config user.email "github-actions[bot]@users.noreply.github.com"
git -C "$WORK" add -A
if git -C "$WORK" diff --cached --quiet; then
  echo "publish_pr_assets: renders unchanged — nothing to push"
else
  git -C "$WORK" commit -q -m "renders for PR #${PR_NUMBER} @ ${SHA}"
  # Retry against concurrent pushes from other PRs sharing the branch.
  for i in 1 2 3; do
    if git -C "$WORK" push -q origin "$BRANCH"; then
      break
    fi
    echo "publish_pr_assets: push failed (attempt $i) — rebasing"
    git -C "$WORK" pull -q --rebase origin "$BRANCH" || true
    [ "$i" = 3 ] && { echo "publish_pr_assets: gave up after 3 tries"; exit 0; }
  done
fi

BASE="https://raw.githubusercontent.com/${GITHUB_REPOSITORY}/${BRANCH}/${DEST}"
echo "renders_url=${BASE}" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "publish_pr_assets: published -> ${BASE}"
