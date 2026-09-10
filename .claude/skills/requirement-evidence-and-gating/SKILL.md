---
name: requirement-evidence-and-gating
description: Classify every claim behind a requirement as EXPLICIT (the requester said it), VISUAL (readable in a supplied image), CODEBASE (confirmed in code) or INFERENCE (assumed), account for every part of the request so nothing is silently dropped, and block the deliverable while a material ambiguity is still unresolved. Use whenever raw stakeholder input — PO notes, chat messages, bug reports, feature requests — is being turned into a ticket, spec, user story, plan or any written deliverable where an invented or missed requirement causes real rework. Trigger even when the calling task never says "evidence": any "turn this messy input into a formal document" job needs it. Owns evidence tagging, coverage and the ambiguity gate; does not read images itself and does not own any document's template.
---

# Requirement evidence & gating

A written deliverable is only as good as what it can prove. This skill is the shared
discipline for telling apart what was actually **said** from what was merely **assumed**,
for proving that nothing in the request was **left out**, and for refusing to ship while a
material assumption is still hiding inside the document.

Two failure modes, equally expensive, and this skill exists to catch both:

- **Invented** — the document states something nobody asked for. Caught by §1–§2.
- **Missed** — the requester said or showed something and the document quietly lost it.
  Caught by §3–§4.

## 1. The evidence ledger — build it before writing a word

Keep one working ledger for the whole job. It is internal (chat/scratch, never part of the
deliverable) but it is not optional: the gate in §6 and the coverage check in §4 both read
from it.

| # | Claim, in the source's own words | Tag | Disposition | Lands in |
|---|---|---|---|---|
| 1 | "export all the employee info to Excel" | `EXPLICIT` | `USED` | Requested behaviour |
| 2 | Active filter applied in screenshot 1 | `VISUAL` | `QUESTION` | — (asked, round 1) |
| 3 | Export button already exists on Suppliers | `CODEBASE` | `IMMATERIAL` | — (logged, dropped) |

### Tags

| Tag | Source | May appear in the deliverable |
|---|---|---|
| `EXPLICIT` | The requester said it, in text or speech | Yes |
| `VISUAL` | Clearly readable in a supplied image (rows come from the `screenshot-requirement-analysis` skill) | Yes |
| `CODEBASE` | Confirmed in the code, for the specific environment affected | Yes, as current behaviour |
| `INFERENCE` | You think it is probably meant | **No** |

When sources disagree, priority is `EXPLICIT` > `VISUAL` > `CODEBASE` > `INFERENCE`. Record
the conflict as its own row — a screenshot that contradicts the text is usually the most
important thing you will find, and it is nearly always a `QUESTION`.

`INFERENCE` never becomes a requirement. Material to what gets built → it becomes a
question (§6). Not material → drop it, but log the row so the drop was a decision and not
an accident.

**Unknown beats invented.** Never fabricate fields, rules, roles, permissions, formats,
workflows, severity, estimates, relationships, tool or system field values, or existing
functionality to fill a gap. A guess dressed as a fact is worse than a blank.

## 2. Capture the raw input verbatim first

Before refining anything, keep the requester's original wording — the message, the quoted
chat, the bug report — unedited, in the ledger's source column or beside it. Refinement is
lossy by design; the verbatim text is what §4 checks the draft against, and what settles a
later "that is not what I asked for".

Where the calling skill keeps a record of the work (a sidecar, a ticket comment, a plan
file), the verbatim request belongs there too.

## 3. Every part of the request gets a disposition

Split the input into **atomic** items — one ask, rule, condition, constraint, field,
audience, environment or example per row. A sentence with three clauses is three rows.
Sources to split, all of them:

- the request text, including asides, parentheses, "also" clauses and anything after
  "oh and";
