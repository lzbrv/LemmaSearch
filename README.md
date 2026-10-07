# LemmaSearch

Pilot study: does giving a model **lemma search** help it prove Lean theorems?
We run Claude Code on a few small theorem-proving problems, once without search and
once with search, and compare.

This repo currently has the Lean project and a **checker** (`leanfile/check_lean.py`)
that decides whether a proof file really solves a problem. This README gets you from
zero to running that checker. You don't need to know Lean beforehand.

---

## Lean in 5 minutes (just what you need here)

- **Lean 4** is a programming language and a proof checker. You write a theorem
  statement and a proof. If the file compiles, Lean has verified the proof.
- **Mathlib** is Lean's big math library (real numbers, algebra, and a huge set of
  already-proven lemmas). Our problems only use Mathlib.
- **elan** installs and manages Lean versions (like `pyenv`). **lake** is Lean's
  build tool and package manager (like `pip` plus `make`). Both come with elan.

A Lean file looks like this (`leanfile/Leanfile/Good.lean`):

```lean
import Mathlib

theorem test_thm (a b : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) : 0 ≤ a * b := by
  exact mul_nonneg ha hb
```

Read it as: "for real numbers `a`, `b`, assuming `0 ≤ a` (call that fact `ha`) and
`0 ≤ b` (`hb`), we have `0 ≤ a * b`." Everything after `:= by` is the proof. Here it
applies the Mathlib lemma `mul_nonneg` to the two facts.

Two ways a file can compile but **not** be a real proof:

- **`sorry`** is a placeholder that means "skip this proof." Lean accepts it with a
  warning.
- **`axiom`** declares something as true without proof. It can "prove" anything.

So "it compiles" isn't enough, which is why the checker exists.

---

## Setup

You need about 10 GB of free disk space (most of it is prebuilt Mathlib) and
ideally 16 GB of RAM. Commands are shown for Windows PowerShell. Where macOS or
Linux differs, that version is given too.

### 1. Install the tools

1. **Git**, **Python 3.8+**, and **VS Code**, if you don't have them. The checker
   uses only Python's standard library, so there's nothing to `pip install`.
2. **The Lean 4 VS Code extension**: in VS Code, open Extensions (`Ctrl+Shift+X`)
   and install **"Lean 4"** (publisher: leanprover).
3. **elan** (installs Lean and lake). Run in a terminal:

   Windows (PowerShell):
   ```powershell
   curl.exe -O --location https://raw.githubusercontent.com/leanprover/elan/master/elan-init.ps1
   powershell -ExecutionPolicy Bypass -f elan-init.ps1
   del elan-init.ps1
   ```
   macOS / Linux:
   ```bash
   curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh
   ```
   Accept the defaults. Then **close and reopen your terminal** (and VS Code) so
   `lake` is on your PATH. Check with:
   ```
   elan --version
   ```

### 2. Get the repo and prebuilt Mathlib

```
git clone https://github.com/lzbrv/LemmaSearch.git
cd LemmaSearch/leanfile
lake exe cache get
```

Run every `lake` command from the `leanfile/` folder.

`lake exe cache get` does three things:
- reads `lean-toolchain` and installs the exact Lean version we use (v4.34.1)
- downloads Mathlib's source
- downloads Mathlib **already compiled**

It takes several minutes and prints a lot. **Don't skip it.** Without it, Lean
compiles Mathlib from scratch, which takes hours.

Then build the project, which should take well under a minute:

```
lake build
```

It should end with `Build completed successfully`.

### 3. Check that VS Code works

1. In VS Code: **File → Open Folder…** and choose `LemmaSearch/leanfile`.
2. Open `Leanfile/Good.lean`. The first time, an orange bar sits in the margin for a
   minute or so while Lean loads Mathlib.
3. Put your cursor at the end of the proof line. The **Lean Infoview** panel on the
   right should say **"Goals accomplished!"** (meaning the proof is complete). If the
   panel isn't open, press `Ctrl+Shift+Enter`.
4. Open `Leanfile/Sorry.lean`. You should see a yellow warning: `declaration uses
   'sorry'`.

### 4. Run the checker

