#!/usr/bin/env bash
# UserPromptSubmit: house writing style. Injected every turn so it cannot drift.
# Kept short on purpose; the PostToolUse lint catches spelling in .md/.txt.
cat <<'RULE'
Style: British English, plain words, short sentences, answer first. Code, identifiers, API/DB names, UI labels and quoted errors keep their spelling. Full rules: plain-uk-english skill.
RULE
exit 0
