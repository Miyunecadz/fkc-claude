#!/usr/bin/env bash
# UserPromptSubmit: house writing style. Injected every turn so it cannot drift.
cat <<'RULE'
## House writing style (enforced — applies to every word a human reads)

- **British English.** organise, colour, licence (noun), centre, analyse, cancelled,
  defence, catalogue. Dates `21 September 2026` or `2026-09-21`. Money `£1,250.00`.
- **Code is exempt.** Never change identifiers, API fields, DB columns, CSS (`color`),
  library names, existing UI labels or quoted error text to UK spelling.
- **Plain words.** use (not utilise/leverage), start (not commence), about (not with
  regard to), so (not therefore), help (not facilitate), change (not modification).
  Banned: seamless, robust, leverage, synergy, holistic, going forward, circle back.
- **Short sentences.** One idea each, under 20 words, active voice.
- **Answer first.** `[answer]. [why, one line]. [next step if any].` No "Great question",
  no "Let me know if you need anything else", no restating the question, no summary of a
  summary.
- Keep technical terms exact — precision beats simplicity when they clash.

Applies to chat replies, Jira tickets, PR titles and descriptions, commit messages,
code comments and docs. Full rules: `.claude/skills/plain-uk-english/SKILL.md`.
RULE
exit 0
