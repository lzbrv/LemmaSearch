import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
'''check() decides whether a lean file really proves a problem, compiles with
lake evn lean and marks it solved if 3 things hold:
- It compiles with no errors
- It's not cheating with sorry or axioms. It runs #print axioms on each theorem and 
accepts only the three standard axioms (propext, Classical.choice, Quot.sound).
That rejects sorry (which shows up as sorryAx) and any custom axiom.
- It proves the original statement. This check only runs when you give it the problem 
file. The imports and the theorem's name and statement must be unchanged, and no new
commands that could change the statement's meaning (notation, instance, open, and so 
on) may be added.
'''
# Show Lean's Unicode symbols (≤, ℝ, ...) correctly in the Windows console
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_DIR = Path(__file__).resolve().parent
# Axioms every normal Mathlib proof is allowed to use
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

# Commands that can change what a statement means (or run arbitrary code), so a
# submission may not add them. Ones already in the problem file are allowed.
RISKY_COMMANDS = """
    notation notation3 infix infixl infixr prefix postfix macro macro_rules syntax
    declare_syntax_cat elab elab_rules binder_predicate instance deriving attribute
    axiom opaque variable include universe namespace open export set_option
    unif_hint run_cmd run_elab run_meta #eval
""".split()
# `set_option`s that only raise resource limits, so they are fine to add
SAFE_OPTIONS = {"maxHeartbeats", "maxRecDepth", "synthInstance.maxHeartbeats"}

# Attributes and modifiers that may precede a command, e.g. `@[simp] private`
MODIFIERS = r"(?:@\[[^\]]*\]\s*)?(?:(?:private|protected|noncomputable|local|scoped)\s+)*"
DECL = r"^\s*" + MODIFIERS + r"(?:theorem|lemma)\s+"
NAME_CHARS = r"[^\s(:{\[]"
COMMAND_RE = re.compile(
    r"^[ \t]*" + MODIFIERS
    + "(" + "|".join(map(re.escape, RISKY_COMMANDS)) + r")(?![\w.])[ \t]*(\S*).*$",
    flags=re.MULTILINE,
)


def theorem_names(source):
    """Names of top-level theorems/lemmas in the file."""
    return re.findall(DECL + f"({NAME_CHARS}+)", source, flags=re.MULTILINE)


SCOPE_RE = re.compile(
    r"^[ \t]*(?:(namespace|section)\b[ \t]*(\S*)|(end)\b|" + MODIFIERS
    + f"(?:theorem|lemma)\\s+({NAME_CHARS}+))",
    flags=re.MULTILINE,
)


def qualified_theorem_names(source):
    """Full names of the theorems, with their enclosing `namespace`s, as `#print axioms`
    needs them at the end of the file (e.g. `Foo.bar` for `bar` inside `namespace Foo`)."""
    names, scopes = [], []
    for m in SCOPE_RE.finditer(strip_comments(source)):
        kind, scope_name, end, name = m.groups()
        if kind == "namespace":
            scopes.append(scope_name)
        elif kind == "section":
            scopes.append(None)
        elif end:
            if scopes:
                scopes.pop()
        elif name.startswith("_root_."):
            names.append(name[len("_root_."):])
        else:
            names.append(".".join([s for s in scopes if s] + [name]))
    return names


def strip_comments(source):
    """Remove `--` and (nested) `/- -/` comments, leaving string literals intact."""
    out, i, depth, n = [], 0, 0, len(source)
    while i < n:
        two = source[i : i + 2]
        if depth:
            if two in ("/-", "-/"):
                depth += 1 if two == "/-" else -1
                i += 2
            else:
                i += 1
        elif two == "/-":
            depth, i = 1, i + 2
            out.append(" ")
        elif two == "--":
            while i < n and source[i] != "\n":
                i += 1
        elif source[i] == '"':
            j = i + 1
            while j < n and source[j] != '"':
                j += 2 if source[j] == "\\" else 1
            out.append(source[i : j + 1])
            i = j + 1
        else:
            out.append(source[i])
            i += 1
    return "".join(out)


def normalize(text):
    """Collapse whitespace, and drop it around brackets, colons and commas."""
    text = " ".join(text.split())
    return re.sub(r"\s*([()\[\]{}:,])\s*", r"\1", text)


def statements(source, name):
    """Normalized statement (binders and type, up to `:=`) of each `name` theorem."""
    pattern = DECL + re.escape(name) + f"(?!{NAME_CHARS})(.*?):="
    return [normalize(s) for s in re.findall(pattern, source, flags=re.MULTILINE | re.DOTALL)]


def risky_commands(source):
    """Normalized lines that start with a risky command (see RISKY_COMMANDS)."""
    return [
        normalize(m.group(0))
        for m in COMMAND_RE.finditer(source)
        if not (m.group(1) == "set_option" and m.group(2) in SAFE_OPTIONS)
    ]


