---
name: business-requirement-writing-style
description: Write requirement language a developer can build from and QA can pass or fail — refine stakeholder wording instead of transcribing it, resolve vague phrases ("all information", "same as before", "properly"), stay non-technical without going vague, state every condition as a business rule, keep exact product labels, hold scope. Use whenever drafting a ticket, spec, user story or acceptance criteria.
---

# Business requirement writing style

A requirement says **what the requester wants, what the user should experience and what
success looks like** — never **how to build it**. This skill owns the wording. It does not
classify evidence, run the gate, read screenshots or own any template.

Two failures, both look fine on the page:

- **Too loose** — "all the information", "works properly". Wrong build. §3, §5, §8.
- **Too tight in the wrong direction** — the wording specifies implementation, so the build
  is locked to your guess. §4.

## 1. What every requirement sentence carries

| Slot | Question it answers | Missing it means |
|---|---|---|
| **Who** | which user, role or system acts | nobody knows who gets the permission |
| **Where** | product area, page, section, platform | built in the wrong place, or one place of three |
| **What** | the outcome, in the product's own nouns | the developer chooses the outcome |
| **When / condition** | trigger, state, filter, precondition | it fires always, or never |
| **Success** | the observable result | QA cannot pass or fail it |

A check, not a mould: *On \<where\>, \<who\> can \<what\> when \<condition\>, so that
\<why\>. It is done when \<observable result\>.*

## 2. Refine, do not transcribe — and do not over-refine

- **Raw:** `Add Export to Excel.`
- **Refined:** `On the Employees page, HR Admin users can export the employee information
  shown in the supplied screenshots to Excel.`
- **Over-refined (wrong):** `…click a new Export button top right, which downloads
  employees-<date>.xlsx with a bold header row.` — a position, file name and format nobody
  asked for, each now something to build and test.

The test: **can you point at the words or the image the phrase came from?** If not, cut
it or ask.

## 3. Vague wording, resolved

Resolve each from the evidence. Where the reading changes what gets built, it is a
question for the `requirement-evidence-and-gating` gate. Never write the vague phrase into
the document.

| Phrase | Resolve it by |
|---|---|
| "all the information", "everything" | Name the items, or state the boundary the evidence gives ("the fields shown in the supplied screenshots"). Boundary unclear and it changes the work → ask |
| "same as \<other screen\>", "like before" | Name the behaviour being copied, in this document's words. The other screen will change |
| "properly", "correctly", "as expected" | State the correct outcome. Delete the word |
| "user-friendly", "cleaner", "more intuitive" | Name the irritation and the observable fix ("status visible without opening the record") |
| "etc.", "and so on" | Finish the list, or state the rule that generates it |
| "some", "a few", "most" | Get the number or the condition |
| "should be able to" | Say who can, and whether anyone else cannot |
| "make it work", "fix it" | State current and required behaviour separately |
| "ASAP", "urgent" | Priority, not requirement — keep it out of the requirement text |
| "obviously", "just", "simply" | Delete the word; write out the assumption it hid |
| "improve", "optimise", "streamline" | State the current and wanted measure, or drop it |

## 4. Non-technical, but not vague

**Keep out (how):** endpoints, resolvers, components, SQL, migrations, tables, columns,
models, caches, queues, cron, libraries, architecture.

**Keep in, precisely (what):** required/optional/conditional fields, allowed values,
validation, defaults, numbering, notifications and who gets them, permissions that are part
of the requirement, the data included, every condition that changes behaviour.

**How in disguise** — "add a column", "add a toggle", "show the field when the box is
ticked", "run it nightly". Write the rule instead:

> When a supplier is marked as a Plant Supplier, an Off Hire Email Address must be provided.

Exception: when the requester sets a real constraint ("it must be the existing export"),
state it as a constraint and say whose.

## 5. State every condition as a business rule

For the change at hand, each is stated as a rule or deliberately excluded — never silently
absent:

- mandatory, optional or conditional — and the condition;
- allowed values, formats, lengths, ranges, units, decimal places;
- the default when nothing is chosen;
- none, one, many, and the maximum;
- duplicates: allowed, blocked or merged;
- inactive, archived, deleted and historical records — in or out;
- existing data, or only from now on;
- who may see it, who may change it;
- ordering where the user notices it;
- rounding, totals, tax or discount;
- dates: timezone, format, end date inclusive or not;
- notifications: who, when, what they say;
- what the user sees when it fails.

One rule per sentence — a sentence with two rules gets half built, and QA passes it. A rule
whose value is unknown goes to the gate; never invent a default.

## 6. Preserve terminology exactly

- Product and UI labels verbatim, capitals included: `Export to Excel`, never "excel export".
- Keep the requester's noun: "off hire" stays "off hire", not "return".
- Never invent a name for a screen, field or status — it becomes the product's name.
- Technical identifiers are never renamed.
- A label that is wrong in the product: quote it and say so; do not quietly correct it.

## 7. Scope discipline

Deliver the request, nothing adjacent — no unrequested export format, scheduling, emailing,
history, import, filters, bulk actions, audit trail or permissions. Distrust "while we're in
there".

Extra work appears in the text two ways only:

- **Dependency** — the request cannot work without it. State it with why, in the
  deliverable's decisions slot (a ticket's `Decisions already made`): "**Department
  field:** must be populated for existing employees — the export groups by it."
- **Named exclusion** — adjacent and not included. State it once in the out-of-scope line,
  even when obvious, with no invitation to renegotiate.

## 8. Testable, not aspirational

Everything is pass/fail-able by someone who was not in the conversation.

| Not testable | Testable |
|---|---|
| "Handle errors gracefully" | "If the export fails, the user is told it failed and the page stays usable" |

Observable outcomes, in the order a person would check them. Numbers as numerals. No
hedging — "should probably", "ideally", "if possible" each make the requirement optional.

## 9. Sentence craft

- Present tense, active voice, the actor named: "HR Admin users export…".
- One rule per sentence; one idea per bullet.
- No padding, no rhetorical questions, no "as discussed".
- "The field is mandatory", not "the field should probably be mandatory".
- Spelling and tone: `plain-uk-english`. Product labels (§6) and identifiers stay verbatim.

## 10. Boundaries

- **Evidence and the gate** — `requirement-evidence-and-gating`. This skill phrases what
  that skill admitted; it never admits a claim itself.
- **Reading images** — `screenshot-requirement-analysis`.
- **The deliverable** — template, sections, fixed lines, where it is created, tool fields:
  the calling skill (e.g. `ticket-writing`).
- **Estimating, prioritising, planning** — not wording decisions.
