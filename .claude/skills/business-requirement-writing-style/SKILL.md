---
name: business-requirement-writing-style
description: Write requirement language that a developer can build from and QA can pass or fail — refining informal stakeholder wording instead of transcribing it, resolving vague phrases like "all information", "same as before", "properly" and "user-friendly" into stated boundaries, keeping the prose non-technical without letting it go vague, stating every condition as a business rule, preserving the product's exact labels, and holding scope so nothing unrequested creeps in. Use whenever drafting a ticket, spec, user story, acceptance criteria or any requirements document for a developer/QA audience — anywhere the deliverable must describe what and why without describing how. Owns the wording; does not classify evidence, run the ambiguity gate, read screenshots, or own any document's template.
---

# Business requirement writing style

A requirements document answers **what the requester wants, what the user should
experience, and what success looks like** — never **how a developer should build it**.

This skill owns the wording: turning "add export to excel" into a sentence somebody can
build from without guessing, and catching the phrases that read as specific but are not.

Two ways the prose fails, and both look fine on the page:

- **Too loose** — "all the information", "works properly". Passes review, produces the
  wrong build. Caught by §3, §5, §8.
- **Too tight in the wrong direction** — the wording specifies implementation, so the
  build is locked to your guess instead of the requirement. Caught by §4.

## 1. What every requirement sentence has to carry

Five slots. A sentence missing one is not yet a requirement:

| Slot | Question it answers | Missing it means |
|---|---|---|
| **Who** | which user, role or system acts | nobody knows who gets the permission |
| **Where** | product area, page, section, platform | it gets built in the wrong place, or in one place of three |
| **What** | the outcome, in the product's own nouns | the developer chooses the outcome |
| **When / under what condition** | trigger, state, filter, precondition | it fires always, or never |
| **What success is** | the observable result | QA cannot pass or fail it |

Pattern, useful as a check rather than a mould to force prose into:

> On **\<where\>**, **\<who\>** can **\<what\>** when **\<condition\>**, so that
> **\<why\>**. It is done when **\<observable result\>**.

## 2. Refine, do not transcribe — and do not over-refine

**Raw:** `Add Export to Excel.`

**Refined:** `On the Employees page, HR Admin users need to export the employee
information shown in the referenced views to Excel. The export covers the employee
information represented across the supplied screenshots.`

**Over-refined — wrong:** `On the Employees page, HR Admin users can click a new Export
button in the top right, which downloads an .xlsx file named employees-<date>.xlsx with
one sheet per screenshot and a header row in bold.`

The second sentence added **where, who, what data, under what conditions, what success
is**. The third invented a button position, a file name, a sheet layout and a format
nobody asked for — every one of those is now a requirement somebody must implement and QA
must check. Refinement adds precision that came from the request; anything else is
invention, and it belongs nowhere near the document.

Test for the line between them: **can you point at the words or the image the phrase came
from?** If not, cut it or ask.

## 3. Vague wording, resolved

These phrases read as specific and are not. Resolve each from context; where the reading
changes what gets built, it stops being a wording choice and becomes a question for the
`requirement-evidence-and-gating` skill's gate.

| Phrase | What it can mean | Resolve it by |
|---|---|---|
| "all the information" | everything on screen · every field in the system · the fields in the images | Images bound the fields → say "the information represented across the supplied screenshots". Requester said "every X in the system" → keep that broader scope. Conflict, or the boundary changes the work → ask |
| "everything", "the whole thing" | same trap, wider | Name the items. A list of eight beats the word "everything" |
| "same as \<other screen\>", "like before", "as we did for suppliers" | copy behaviour · copy layout · copy only the part they were looking at | Name the behaviour being copied, in this document's own words. Never write "same as X" as the requirement — the other screen changes, and then nobody knows what was agreed |
| "properly", "correctly", "as expected" | there is a rule in the requester's head | Ask what the correct outcome is, then state that outcome. Delete the word |
| "user-friendly", "cleaner", "more intuitive" | a specific irritation | Name the irritation and the observable improvement ("the status is visible without opening the record") |
| "etc.", "and so on", "and the rest" | an unfinished list | Finish the list, or state the rule that generates it ("every field shown in the Details section") |
| "some", "a few", "most" | an unstated threshold | Get the number or the condition |
| "should be able to" | permission · capability · nothing at all | Say who can do it, and whether anyone else cannot |
| "make it work", "fix it" | a defect with an unstated correct behaviour | State current behaviour and required behaviour separately |
| "ASAP", "urgent" | priority, not requirement | Keep it out of the requirement text; it belongs in the deliverable's priority or severity field |
| "obviously", "just", "simply" | assumed shared context | Delete the word and write the assumption out. These three words hide more requirements than any others |
| "improve", "optimise", "streamline" | no target | State the current measure and the wanted one, or drop it |

Resolving a vague phrase yourself is correct when the evidence answers it. Writing the
vague phrase into the document is never correct.

## 4. Non-technical, but not vague

**Keep out** — this is *how*: endpoints, resolvers, controllers, services, components,
SQL, migrations, tables, columns, ORM models, indexes, caches, queues, cron expressions,
libraries, frameworks, architecture.

**Keep in, precisely** — this is *what*: required vs optional vs conditional fields,
allowed values, validation rules, defaults, numbering and sequencing, notifications and
who receives them, permissions where they are part of the requirement, the data that must
be included, and every condition that changes behaviour.

