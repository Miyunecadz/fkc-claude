#!/usr/bin/env node
/* Screenshot a running GraphQL endpoint for a pull request.
 *
 * Shows the query and its real response, side by side, from the GraphQL Playground the
 * backend already serves. The point is evidence a reviewer can read without booting the
 * stack themselves — so it shoots the running app, never a mock.
 *
 * Usage:
 *   node .claude/hooks/pr-endpoint-shot.js \
 *     --endpoint http://localhost:4100/graphql \
 *     --spec .work/<KEY>/shots/spec.json \
 *     --out  .work/<KEY>/shots \
 *     [--token-file <file holding a bearer token>]
 *
 * The spec is a JSON array: [{ "name": "endpoint-getThing", "query": "query Thing {...}" }]
 *
 * The bearer token is sent as a context-level HTTP header, so it never appears in the
 * image. Never type a token into the Playground's own headers pane: that pane is on
 * screen, and the screenshot goes on a pull request.
 *
 * Browsers come from the Playwright cache the frontend repo already installed. On WSL the
 * bundled chromium needs libasound: `sudo apt install libasound2t64` once, or point
 * LD_LIBRARY_PATH at a directory holding libasound.so.2.
 *
 * Exits non-zero if any endpoint answered with `errors` — a screenshot of a failure is
 * not evidence, and it must not reach a pull request unnoticed.
 */
const fs = require('fs');
const path = require('path');

const arg = (name, fallback) => {
  const i = process.argv.indexOf('--' + name);
  return i === -1 ? fallback : process.argv[i + 1];
};

const endpoint = arg('endpoint');
const specPath = arg('spec');
const outDir = arg('out');
const tokenFile = arg('token-file');
const width = parseInt(arg('width', '1600'), 10);
const height = parseInt(arg('height', '900'), 10);

if (!endpoint || !specPath || !outDir) {
  console.error('need --endpoint, --spec and --out; see the header of this file');
  process.exit(2);
}

const { chromium } = require('playwright-core');
const shots = JSON.parse(fs.readFileSync(specPath, 'utf8'));
const token = tokenFile ? fs.readFileSync(tokenFile, 'utf8').trim() : null;

fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 2,
    extraHTTPHeaders: token ? { Authorization: 'Bearer ' + token } : {},
  });

  let failed = 0;
  for (const shot of shots) {
    const page = await context.newPage();
    await page.goto(endpoint + '?query=' + encodeURIComponent(shot.query), { waitUntil: 'load' });
    await page.waitForTimeout(6000);                   // the Playground bundle is large

    // Focus the query editor, then run it with the Playground's own shortcut. Clicking
    // the play button by position breaks whenever the pane widths change.
    const anchor = shot.anchor || (shot.query.match(/[A-Za-z_][A-Za-z0-9_]*(?=\s*[({])/) || [])[0];
    if (anchor) await page.click('text=' + anchor, { force: true }).catch(() => {});
    await page.keyboard.press('Control+Enter');
    await page.waitForTimeout(4500);

    const text = await page.innerText('body');
    const ok = text.includes('"data"') && !text.includes('"errors"');
    if (token && text.includes(token.slice(0, 20))) {
      console.error(shot.name, '- ABORT: the token is visible on screen');
      process.exit(1);
    }
    if (!ok) failed += 1;

    const file = path.join(outDir, shot.name + '.png');
    await page.screenshot({ path: file });
    console.log([shot.name, ok ? 'ok' : 'RESPONDED WITH ERRORS', file].join(' | '));
    await page.close();
  }

  await browser.close();
  process.exit(failed ? 1 : 0);
})().catch((e) => {
  console.error('FAIL', e.message.split('\n')[0]);
  process.exit(1);
});
