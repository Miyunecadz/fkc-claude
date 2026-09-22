# Title and description — write the meaning once, let the script shape it

Two jobs, and they never mix:

| You | The script |
|---|---|
| Understand the ticket and the diff. Write **Ticket / What / Why / Check** once. | Order the sections, fix the spacing, number the checks, strip the attribution, refuse anything that is not the contract. |

So: **do not fuss over the Markdown.** Do not re-read your own draft to tidy the headings,
do not rewrite it to remove a footer, do not count the blank lines. Write the four pieces
in any reasonable shape and pipe them through
[`pr-body.py`](../../hooks/pr-body.py) — `format` produces the body that gets posted, and
a `PreToolUse` hook re-checks it on the way to Bitbucket. Rewriting for formatting is
wasted tokens; the formatter is deterministic and free.

The failure mode this guards against is not a missing detail. It is a wall of text nobody
reads, so the reviewer skims it, misses the one line that mattered, and reviews the diff
blind. A PR description is a **note to a busy colleague**, not a report. Everything else a
curious reviewer needs is already in the diff, the ticket and the commit.

## What you write — the semantic block

Four labels, any order, headings or `Label:` prefixes, wrapped however you like — plus
`Screenshot`, which is optional and always comes last:

```text
Ticket: https://zero-hero-tech.atlassian.net/browse/FKC-279

What: The purchase order and plant order number series are only given to, and only
accepted from, users whose role holds the new No. Series view or edit permission.

Why: Anyone signed in who could reach the Configuration area could rename every future
order.

Check:
- With a role holding neither permission, the Configuration number series show no values
  and a save is refused.
- Grant No. Series — view: values show, saving is still refused.
- Grant No. Series — edit: values show and a change saves.
- Create a purchase order — its name and prefix are unchanged.
```

## What gets posted — the contract

`pr-body.py format` turns the block above into exactly this, and nothing else:

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
```

A PR that changes what someone sees, or an endpoint someone calls, ends with one more
section:

```markdown
**Screenshot**

