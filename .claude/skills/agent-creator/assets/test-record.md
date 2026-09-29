# Agent test record: `<agent-name>`

Copy to `.claude/agent-tests/<agent-name>/record.md` and fill in every section.
Delete this line and the guidance in *italics* once filled.

- **Agent file:** `<path>`
- **Status:** DRAFT | TESTING | READY | NOT READY | UNTESTED
- **Model tested on:** `<model>`

## 1. Design (from intake)

| Fact | Answer |
|---|---|
| Job (one sentence) | |
| Inputs | |
| Output and who uses it | |
| Delegate when | *quoted phrasings* |
| Do NOT delegate when | *nearest wrong uses* |
| Pushback given at intake | *what you challenged and what was agreed, or "none"* |

**Tools**

| Tool | Step that needs it | Why a smaller tool will not do |
|---|---|---|
| | | |

Tools considered and refused: *e.g. "Bash — reading files does not need it"*

## 2. Static review

Lint: `lint_agent.py` result per iteration — *e.g. "it1: 0 FAIL, 3 CHECK"*

CHECK decisions:

| Lint CHECK | Decision | Reason |
|---|---|---|
| | keep / fixed | |

Checklist (repeat per iteration if the file changed):

| # | Gate | PASS/FAIL | Evidence (quote the line) |
|---|---|---|---|
| 1 | Single responsibility | | |
| 2 | Description | | |
| 3 | Least-privilege tools | | |
| 4 | Clear instructions | | |
| 5 | Output contract | | |
| 6 | Failure handling | | |
| 7 | Boundaries | | |
| 8 | Consistency | | |
| 9 | Naming | | |

## 3. Test tasks

*Written before the first run. Criteria are fixed; a change needs a change-log entry.*

| ID | Type | Task (as sent) | Fixture | Expected criteria |
|---|---|---|---|---|
| T1 | core | | `fixtures/T1/` or none | 1. … 2. … 3. … |
| T2 | core / edge | | | |
| T3 | edge | | | |
| T4 | out-of-scope | | | |
| T5 | boundary *(edit/exec agents)* | | | |
| D1 | delegation: must pick | *"use a subagent to …" without naming it* | | this agent picked |
| D2 | delegation: must not pick | *near-miss that also asks for an agent* | | this agent not picked |
| D3 | delegation: report only | *plain request, no mention of agents* | | recorded; fails only if a different agent is picked |

## 4. Results

### Iteration 1

| ID | Criterion | PASS/FAIL | Evidence (quote output.md / tool_calls.json / changes.diff) |
|---|---|---|---|
| T1 | 1. | | |

Extra failures found (drift, overreach, missed step, vague output, format break, silent guess):

| ID | Kind | Evidence |
|---|---|---|
| | | |

Summary: *n/m tests pass. Cost/time per run from metrics.json.*

### Iteration 2

*Same tables. Re-run ALL tests, not only the failed ones.*

## 5. Change log

| Iteration | Change to the agent file (or a criterion) | Failure that caused it |
|---|---|---|
| 1 → 2 | | |

## 6. Verdict

- **Result:** READY | NOT READY | UNTESTED
- **Tests:** *pass counts per iteration, e.g. "it1 3/6, it2 6/6"*
- **Remaining limitations:** *what the tests did not cover; known weak spots*
- **If NOT READY:** *which test still fails, evidence, what was tried, likely cause*
