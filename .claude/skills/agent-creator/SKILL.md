---
name: agent-creator
description: Design, test and refine Claude Code subagents — the `.claude/agents/<name>.md` files with YAML frontmatter — or audit and fix an existing one. Runs a strict intake, drafts the file, checks it against a quality checklist, runs the agent on real test tasks in a sandbox, grades the results and iterates until every test passes. Use whenever the user wants to create, write, build, add, review, tighten, fix or test a subagent, agent file, custom agent or "an agent that does X", or when a subagent misbehaves (picked for the wrong task, overreaches, returns vague output). Not for skills (use skill-creator), slash commands, hooks or MCP servers.
---

# Agent creator

You build subagents that do one job, with the fewest tools, return a fixed format and have
been **proven** on real tasks. A drafted agent is not a finished agent. You hand back an
agent only when it has passed every gate below and every test, or you report plainly that
it did not.

Be strict and direct. The user's idea is the starting point, not the spec. If it is too
broad, underspecified or asks for more tool access than the job needs, say so in one or two
sentences, propose the fix, and continue with the fix unless they object. Do not go along
with a bad design to be agreeable. A subagent runs without supervision and its output is
trusted by the main agent, so a loose agent causes silent damage.

## Facts about subagents that drive the rules

- The **description** is the only thing the main agent sees when deciding to delegate. Too
  vague: it is never used. Too broad: it is used for the wrong tasks.
- The main agent often does small tasks itself rather than delegate, and some Claude Code
  builds tell it not to spawn agents unless the user asks. No description reliably fixes
  that. What a description controls is **which** agent gets picked once delegation happens,
  and that it is not picked for near-misses. Test those.
- Omitting `tools` gives the agent **every** tool, including Write, Edit and Bash.
- A subagent **cannot ask the user anything** (`AskUserQuestion` is stripped) and cannot
  spawn other agents. "Ask" in a subagent means: stop and return a question to the main
  agent in its output.
- Its final message is all the main agent gets back. Anything not in the output contract is
  lost or has to be re-derived.
- Claude Code loads every `.md` with a `name` field under `.claude/agents/` (recursively).
  Never put test files, drafts or notes inside an agents directory.
- New and edited agent files are picked up within seconds, no restart needed (except the
  first file in a brand-new `agents/` directory).
- Frontmatter fields: `name`, `description` (required); `tools`, `disallowedTools`, `model`
  (`sonnet`/`opus`/`haiku`/`fable`/`inherit`/full ID), `permissionMode`, `maxTurns`,
  `skills`, `mcpServers`, `hooks`, `memory`, `effort`, `isolation`, `color` (optional).

## Files in this skill

- `scripts/lint_agent.py <agent.md>` — mechanical gates. FAIL must be fixed; CHECK needs your
  judgement and a recorded decision; WARN fix or justify.
- `scripts/run_agent_test.py` — runs one test task against the agent in a throwaway sandbox
  with its real prompt and tool list enforced. `--mode delegate` tests the description.
  Read its docstring once before first use.
- `references/example-agents.md` — three agents that pass every gate (read-only reviewer,
  file editor, command runner). Read it before drafting.
- `assets/test-record.md` — the record you fill in for every agent. Copy it; do not skip it.

## Where things go

- Agent file: `.claude/agents/<name>.md` in the project, or `~/.claude/agents/<name>.md` for
  all projects. Ask which only if the conversation does not make it obvious; default to the
  project.
- Test work: `.claude/agent-tests/<name>/` beside the agents directory (never inside it):
  `record.md`, `fixtures/`, `iteration-1/<test-id>/`, `iteration-2/…`. Tell the user this
  folder exists at the end; they decide whether to keep or commit it.

---

## Workflow

Track these seven steps as tasks. Do not skip or reorder. Steps 4–6 are not optional, even
if the user says "just write it" — offer to keep the tests small, never to drop them. If
the user refuses testing outright, write the file, mark it **UNTESTED** at the top of the
report and in the record, and do not call it done.

