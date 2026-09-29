# Title and description — write the meaning once

You write the meaning. [`pr-body.py`](../../hooks/pr-body.py) writes the Markdown: it
orders the sections, fixes the spacing, numbers the checks and strips attribution. So do not
tidy headings, count blank lines or re-read your draft for layout — there is none to tidy.

A PR description is a **note to a busy colleague**, not a report. A wall of text gets
skimmed, and the one line that mattered is missed. The rest is in the diff and the ticket.

## What you write

Two files. The title goes in `<repo>.title`, one line. The body goes in `<repo>.txt` and
starts at `Ticket:` — nothing above it. Four labels, any order, headings or `Label:`
prefixes, wrapped however you like, plus an optional `Screenshot` that always comes last:

```text
Ticket: https://trello.com/c/bZZ0akWV/279

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

## The parts, and the limits the script enforces

| Part | Rule |
|---|---|
| `Ticket:` | The **Trello** card URL you were given, bare — the formatter wraps it. None given → `Ticket: none`. Never build a Trello URL from a key, and a Jira link is not the card |
| `What` | 1–2 sentences. What someone *using the app* now sees. Never a file, resolver, hook or component name |
| `Why` | 1 sentence. The reason it was needed, not a restatement of What |
| `Check` | Steps a reviewer can do in the running app. Aim for 2–6 |
| `Screenshot` | Optional, last. Bitbucket-hosted image links only, one per line |

Enforced by `pr-body.py` — these numbers are the only ones that count:

| Limit | Warned | Refused |
|---|---|---|
| Words, outside image links | above 120 | above 250 |
| Lines, outside image links | above 20 | — |
| Check steps | — | none, or above 12 |
| Screenshot images | — | none in the section, above 6, or not on bitbucket.org |
| Title | — | empty, more than one line, above 70 characters, or starting with a type prefix (`feat:`) or a ticket key |

Above 120 words, cut. Above 250, the PR is too big — say so; do not squeeze the meaning out.

## Rules

- **British English. Non-technical in What and Why.** Name buttons, pages, messages.
- **Every claim is something the diff does.** Do not copy acceptance criteria across without
  confirming them, and never describe the other repo's half as if it were in this PR.
- **A step you never exercised is not a passed step.** Write it as something to check.
- **Permissions in the change → permissions in the Check**: one step per role or permission
  that behaves differently, the negative case included.
- **A purely technical PR** says so under What: "No user-visible change — <what moved and
  why>." It still gets a Check.
- **A cross-repo pointer, a migration warning or a breaking change** is the last sentence of
  Why ("Includes a dbmate migration — run `yarn db:migrate` after merge."), not a section.
- **Screenshots show the change, with no arrows or captions.** A frontend PR shows the page, a
  backend PR the endpoint answering with real data. Never a failing response, never a
  visible bearer token. Include one only when the user gives an already-uploaded Bitbucket
  URL — the API cannot upload one (`BITBUCKET.md`).

## Banned sections — dropped with their content

A heading, **or any line that starts with one of these words followed by `:` or `-`**, starts
a section that the formatter deletes, content and all, until the next Ticket / What / Why /
Check / Screenshot label. It prints `dropped section: <name>` on stderr:

Summary, Overview, Background, Context, Description, Motivation, Changes, Changes Made,
Change Summary, File Changes, Files Changed, Testing, Testing Strategy, Test Plan, Tests,
How to Test, QA, Note, Notes, Implementation Details, Implementation Notes, Technical
Details, Risk, Risks, Future Work, Follow-up, Follow up, Checklist, Acceptance Criteria.

So `Note: run the migration first` inside Why silently drops the rest of Why. Write the
sentence without the label. Any *other* unknown heading is refused, not dropped.

Banned phrases: "This PR", "This change introduces", "In order to", "It is worth noting",
"Additionally", "Comprehensive", "Robust", "Seamlessly", "leverage", "utilise". No emoji, no
bold sentences, no bullet list restating the file list. No attribution — the script strips
it, and `attribution.pr` is blank in `.claude/settings.json`.

## Cut it down

Write it, then delete, in order: any sentence that repeats the title; any sentence about
*how* the code works; any adverb, and "simply / just / basically / essentially"; any Check
step that only proves the app starts.

Before (56 words):

> This PR introduces a comprehensive permission check for the number series configuration
> functionality. Previously, the `numberSeries` settings page was accessible to all admin
> users regardless of their assigned permissions. We have now added a new `No. Series`
> permission to the shield configuration and wired it through the settings resolver so
> that the page is appropriately gated.

After (22 words):

> What: Number series settings are hidden from anyone without the No. Series permission.
> Why: Any admin could change them; only the finance role should.

## Title

A plain sentence describing the behaviour change, sentence case, 70 characters at most.
No type prefix, no ticket key, no repo name — the branch and commit carry those. Take it
from the ticket summary and shorten it. Seen in these repos:

```
Refuse holiday requests that exceed the remaining allowance
Export to Excel on the HR admin employees page
HR: keep filters in the address bar, and a Back button on employee pages
```

For a cross-repo pair, each title says what *that* repo's half does.
