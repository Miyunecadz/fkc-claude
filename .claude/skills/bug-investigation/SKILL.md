---
name: bug-investigation
description: Use when diagnosing a bug, regression, or unexpected behaviour in any repo in this workspace — before any fix is written. Diagnosis only; produces a root-cause report, not a patch.
---

# Bug investigation (diagnosis only)

**This phase produces a diagnosis, not a patch.** Do not edit code or propose a fix until the user asks for one. Stop at the report in §5.

## 1. Establish facts before theory

- Restate the symptom, quoting exact error text, stack trace, log line, or reproduction steps as given.
- Separate what is **known** (given, or read from the repo) from what is **assumed**. Assumptions get verified or labelled as open questions — never silently promoted to facts.
- No root cause before the code path has actually been traced.

## 2. Locate the code path

Start from the architecture graph, then confirm in source.

Each repo has `docs/<repo>/architecture/graph.json` — a node-link JSON snapshot produced by Graphify (`docs/fk-admin-panel-be/`, `docs/fk-admin-panel-fe/`, `docs/fk-mobile/`). Nodes carry `id`, `label`, `source_file`, `source_location`; links carry `relation`, `source`, `target`, `source_file`, `source_location`. Relations present in these graphs: `contains`, `imports`, `imports_from`, `calls`, `indirect_call`, `references`, `defines`.

Find a symbol and its callers:

```bash
python3 - <<'EOF'
import json
REPO, TERM = 'fk-admin-panel-be', 'login'   # edit both
g = json.load(open(f'docs/{REPO}/architecture/graph.json'))
hits = [n for n in g['nodes'] if TERM.lower() in n['label'].lower()]
for n in hits[:10]:
    print(n['id'], '|', n['label'], '|', n.get('source_file'), n.get('source_location'))
ids = {n['id'] for n in hits}
print('--- callers ---')
for l in g['links']:
    if l['target'] in ids and l['relation'] in ('calls', 'indirect_call', 'imports_from'):
        print(l['relation'], l['source'], '->', l['target'], '@', l.get('source_file'), l.get('source_location'))
EOF
```

Then:

- **Confirm every graph hit by reading the file at that line.** The graph is a manual snapshot — no hook rebuilds it on commit, so it can lag the working tree. If it clearly disagrees with source, trust source and mention the drift (`/lodestar-refresh <repo>` rebuilds it).
- Trace **backward** from where the error surfaces to where the bad state originates. They are usually different files.
- Check the **call sites**, not only the callee — wrong argument, wrong order, or wrong sequencing is a common cause.
- Read current code. Never rely on remembered framework behaviour. All three repos use **Yarn** (`yarn.lock` in each); for the version actually installed, read `<repo>/node_modules/<pkg>/package.json` or `yarn.lock`, not the range in `package.json`.

## 3. Surrounding context

- **Git:** the workspace root is *not* a git repo — each of `fk-admin-panel-be`, `fk-admin-panel-fe`, `fk-mobile` is its own. Run `git -C <repo> log`/`blame` on the suspect file; many bugs are regressions.
- **Tests are not a safety net here.** `fk-admin-panel-be` has no tests at all (`yarn test` is `echo "Error: no test specified" && exit 1`). `fk-admin-panel-fe` has one unit test (`src/utils/routeMatching.test.js`) plus Playwright specs (`browser.test.ts`, `yarn test:chrome|firefox|safari`). `fk-mobile` has `__tests__/App-test.js` and nothing under `src`. So: absence of a failing test is **no evidence**, and "a test would have caught this" is not a finding. Reproduce by running the app or querying the API/DB instead.
- **Environment:** real `.env` files are blocked from reading by the `block-env-files` guardrail. Use `.env.example` (all three repos; mobile's real tier file is `.env.development`) and `docs/_shared/env-matrix.md` for the expected variable shape. `docs/_shared/local-setup.md` and the root `docker-compose.yml` / `docker-compose.deps.yml` cover bringing dependencies up.
- **Data / schema (backend):** migrations are dbmate SQL under `fk-admin-panel-be/db/migrations`; `db/schema.sql` is the generated snapshot (hand-edits blocked by `protect-dbmate-schema`). Read them to check whether the bug is data- or migration-shaped. `yarn db:status` shows what has been applied.
- If several modules touch the logic, check all of them — do not stop at the first plausible culprit.

## 4. Cross-repo symptoms

A symptom in `fk-admin-panel-fe` or `fk-mobile` frequently roots in `fk-admin-panel-be`. The graphs cannot show this: repos talk over the API at runtime and Graphify only records static edges, so **no graph contains a cross-repo edge**. The boundary is documented in `docs/_shared/api-contract.md`; check the GraphQL operation there and follow it into the backend resolver. Auth-shaped symptoms: `docs/_shared/auth-model.md`.

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
