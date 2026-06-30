#!/usr/bin/env bash
# push_to_github.sh
# Run this once from inside the polytools/ directory to initialize and push
# to github.com/aenealabs/polytools.
#
# Prerequisites:
#   - The repo aenealabs/polytools must already exist on GitHub (create it
#     at https://github.com/new — choose "aenealabs" as the owner, name it
#     "polytools", set it to Public, and do NOT initialize with any files).
#   - You must be authenticated: either `gh auth login` (if you have gh CLI)
#     or have HTTPS credentials cached / an SSH key configured.

set -e

REPO="https://github.com/aenealabs/polytools.git"
# Swap the line above for SSH if you prefer:
# REPO="git@github.com:aenealabs/polytools.git"

echo "→ Configuring git identity (if not already set globally)..."
git config --global user.name  "$(git config --global user.name  2>/dev/null || echo 'LaVon Rutledge')"
git config --global user.email "$(git config --global user.email 2>/dev/null || echo 'lavonrutledge2@gmail.com')"

echo "→ Initializing git repository..."
git init
git checkout -b main

echo "→ Staging all files..."
git add .

echo "→ Creating initial commit..."
git commit -m "feat: initial release v0.1.0

- @tool decorator — wraps any Python function, exposes cross-provider schema methods
- to_openai(), to_anthropic(), to_gemini(), to_mcp(), to_all()
- Full type annotation support: primitives, generics, Optional, Union, Literal
- Google / NumPy / RST docstring auto-detection
- 91 tests, zero external dependencies, Python 3.9+"

echo "→ Adding remote origin..."
git remote add origin "$REPO"

echo "→ Pushing to GitHub..."
git push -u origin main

echo ""
echo "✓ Done! Visit https://github.com/aenealabs/polytools"
echo ""
echo "Next steps:"
echo "  1. Tag and publish v0.1.0:"
echo "       git tag v0.1.0"
echo "       git push origin v0.1.0"
echo "  2. Set up PyPI Trusted Publishing at:"
echo "       https://pypi.org/manage/project/polytools/settings/publishing/"
echo "     (GitHub owner: aenealabs, repo: polytools, workflow: publish.yml, environment: pypi)"
