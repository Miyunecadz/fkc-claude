# Triage — duplicate, existence verdict, tier

Read at intake, before refining anything. Three questions: **does Jira already have it**,
**does the code already do it**, and **how much definition does it need**.

## 0. Order and budget — cheapest exit first

They are not equally cheap. §1 and §3 cost a handful of calls; **§2 is where every git
and grep call goes**, and it is the single largest cost in creating a ticket. So §2 runs
**last of the three, and only on a request that survived the first two**:

1. **§1 duplicate check** — 2–3 `jira_search` calls. A hit ends the workflow for the
   price of three tool calls, before a line of code is read.
2. **Text-only gap screen** — from the request, the screenshots and nothing else, list
   the material gaps; `requirement-evidence-and-gating` §5 decides what counts as
   material. If a gap would change *what gets built* and **no amount of code reading can
   answer it** — an undecided business rule, an unnamed threshold, an unstated
   environment, a conflict between two things the requester asked for — **ask now**,
   before §2, and create nothing while it is open. Code inspection against a requirement
   that is not yet decided is paid for twice: once now, once after the answer changes it.
3. **§2 existence verdict** — only for what is still live after 1 and 2, only for the
   area the request touches, and within the caller's inspection budget.
4. **§3 tier** — free; it reads what 1–3 already found.

A gap the code *can* settle — "does the export already include that column", "is the
field already optional" — is **not** a question for the requester. That is what §2 is
for. Only ask what the code cannot decide.

## 1. Duplicate check — always first

The ticket is going into a shared backlog, so a duplicate costs someone else time. Search
the project resolved from `.mcp.json` (`JIRA.md` §1–2) using the requester's own nouns:

```
mcp__jira__jira_search { jql: "project = <KEY> AND statusCategory != Done AND text ~ \"<key phrase>\" ORDER BY updated DESC", limit: 20 }
```

Try two or three phrasings — the product's label for the thing, and the user-visible noun.
Also sweep `statusCategory = Done` when the request sounds like a regression: an issue
closed last month is evidence about current behaviour.

| Finding | What happens |
|---|---|
| An open issue covers the same outcome | **Stop.** Report the key; the requester extends that issue or reframes this one |
| An open issue overlaps partly | Report it, then continue with the boundary narrowed — say in `Not included in this ticket` what the other issue owns |
| A closed issue describes the same outcome | Read it before continuing. Either this is a regression (say so, with the key) or the outcome already holds |
| Nothing | Continue |

Never conclude "no duplicate" from one query with one phrasing.

## 2. Existence verdict — before any clarification round

Targeted read at the branch the request is about (`git show <ref>:<path>`, `grep` the
directory the request touches). Stop as soon as one of these is true:

| Verdict | Means | What happens |
|---|---|---|
| `NOT_PRESENT` | nothing implements this | continue to refinement |
| `PARTIALLY_IMPLEMENTED` | some of the outcome already holds | report what exists with `file:line`; the requester reduces scope before refinement continues |
| `ALREADY_IMPLEMENTED` | the requested outcome is already true on that branch | report the evidence and **stop**. The requester closes or reframes |
| `IMPLEMENTED_DIFFERENTLY` | it exists but behaves differently from the request | this is a change or a fix, not a new feature — reframe before refining |
| `ELSEWHERE_ONLY` | it exists on another branch, not the one the request is about | say which branch. A difference between environments is not automatically a bug |

Never conclude `NOT_PRESENT` from a single failed grep — check the plausible names first.
This stage prevents the most expensive mistake in the workflow — refining, planning and
building something the product already does — but it is not free: it is where the shell
calls go, so it runs inside the caller's inspection budget and stops the moment it has a
verdict. Read the area the request touches, nothing wider.

Branch matters: `master` and `staging` have diverged in this workspace, so "does this
exist" has no answer until a branch is named. Read current behaviour at that ref with
`git show <branch>:<path>` — never switch the user's working tree to look.

## 3. Tier — set by triggers, not by feel

Any one trigger is sufficient. Take the highest tier that matches.

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

What the tier changes in the ticket:

```
T1   Problem, Requested behaviour, Not included, Expected result
T2   + Success measure, and Business rules spelled out with their edge cases
T3   + the problem stated as a problem, not a solution; the alternatives the requester
       has already rejected, if they named any; explicit data-safety expectations
```

Two rules keep this honest:

- **Escalate freely, downgrade only with a human.** Raising a tier is a safety move.
  Lowering one accepts risk, which is not the assistant's decision.
- **Re-check the tier if refinement uncovers something new.** A migration nobody expected
  moves T2 to T3, and the extra requirements then apply.

## 4. What triage does not do

It does not design, estimate in hours, or decide priority. Appetite — how much time this is
worth — comes from the requester and belongs in `TIME ESTIMATE` as a budget, never as a
prediction.
