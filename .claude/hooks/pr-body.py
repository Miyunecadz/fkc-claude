#!/usr/bin/env python3
"""PR body formatter, validator and PreToolUse guard. No LLM anywhere in here.

The split this file exists to enforce:

    Claude   understands the ticket and the diff, and writes four pieces of meaning
             (Ticket / What / Why / Check) once, in whatever shape it likes.
    this     turns that into the one body shape this workspace posts, strips the
             attribution footer, and refuses anything that is not that shape.

So a badly shaped body costs a hook message, never a rewrite round-trip.

Usage:
    pr-body.py format [-f FILE]   semantic content in  -> final body on stdout
    pr-body.py check  [-f FILE]   final body in        -> exit 0 / 1 + report on stderr
    pr-body.py hook               PreToolUse JSON on stdin (bitbucket bb_post / bb_put)

Exit: 0 ok | 1 the body is not valid (report on stderr) | 2 bad usage

The shape, and there is no other:

    Ticket: <key or url>

    What
    <one short paragraph>

    Why
    <one short paragraph>

    Check:
    1. <verification step>
    2. <verification step>
"""
import json
import re
import sys

# --- the contract ---------------------------------------------------------------------
CANON = ("ticket", "what", "why", "check")
ALIASES = {
    "ticket": "ticket", "jira": "ticket", "issue": "ticket",
    "what": "what", "what changed": "what",
    "why": "why", "why now": "why",
    "check": "check", "checks": "check", "verification": "check",
    "verify": "check", "how to verify": "check",
}
MAX_WORDS_HARD = 250       # over this the PR is too big, or the body is padded
MAX_CHECKS = 12
WARN_WORDS = 120           # DESCRIPTION.md's budget — a warning, never a block
WARN_LINES = 20
HARD_BREAK = "  "        # trailing spaces = a Markdown line break, not stray whitespace

# Boilerplate headings this workspace never posts. Dropped by `format`, with their
# content, and reported on stderr. Rejected by `check`.
BANNED_NAMES = (
    "summary", "overview", "background", "context", "description",
    "changes", "changes made", "change summary", "file changes", "files changed",
    "testing", "testing strategy", "test plan", "tests", "how to test", "qa",
    "note", "notes", "implementation details", "implementation notes",
    "technical details", "risk", "risks", "future work", "follow-up", "follow up",
    "checklist", "acceptance criteria", "motivation",
)