- every readable element the screenshot skill reported (§ that skill's inventory);
- quoted messages, forwarded complaints, and the example the requester gave;
- explicit non-asks ("not the mobile app", "don't touch the invoices") — these are rows
  too;
- anything the requester asked for **earlier in this same conversation** and has not
  withdrawn.

Every row carries exactly one disposition:

| Disposition | Means | Requirement |
|---|---|---|
| `USED` | It is in the deliverable | Name the section it lands in |
| `SCOPE-OUT` | Deliberately not included | Must be stated once in the deliverable's out-of-scope line — a silent exclusion is a missed requirement |
| `IMMATERIAL` | Does not change what gets built | Logged in the ledger, absent from the deliverable |
| `QUESTION` | Material and unresolved | Blocks (§6) until answered |
| `UNVERIFIABLE` | A system fact you could not confirm | §8 — the only legitimate "unknown" |

No row may be left blank. An unassigned row is exactly how a requirement goes missing.

## 4. Coverage check — before the deliverable is written

Re-read the verbatim input (§2) clause by clause with the draft beside it, and confirm all
four:

1. **Nothing dropped** — every ledger row has a disposition, and every `USED` row is
   actually findable in the draft. Not "covered in spirit" — findable.
2. **Nothing added** — every statement in the draft traces back to a ledger row tagged
   `EXPLICIT`, `VISUAL` or `CODEBASE`. A sentence with no row is an `INFERENCE` that got
   in; cut it or turn it into a question.
3. **Both directions cross-checked** — something the text names but no image shows, and
   something an image shows that the text never mentions, are both findings. Each is a
   `QUESTION` when it changes the work, `IMMATERIAL` when it does not, never nothing.
4. **Numbers, names and values survived** — every quantity, limit, date format, currency,
   role name, status name, field label and option value appears in the draft exactly as
   the source gave it. Rewording a product label or rounding a number is a lost
   requirement, not a style choice.

Failing 1 or 4 means go back and fix the draft. Failing 2 means cut or ask. Failing 3
means ask.

## 5. Materiality — the test that decides whether to interrupt

**Material** means two readings would produce different functionality, different
acceptance criteria, or different work. Worked examples of material: all records vs only
the filtered ones; mandatory vs optional; applies to existing data or only to new; what
happens when a selection is removed; which environment or branch is affected; who is
allowed to see it; the exact user-facing wording when the requester cares about wording;
whether a total includes tax.

Not material: wording nits in your own prose, formatting, ordering of sections, anything
the deliverable's template already decides.

**Resolve it yourself** when intent is obvious from the requester's wording, the images,
existing product terminology, or existing behaviour confirmed in code. Interrupting for
what the evidence already answers slows the job and teaches people to stop reading your
questions carefully.

## 6. The gate — ambiguity is blocking, not annotatable

You are refining a requirement with the requester, not summarising whatever they happened
to send. An unresolved material question **stops the deliverable**. It is never written
down as an open item and handed downstream as someone else's problem.

Before the deliverable is written, every `QUESTION` row needs a requester answer.

- Ask with your available question tool (`AskUserQuestion` where present), **batched — at
  most four per round**.
- Each question carries **concrete options drawn from what the evidence actually
  supports**, never invented options, and says in one clause why the answer changes what
  gets built.
- An answer that opens a new material question earns another round. **Three rounds
  maximum.**
- After three rounds still unresolved, or the requester declines to decide: **do not
  produce the deliverable.** Report instead (§9).
- Never ask what the code, the images, or the requester's own wording already answers.
- One question per decision. A question bundling two decisions gets one answer and leaves
  one still open.

**Answers are `EXPLICIT` from that point on.** Use them exactly as given: an answer is not
raw material to re-interpret, and "yes, but also…" is a new row, not a rewrite of the old
one.

### Forbidden in the finished deliverable

No placeholder standing in for a decision the requester must make: "to be confirmed",
"TBC", "TBD", "to be decided", "to be agreed", "development to decide", "assumed",
"presumably" — and no `UNKNOWN — REQUIRES VERIFICATION` attached to anything the requester
could have answered. Search the draft for these strings before handing it on; a hit means
the gate did not actually run.

## 7. Scope is not ambiguity

Something the requester deliberately chose *not* to ask for is scope, not an open
question. It is a `SCOPE-OUT` row: state it once in the deliverable's out-of-scope line,
with no invitation to revisit it later, and do not raise it as a question.

## 8. The one legitimate "unknown"

`UNKNOWN — REQUIRES VERIFICATION` is legitimate for exactly one thing: a **system fact you
genuinely could not verify** — whether a feature exists in a given environment, how code
reaches a particular stage, what a third party returns. That is an investigation limit, and
it belongs in the deliverable stated as such, with what you tried.

A requirement gap is never this. It is always a question for the requester.

## 9. If the gate fails, report — do not produce

When three rounds pass without resolution, or the requester will not decide, stop and
report in this shape (swap `<deliverable>` for whatever the calling skill produces —
ticket, spec, story, plan):

```
<Deliverable> not created — requirement not sufficiently defined.

Open questions:
- <question>  (why it changes what gets built)

Already established:
- <what the investigation did settle>

Answer these and the <deliverable> can be written.
```

Nothing partial gets saved, created or sent. A half-resolved document is more dangerous
than none, because it looks finished. Reporting open questions is a **successful
outcome** — do not apologise for it, and do not offer to produce the deliverable anyway
with the gaps noted.

## 10. What the calling skill gets back

Hand back exactly this, so the caller can write without re-deriving anything:

- the ledger, with every row dispositioned;
- the `USED` rows grouped by the section they land in;
- the `SCOPE-OUT` lines, ready to paste into the out-of-scope statement;
- any `UNVERIFIABLE` row with what was tried;
- gate verdict: `PASSED` (nothing blocking) or `BLOCKED` with the §9 report.

`BLOCKED` means the caller writes nothing. That decision is this skill's, not the
caller's.

## 11. Boundaries — what this skill does not own

- **Reading images.** Page, tabs, labels, columns, states, annotations, before/after
  pairs, unreadable crops, and whether several images are one requirement — all owned by
  the `screenshot-requirement-analysis` skill. This skill consumes the rows it produces
  and tags them `VISUAL`. Do not re-derive image content here.
- **The deliverable's shape.** Templates, section wording, house style, where it is saved
  or created, and any tool-specific field values belong to the calling skill (for example
  `ticket-writing`, which owns the Jira ticket template and its fields).
- **Investigating the codebase.** This skill says a `CODEBASE` claim must be confirmed at
  the affected environment; how to confirm it is the calling skill's or the repo's job.
- **Writing prose.** Language, tone and British English are the calling skill's.