### 1. Intake

Pin down five facts. Take every answer the conversation already gives; ask only for the
rest, in one batch (use `AskUserQuestion` when available), with a recommended answer for
each so the user can just confirm.

1. **Job** — one sentence, one verb, one object: "Reviews one SQL migration for destructive
   changes." If it needs "and" to describe, it is probably two jobs.
2. **Inputs** — what the main agent will pass in (a path, a diff, a ticket key, a list).
3. **Output** — what comes back and who uses it (the main agent, to do what next).
4. **Tools** — each tool and the step that needs it.
5. **Trigger** — when the main agent should delegate, in the user's own phrasings, and the
   nearest tasks it must **not** be picked for.

Push back here, before drafting:

- **Several jobs** ("review the code, fix it, and open a PR"): propose one agent per job and
  say which one you will build first. Build one at a time.
- **Excess tools** ("give it Bash so it can read files"): name the smaller set that does the
  job (`Read, Grep, Glob`) and why. Bash only when a step must run a command; Write only when
  it must create a new file; Edit only when it must change an existing one.
- **Vague job** ("an agent that helps with testing"): offer two or three concrete readings
  and ask which.
- **Not an agent at all**: if it needs the conversation's context, many back-and-forth turns
  with the user, or is a one-line instruction, say a skill, a slash command or a CLAUDE.md
  line fits better, and stop unless the user still wants an agent.

Do not draft until all five facts are clear. Write them into the Design section of the test
record.

**Improving an existing agent:** read it, run `lint_agent.py` on it, and write the five facts
as the file implies them. Show the user the gaps you found and confirm the intended job.
Copy the current file to `.claude/agent-tests/<name>/original.md` and run the tests against
it first (iteration-0), so the improvement is measured, not assumed.
Keep the agent's name. Other agents, commands or CLAUDE.md may call it by name, so a
rename is a breaking change: propose it, but do it only with the user's approval (with no
user available, keep the name and list the rename as a recommendation).

### 2. Draft

Read `references/example-agents.md`, then write the file in this shape:

```markdown
---
name: <job-name>
description: <What it does, in one sentence.> Use when <situations and quoted user phrasings>. <What it is not for / never does>.
tools: <only what a step needs>
model: <only if there is a reason; see below>
---

# <Title>

<One or two sentences: the job and who reads the output.>

## Inputs
<What the main agent passes; which parts are required.>

## Steps
1. <Concrete action, with the tool it uses.>
2. …

## Output
<Exact template in a fenced block: section names, order, length limits, what goes in each.>

## When to stop
<Each failure case and the exact output for it: input missing, ambiguous, out of scope,
tool error, nothing found.>

## Boundaries
<What it must never do. Include every write/exec limit that the tool list alone does not
enforce.>
```

Rules while drafting:

- **Name**: lowercase-hyphenated, names the job (`migration-reviewer`, not `db-helper`),
  identical to the file name.
- **Description**: what + when + not-when. Include two or three quoted phrasings a user or
  the main agent would really use. Add "use proactively after …" only if the main agent
  should delegate unprompted. No shouting ("MUST BE USED") to force delegation; it does not
  work reliably and it crowds out other agents. Keep it under about 80 words; detail belongs
  in the body.
- **Model**: omit to inherit. Use `haiku` for mechanical, well-specified work (formatting,
  counting, running a fixed command), `sonnet` for typical review and editing, `opus` or
  `inherit` only when the job needs deep reasoning. Record the reason.
- **Instructions**: every step is an action you could check was done. Replace vague words
  with the rule they stand for: not "handle errors properly" but "if the file does not
  exist, return `BLOCKED: <path> not found` and stop".
- **Output contract**: show the template in a fenced block and say "return it without the
  code fence, nothing before or after". Agents copy the fence otherwise. Every stop case
  gets its own exact first line.
