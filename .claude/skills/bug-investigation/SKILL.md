---
name: bug-investigation
description: Use when diagnosing a bug, regression, or unexpected behaviour in any repo in this workspace — before any fix is written. Diagnosis only; produces a root-cause report, not a patch.
---

# Bug investigation (diagnosis only)

**This phase produces a diagnosis, not a patch.** Do not edit code or propose a fix until the user asks for one. Stop at the report in §6.

## 1. Establish facts before theory

- Restate the symptom, quoting exact error text, stack trace, log line, or reproduction steps as given.
- Separate what is **known** (given, or read from the repo) from what is **assumed**. Assumptions get verified or labelled as open questions — never silently promoted to facts.
- No root cause before the code path has actually been traced.

## 2. Locate the code path

Start from the architecture map, then confirm in source. Always go through the resolver, which picks the map for the tree you name and rebuilds it if the code moved:

```bash
.claude/hooks/graph.sh query    <repo-worktree-or-file> "<symptom words>"
.claude/hooks/graph.sh affected <path> "<symbol>"   # callers and dependants
.claude/hooks/graph.sh explain  <path> "<symbol>"
```

Then:

- **Confirm every map hit by reading the file at that line.** The map locates; source decides. If they disagree, trust source.
- Trace **backward** from where the error surfaces to where the bad state originates. They are usually different files.
- Check the **call sites**, not only the callee — wrong argument, wrong order, or wrong sequencing is a common cause.
- Read current code. Never rely on remembered framework behaviour. All three repos use **Yarn** (`yarn.lock` in each); for the version actually installed, read `<repo>/node_modules/<pkg>/package.json` or `yarn.lock`, not the range in `package.json`.

## 3. Surrounding context

- **Git:** the root is its own git repo and ignores the three repos, so each of `fk-admin-panel-be`, `fk-admin-panel-fe`, `fk-mobile` needs `git -C <repo>`. Run `git -C <repo> log`/`blame` on the suspect file; many bugs are regressions.
- **Tests are not a safety net here.** `fk-admin-panel-be` has no tests at all (`yarn test` is `echo "Error: no test specified" && exit 1`). `fk-admin-panel-fe` has one unit test (`src/utils/routeMatching.test.js`) plus Playwright specs (`browser.test.ts`, `yarn test:chrome|firefox|safari`). `fk-mobile` has `__tests__/App-test.js` and nothing under `src`. So: absence of a failing test is **no evidence**, and "a test would have caught this" is not a finding. Reproduce by running the app or querying the API/DB instead.
- **Environment:** real `.env` files are blocked from reading by the `block-env-files` guardrail. Use `.env.example` in each repo for the expected variable shape. The root `docker-compose.yml` and `docker-compose.deps.yml` bring dependencies up.
- **Data / schema (backend):** migrations are dbmate SQL under `fk-admin-panel-be/db/migrations`; `db/schema.sql` is the generated snapshot (hand-edits blocked by `protect-dbmate-schema`). Read them to check whether the bug is data- or migration-shaped. `yarn db:status` shows what has been applied.
- If several modules touch the logic, check all of them — do not stop at the first plausible culprit.

## 4. Cross-repo symptoms

A symptom in `fk-admin-panel-fe` or `fk-mobile` frequently roots in `fk-admin-panel-be`. The graphs cannot show this: repos talk over the API at runtime and Graphify only records static edges, so **no graph contains a cross-repo edge**. Trace it by hand: the client `gql` constant (`fk-admin-panel-fe/src/graphql/` or `fk-mobile/src/graphql/`) → `fk-admin-panel-be/src/typedefs/` → the permission rule in `src/configs/shield.js` → the resolver in `src/resolvers/`. Auth-shaped symptoms start at `shield.js`, `src/utils/permissions/` and `src/utils/auth.js`.

For orientation: `docs/_shared/api-contract.md`, `auth-model.md`, `env-matrix.md` and `local-setup.md`, and `docs/<repo>/conventions.md`. They can lag the code; quote the code, not the doc.

## 5. Multiple hypotheses before converging

- List 2–3 plausible root causes, each grounded in code actually read.
- For each, state the evidence that would confirm or kill it, then go check it.
- Rule hypotheses out explicitly. Do not drop them silently.
- Converge only on a cause verified against real code behaviour, not plausibility.

## 6. Report

- **Symptom** — what is observed.
- **Root cause** — the responsible code, with `path:line` references.
- **Evidence** — quoted code, not a paraphrase of what it presumably does.
- **Confidence** — certain / likely / needs more info; if not certain, name the information or reproduction that would raise it.
- **Ruled out** — what else was considered, and why it was not it.

## Hard rules

- Never state a root cause not verified by reading the code.
- Never jump to the fix; diagnosis and fix are separate turns.
- If the repo does not answer the question, say so — do not fill the gap with a guess.
- If the investigation contradicts a claim in the bug report, flag the contradiction rather than working around it.
