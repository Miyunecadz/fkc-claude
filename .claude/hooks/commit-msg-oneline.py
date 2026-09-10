#!/usr/bin/env python3
"""PreToolUse/Bash hook: force git commit messages to a single line.

Rewrites the Bash tool input so that:
  - the first -m/--message value is collapsed to its first meaningful line
    (bodies, Co-Authored-By and "Generated with" trailers are dropped)
  - any additional -m/--message arguments (git's body paragraphs) are removed

Emits hookSpecificOutput.updatedInput only when something actually changed.
Never blocks: any parse failure exits 0 with no output.
"""
import json
import re
import shlex
import sys

MSG_FLAG = re.compile(r"(?<![\w=-])(--message=|--message(?=[\s'\"])|-m)")
NOISE = re.compile(
    r"^\s*(co-authored-by\s*:|signed-off-by\s*:|generated with|🤖)", re.IGNORECASE
)
HEREDOC = re.compile(
    r"\"\$\(\s*cat\s*<<-?\s*(['\"]?)(\w+)\1\s*\n(.*?)\n[ \t]*\2[ \t]*\n?\s*\)\"",
    re.DOTALL,
)


def subject(msg):
    """First line that is not blank and not a trailer/attribution line."""
    for line in msg.splitlines():
        stripped = line.strip()
        if stripped and not NOISE.match(stripped):
            return stripped
    return msg.strip().splitlines()[0].strip() if msg.strip() else ""


def read_value(cmd, i):
    """Read the argument value starting at index i. Returns (value, end_index)."""
    while i < len(cmd) and cmd[i] in " \t":
        i += 1
    if i >= len(cmd):
        return None, i

    heredoc = HEREDOC.match(cmd, i)
    if heredoc:
        return heredoc.group(3), heredoc.end()

    ch = cmd[i]
    if ch == "'":
        end = cmd.find("'", i + 1)
        if end == -1:
            return None, i
        return cmd[i + 1 : end], end + 1
    if ch == '"':
        out, j = [], i + 1
        while j < len(cmd):
            if cmd[j] == "\\" and j + 1 < len(cmd):
                out.append(cmd[j + 1])
                j += 2
                continue
            if cmd[j] == '"':
                return "".join(out), j + 1
            out.append(cmd[j])
            j += 1
        return None, i
    if ch == "$" and cmd[i : i + 2] == "$'":
        end = cmd.find("'", i + 2)
        if end == -1:
            return None, i
        return cmd[i + 2 : end].encode().decode("unicode_escape"), end + 1

    j = i
    while j < len(cmd) and cmd[j] not in " \t\n":
        j += 1
    return cmd[i:j], j


def rewrite(cmd):
    if "commit" not in cmd:
        return cmd

    edits = []  # (start, end, replacement)
    seen_message = False
    pos = 0
    while True:
        flag = MSG_FLAG.search(cmd, pos)
        if not flag:
            break
        value_start = flag.end()
        if flag.group(1) == "--message=":
            value, value_end = read_value(cmd, value_start)
        else:
            value, value_end = read_value(cmd, value_start)
        if value is None:
            pos = flag.end()
            continue

        if not seen_message:
            seen_message = True
            line = subject(value)
            if line and line != value:
                keep = flag.group(1)
                joiner = "" if keep == "--message=" else " "
                edits.append(
                    (flag.start(), value_end, f"{keep}{joiner}{shlex.quote(line)}")
                )
        else:
            # extra -m becomes a body paragraph in git: drop it entirely
            edits.append((flag.start(), value_end, ""))
        pos = value_end

    if not edits:
        return cmd
    out = cmd
    for start, end, replacement in reversed(edits):
        out = out[:start] + replacement + out[end:]
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if payload.get("tool_name") != "Bash":
        return
    tool_input = payload.get("tool_input") or {}
    cmd = tool_input.get("command")
    if not isinstance(cmd, str) or "git" not in cmd:
        return
    try:
        new_cmd = rewrite(cmd)
    except Exception:
        return
    if new_cmd == cmd:
        return
    print(
        json.dumps(
            {
                "systemMessage": "Commit message collapsed to one line (no trailers).",
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": {**tool_input, "command": new_cmd},
                },
            }
        )
    )


if __name__ == "__main__":
    main()
