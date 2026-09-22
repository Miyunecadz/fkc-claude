# fk-connect — Workspace Router

This folder is a **Lodestar workspace**: several independent repositories coordinated from one root. This file is a *router*, not a knowledge base — it stays intentionally small. Real knowledge lives in skills and docs that load on demand.

## Repositories

<!-- One line per repo. Filled in by /lodestar-init and /lodestar-onboard. -->

- **fk-admin-panel-be** — GraphQL API, DB & auth owner (Node/Express/Apollo Server, MariaDB via dbmate, Redis/Bull). See docs/fk-admin-panel-be/.
- **fk-admin-panel-fe** — Admin web client (React + craco, Apollo Client, Tailwind). See docs/fk-admin-panel-fe/.
- **fk-mobile** — Mobile app (React Native, Apollo Client, Firebase messaging). See docs/fk-mobile/.

_All three repos are onboarded — each has `docs/<repo>/conventions.md` and a queryable `docs/<repo>/architecture/graph.json`._

Full map and cross-repo relationships: **[docs/repo-map.md](docs/repo-map.md)**

## Loading policy (do not remove — this keeps the router thin)

- **Do not read docs eagerly.** Skills declare *when* they apply via their `description`. Trust those triggers; load a skill only when the current task matches.
- **Stay in the relevant repo.** For a task in one repo, do not load another repo's docs or skills.
- **Match the layer to the task.** Planning a feature → the planning skill (not coding standards). Writing code → the relevant stack skill (not the planning playbook).
- **Cross-repo truth lives in `docs/_shared/`.** The API contract there is the spine that links the repos; consult it for anything spanning repo boundaries.
- **Architecture graphs are queryable — reach for them before re-reading source.** Always
  through the resolver, never by passing `--graph` yourself:

  ```bash
  .claude/hooks/graph.sh status                       # every map here, and whether it is current
  .claude/hooks/graph.sh query <path> "<question>"    # <path> = any repo, worktree, or file in one
  ```

  This workspace holds one map per repo **plus one per ticket worktree** under `.work/`, and
  they describe different commits. `graph.sh` picks the map that describes the path you name,
  rebuilds it first if the code moved under it (uncommitted edits included, ~3s), and prints
  which map answered. Choosing by hand is how an answer arrives about a branch you are not on.

## Writing style (enforced)

Everything a human reads — chat replies, Jira tickets, PR titles and descriptions,
commit messages, code comments, docs — is **British English, plain words, short
sentences, answer first**. Code identifiers, API fields, DB columns and quoted error
text keep their original spelling.

Rules: **[.claude/skills/plain-uk-english/SKILL.md](.claude/skills/plain-uk-english/SKILL.md)**.
Two hooks hold the line: the rule is injected on every prompt, and prose written to
`.md`/`.txt` is scanned for American spelling and banned jargon.

## Enforcement

Guardrails (if enabled via `/lodestar-guardrails`) are **enforced**, not advisory — e.g. applied database migrations cannot be edited; secrets cannot be read. Follow the redirect a blocked action gives you.

## Onboarding a new repo

Run `/lodestar-onboard ./<new-repo>`. It detects the stack, generates the architecture graph, files docs, and installs matching skills. This router does not need editing — the repo registry above is updated for you.
