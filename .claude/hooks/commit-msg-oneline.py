#!/usr/bin/env python3
"""PreToolUse/Bash hook: keep git commit messages to one conventional line.

For each `git … commit` in the command (and only that segment — parsing stops at the
first unquoted `&&`, `||`, `;`, `|`, `&` or newline, so `-m` on a later command such
as `python3 -m pytest` is never touched):

  - the first -m / --message value is collapsed to its first meaningful line
    (bodies, Co-Authored-By and "Generated with" lines are dropped);
  - any further -m values (git's body paragraphs) are removed;
  - `--trailer "Co-authored-by: …"` is removed;
  - a subject without a conventional prefix — `type(scope)!: summary`, type one of
    feat fix chore docs refactor test perf build ci style revert — is DENIED;
  - `-F` / `--file` is DENIED: the hook cannot see the file, and the rule is one line;
  - a message from a variable or command (`-m "$MSG"`) cannot be read, so it is left
    alone with a note.

Combined short flags (`-am "msg"`, `-mmsg`) are understood. Only the edited spans
change; the rest of the command is left byte for byte.

Emits `updatedInput` only when something changed. Any parse failure exits 0 with no
output — this hook tidies, it must never break a command it does not understand.
"""
import json
import re
import shlex
import sys

NOISE = re.compile(
    r"^\s*(co-authored-by\s*:|signed-off-by\s*:|generated with|🤖)", re.IGNORECASE
)
CO_AUTHOR = re.compile(r"^\s*co-authored-by\s*[:=]", re.IGNORECASE)
HEREDOC = re.compile(
    r"\"\$\(\s*cat\s*<<-?\s*(['\"]?)(\w+)\1\s*\n(.*?)\n[ \t]*\2[ \t]*\n?\s*\)\"",
    re.DOTALL,
)
CONVENTIONAL = re.compile(
    r"^(feat|fix|chore|docs|refactor|test|perf|build|ci|style|revert)"
    r"(\([^()\s]+\))?!?: \S"
)
AUTOSQUASH = re.compile(r"^(fixup|squash|amend)! ")
TYPES = "feat, fix, chore, docs, refactor, test, perf, build, ci, style, revert"

# git global options that take a separate value: `git -C <dir> commit`.
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix"}
# `git commit` long options whose value may be the next word.
COMMIT_VALUE_OPTS = {
    "--author", "--date", "--reuse-message", "--reedit-message", "--fixup",
    "--squash", "--template", "--cleanup", "--trailer", "--pathspec-from-file",
}
# short options whose value is the rest of the word or the next word.
SHORT_VALUE = set("mFCct")
# short options whose value may only be attached (`-S<key>`, `-u<mode>`).
SHORT_OPTIONAL = set("Su")


class Unparsed(Exception):
    pass