_NAME = "|".join(sorted((re.escape(n) for n in list(ALIASES) + list(BANNED_NAMES)), key=len, reverse=True))
SECTION = re.compile(
    r"^[ \t]{0,3}(?:#{1,6}[ \t]*)?(?:\*\*|__)?[ \t]*"
    r"(?P<name>" + _NAME + r")"
    r"[ \t]*(?P<sep1>[:\-–—])?[ \t]*(?:\*\*|__)?[ \t]*(?P<sep2>[:\-–—])?[ \t]*"
    r"(?P<rest>.*?)[ \t]*$",
    re.IGNORECASE,
)
# any other heading-shaped line: `## Foo`, `**Foo**`, `**Foo:**`
OTHER_HEADING = re.compile(
    r"^[ \t]{0,3}(?:#{1,6}[ \t]+\S|(?:\*\*|__)[^*_\n]{1,60}(?:\*\*|__)[ \t]*:?[ \t]*$)"
)
# `1\.` is how Bitbucket's editor escapes a numbered line — treat it as a number
ITEM = re.compile(r"^[ \t]*(?:\(?\d+\\?[.)\]]|[-*•+])[ \t]+(?P<text>.*)$")
RULE = re.compile(r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$")
KEY_ONLY = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
URL_ONLY = re.compile(r"^https?://\S+$")
MD_LINK = re.compile(r"^\[(?P<text>[^\]]*)\]\((?P<url>[^)\s]+)\)\s*(?:\{[^}]*\})?\s*$")
# Bitbucket's own editor writes this; it is what makes a link render as a smart card
INLINE_CARD = "{: data-inline-card='' }"

ATTRIBUTION = re.compile(
    r"(generated\s+(?:with|by)\s+\[?claude"
    r"|created\s+(?:with|by)\s+\[?claude"
    r"|via\s+\[?claude\s+code"
    r"|co-authored-by\s*:\s*claude"
    r"|claude-session\s*:"
    r"|\U0001f916)",
    re.IGNORECASE,
)
CLAUDE_URL_LINE = re.compile(
    r"^[\s>*_\-\[\]()]*<?https?://(?:www\.)?claude\.(?:ai|com)/\S*>?[\s\])>*_]*$", re.IGNORECASE
)
ANY_ATTRIBUTION = re.compile(
    r"(claude\s+code|claude\.ai/code|co-authored-by\s*:\s*claude|claude-session\s*:|\U0001f916)",
    re.IGNORECASE,
)


class Invalid(Exception):
    """The content cannot be turned into the required body without inventing meaning."""

    def __init__(self, problems):
        self.problems = problems if isinstance(problems, list) else [problems]
        super().__init__("; ".join(self.problems))


def heading(line):
    """A section heading line -> (lowercased name, inline text). Otherwise None.

    A heading is the name, then either a separator (`:` `-` `--`) or nothing else on the
    line. `What the reviewer sees` is prose, not a What heading; `**What** - x` is one.
    """
    m = SECTION.match(line)
    if not m or ITEM.match(line):
        return None
    rest = m.group("rest").strip()
    if rest and not (m.group("sep1") or m.group("sep2")):
        return None
    return m.group("name").strip().lower(), rest


# --- attribution ----------------------------------------------------------------------
def strip_attribution(text):
    """Remove Claude Code attribution/footer lines. Returns (text, removed_lines)."""
    text = text.replace("\u200c", "").replace("\u200b", "").replace("\ufeff", "")
    kept, removed = [], []
    for line in text.splitlines():
        if ATTRIBUTION.search(line) or CLAUDE_URL_LINE.match(line):
            removed.append(line.strip())
            continue
        kept.append(line)
    # a horizontal rule that only existed to fence the footer
    while kept and (not kept[-1].strip() or RULE.match(kept[-1])):
        if RULE.match(kept[-1]):
            removed.append(kept[-1].strip())
        kept.pop()
    return "\n".join(kept), removed


# --- parsing --------------------------------------------------------------------------
def _canon(name):
    return ALIASES.get(name.strip().lower())


def parse(text):
    """Semantic content -> ({section: raw lines}, dropped, problems). Order-insensitive."""
    sections, dropped, problems = {}, [], []
    current, buf = None, []

    def flush():
        if current is not None:
            sections.setdefault(current, []).extend(buf)

    for line in text.splitlines():
        if not line.strip():
            buf.append("")
            continue
        head = heading(line)
        if head:
            name, rest = head
            canon = _canon(name)
            if canon is None:                       # a banned boilerplate section
                flush()
                current, buf = "_dropped", []
                dropped.append(name)
                continue
            if canon in sections:
                problems.append("duplicate %s section" % canon.capitalize())
            flush()
            current, buf = canon, ([rest] if rest else [])
            continue
        if OTHER_HEADING.match(line) and current != "check":
            flush()
            problems.append("unexpected section: %s" % line.strip().strip("#* _:"))
            current, buf = "_unknown", []
            continue
        if current is None:
            problems.append("text before the Ticket line: %r" % line.strip()[:60])
            continue
        buf.append(line)
    flush()
    sections.pop("_dropped", None)
    sections.pop("_unknown", None)
    return sections, dropped, problems


def paragraph(lines):
    """Wrapped lines -> one line per paragraph. Structure changes; wording does not."""
    out, cur = [], []
    for line in lines:
        if line.strip():
            cur.append(" ".join(line.split()))
        elif cur:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return "\n\n".join(out).strip()


def check_items(lines):
    """Lines -> ordered check items. Numbers, bullets and bare lines all accepted."""
    items = []
    for line in lines:
        if not line.strip():
            continue
        m = ITEM.match(line)
        if m:
            items.append(" ".join(m.group("text").split()))
        elif items and line.startswith((" ", "\t")):
            items[-1] += " " + " ".join(line.split())      # wrapped continuation
        else:
            items.append(" ".join(line.split()))
    return [i for i in items if i]


def ticket_value(raw, base_url=None):
    """The ticket line's value, in the form Bitbucket unfurls into a smart card.

    `[<url>](<url>){: data-inline-card='' }` is what Bitbucket's own editor writes, and the
    attribute is what turns the link into a card showing the Trello card's title and list.
    A bare URL renders as a plain blue link instead, so any http(s) ticket is normalised to
    that form — the visible title comes from the card itself, not from the link text.
    """
    value = " ".join(raw.split()).strip().strip("<>")
    if KEY_ONLY.match(value) and base_url:
        value = "%s/browse/%s" % (base_url.rstrip("/"), value)
    m = MD_LINK.match(value)
    if m:
        value = m.group("url").strip()
    if URL_ONLY.match(value):
        return "[%s](%s)%s" % (value, value, INLINE_CARD)
    return value


# --- format ---------------------------------------------------------------------------
def format_body(text, base_url=None):
    """Semantic content -> the final body. Raises Invalid; never invents meaning."""
    text, removed = strip_attribution(text.replace("\r\n", "\n"))
    sections, dropped, problems = parse(text)

    ticket = ticket_value(paragraph(sections.get("ticket", [])), base_url)
    what = paragraph(sections.get("what", []))
    why = paragraph(sections.get("why", []))
    checks = check_items(sections.get("check", []))

    if "ticket" not in sections:
        problems.append("missing Ticket line (use `Ticket: none` when there is no ticket)")
    elif not ticket:
        problems.append("Ticket line is empty")
    if "what" not in sections:
        problems.append("missing What section")
    elif not what:
        problems.append("What section is empty")
    if "why" not in sections:
        problems.append("missing Why section")
    elif not why:
        problems.append("Why section is empty")
    if "check" not in sections:
        problems.append("missing Check section")
    elif not checks:
        problems.append("Check section has no steps")
    elif len(checks) > MAX_CHECKS:
        problems.append("%d check steps — at most %d" % (len(checks), MAX_CHECKS))
    if problems:
        raise Invalid(problems)

    # Markdown, not plain text: Bitbucket renders this. A bare `What` with the text on the
    # next line is ONE paragraph ("What One system-wide..."), and a numbered list that is
    # not preceded by a blank line is swallowed into the paragraph above it. Hence the
    # two-space hard break after the bold labels, and the blank line before the list.
    body = (
        "Ticket: %s\n\n"
        "**What**%s\n%s\n\n"
        "**Why**%s\n%s\n\n"
        "**Check**\n\n%s\n"
    ) % (
        ticket, HARD_BREAK, what, HARD_BREAK, why,
        "\n".join("%d. %s" % (n, c) for n, c in enumerate(checks, 1)),
    )
    body = re.sub(r"\n{3,}", "\n\n", body)

    notes = ["dropped section: %s" % d for d in dropped]
    notes += ["removed attribution: %s" % r for r in removed if r]
    return body, notes


# --- check ----------------------------------------------------------------------------
def validate(body):
    """Final body -> list of problems. Empty list means it may be posted."""
    problems = []
    if not body or not body.strip():
        return ["the body is empty"]
    body = body.replace("\r\n", "\n")
    if ANY_ATTRIBUTION.search(body):
        problems.append("Claude Code attribution is present — it must not reach the PR")

    lines = body.rstrip().split("\n")
    order, seen = [], {}
    for i, line in enumerate(lines):
        head = heading(line)
        if head:
            name = head[0]
            canon = _canon(name)
            if canon is None:
                problems.append("unexpected section: %s" % name)
                continue
            if canon in seen:
                problems.append("duplicate %s section" % canon.capitalize())
                continue
            seen[canon] = i
            order.append(canon)
        elif OTHER_HEADING.match(line):
            problems.append("unexpected section: %s" % line.strip().strip("#* _:"))

    missing = [s for s in CANON if s not in seen]
    for s in missing:
        problems.append("missing %s section" % s.capitalize())
    if not missing and order != list(CANON):
        problems.append("sections out of order: %s — required Ticket, What, Why, Check"
                        % ", ".join(o.capitalize() for o in order))

    def content(name, stop):
        start = seen[name]
        end = min([seen[s] for s in stop if s in seen] or [len(lines)])
        head = heading(lines[start])
        first = head[1] if head else ""
        rest = [l for l in lines[start + 1:end] if l.strip()]
        return ([first] if first else []) + rest

    if "ticket" in seen:
        value = " ".join(content("ticket", ("what", "why", "check")))
        if not value:
            problems.append("Ticket line is empty")
        if lines[seen["ticket"]] != "Ticket: " + value:
            problems.append("the Ticket line must read `Ticket: <value>` on one line")
    if "what" in seen and not content("what", ("why", "check")):
        problems.append("What section is empty")
    if "why" in seen and not content("why", ("check",)):
        problems.append("Why section is empty")
    if "check" in seen:
        raw = content("check", ())
        numbered = [l for l in raw if re.match(r"^\d+\.[ \t]+\S", l)]
        if not numbered:
            problems.append("Check section has no numbered steps")
        elif len(numbered) != len(raw):
            problems.append("every Check step must be a numbered `N. ` line")
        elif [int(l.split(".", 1)[0]) for l in numbered] != list(range(1, len(numbered) + 1)):
            problems.append("Check steps must be numbered 1..n in order")
        elif len(numbered) > MAX_CHECKS:
            problems.append("%d check steps — at most %d" % (len(numbered), MAX_CHECKS))

    words = len(body.split())
    if words > MAX_WORDS_HARD:
        problems.append("%d words — over the %d limit; the PR is too big, or the body is padded"
                        % (words, MAX_WORDS_HARD))

    # The rendered Markdown has one right answer. Anything else — a missing hard break, a
    # list with no blank line above it, a heading that is not bold — renders as a wall of
    # paragraphs in Bitbucket, so it is a failure, not a nit.
    if not problems:
        try:
            canonical = format_body(body)[0]
        except Invalid:
            canonical = None
        if canonical is not None and body.rstrip("\n") + "\n" != canonical:
            problems.append("not the canonical Markdown shape (bold labels, `  ` hard break, "
                            "blank line before the numbered list) — run "
                            "`.claude/hooks/pr-body.py format`")
    return problems


def warnings(body):
    out = []
    words, lines = len(body.split()), len(body.strip().split("\n"))
    if words > WARN_WORDS:
        out.append("%d words (budget %d) — consider cutting" % (words, WARN_WORDS))
    if lines > WARN_LINES:
        out.append("%d lines (budget %d) — consider cutting" % (lines, WARN_LINES))
    return out


def report(problems, header="PR validation failed."):
    return "%s\n\nMissing or invalid:\n%s\n\nThe PR was not created." % (
        header, "\n".join("- %s" % p for p in problems))


# --- hook -----------------------------------------------------------------------------
PR_PATH = re.compile(r"^/(?:2\.0/)?repositories/[^/]+/[^/]+/pullrequests(?:/\d+)?/?$")


def hook():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if payload.get("tool_name") not in ("mcp__bitbucket__bb_post", "mcp__bitbucket__bb_put"):
        return
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("path")
    body = tool_input.get("body")
    if not isinstance(path, str) or not PR_PATH.match(path.split("?")[0]):
        return
    if not isinstance(body, dict):
        return
    # a PUT that touches neither description nor title is not a PR write we own
    if "description" not in body and "title" not in body:
        return

    desc = body.get("description")
    if not isinstance(desc, str) or not desc.strip():
        deny("PR validation failed.\n\nMissing or invalid:\n- the body is empty\n\n"
             "The PR was not created. Build the description with:\n"
             "  .claude/hooks/pr-body.py format")
        return

    problems = validate(desc)
    if not problems:
        return                                   # already the required shape — allow

    try:
        fixed, notes = format_body(desc)
    except Invalid as e:
        deny(report(e.problems) + "\n\nWrite the four pieces once and run:\n"
             "  .claude/hooks/pr-body.py format")
        return
    remaining = validate(fixed)
    if remaining:
        deny(report(remaining))
        return

    print(json.dumps({
        "systemMessage": "PR description normalised by pr-body.py"
                         + (" (%s)" % "; ".join(notes) if notes else ""),
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {**tool_input, "body": {**body, "description": fixed}},
        },
    }))


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }))


# --- cli ------------------------------------------------------------------------------
def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        sys.stderr.write(__doc__)
        return 2
    mode, args = argv[0], argv[1:]
    if mode == "hook":
        hook()
        return 0

    base_url = None
    src = None
    while args:
        a = args.pop(0)
        if a in ("-f", "--file"):
            src = args.pop(0) if args else None
        elif a in ("-b", "--ticket-base"):
            base_url = args.pop(0) if args else None
        else:
            sys.stderr.write("unknown argument: %s\n" % a)
            return 2
    text = open(src, encoding="utf-8").read() if src else sys.stdin.read()

    if mode == "format":
        try:
            body, notes = format_body(text, base_url)
        except Invalid as e:
            sys.stderr.write(report(e.problems) + "\n")
            return 1
        for n in notes + warnings(body):
            sys.stderr.write("note: %s\n" % n)
        sys.stdout.write(body)
        return 0

    if mode == "check":
        problems = validate(text)
        if problems:
            sys.stderr.write(report(problems) + "\n")
            return 1
        for w in warnings(text):
            sys.stderr.write("note: %s\n" % w)
        sys.stderr.write("PR body OK.\n")
        return 0

    sys.stderr.write("unknown mode: %s\n" % mode)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
