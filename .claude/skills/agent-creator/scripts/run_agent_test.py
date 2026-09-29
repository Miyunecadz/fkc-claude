#!/usr/bin/env python3
"""Run one test task against a subagent file, in a throwaway sandbox, with the agent's
real system prompt and real tool list enforced by Claude Code.

How: creates a fresh sandbox in the system temp directory (never under the project:
Claude Code refuses writes to any path inside a `.claude/` directory, which would fail
every edit test), copies the fixture (if any) into it, installs the agent file at
<sandbox>/.claude/agents/<name>.md, makes the sandbox a git repo with a baseline commit,
then runs `claude -p` there with only project settings loaded. The task goes in on stdin.

Modes
  run       (default) the session runs AS the agent (--agent <name>). The task text is
            what the main agent would send it. Tools outside the agent's `tools` list are
            not available. The agent's own tools are pre-approved so it can act headless.
  delegate  the session runs as a normal main agent with the agent file installed. The
            task text is a USER prompt. Records whether the main agent delegated to this
            agent (Agent tool call with subagent_type == name). Stops at the first Agent
            call. Use it to test the description, not the body. The other agents in the
            agent file's directory are installed too (turn off with --alone), so the probe
            shows whether THIS agent wins against its real neighbours.

Writes to <out>/:
  output.md        final text the agent returned (run mode)
  tool_calls.json  every tool call: tool name + short input summary
  changes.diff     every file the run created, changed or deleted in the sandbox
  metrics.json     duration, cost, turns, exit status, errors
  delegation.json  (delegate mode) delegated yes/no, which agent, the prompt it sent
  transcript.jsonl raw stream-json events
  (metrics.json records the sandbox path; inspect it there after the run)

The sandbox is a copy. Never point --fixture at a live repo you care about, and never put
credentials in a fixture: in run mode the agent's own tools are pre-approved, nothing
else. Do not change the permission mode or patch this script to get a test through; a
harness problem is a finding to report, not something to work around.

Usage:
  run_agent_test.py <agent.md> --out DIR (--task TEXT | --task-file FILE)
                    [--fixture DIR] [--mode run|delegate] [--model MODEL]
                    [--timeout SECONDS] [--budget USD] [--alone]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lint_agent import parse_tools, split_frontmatter  # noqa: E402

import yaml  # noqa: E402


def summarise_input(tool, inp):
    if not isinstance(inp, dict):
        return str(inp)[:200]
    for key in ("command", "file_path", "path", "pattern", "url", "subagent_type", "skill", "query"):
        if key in inp:
            extra = ""
            if tool == "Agent":
                extra = " | " + str(inp.get("prompt", ""))[:200]
            return f"{key}={str(inp[key])[:200]}{extra}"
    return json.dumps(inp)[:200]


def git(sandbox, *args):
    return subprocess.run(["git", "-c", "user.name=agent-test", "-c", "user.email=agent-test@localhost",
                           "-c", "commit.gpgsign=false", *args], cwd=sandbox,
                          capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("--out", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--task")
    g.add_argument("--task-file")
    ap.add_argument("--fixture")
    ap.add_argument("--mode", choices=["run", "delegate"], default="run")
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--budget", type=float, default=3.0, help="max USD for this run")
    ap.add_argument("--alone", action="store_true",
                    help="delegate mode: install only this agent, not its neighbours")
    a = ap.parse_args()

    agent_path = Path(a.agent).resolve()
    fm_text, _ = split_frontmatter(agent_path.read_text(encoding="utf-8"))
    if fm_text is None:
        sys.exit("agent file has no frontmatter; run lint_agent.py first")
    fm = yaml.safe_load(fm_text)
    name = str(fm["name"])
    tools = parse_tools(fm.get("tools")) or []
    task = a.task if a.task is not None else Path(a.task_file).read_text(encoding="utf-8")

    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix=f"agent-test-{name}-"))
    if a.fixture:
        shutil.copytree(Path(a.fixture).resolve(), sandbox, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git"))
    agents_dir = sandbox / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    if a.mode == "delegate" and not a.alone:
        for other in agent_path.parent.glob("*.md"):
            if other.resolve() != agent_path:
                shutil.copy(other, agents_dir / other.name)
    shutil.copy(agent_path, agents_dir / f"{name}.md")
    git(sandbox, "init", "-q")
    git(sandbox, "add", "-A")
    git(sandbox, "commit", "-q", "-m", "baseline", "--allow-empty")

    cmd = ["claude", "-p", "--setting-sources", "project", "--output-format", "stream-json",
           "--verbose", "--max-budget-usd", str(a.budget)]
    if a.mode == "run":
        cmd += ["--agent", name, "--permission-mode", "acceptEdits"]
        if tools:
            # "=" form: the flag is variadic and would otherwise swallow what follows
            cmd.append("--allowedTools=" + ",".join(tools))
    if a.model:
        cmd += ["--model", a.model]

    env = dict(os.environ)
    env.pop("CLAUDECODE", None)  # allow a nested headless session
    started = time.time()
    events, tool_calls, delegation = [], [], {"delegated": False, "subagent_type": None, "prompt": None}
    result, timed_out = None, False
    proc = subprocess.Popen(cmd, cwd=sandbox, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, env=env)
    proc.stdin.write(task)
    proc.stdin.close()
    try:
        for line in proc.stdout:
            if time.time() - started > a.timeout:
                timed_out = True
                proc.kill()
                break
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(ev)
            if ev.get("type") == "assistant":
                for block in ev.get("message", {}).get("content", []) or []:
                    if block.get("type") == "tool_use":
                        call = {"tool": block.get("name"),
                                "input": summarise_input(block.get("name"), block.get("input")),
                                "from_subagent": bool(ev.get("parent_tool_use_id"))}
                        tool_calls.append(call)
                        if a.mode == "delegate" and block.get("name") in ("Agent", "Task") \
                                and not ev.get("parent_tool_use_id"):
                            inp = block.get("input") or {}
                            delegation = {"delegated": inp.get("subagent_type") == name,
                                          "subagent_type": inp.get("subagent_type"),
                                          "prompt": inp.get("prompt")}
                            proc.kill()
                            break
            elif ev.get("type") == "result":
                result = ev
        else:
            pass
    finally:
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    stderr = proc.stderr.read() if proc.stderr else ""

    git(sandbox, "add", "-A")
    diff = git(sandbox, "diff", "--cached", "HEAD", "--", ".", ":(exclude).claude/agents").stdout

    out.mkdir(parents=True, exist_ok=True)
    (out / "transcript.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    (out / "tool_calls.json").write_text(json.dumps(tool_calls, indent=2))
    (out / "changes.diff").write_text(diff)
    final_text = (result or {}).get("result") or ""
    if a.mode == "run":
        (out / "output.md").write_text(final_text)
    else:
        (out / "delegation.json").write_text(json.dumps(delegation, indent=2))
    metrics = {
        "agent": name, "mode": a.mode, "model_override": a.model, "sandbox": str(sandbox),
        "agents_installed": sorted(p.stem for p in agents_dir.glob("*.md")),
        "duration_s": round(time.time() - started, 1),
        "api_duration_ms": (result or {}).get("duration_ms"),
        "cost_usd": (result or {}).get("total_cost_usd"),
        "turns": (result or {}).get("num_turns"),
        "is_error": (result or {}).get("is_error"),
        "subtype": (result or {}).get("subtype"),
        "timed_out": timed_out,
        "tool_call_count": len(tool_calls),
        "files_changed": sum(1 for l in diff.splitlines() if l.startswith("diff --git")),
        "stderr_tail": stderr.strip()[-500:],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))

    print(json.dumps({k: metrics[k] for k in ("agent", "mode", "duration_s", "cost_usd", "turns",
                                              "tool_call_count", "files_changed", "timed_out")}))
    if a.mode == "delegate":
        print(json.dumps(delegation)[:400])
    elif not final_text:
        print("WARNING: no final output captured; see metrics.json stderr_tail and transcript.jsonl")


if __name__ == "__main__":
    main()
