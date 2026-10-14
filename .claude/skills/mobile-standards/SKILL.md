---
name: mobile-standards
description: Use when editing fk-mobile — React Native screens, navigation, NativeWind styling, Apollo queries, env config or Firebase push. Load before writing mobile code.
stacks: [react-native]
---

# Mobile standards (fk-mobile)

**Read `docs/fk-mobile/conventions.md` first.** It holds the rules the code cannot show. It was
written from the code on a date and may lag: when it and the code disagree, the code wins,
and you fix the doc in the same change.

**Find the pattern first.** Locate the nearest similar file and copy its shape:
`.claude/hooks/graph.sh query fk-mobile "<feature>"`. For an overview, read
`fk-mobile/graphify-out/GRAPH_REPORT.md`.

**Verified facts:**

- **Layout:** screens in `src/screens/` (`authenticated/` for signed-in), registered
  in `src/configs/screens.jsx`; navigator in `src/Root.jsx` (React Navigation).
  Components are `src/components/atoms|molecules|organisms`.
- **Data:** Apollo client in `src/configs/apollo.js`. Operations are `gql` constants
  in `src/graphql/<area>.js`.
- **Styling:** NativeWind (`nativewind/babel` in `babel.config.js`, `tailwind.config.js`).
- **Env:** `react-native-config` (`Config.API_URL`). Tier chosen by `ENVFILE` in the
  `package.json` scripts. Never hard-code per-environment values.
- **Native patches:** `patches/` via patch-package (`postinstall`). Never hand-edit
  `node_modules`.
- **Push:** Firebase messaging, see `src/utils/notification.js`.
- **Checks:** `yarn lint` (`.eslintrc.js`), `yarn test` (jest; only `__tests__/App-test.js`).

**Readability and house style**

- Match the nearest similar file: its naming, casing, import style, file shape and
  comment density. Copy the pattern; do not invent one.
- Full words for names — `index`, `response`, `connection` — unless the surrounding file
  already uses the short form. The file's own idiom wins.
- A comment says *why*, and only where the nearby code already comments. Never a comment
  that restates what the line does. No commented-out code, no `TODO`/`FIXME`, no
  `console.log` left behind.
- Nothing the task did not need: no scaffolding, no example code, no narration of the work.
- Re-read the diff as a stranger. Delete any line that only explains the code, or shortens
  a name the file spells out.