def statement_issues(problem_src, submission_src):
    """Reasons the submission may not prove the problem's original statement.

    Text-based check for the pilot: same imports, every problem theorem present
    exactly once with the same statement, and no added commands that could
    change what the statement means. An empty list means it passed.
    """
    problem, submission = strip_comments(problem_src), strip_comments(submission_src)
    issues = []

    imports = r"^\s*import\s+(\S+)"
    if set(re.findall(imports, problem, flags=re.MULTILINE)) != set(
        re.findall(imports, submission, flags=re.MULTILINE)
    ):
        issues.append("imports changed")

    names = theorem_names(problem)
    if not names:
        issues.append("problem file has no theorems to check against")
    for name in names:
        expected = statements(problem, name)[0]
        found = statements(submission, name)
        if not found:
            issues.append(f"theorem '{name}' missing")
        elif len(found) > 1:
            issues.append(f"theorem '{name}' appears {len(found)} times")
        elif found[0] != expected:
            issues.append(
                f"statement of '{name}' changed:\n      expected {expected}\n      found    {found[0]}"
            )

    added = Counter(risky_commands(submission)) - Counter(risky_commands(problem))
    issues += [f"added command: {line}" for line in added.elements()]
    return issues


def check(path, problem=None):
    """Check a Lean file. If `problem` (the original problem file) is given, also
    check that the file still proves the problem's statement (see statement_issues)."""
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    names = qualified_theorem_names(source)
    issues = (
        statement_issues(Path(problem).read_text(encoding="utf-8"), source)
        if problem
        else None
    )
    statement_ok = None if issues is None else not issues

    # Copy the file to a temp file with `#print axioms` appended for each theorem,
    # so the original file is never modified.
    probe = source + "\n\n" + "\n".join(f"#print axioms {n}" for n in names) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", suffix=".lean", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(probe)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["lake", "env", "lean", tmp_path],
            cwd=PROJECT_DIR,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Report errors against the original file name, not the temp file
    output = (result.stdout + result.stderr).replace(tmp_path, str(path))

    # Parse `#print axioms` results. Names may contain `'` (e.g. `foo'`), and axioms
    # may carry universe levels (`Classical.choice.{u}`), which are dropped.
    axioms = {}
    for name, ax_list in re.findall(
        r"^'([^\n]+?)' depends on axioms: \[(.*?)\]", output, flags=re.DOTALL | re.MULTILINE
    ):
        ax_list = re.sub(r"\.\{[^}]*\}", "", ax_list)
        axioms[name] = {a.strip() for a in ax_list.split(",") if a.strip()}
    for name in re.findall(r"^'([^\n]+?)' does not depend on any axioms", output, flags=re.MULTILINE):
        axioms[name] = set()

    used = set().union(*axioms.values())
    compiled = result.returncode == 0
    # Primary test: sorryAx in the axioms. Backup: the warning text.
    has_sorry = "sorryAx" in used or (
        "declaration uses" in output and "sorry" in output
    )
    bad_axioms = used - STANDARD_AXIOMS - {"sorryAx"}
    all_checked = bool(names) and all(n in axioms for n in names)
    solved = (
        compiled
        and all_checked
        and not has_sorry
        and not bad_axioms
        and statement_ok is not False
    )

    print(
        f"{path}: compiled={compiled}, sorry={has_sorry}, "
        f"bad_axioms={sorted(bad_axioms) or None}, statement_ok={statement_ok}, "
        f"solved={solved}"
    )
    for issue in issues or []:
        print("    statement:", issue)
    if output.strip():
        print("   ", output.strip()[:500].replace("\n", "\n    "))

    return {
        "path": str(path),
        "compiled": compiled,
        "sorry": has_sorry,
        "axioms": {n: sorted(a) for n, a in axioms.items()},
        "bad_axioms": sorted(bad_axioms),
        "statement_ok": statement_ok,
        "statement_issues": issues,
        "solved": solved,
        "output": output,
    }


# Test files in Leanfile/, all checked against Problem.lean, with expected `solved`
TESTS = [
    ("Good.lean", True),
    ("Wrong.lean", False),
    ("Sorry.lean", False),
    ("Axiom.lean", False),
    ("Helper.lean", True),  # helper lemma + reformatted statement: still fine
    ("Weakened.lean", False),
    ("Renamed.lean", False),
    ("Notation.lean", False),
]

if __name__ == "__main__":
    problem = PROJECT_DIR / "Leanfile/Problem.lean"
    failures = [
        f for f, want in TESTS if check(PROJECT_DIR / "Leanfile" / f, problem)["solved"] != want
    ]
    print("\nAll tests passed" if not failures else f"\nFAILED: {failures}")
