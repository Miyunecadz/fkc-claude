# The PR body pipeline — where the tokens stop

```
/create-pr
   │  ticket + implementation context (pr-preflight.sh, Jira, the sidecar)
   ▼
pr-author agent ──────────► the semantic block: Ticket / What / Why / Check
   │                        (Claude's only job — written once, never reformatted)
   ▼
pr-body.py format ────────► the exact body: sections ordered, spacing normalised,
   │                        checks renumbered, banned sections dropped,
   │                        attribution stripped
   ▼
pr-body.py hook (PreToolUse on bb_post / bb_put)
   │                        re-checks the body actually being sent; normalises it
   │                        again if it drifted; denies the call if it cannot be
   ▼
Bitbucket ────────────────► PR created / updated
```

No LLM runs after the semantic block. Formatting and validation are pure Python and cost
nothing.

## The components

| Component | Path | Job |
|---|---|---|
| Content contract | `.claude/skills/pull-request/DESCRIPTION.md` | What Claude writes, and the shape that gets posted |
| Drafting agent | `.claude/agents/pr-author.md` | Reads one repo's diff, returns the semantic block. The diff never enters the main thread |
| Formatter + validator + hook | `.claude/hooks/pr-body.py` | `format`, `check`, `hook` — one file, one grammar, no duplication |
| Tests | `.claude/hooks/tests/test_pr_body.py` | 40 cases, standard library only |
| Orchestration | `.claude/commands/create-pr.md`, `pull-request/SKILL.md` | When it runs, and the approval gate |

## Using it

```bash
.claude/hooks/pr-body.py format -f draft.txt          # semantic block -> body (stdout)
.claude/hooks/pr-body.py format < draft.txt > body.md
.claude/hooks/pr-body.py check  -f body.md            # validate a finished body
.claude/hooks/pr-body.py format -b https://zero-hero-tech.atlassian.net -f draft.txt
```

`-b/--ticket-base` expands a bare `FKC-279` into a browse URL. Without it a bare key is
posted as a key — the formatter never invents a link.

Exit codes: `0` fine · `1` the body is not valid (report on stderr, nothing printed to
stdout) · `2` bad usage. Warnings (`note: 137 words (budget 120)`) go to stderr and do not
fail the run.

## What the formatter does, exactly

1. Strips attribution — `Generated with/by Claude Code`, `🤖`, `Co-Authored-By: Claude`,
   `Claude-Session:`, a bare `claude.ai`/`claude.com` URL, and a trailing `---` left behind.
2. Parses the four labels in any order, from `## What`, `**What**`, `What:`, `What —` or a
   bare `What` line. Aliases: `Jira`/`Issue` → Ticket; `Checks`/`Verification`/`Verify` →
   Check.
3. Drops the banned boilerplate sections **with their content**, printing
   `dropped section: <name>` per drop. Rejects any *other* unrecognised heading rather than
   guessing — it may hold meaning.
4. Rewraps each section to one line per paragraph, trims trailing whitespace, collapses
   blank runs. **Wording is never altered** — no truncation, no rewriting, no summarising.
5. Turns bullets, bare lines or any numbering into `1.` `2.` `3.` from 1.
6. Wraps a ticket URL as `[<url>](<url>){: data-inline-card='' }` — Bitbucket's smart-card
   syntax. A bare key (`FKC-281`) or `none` is left alone; `--ticket-base` turns a key into
   a URL first.
7. Emits the rendered Markdown — `Ticket:`, `**What**` + hard break, `**Why**` + hard
   break, `**Check**` + blank line + the list — in that order, and validates its own
   output before returning it.

Why bold labels and trailing spaces rather than the plainer text they replace: Bitbucket
renders the description as Markdown. `What` on its own line with the text below it is one
paragraph, and a numbered list that is not preceded by a blank line is absorbed into the
paragraph above. PR #125 shipped exactly that and rendered as a wall of prose. The two
trailing spaces are a hard break, and the blank line before `1.` is what makes a real
list; both are load-bearing, and `Rendering` in the test file pins them.
`Formatter.test_reproduces_the_hand_fixed_pr_125_body` pins the whole shape against the
body a human repaired by hand in the Bitbucket editor — that body is the specification.

## What the validator refuses

Empty body · a missing or empty Ticket, What, Why or Check · a Check with no numbered
steps, steps that are not all numbered, or numbering that is not 1..n · sections out of
order · a duplicated section · a banned or unknown heading · any Claude Code attribution ·
more than 12 check steps · more than 250 words · **anything that is not byte-identical to
what the formatter renders** — the validator's last act is to re-render the body and
compare, so a lost hard break or a missing blank line fails like any other defect.

Failure output is the same everywhere:

```
PR validation failed.

Missing or invalid:
- missing Why section

The PR was not created.
```

## The hook

Registered in `.claude/settings.json` as `PreToolUse` on
`mcp__bitbucket__bb_post|mcp__bitbucket__bb_put`. It only acts on paths matching
`/repositories/<ws>/<repo>/pullrequests[/<id>]` that carry a `title` or `description` —
comments, approvals, merges and every other Bitbucket call pass through untouched.

- Body already valid → silent allow.
- Body fixable (attribution, headings, numbering) → `updatedInput` with the cleaned
  description, plus a system message saying what changed. **No Claude turn is spent.**
- Body missing meaning (no Why, empty What, unknown section) → `deny` with the report. The
  PR is not created, and semantic content is never invented to make it pass.

## Attribution, at source

`.claude/settings.local.json` sets `attribution.pr` to `""` (next to the existing
`attribution.commit`), so Claude Code does not append its footer to a PR body at all. The
formatter's stripping is the second line of defence, for a body pasted or written by hand.

## Changing the format later

The contract lives in two places and they must move together:

1. `pr-body.py` — `CANON`, `ALIASES`, `BANNED_NAMES`, `HARD_BREAK`, the budgets
   (`MAX_WORDS_HARD`, `MAX_CHECKS`, `WARN_WORDS`, `WARN_LINES`), and the one format string
   in `format_body()` that renders the body. The validator follows automatically — it
   compares against that render rather than repeating the rules.
2. `DESCRIPTION.md` — what Claude is told to write.

Then run the tests. Changing the rendered shape will fail
`Formatter.test_produces_the_required_shape` and `test_idempotent` first — update those
expectations deliberately, never by loosening the assertion.

```bash
python3 .claude/hooks/tests/test_pr_body.py          # 40 tests, ~5 ms, no dependencies
```

## Why this is deterministic and not a second Claude pass

An LLM asked to "reformat this to the house style" is a fresh sample every time: it costs
a round trip, it can drop a Check step, it can soften a sentence, and it can leave the
footer in. The shape of a PR body has one right answer and no judgement in it, so it
belongs in code that is testable, instant and identical every run. Judgement — what
changed, why it mattered, how to verify it — stays with Claude, and is written once.