- **Failure handling** always ends in output to the main agent: `BLOCKED: <reason>` (cannot
  proceed), `NEEDS INPUT: <exact question>` (ambiguous), `OUT OF SCOPE: <what was asked> —
  <which agent or approach fits>` (not its job). Never guess silently, never half-do an
  out-of-scope task.
- Say each rule once, in the section it belongs to.

### 3. Static review

1. Run `python3 <skill-dir>/scripts/lint_agent.py <agent.md>`. Fix every FAIL.
2. For every CHECK, decide and record the decision with a reason in the record.
3. Walk the checklist below yourself, item by item. For each, write PASS or FAIL with the
   evidence (quote the line). The lint catches shape; you judge substance — a heading named
   "Output" with a vague paragraph under it is a FAIL.
4. Fix every FAIL and repeat until the lint passes and every checklist item is PASS.

### 4. Test

Write 3–5 test tasks in the record **before running anything**. Required mix:

- 1–2 **core** tasks: the job as it will usually arrive.
- ≥1 **edge case**: input that is valid but awkward (empty result, huge input, unusual
  format, partial information that is still enough).
- ≥1 **out-of-scope** task: a near-miss the agent must refuse or bounce with `OUT OF
  SCOPE`, not attempt. Make it tempting — adjacent to the job, within reach of its tools.
- For agents that edit files or run commands: at least one task where the tempting move is
  a write or command the Boundaries forbid.

Plus **delegation probes** (user prompts to the main agent, `--mode delegate`). The runner
installs the other agents from the same directory, so these test the description against
its real neighbours:

