# The PR body pipeline — for changing it, not for running it

Nothing here is needed during `/create-pr`. Read it when you change `pr-body.py`, its tests
or the posted shape.

```
/create-pr
   │  preflight, Jira, the sidecar
   ▼
pr-author ────────────────► <repo>.title (one line) + <repo>.txt (Ticket / What / Why / Check)
   │                        the only LLM step — written once
   ▼
pr-body.py format / title ► the exact body and a checked title, shown at the gate
   ▼
pr-body.py hook (PreToolUse on bb_post / bb_put / bb_patch)
   │                        re-checks title and body; allows, or denies with the diff.
   │                        It never rewrites: what the user approved is what is sent
   ▼
Bitbucket
```

The shape of a PR body has one right answer and no judgement in it, so it lives in code
that is testable, instant and identical every run. An LLM asked to "reformat to the house
style" is a fresh sample each time: it costs a round trip, can drop a step, soften a
sentence or keep the footer. Judgement — what changed, why, how to check — stays with the
agent and is written once.

## Components

| Component | Path | Job |
|---|---|---|
| Content rules | `.claude/skills/pull-request/DESCRIPTION.md` | What `pr-author` writes, and every enforced limit |
| Drafting agent | `.claude/agents/pr-author.md` | Reads one repo's diff, writes the two files |
| Formatter, validator, hook | `.claude/hooks/pr-body.py` | `format`, `check`, `title`, `hook` — one grammar |
| Tests | `.claude/hooks/tests/test_pr_body.py` | 72 cases, standard library only |
| Orchestration | `.claude/commands/create-pr.md`, `pull-request/SKILL.md` | When it runs, and the gate |

```bash
.claude/hooks/pr-body.py format -f draft.txt [-t <card url>] [-b <jira base>]
.claude/hooks/pr-body.py check  -f body.md
.claude/hooks/pr-body.py title  -f repo.title
python3 .claude/hooks/tests/test_pr_body.py
```

`-t` replaces the Ticket value (a card URL the user gave at the gate). `-b` turns a bare key
into a Jira browse URL; `/create-pr` does not use it, because the ticket line is the Trello
card. Exit codes: `0` fine · `1` not valid (report on stderr, nothing on stdout) · `2` bad
usage. Warnings go to stderr and do not fail the run.

## The rendered contract

The semantic block in `DESCRIPTION.md` comes out as exactly this (`··` is two real spaces):

```markdown
Ticket: [https://trello.com/c/bZZ0akWV/279](https://trello.com/c/bZZ0akWV/279){: data-inline-card='' }

**What**··
The purchase order and plant order number series are only given to, and only accepted from, users whose role holds the new No. Series view or edit permission.

**Why**··
Anyone signed in who could reach the Configuration area could rename every future order.

**Check**

1. With a role holding neither permission, the Configuration number series show no values and a save is refused.
2. Grant No. Series — view: values show, saving is still refused.
3. Grant No. Series — edit: values show and a change saves.
4. Create a purchase order — its name and prefix are unchanged.

**Screenshot**

![](https://bitbucket.org/repo/bxjg5L4/images/2340471243-image.png){: data-layout='center' }
```

Bitbucket renders the description as Markdown, and every detail is load-bearing:

| Detail | Without it, Bitbucket renders |
|---|---|
| `**What**` bold | a plain word that reads as part of the sentence |
| two trailing spaces after `**What**` / `**Why**` | label and text welded into one paragraph |
| blank line between `**Check**` and `1.` | the whole list swallowed into one line |
| no hard break after `**Check**` | the list pulled back into the label's paragraph |
| `{: data-inline-card='' }` on the ticket link | a plain blue URL instead of the Trello smart card |

PR #125 shipped the plain version and rendered as a wall of prose.
`Formatter.test_reproduces_the_hand_fixed_pr_125_body` pins the shape against the body a
human repaired in the Bitbucket editor; `Rendering` pins each detail.

## What the formatter does

1. Strips attribution — `Generated with/by Claude Code`, `🤖`, `Co-Authored-By: Claude`,
   `Claude-Session:`, a bare `claude.ai`/`claude.com` URL, and a trailing `---`.
2. Parses the labels in any order, from `## What`, `**What**`, `What:`, `What —` or a bare
   `What` line. Aliases: `Jira`/`Issue` → Ticket; `Checks`/`Verification`/`Verify` → Check.
   Text above the Ticket line is refused, with a hint when it is a `title:` block.
3. Drops banned sections with their content (the list is `BANNED_NAMES`; `DESCRIPTION.md`
   repeats it), printing `dropped section: <name>`. Refuses any other unknown heading.
4. Rewraps each section to one line per paragraph. **Wording is never altered.**
5. Turns bullets, bare lines or any numbering into `1.` `2.` `3.`.
6. Wraps a ticket URL as a smart card. A bare key or `none` is left alone.
7. Renders the contract above and validates its own output.

## What the validator refuses

Empty body · a missing or empty Ticket, What, Why or Check · Check steps not numbered 1..n ·
sections out of order or duplicated · a banned or unknown heading · attribution · more than
12 steps · more than 250 words · more than 6 images, or one not on bitbucket.org · anything
not byte-identical to what the formatter renders.

## The hook

Registered in `.claude/settings.json` as `PreToolUse` on the Bitbucket write tools. It acts
on `repositories/<ws>/<repo>/pullrequests[/<id>]`, with or without a leading `/` or `2.0/`.
Comments, approvals, merges and other paths pass untouched.

- **Create** (`bb_post` to `pullrequests`): title and description are both required.
- **Update** (`bb_put` / `bb_patch` to `pullrequests/<id>`): checks only the fields sent.
  A title-only update is allowed when the title passes; a call with neither passes through.
- A body sent as a JSON string is parsed first; one that is not an object is denied.
- Any body that is not the formatter's output is **denied with a unified diff** (trailing
  spaces shown as `·`). Nothing is rewritten in flight, because the user approved exact
  text at the gate.
- A payload the hook cannot read is denied when it mentions `pullrequests`, and allowed
  otherwise. It never fails open on a PR write.

## Attribution, at source

`.claude/settings.json` sets `attribution.pr` to `""`, so Claude Code adds no footer. The
formatter's stripping is the second line of defence.

## Changing the format

Two places move together:

1. `pr-body.py` — `CANON`, `ALIASES`, `BANNED_NAMES`, `HARD_BREAK`, the limits
   (`MAX_WORDS_HARD`, `MAX_CHECKS`, `MAX_IMAGES`, `MAX_TITLE`, `WARN_WORDS`, `WARN_LINES`), and
   the format string in `format_body()`. The validator follows, because it compares against
   that render.
2. `DESCRIPTION.md` — the rules and the limits table.

Then run the tests. A shape change fails `Formatter.test_produces_the_required_shape` and
`test_idempotent` first — update them deliberately, never by loosening the assertion.