![](https://bitbucket.org/repo/bxjg5L4/images/2340471243-image.png){: data-layout='center' }
```

`··` is **two real spaces** — a Markdown hard break. This is not decoration, and none of
it is negotiable:

| Detail | Without it, Bitbucket renders |
|---|---|
| `**What**` bold | a plain word that reads as part of the sentence |
| two trailing spaces after `**What**` / `**Why**` | `What One system-wide subcontract...` — label and text welded into one paragraph |
| blank line between `**Check**` and `1.` | `Check: 1. Apply the migration 2. Read the series...` — the whole list swallowed into one line |
| no hard break after `**Check**` | the list pulled back into the label's paragraph |
| `{: data-inline-card='' }` on the ticket link | a plain blue URL instead of the Trello smart card with its title and list |

The ticket line is written for you: give the formatter a bare Trello URL and it emits
`[<url>](<url>){: data-inline-card='' }`, which is exactly what Bitbucket's own editor
writes. The visible title comes from the card, so the link text is the URL, not a title
you type.

You do not type any of this. `pr-body.py format` does, every time. That is the entire
reason it exists — the shape above was got wrong by hand on PR #125.

| Part | Budget | Rule |
|---|---|---|
| `Ticket:` | 1 line | The **Trello** card URL — paste it bare, the formatter wraps it. Jira holds the requirement; Trello holds the number the branch is named after. **No ticket → the literal `Ticket: none`.** Never invent one |
| `What` | 1–2 sentences | What someone *using the app* now sees. Never a file, resolver, hook or component name |
| `Why` | 1 sentence | The reason it was needed. Not a restatement of What |
| `Check` | 2–6 steps | Things a reviewer can actually do in the running app |
| `Screenshot` | 0–6 images | Optional, and always last. **Bitbucket-hosted images only**, one per line; the formatter centres them. A local path or an outside host is refused, because it renders as a broken image for every reviewer |

**Budget: 120 words.** The formatter warns above it and refuses above 250 — over that,
either the body is padded or the PR is too big. Say the PR is too big; do not squeeze the
meaning out to fit.

## Rules

- **British English. Non-technical in What and Why.** Name buttons, pages, messages — the
  things a user sees. Technical detail belongs in the diff.
- **Every claim must be something the diff does.** Do not copy acceptance criteria across
  from the ticket without confirming they were implemented, and never describe the other
  repo's half as if it were in this PR.
- **A step you never exercised is not a passed step.** Write it as a check the reviewer
  should do; say separately, in the handover, what nobody has actually run.
- **Permissions in the change → permissions in the Check.** One step per role/permission
  combination that behaves differently, including the negative case.
- **A purely technical PR** (a refactor with no user-visible change) says so in one line
  under What: "No user-visible change — <what moved and why>." It still gets a Check.
- **A cross-repo pointer, a migration warning or a breaking-change line** goes as the last
  sentence of **Why** — one sentence, not a section of its own. ("Includes a dbmate
  migration — run `yarn db:migrate` after merge.")
- **Show the change, do not describe the picture.** A screenshot needs no arrows, boxes or
  captions; the diff says what moved. A frontend PR shows the page, a backend PR shows the
  endpoint answering with real data. Never post a shot of a failing response, and never
  post one with a bearer token on screen.
- **Image URLs are not counted** against the word budget. Pictures are not padding.

## Banned — and what the script does about it

Sections: Summary, Overview, Background, Context, Description, Changes, Changes Made,
Files Changed, Testing, Test Plan, Testing Strategy, Notes, Implementation Details,
Implementation Notes, Technical Details, Risks, Future Work, Checklist, Acceptance
Criteria. **The formatter deletes these headings and their content**, and prints
`dropped section: <name>` on stderr so nothing disappears quietly. Anything worth keeping
belongs in What, Why or Check — put it there, do not smuggle it in under a heading.

Any *other* unrecognised heading is **rejected**, not dropped — it might carry meaning the
script has no right to throw away. The run stops and tells you which heading.

Phrases: "This PR", "This change introduces", "In order to", "It is worth noting",
"Additionally", "Comprehensive", "Robust", "Seamlessly", "leverage", "utilise". Emoji.
Bold on whole sentences. A bullet list restating the file list.

Attribution — `Generated with Claude Code`, `🤖`, `Co-Authored-By: Claude`, a session URL —
**is stripped by the script**, and `attribution.pr` is blank in `.claude/settings.local.json`
so it is not added in the first place. Never spend a turn removing it by hand.

## Cut it down

Write it, then delete. In order:

1. Any sentence that repeats the title.
2. Any sentence about *how* the code works.
3. Any adverb, and any "simply / just / basically / essentially".
4. Any Check step that only proves the app still starts.

Before (74 words, and a reviewer's eyes glaze):

> ## What this does
> This PR introduces a comprehensive permission check for the number series configuration
> functionality. Previously, the `numberSeries` settings page was accessible to all admin
> users regardless of their assigned permissions. We have now added a new `No. Series`
> permission to the shield configuration and wired it through the settings resolver so
> that the page is appropriately gated.

After (31 words):

> What
> Number series settings are hidden from anyone without the No. Series permission.
>
> Why
> Any admin could change them; only the finance role should.

## Title

The title is **not** part of the formatted body and the script does not touch it. A plain
sentence describing the behaviour change. Sentence case. **No type prefix, no ticket key,
no repo name** — that is the branch and the commit's job. Under 70 characters. Observed in
these repos:

```
Refuse holiday requests that exceed the remaining allowance
Export to Excel on the HR admin employees page
HR: keep filters in the address bar, and a Back button on employee pages
```

Take it from the ticket summary and shorten it. For a cross-repo pair, each title says what
*that* repo's half does — they are not the same sentence twice.

## Running it

```bash
.claude/hooks/pr-body.py format -f draft.txt      # semantic block -> the body to post
.claude/hooks/pr-body.py check  -f body.md        # is this body postable?
```

Mechanics, exit codes and how to change the format: [`PIPELINE.md`](./PIPELINE.md).
