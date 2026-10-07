"""Pilot loop: run Claude Code headless on each problem, then check its proof.

For each problem file and attempt, this:
1. makes an isolated work folder outside the repo: its own small Lean project whose
   .lake/packages links to this project's Mathlib, so nothing is re-downloaded and
   the model can't see the repo (CLAUDE.md, test files, earlier runs);
2. runs `claude -p` there with a fixed tool set, saving the raw stream-json log;
3. runs check() on the model's final file against the original problem.

Condition "builtin": no retrieval tool, but the model may grep Mathlib's source and
use `exact?` / `apply?` (they run inside the file via `lake env lean`).

Usage, from leanfile/ (close Lean files in VS Code first: Mathlib needs the memory):
    python run_pilot.py                                  # Leanfile/Problem.lean
    python run_pilot.py Problems/A.lean Problems/B.lean --attempts 3

Output goes to ../../LemmaSearchRuns/<timestamp>_<condition>/ (next to the repo):
    config.json, summary.jsonl, and per attempt: log.jsonl, stderr.txt,
    result.json, proof.lean, work/
Work folders contain a link to Mathlib, so delete them with Python 3.12+'s
shutil.rmtree or Explorer, which remove the link, not Mathlib.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from check_lean import PROJECT_DIR, check

DEFAULT_RUNS_DIR = PROJECT_DIR.parent.parent / "LemmaSearchRuns"
PACKAGES_DIR = PROJECT_DIR / ".lake" / "packages"
PROOF_FILE = "Proof.lean"

PROMPT = f"""\
Prove the theorem in {PROOF_FILE} by replacing `sorry` with a complete Lean 4 proof.

Rules:
- Do not change the theorem's name or statement, or the imports.
- Do not use `sorry`, and do not add axioms, notation, instances, `open`,
  `variable`, or `set_option` (except `set_option maxHeartbeats N in`).
- You may add helper lemmas above the theorem.

Tools:
- Check your proof by running exactly `lake env lean {PROOF_FILE}` (about a minute;
  no output means it compiled). Other shell commands are not allowed.
- Mathlib's source is in .lake/packages/mathlib/Mathlib. You can search it with Grep
  and Glob, and use `exact?` and `apply?` in the file.

Stop when `lake env lean {PROOF_FILE}` reports no errors and no `sorry` warning.
"""

TOOLS = ["Read", "Edit", "Write", "Grep", "Glob", "Bash"]
ALLOWED = ["Read", "Edit", "Write", "Grep", "Glob", "Bash(lake env lean *)"]


def find_claude():
    """The Claude Code CLI: $CLAUDE_BIN, `claude` on PATH, or the VS Code extension's."""
    if os.environ.get("CLAUDE_BIN"):
        return os.environ["CLAUDE_BIN"]
    if shutil.which("claude"):
        return shutil.which("claude")
    bundled = sorted(
        glob.glob(str(Path.home() / ".vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude*"))
    )
    if bundled:
        return bundled[-1]
    sys.exit("Claude Code CLI not found: install it or set CLAUDE_BIN")


def link_dir(link, target):
    """Directory link that needs no admin rights (a junction on Windows)."""
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
    else:
        os.symlink(target, link, target_is_directory=True)


def make_workdir(work, problem):
    """A minimal Lean project in `work` containing a copy of the problem."""
    (work / ".lake").mkdir(parents=True)
    for name in ["lakefile.toml", "lean-toolchain", "lake-manifest.json"]:
        shutil.copy(PROJECT_DIR / name, work / name)
    shutil.copy(problem, work / PROOF_FILE)
    link_dir(work / ".lake" / "packages", PACKAGES_DIR)


def claude_command(claude, model):
    return [
        claude, "-p",
        "--output-format", "stream-json", "--verbose",
        "--model", model,
        "--safe-mode",  # no CLAUDE.md, memory, MCP servers, plugins, hooks, skills
        "--strict-mcp-config",
        "--tools", ",".join(TOOLS),
        "--allowedTools", ",".join(ALLOWED),
        "--permission-mode", "dontAsk",
        "--permission-prompts", "none",
        "--add-dir", str(PACKAGES_DIR),
        "--no-session-persistence",
    ]