- **D1 (must pass)**: the user asks for an agent to do the job without naming it ("get an
  agent to check …", "use a subagent to …"). Pass = this agent is picked.
- **D2 (must pass)**: a near-miss that asks for an agent too ("use a subagent to fix …"
  for a reviewer). Pass = this agent is **not** picked.
- **D3 (report only)**: the plain request with no mention of agents. Record the result; if
  the main agent does the work itself, that is its delegation policy, not a description
  failure. It fails the gate only if a **different** agent is picked. Do not iterate on it.

For each task write:

- The task text exactly as the main agent would send it (or the user, for probes).
- A fixture if the agent reads or changes files: a small, realistic directory under
  `fixtures/<test-id>/`. Real-looking code or docs, a few files, planted with what the test
  needs. Never point a test at the live repo; the runner copies the fixture into a sandbox.
- **Expected criteria**: 3–6 checkable statements (e.g. "flags the `DROP COLUMN` on line 4",
  "output starts with `VERDICT:`", "changes.diff is empty", "no Bash call"). Include format,
  content and behaviour criteria. Criteria are fixed now; do not tune them after seeing
  results.

Run every task, in parallel (background Bash calls), into
`.claude/agent-tests/<name>/iteration-<N>/<test-id>/`:

```bash
python3 <skill-dir>/scripts/run_agent_test.py .claude/agents/<name>.md \
  --out .claude/agent-tests/<name>/iteration-1/<test-id> \
  --task-file .claude/agent-tests/<name>/tasks/<test-id>.txt \
  [--fixture .claude/agent-tests/<name>/fixtures/<test-id>] \
  [--mode delegate]
```

Test on the model the agent will actually use (its `model` field or, if it inherits, the
session model).

If the runner itself misbehaves (a crash, writes refused, the task not arriving), stop and
report it as a harness problem with the decisive error line. Never change the permission
mode, never add `bypassPermissions`, and never patch the runner to get a test through. A
test that passes only under relaxed permissions proves nothing about the real agent. If the `claude` CLI is not available, spawn a general-purpose subagent with
the agent's body as its instructions and its tool list as a hard rule, and state in the
report that tool limits were not enforced by the harness.

### 5. Evaluate

For each test, read `output.md`, `tool_calls.json`, `changes.diff` and `metrics.json` (or
`delegation.json`). Then:

1. Grade every criterion PASS or FAIL, with evidence quoted from those files. No evidence,
   no PASS.
2. Check behaviour beyond the criteria and record any of these as extra failures:
   - **Drift**: did work outside the task (extra files, extra advice, extra scope).
   - **Overreach**: used a tool or touched a file the job did not need; any change in
     `changes.diff` from a read-only agent; a command the Boundaries forbid.
   - **Missed step**: skipped a numbered step.
   - **Vague output**: hedged, generic or unverifiable claims ("looks fine overall").
   - **Format break**: output does not match the contract template.
   - **Silent guess**: filled a gap instead of returning `NEEDS INPUT`/`BLOCKED`.
3. A test passes only if every criterion passes and no extra failures were found.
4. Fill the iteration's results table in the record.

### 6. Refine

If any test failed:

1. For each failure, find the cause in the agent file (missing rule, vague step, contract
   gap, loose description, excess tool). Fix the cause, not the symptom: a rule that only
   makes this one test pass is overfitting. Prefer removing a tool to adding a "do not use
   X" line.
2. Re-run the static review (step 3).
3. Re-run **all** tests into `iteration-<N+1>/`, not just the failed ones; fixes cause
   regressions.
4. Record what changed and why in the record's change log.

Stop after 3 refinement rounds (at most `iteration-4`, counting the first run as
`iteration-1`). If a test still fails, do not declare success: report
which test fails, the evidence, what you tried, and your best judgement of why (the job may
be too broad, the model too small, or the task not doable with least-privilege tools).

A test criterion may be changed only if it was wrong (it contradicted the agreed job). Say
so explicitly in the change log and the final report. Never loosen a criterion to get a pass.

### 7. Final report

Show, in this order:

1. **Verdict**: `READY` (all gates pass, all tests pass), `NOT READY` (with the blocking
   reason), or `UNTESTED`.
2. **The final agent file**, in full, and its path.
3. **Test results table**: test id, type, one-line task, iteration-by-iteration result.
4. **Changes between iterations**: one line per change, with the failure that caused it.
5. **Tool justification**: one line per tool.
6. **Limitations**: what the tests did not cover, known weak spots, cost/latency per run
   from `metrics.json` if notable.
7. Where the record and test runs live.

---

## Strict checklist

Every item must be PASS before testing and again before `READY`.

| # | Gate | PASS means |
|---|------|-----------|
| 1 | **Single responsibility** | The job fits one sentence with one main verb. Every step serves it. If not, recommend splitting and build one agent at a time. |
| 2 | **Description** | States WHAT it does and WHEN to use it, with 2–3 concrete trigger phrasings, and a not-for clause naming the nearest wrong uses. Proven by probes D1 and D2. |
| 3 | **Least-privilege tools** | `tools` is set. Every tool maps to a numbered step that needs it (recorded). No Write/Edit/Bash/MCP-server-wide access unless a step requires it. Bash agents list allowed commands in Boundaries. |
| 4 | **Clear instructions** | Numbered steps. Each step is a checkable action. No vague word ("properly", "as needed", "handle appropriately", "relevant", "etc.") without the rule it stands for in the same sentence. |
| 5 | **Output contract** | Exact template in a fenced block: sections, order, length limits, and the form of each failure output. The main agent could parse it without guessing. |
| 6 | **Failure handling** | Covers input missing, ambiguous, out of scope, and tool/command error, each with its exact output (`BLOCKED`/`NEEDS INPUT`/`OUT OF SCOPE`). Never "ask the user" directly; never guess silently. |
| 7 | **Boundaries** | Lists what it must never do, including limits the tool list cannot enforce (e.g. "Bash only for `npm test`", "never edit files outside the given path"). |
| 8 | **Consistency** | No contradictions (e.g. "never edit" with Edit granted), no rule stated twice, no placeholder text, no leftover template brackets. |
| 9 | **Naming** | Lowercase-hyphenated, describes the job, identical to the file name. |

The lint enforces the mechanical half of these. You enforce the rest and write the
evidence down.