**How, in disguise.** These read as requirements and are not:

- "add a column to the table" — a storage decision. The requirement is what information
  must be recorded and shown.
- "add a toggle in settings" — a UI mechanic. The requirement is what must be
  configurable, by whom.
- "show/hide the field when the checkbox is ticked" — mechanics again. Write the rule:

  > When a supplier is marked as a Plant Supplier, an Off Hire Email Address must be
  > provided. This address is used for off-hire notifications.

- "cache it", "run it nightly", "use a background job" — performance and scheduling
  implementations. The requirement is the freshness or timing the business needs ("the
  figure reflects yesterday's close of business").

The exception: when the requester **is** the one specifying it and it is a genuine
constraint ("it must be the existing export, not a new one"), state it as a constraint and
say whose constraint it is.

## 5. State every condition as a business rule

Business rules are where requirements go missing, because the happy path is easy to write
and the edges are where the work is. For the change at hand, each of these is either
stated as a rule or deliberately excluded — never silently absent:

- mandatory, optional, or conditional — and what the condition is;
- allowed values, formats, lengths, ranges, units, decimal places;
- the default when nothing is chosen;
- what happens with none, one, many, and the maximum;
- duplicates: allowed, blocked, or merged;
- inactive, archived, deleted and historical records — in or out;
- does it apply to existing data, or only from now on;
- who may see it, who may change it;
- ordering and sorting where the user notices it;
- rounding, totals, and whether a figure includes tax or discount;
- dates: which timezone, which format, inclusive or exclusive of the end date;
- notifications: who receives them, when, and what they say;
- what the user sees when it fails.

One rule per sentence. A sentence holding two rules gets half-implemented, and QA passes
it.

Where the rule's value is genuinely unknown, that is not a wording problem — hand it to
the gate rather than inventing a default.

## 6. Preserve terminology exactly

- Product and UI labels stay verbatim, capitalisation included: `Export to Excel` stays
  `Export to Excel`, never "Export to Spreadsheet", never "excel export".
- Keep the requester's noun for the entity. If the business says "off hire", the document
  says "off hire", not "return".
- Never invent a label for something that has one, and never name a new screen, field or
  status in passing — a name invented in a requirement document becomes the name in the
  product.
- Technical identifiers are never renamed: variables, functions, columns, API fields,
  routes, file names appear exactly as they are, when they appear at all.
- Where the product's own label is wrong or inconsistent, quote it and say so; do not
  quietly correct it.

## 7. Scope discipline

Deliver the request, nothing adjacent. No unrequested CSV or PDF export, scheduling,
emailing, export history, import, extra filtering, bulk actions, audit trail or new
permissions, however natural the add-on feels.

The "while we're in there" instinct is the one to distrust: it turns a one-day change into
a three-day change nobody asked for, and it puts work in the document that the requester
never agreed to prioritise.

Two legitimate ways extra work appears in the text:

- **Dependency** — the request cannot work without it. State it as a dependency, with why:
  "This requires the Department field to be populated for existing employees."
- **Named exclusion** — it is adjacent and deliberately not included. State it once in the
  out-of-scope line: "The same export on the Contractors page is not included."

An exclusion is stated even when it feels obvious, and stated without inviting a later
negotiation.

## 8. Testable, not aspirational

Every statement is pass/fail-able by someone who was not in the conversation. Rewrite
anything that is not:

| Not testable | Testable |
|---|---|
| "The export should be user-friendly" | "The exported file opens in Excel with one row per employee and the column headings shown in the screenshots" |
| "Performance should be acceptable" | "The export completes without the page timing out for the largest current department (412 employees)" |
| "Handle errors gracefully" | "If the export fails, the user is told it failed and the page stays usable" |
| "Validation should be improved" | "An Off Hire Email Address that is not a valid email address is rejected, and the user is told why" |

Write the expected result as observable outcomes, in the order a person would check them.
Numbers as numerals. No hedging — "should probably", "ideally", "if possible" — because
each one silently makes the requirement optional and it will be the first thing dropped.

## 9. Sentence craft

- Present tense, active voice, the actor named: "HR Admin users export…", not "it should
  be possible for the data to be exported".
- One rule per sentence; one idea per bullet.
- No narrative padding, no restating the problem inside the solution, no rhetorical
  questions, no "as discussed".
- Direct prose over hedged prose. "The field is mandatory" — not "the field should
  probably be mandatory".
- Which spelling variant and house language the document uses is the **calling skill's**
  decision, not this skill's. Apply whatever it specifies, and remember the two carve-outs
  that always survive it: product labels (§6) and technical identifiers.

## 10. Boundaries — what this skill does not own

- **Evidence and the gate.** Whether a claim is allowed in at all — tags, coverage,
  materiality, question rounds, placeholder ban, the "not sufficiently defined" report —
  belongs to `requirement-evidence-and-gating`. This skill phrases what that skill
  admitted; it never admits a claim on its own.
- **Reading images.** Page, tabs, labels, columns, filters, states, annotations,
  before/after pairs and unreadable crops belong to `screenshot-requirement-analysis`.
- **The deliverable.** Template, section order, fixed lines, house language variant, where
  it is saved or created, and any tool field values belong to the calling skill (for
  example `ticket-writing`, which owns the Jira ticket template and its fields).
- **Estimating, prioritising, planning.** Effort, severity, priority and sequencing are
  not wording decisions.