def run_claude(cmd, work, log_path, stderr_path, timeout):
    """Run Claude Code in `work`, streaming its output to `log_path`."""
    start = time.time()
    with open(log_path, "w", encoding="utf-8") as log, open(stderr_path, "w", encoding="utf-8") as err:
        proc = subprocess.Popen(
            cmd, cwd=work, stdin=subprocess.PIPE, stdout=log, stderr=err,
            encoding="utf-8", errors="replace",
        )
        proc.stdin.write(PROMPT)
        proc.stdin.close()
        try:
            proc.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            # Kill the whole process tree, including any Lean it started
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
            else:
                proc.kill()
            proc.wait()
            timed_out = True
    return {"exit_code": proc.returncode, "timed_out": timed_out, "wall_s": round(time.time() - start, 1)}


def summarize_log(log_path):
    """Basic stats from the stream-json log. The full metrics parser comes later."""
    init, result, tool_calls, lean_runs = {}, {}, Counter(), 0
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "system" and msg.get("subtype") == "init":
            init = msg
        elif msg.get("type") == "result":
            result = msg
        elif msg.get("type") == "assistant":
            for block in msg.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    tool_calls[block["name"]] += 1
                    lean_runs += "lake env lean" in str(block.get("input", {}).get("command", ""))

    # Flag anything that breaks the isolation the condition assumes
    warnings = []
    extra_tools = set(init.get("tools", [])) - set(TOOLS)
    if extra_tools:
        warnings.append(f"unexpected tools available: {sorted(extra_tools)}")
    if init.get("mcp_servers"):
        warnings.append(f"MCP servers loaded: {init['mcp_servers']}")
    if not init:
        warnings.append("no init message in log")

    return {
        "model": init.get("model"),
        "tools_available": init.get("tools"),
        "result_subtype": result.get("subtype"),
        "is_error": result.get("is_error"),
        "num_turns": result.get("num_turns"),
        "duration_ms": result.get("duration_ms"),
        "total_cost_usd": result.get("total_cost_usd"),
        "usage": result.get("usage"),
        "tool_calls": dict(tool_calls),
        "lean_runs": lean_runs,
        "final_message": result.get("result"),
        "isolation_warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("problems", nargs="*", default=[str(PROJECT_DIR / "Leanfile/Problem.lean")])
    parser.add_argument("--model", default="claude-opus-5-5")
    parser.add_argument("--attempts", type=int, default=1, help="attempts per problem")
    parser.add_argument("--timeout", type=int, default=1800, help="seconds per attempt")
    parser.add_argument("--condition", default="builtin", help="label for this condition")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    args = parser.parse_args()

    claude = find_claude()
    run_dir = args.runs_dir / f"{datetime.now():%Y%m%d_%H%M%S}_{args.condition}"
    run_dir.mkdir(parents=True)
    cmd = claude_command(claude, args.model)
    (run_dir / "config.json").write_text(
        json.dumps({**vars(args), "runs_dir": str(args.runs_dir), "command": cmd, "prompt": PROMPT}, indent=2),
        encoding="utf-8",
    )
    print(f"Run folder: {run_dir}")

    for problem in map(Path, args.problems):
        for attempt in range(1, args.attempts + 1):
            out = run_dir / f"{problem.stem}_a{attempt}"
            work = out / "work"
            make_workdir(work, problem)
            print(f"\n[{problem.stem} attempt {attempt}] running Claude Code...")

            run = run_claude(cmd, work, out / "log.jsonl", out / "stderr.txt", args.timeout)
            stats = summarize_log(out / "log.jsonl")
            shutil.copy(work / PROOF_FILE, out / "proof.lean")
            checked = check(work / PROOF_FILE, problem)

            record = {
                "problem": str(problem),
                "attempt": attempt,
                "condition": args.condition,
                "solved": checked["solved"],
                **run,
                **stats,
                "check": {k: v for k, v in checked.items() if k != "path"},
            }
            (out / "result.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            with open(run_dir / "summary.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({k: v for k, v in record.items() if k not in ("check", "usage", "final_message")}) + "\n")

            print(
                f"[{problem.stem} attempt {attempt}] solved={checked['solved']} "
                f"turns={stats['num_turns']} lean_runs={stats['lean_runs']} wall={run['wall_s']}s"
                + (" TIMED OUT" if run["timed_out"] else "")
            )
            for w in stats["isolation_warnings"]:
                print(f"    WARNING: {w}")


if __name__ == "__main__":
    main()