**First close all Lean files in VS Code** and run **"Lean 4: Stop Server"** from the
command palette (`Ctrl+Shift+P`). See [Troubleshooting](#troubleshooting) for why.

```
cd LemmaSearch/leanfile
python check_lean.py
```

This takes a few minutes (each file takes 30–70 s, mostly loading Mathlib). It
prints one line per test file and should end with:

```
All tests passed
```

**At that point you're fully set up.**

---

## What the checker does

`check_lean.py` compiles a proof file (it runs `lake env lean <file>` on a temporary
copy, so your file is never changed). It marks the file **solved** only if all of
these hold:

1. **It compiles** with no errors.
2. **No `sorry` and no custom axioms.** The checker adds `#print axioms <theorem>`
   for each theorem, which lists every axiom the proof depends on. Normal Mathlib
   proofs use only `propext`, `Classical.choice` and `Quot.sound`. A `sorry` shows
   up as `sorryAx`. Anything else (like an `axiom cheat` someone declared) is
   rejected.
3. **It still proves the original problem** (only when you pass the problem file).
   A model under pressure might "solve" a problem by editing the statement. So the
   checker compares against the original problem file and requires:
   - the same imports
   - the theorem present, with the same name and the same statement (whitespace
     differences are ignored)
   - no newly added commands that could change what the statement means
     (`notation`, `instance`, `axiom`, `variable`, `open`, `set_option`, ...)

   Helper lemmas are allowed.

### The test files (`leanfile/Leanfile/`)

All test files use the same theorem. `Problem.lean` is the original problem (the
statement with `sorry` as its proof). The checker compares every test file against it.

| File | What it does | Expected |
|---|---|---|
| `Good.lean` | correct proof | solved |
| `Helper.lean` | correct proof via a helper lemma, statement reformatted | solved |
| `Wrong.lean` | proof doesn't typecheck | not solved (doesn't compile) |
| `Sorry.lean` | uses `sorry` | not solved |
| `Axiom.lean` | declares `axiom cheat` and uses it | not solved |
| `Weakened.lean` | changes the goal to the easier `0 ≤ a * a` | not solved |
| `Renamed.lean` | deletes the theorem and proves a different, easier one | not solved |
| `Notation.lean` | redefines `ℝ` to mean `ℕ`, where the goal is trivial | not solved |

The last three compile cleanly with only standard axioms. Only check 3 catches them.

### Using it from Python

Run this from `leanfile/` (the paths are relative):

```python
from check_lean import check

result = check("Leanfile/Good.lean", problem="Leanfile/Problem.lean")
result["solved"]            # True / False
result["compiled"], result["sorry"], result["bad_axioms"]
result["statement_issues"]  # list of reasons check 3 failed ([] if fine)
result["output"]            # Lean's full output
```

Leave out `problem=` to skip check 3.

### Known limitations

- Check 3 compares **text**, so a harmless rewording of the statement is flagged.
  Look at those by hand.
- It catches the realistic cheats but isn't airtight. Before we report results, the
  plan is to compare the statements as Lean understands them, not as text.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `lake` / `elan` not found | Close and reopen the terminal (and VS Code) after installing elan. |
| `error: failed to read file '...Mathlib/....olean'` | Usually **out of memory**: each Lean process that loads Mathlib takes several GB, and VS Code may be running a few. Close Lean files in VS Code, run "Lean 4: Stop Server", and try again. If it persists, rerun `lake exe cache get`. |
| `lake build` starts compiling thousands of Mathlib files | The prebuilt cache is missing. Stop it (`Ctrl+C`) and run `lake exe cache get`. |
| Everything is very slow | Normal: loading Mathlib takes 30–70 s per file. On Windows, adding Windows Defender exclusions for the `LemmaSearch` folder and `%USERPROFILE%\.elan` can help. |
| Git warns about `LF will be replaced by CRLF` | Harmless. |
| Lean symbols show up garbled (`â‰¤` instead of `≤`) | Make sure you're running the current `check_lean.py`, which forces UTF-8 output. |

### Please don't

- **Run `lake update`.** It moves Mathlib to a newer version than the one we pinned
  (v4.34.1), and the newest versions sometimes have no prebuilt cache.
- **Commit the `.lake/` folder.** It's the multi-GB build output and is already in
  `.gitignore`.