def skip_subst(cmd, i):
    """Index just past the `)` closing the `$(` whose `(` is at cmd[i]."""
    depth, n = 0, len(cmd)
    while i < n:
        c = cmd[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        elif c == "'":
            j = cmd.find("'", i + 1)
            if j < 0:
                raise Unparsed()
            i = j
        elif c == '"':
            i += 1
            while i < n and cmd[i] != '"':
                if cmd[i] == "\\":
                    i += 1
                elif cmd.startswith("$(", i):
                    i = skip_subst(cmd, i + 1) - 1
                i += 1
            if i >= n:
                raise Unparsed()
        elif c == "\\":
            i += 1
        i += 1
    raise Unparsed()


def is_expansion(cmd, j):
    nxt = cmd[j + 1 : j + 2]
    return bool(nxt) and (nxt.isalnum() or nxt in "_{(@*#?!$-")


def scan(cmd):
    """Split into words and operators. Returns a list of dicts, or raises Unparsed.

    Word: {"op": None, "start", "end", "value", "dynamic"}. `value` is the text the
    shell would pass; `dynamic` is True when it holds an expansion we cannot resolve.
    Operator: {"op": "&&" | "||" | ";" | "|" | "&" | "\\n", "start", "end"}.
    """
    toks, i, n = [], 0, len(cmd)
    while i < n:
        ch = cmd[i]
        if ch in " \t":
            i += 1
            continue
        if ch == "\\" and cmd[i + 1 : i + 2] == "\n":
            i += 2
            continue
        if ch in ";\n":
            toks.append({"op": ch, "start": i, "end": i + 1})
            i += 1
            continue
        if ch in "&|":
            op = cmd[i : i + 2] if cmd[i : i + 2] in ("&&", "||") else ch
            toks.append({"op": op, "start": i, "end": i + len(op)})
            i += len(op)
            continue
        if ch == "#":
            while i < n and cmd[i] != "\n":
                i += 1
            continue
        start, buf, dynamic = i, [], False
        while i < n and cmd[i] not in " \t\n;&|":
            c = cmd[i]
            m = HEREDOC.match(cmd, i)
            if m:
                buf.append(m.group(3))
                i = m.end()
                continue
            if c == "'":
                j = cmd.find("'", i + 1)
                if j < 0:
                    raise Unparsed()
                buf.append(cmd[i + 1 : j])
                i = j + 1
            elif c == '"':
                j = i + 1
                while j < n and cmd[j] != '"':
                    d = cmd[j]
                    if d == "\\" and j + 1 < n:
                        nxt = cmd[j + 1]
                        if nxt in '"\\$`':
                            buf.append(nxt)
                        elif nxt != "\n":
                            buf.append("\\" + nxt)
                        j += 2
                        continue
                    if d == "$" and cmd[j + 1 : j + 2] == "(":
                        dynamic = True
                        k = skip_subst(cmd, j + 1)
                        buf.append(cmd[j:k])
                        j = k
                        continue
                    if d == "`" or (d == "$" and is_expansion(cmd, j)):
                        dynamic = True
                    buf.append(d)
                    j += 1
                if j >= n:
                    raise Unparsed()
                i = j + 1
            elif c == "$" and cmd[i + 1 : i + 2] == "'":
                j = cmd.find("'", i + 2)
                if j < 0:
                    raise Unparsed()
                buf.append(cmd[i + 2 : j].encode().decode("unicode_escape"))
                i = j + 1
            elif c == "$" and cmd[i + 1 : i + 2] == "(":
                dynamic = True
                k = skip_subst(cmd, i + 1)
                buf.append(cmd[i:k])
                i = k
            elif c == "`":
                j = cmd.find("`", i + 1)
                if j < 0:
                    raise Unparsed()
                dynamic = True
                buf.append(cmd[i : j + 1])
                i = j + 1
            elif c == "\\" and i + 1 < n:
                buf.append(cmd[i + 1])
                i += 2
            else:
                if c == "$" and is_expansion(cmd, i):
                    dynamic = True
                buf.append(c)
                i += 1
        toks.append({"op": None, "start": start, "end": i, "value": "".join(buf),
                     "dynamic": dynamic})
    return toks


def segments(toks):
    seg = []
    for t in toks:
        if t["op"]:
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def commit_args(seg):
    """The words after `commit` when this segment is a `git … commit`, else None."""
    k = 0
    while k < len(seg) and re.match(r"^[A-Za-z_]\w*=", seg[k]["value"]) and not seg[k]["dynamic"]:
        k += 1  # FOO=bar git commit …
    if k >= len(seg) or not (seg[k]["value"] == "git" or seg[k]["value"].endswith("/git")):
        return None
    k += 1
    while k < len(seg):
        v = seg[k]["value"]
        if v in GIT_VALUE_OPTS:
            k += 2
        elif v.startswith("-"):
            k += 1
        else:
            break
    if k < len(seg) and seg[k]["value"] == "commit":
        return seg[k + 1 :]
    return None


def subject(msg):
    """First line that is not blank and not a trailer/attribution line."""
    for line in msg.splitlines():
        stripped = line.strip()
        if stripped and not NOISE.match(stripped):
            return stripped
    return msg.strip().splitlines()[0].strip() if msg.strip() else ""


def parse_commit(args):
    """Find the message-bearing options. Returns (messages, trailers, file_flag).

    messages: list of dicts {flag, value_tok, prefix} — `flag` is the option word,
    `value_tok` the word holding the value (the same word when attached), `prefix`
    the attached option text (`-am`, `--message=`) or None when the value is separate.
    """
    messages, trailers, file_flag = [], [], None
    k = 0
    while k < len(args):
        tok = args[k]
        v = tok["value"]
        if v == "--":
            break
        if v.startswith("--"):
            name, eq, rest = v.partition("=")
            if name == "--message":
                if eq:
                    messages.append({"flag": tok, "value_tok": tok, "prefix": "--message="})
                elif k + 1 < len(args):
                    messages.append({"flag": tok, "value_tok": args[k + 1], "prefix": None})
                    k += 1
            elif name == "--file":
                file_flag = v
                k += 0 if eq else 1
            elif name in COMMIT_VALUE_OPTS:
                if name == "--trailer":
                    value_tok = tok if eq else (args[k + 1] if k + 1 < len(args) else None)
                    value = rest if eq else (value_tok["value"] if value_tok else "")
                    if value_tok is not None and CO_AUTHOR.match(value):
                        trailers.append((tok, value_tok))
                if not eq:
                    k += 1
            k += 1
            continue
        if v.startswith("-") and len(v) > 1:
            for idx in range(1, len(v)):
                c = v[idx]
                if c in SHORT_VALUE:
                    attached = v[idx + 1 :]
                    if c == "F":
                        file_flag = "-F"
                    if attached:
                        if c == "m":
                            messages.append({"flag": tok, "value_tok": tok, "prefix": v[: idx + 1]})
                    elif k + 1 < len(args):
                        if c == "m":
                            messages.append({"flag": tok, "value_tok": args[k + 1], "prefix": None})
                        k += 1
                    break
                if c in SHORT_OPTIONAL:
                    break
        k += 1
    return messages, trailers, file_flag


def removal_span(cmd, start, end):
    """Widen a span to swallow the whitespace before it, so no double space is left."""
    while start > 0 and cmd[start - 1] in " \t":
        start -= 1
    return start, end


def check(cmd):
    """Return (edits, deny_reason, notes) for every git commit in cmd."""
    edits, deny, notes = [], None, []
    toks = scan(cmd)
    for seg in segments(toks):
        args = commit_args(seg)
        if args is None:
            continue
        messages, trailers, file_flag = parse_commit(args)
        if file_flag:
            deny = ("Commit messages here must be one line. Use `-m \"type(scope): summary\"` "
                    "instead of %s <file>." % file_flag)
            continue
        for flag_tok, value_tok in trailers:
            edits.append(removal_span(cmd, flag_tok["start"], value_tok["end"]) + ("",))
        if not messages:
            continue
        first = messages[0]
        vt = first["value_tok"]
        if vt["dynamic"]:
            notes.append("The commit message comes from a variable or command, so the "
                         "one-line and prefix rules were not checked.")
        else:
            full = vt["value"][len(first["prefix"]):] if first["prefix"] else vt["value"]
            line = subject(full)
            if not (CONVENTIONAL.match(line) or AUTOSQUASH.match(line)):
                deny = ("Commit message needs a conventional prefix: `type(scope): summary`, "
                        "one line, type one of %s. Got: %r" % (TYPES, line))
            elif line != full:
                if first["prefix"]:
                    edits.append((vt["start"], vt["end"], first["prefix"] + shlex.quote(line)))
                else:
                    edits.append((vt["start"], vt["end"], shlex.quote(line)))
        for extra in messages[1:]:
            flag = extra["flag"]
            if extra["prefix"] or flag["value"] in ("-m", "--message"):
                edits.append(removal_span(cmd, flag["start"], extra["value_tok"]["end"]) + ("",))
            else:
                # combined short flags such as `-am`: keep the other flags, drop the value
                kept = flag["value"][: flag["value"].index("m")]
                edits.append((flag["start"], flag["end"], kept))
                edits.append(removal_span(cmd, extra["value_tok"]["start"],
                                          extra["value_tok"]["end"]) + ("",))
    return edits, deny, notes


def apply(cmd, edits):
    out = cmd
    for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
        out = out[:start] + repl + out[end:]
    return out


def rewrite(cmd):
    """Back-compatible helper: the command with message edits applied."""
    try:
        edits, _deny, _notes = check(cmd)
    except Unparsed:
        return cmd
    return apply(cmd, edits) if edits else cmd


def decide(cmd):
    """The hook's JSON output for this command, or None for no output."""
    if "commit" not in cmd or "git" not in cmd:
        return None
    try:
        edits, deny, notes = check(cmd)
    except (Unparsed, ValueError, UnicodeDecodeError):
        return None
    if deny:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": deny,
            },
            "systemMessage": "Commit blocked: " + deny.split(".")[0] + ".",
        }
    if edits:
        new_cmd = apply(cmd, edits)
        if new_cmd != cmd:
            return {
                "systemMessage": "Commit message collapsed to one line (no trailers).",
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": {"command": new_cmd},
                },
            }
    if notes:
        return {"systemMessage": " ".join(notes)}
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return
    tool_input = payload.get("tool_input") or {}
    cmd = tool_input.get("command")
    if not isinstance(cmd, str):
        return
    try:
        out = decide(cmd)
    except Exception:
        return
    if out is None:
        return
    upd = out.get("hookSpecificOutput", {}).get("updatedInput")
    if upd is not None:
        out["hookSpecificOutput"]["updatedInput"] = {**tool_input, **upd}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
