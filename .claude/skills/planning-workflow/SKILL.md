---
name: planning-workflow
description: Use when scoping or breaking down a feature in this workspace BEFORE any code is written. For an FKC Jira ticket, use /implement-ticket instead. Produces a plan, never code.
stacks: [all]
---

# Planning workflow

**FKC ticket?** Use `/implement-ticket` (the `ticket-delivery` skill). It owns
analysis, planning and gates. Stop here.

**Otherwise,** plan without writing code:

1. **Which repos?** If data crosses the API, the GraphQL change comes first and drives
   the rest. Load `graphql-contract`.
2. **Which files?** List each file to touch or add, per repo. Every path must be
   confirmed with `.claude/hooks/graph.sh query <repo> "<feature>"` or `grep`.
   Mark new files as new.
3. **Which pattern?** Name one existing file per repo to copy.
4. **Steps.** Small, ordered by dependency (migration → typedef/resolver/permission →
   clients), each with a clear done-condition.
5. **Open questions.** Anything the code or the request does not settle. Do not guess.

Do not load the repo standards skills while planning. They are for writing code.
