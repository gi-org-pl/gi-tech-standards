#!/usr/bin/env bash
# Prepares the checkout of the pull request for the reviewer, which reads it
# as data. Symbolic links could point the read tools at /proc/self/environ or
# the runner's files, so every one goes. Agent configuration of the pull
# request (CLAUDE.md, AGENTS.md, .claude/, .mcp.json at any depth) is no
# instruction for its reviewer: the base-branch guides are in the context,
# and the action restores the root files from the base branch.
#
# Usage: clean-checkout.sh CONTEXT_DIR   (run in the root of the checkout)
set -euo pipefail

: "${1:?usage: clean-checkout.sh CONTEXT_DIR}"
find . -path ./.git -prune -o -type l -print -exec rm -f {} +
find . -path ./.git -prune -o \
  \( -name CLAUDE.md -o -name CLAUDE.local.md -o -name AGENTS.md -o -name .mcp.json -o -name .claude.json \) \
  -type f -print -exec rm -f {} +
find . -path ./.git -prune -o -name .claude -type d -prune -print -exec rm -rf {} +
rm -rf "$1"
