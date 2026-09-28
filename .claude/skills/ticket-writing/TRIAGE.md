# Triage — duplicate, existence verdict, tier

Three questions: **does Jira already have it**, **does the code already do it**, and **how
much definition does it need**. This file owns the order they run in and what the tier
changes.

## 0. Order — cheapest exit first

Code reading is the largest cost in creating a ticket, so it runs last, and only on a
request that survived the cheap checks:

1. **§1 duplicate check** — 2–3 `jira_search` calls. A hit ends the workflow before a line
   of code is read.
2. **Text-only gap screen** — from the request and screenshots alone, list the material
   gaps (`requirement-evidence-and-gating` §5 decides what is material). A gap that would
   change *what gets built* and that **no code reading can answer** — an undecided rule, an
   unnamed threshold, an unstated environment, two asks that conflict — is asked now,
   before §2. Inspecting code against an undecided requirement is paid for twice.
3. **§2 existence verdict** — only for what is still live, only for the area the request
   touches, inside the caller's inspection budget.
4. **§3 tier** — free; it reads what the steps above found.

A gap the code *can* settle — "does the export already include that column" — is not a
question for the requester. That is what §2 is for.

## 1. Duplicate check — always first

Run the searches in `JIRA.md` §2, using the requester's own nouns. Try two or three
phrasings — the product's label for the thing, and the user-visible noun. Never conclude
"no duplicate" from one query with one phrasing.

| Finding | What happens |
|---|---|
| An open issue covers the same outcome | **Stop.** Report the key; the requester extends that issue (`UPDATE.md`) or reframes this one |
| An open issue overlaps partly | Report it, then continue with the boundary narrowed — `Out of scope` names what the other issue owns, with its key |
| A closed issue describes the same outcome | Read it. Either this is a regression (say so, with the key) or the outcome already holds |
| Nothing | Continue |

A `Bug` also needs a way to see the fault: a page or screen, an environment, and steps or
a screenshot of the result. Missing and the code cannot settle it → a text-only gap (§0
step 2), asked before any code is read.

## 2. Existence verdict

A targeted read at the branch the request is about (`git -C <repo> show <branch>:<path>`,
or `grep` on the directory the request touches). Stop as soon as one verdict holds:

| Verdict | Means | What happens |
|---|---|---|
| `NOT_PRESENT` | nothing implements this | continue |
| `PARTIALLY_IMPLEMENTED` | some of the outcome already holds | report what exists with `file:line`; the requester reduces scope before refinement continues |
| `ALREADY_IMPLEMENTED` | the outcome is already true on that branch | report the evidence and **stop** |
| `IMPLEMENTED_DIFFERENTLY` | it exists but behaves differently | a change or fix (`Bug`), not a new feature — reframe first |
| `ELSEWHERE_ONLY` | it exists on another branch only | name the branch. A difference between environments is not automatically a bug |

Never conclude `NOT_PRESENT` from one failed grep — check the plausible names first. Read
the area the request touches, nothing wider.

"Does this exist" has no answer until a branch is named: environment branches in these
repos can diverge, so a feature on one is not evidence about another. Never switch the
user's working tree to look.

**Keep what you read — it becomes two sections.** Every path you open, with the branch,
what it does today and what would change there, is `Files/areas to touch`. While in the
area, look once for a feature in the same repo that already solves a similar problem (the
other list with an export, the other form with that validation) and open it: that is
`Existing patterns to follow`. Nothing comparable → the ticket says so. Do not widen the
read to find one.

## 3. Tier — set by triggers, not by feel

Any one trigger is enough. Take the highest tier that matches.

| Trigger | Minimum tier |
|---|---|
| copy, label, message, styling, or one field's validation — single repo, no contract change | **T1** |
| new or changed business rule affecting what gets saved | **T2** |
| schema change or a new migration | **T2** |
| a GraphQL type, query or mutation added or altered | **T2** |
| `src/configs/shield.js`, roles, or who may see a record | **T2** |
| money, allowance, rate or period arithmetic | **T2** |
| two or more repos in scope | **T2** |
| `fk-mobile` in scope | **T2**, and flag it: no `node_modules`, no pipeline, nothing runnable |
| existing rows change meaning, or need a backfill | **T3** |
| data can be lost, or a migration cannot be reversed | **T3** |
| authentication, tenancy, or cross-employee visibility changes | **T3** |
| a new integration, external system, or class of background job | **T3** |
| the problem itself is not agreed (competing objectives, unclear user) | **T3** |

What the tier changes — every section is present at every tier (`TEMPLATE.md`); the tier
decides how much goes in:

```
T1   Decisions may be "None beyond the acceptance criteria."
T2   + a success measure in the Goal; every business rule and edge case as a decision,
       and as its own acceptance criterion
T3   + the Goal stated as a problem, not a solution; alternatives the requester already
       rejected, as decisions; explicit data-safety expectations, as decisions
```

The tier never sets a Jira label or priority.

- **Escalate freely, downgrade only with a human.** Lowering a tier accepts risk, which is
  not the assistant's decision.
- **Re-check the tier if refinement finds something new.** A migration nobody expected moves
  T2 to T3.

## 4. What triage does not do

It does not design, estimate in hours or decide priority. An appetite comes from the
requester (`TEMPLATE.md`, `TIME ESTIMATE`).
