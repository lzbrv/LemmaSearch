"""Find solved, Mathlib-only Prove2Me problems and save them for the pilot.

A problem qualifies if its preamble (imports) and its accepted proof both import
only Mathlib, so it runs in this project and doesn't depend on other Prove2Me files.
For each one this writes:
    Problems/<name>.lean     preamble + formal statement (ending in `:= by sorry`)
    References/<name>.lean   an accepted proof (declares `theorem solution`), which
                             the pilot model never sees
    Problems/candidates.jsonl  metadata, one line per problem

Needs a Prove2Me API key (from the account menu on prove2.me) in the P2M_API_KEY
environment variable or in ~/.prove2me_api_key.

Usage, from leanfile/:
    python find_problems.py --explore    # save sample API responses to p2m_raw/
    python find_problems.py              # find up to 15 candidates
    python find_problems.py --verify     # ...and check each compiles locally (slow)

Field names were checked against the live API on 2026-10-07 (see --explore).
Prove2Me verifies against its own Mathlib versions (default Lean v4.33.1), not our
v4.34.1, so a problem can fail to compile here: --verify catches that.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from check_lean import PROJECT_DIR, check

API = "https://prove2.me/api/v1"
KEY_FILE = Path.home() / ".prove2me_api_key"
PROBLEMS_DIR = PROJECT_DIR / "Problems"
REFERENCES_DIR = PROJECT_DIR / "References"
RAW_DIR = PROJECT_DIR / "p2m_raw"
DELAY = 0.3  # seconds between requests, to be polite to the server


class Client:
    """Prove2Me API client: exchanges the API key for short-lived access tokens."""

    def __init__(self, api_key):
        self.api_key = api_key
        self.token, self.expires_at = None, 0

    def _request(self, method, path, params=None, body=None, auth=True):
        url = f"{API}{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if auth:
            if time.time() > self.expires_at - 60:
                self._refresh()
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        time.sleep(DELAY)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text  # e.g. a solution returned as plain Lean source

    def _refresh(self):
        resp = self._request("POST", "/agent/refresh", body={"api_key": self.api_key}, auth=False)
        self.token = resp["access_token"]
        self.expires_at = resp.get("expires_at") or time.time() + 3000

    def get(self, path, **params):
        return self._request("GET", path, params)


def load_api_key():
    key = os.environ.get("P2M_API_KEY") or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else "")
    if not key:
        sys.exit(f"No API key: set P2M_API_KEY or save it in {KEY_FILE}")
    return key


def imports_of(lean_src):
    return re.findall(r"^\s*import\s+(\S+)", lean_src or "", flags=re.MULTILINE)


def mathlib_only(lean_src):
    """True if the file imports something and every import is Mathlib."""
    imps = imports_of(lean_src)
    return bool(imps) and all(i == "Mathlib" or i.startswith("Mathlib.") for i in imps)


def scan_theorems(client, status, max_theorems):
    """Yield theorems with the given status, 200 per request, at most max_theorems."""
    offset, limit = 0, 200
    while offset < max_theorems:
        page = client.get("/theorems", status=status, limit=limit, offset=offset)["theorems"]
        if not page:
            return
        yield from page[: max_theorems - offset]
        offset += limit


def explore(client, status):
    """Save one raw response from each endpoint used, to check the response format."""
    RAW_DIR.mkdir(exist_ok=True)

    def save(name, data):
        (RAW_DIR / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"saved p2m_raw/{name}.json")

    save("environments", client.get("/environments"))
    listed = client.get("/theorems", status=status, limit=5)
    save(f"theorems_{status}", listed)
    tid = listed["theorems"][0]["theorem_id"]
    save("theorem_detail", client.get(f"/theorems/{tid}"))
    subs = client.get(f"/theorems/{tid}/submissions", status="ACCEPTED")
    save("submissions", subs)
    if subs["submissions"]:
        save("solution", client.get(f"/submissions/{subs['submissions'][0]['id']}/solution"))


def find(client, args):
    PROBLEMS_DIR.mkdir(exist_ok=True)
    REFERENCES_DIR.mkdir(exist_ok=True)
    found, skipped, scanned = [], Counter(), 0

    for t in scan_theorems(client, args.status, args.max_theorems):
        if len(found) >= args.want:
            break
        scanned += 1
        preamble, statement = t.get("preamble") or "", t.get("formal_statement") or ""
        if t.get("deprecated_at"):
            skipped["deprecated"] += 1
            continue
        if not statement or not mathlib_only(preamble):
            skipped["imports beyond Mathlib"] += 1
            continue

        # An accepted proof that is itself Mathlib-only (not built from other Prove2Me
        # lemmas) and short enough to be a standalone proof, not a transplanted project
        subs = client.get(f"/theorems/{t['theorem_id']}/submissions", status="ACCEPTED")["submissions"]
        solution, reason = None, "no accepted proof"
        for sub in subs[: args.max_submissions]:
            text = client.get(f"/submissions/{sub['id']}/solution").get("content") or ""
            if not mathlib_only(text):
                reason = "proof imports beyond Mathlib"
            elif len(text.splitlines()) > args.max_ref_lines:
                reason = f"proof over {args.max_ref_lines} lines"
            else:
                solution = text
                break
        if not solution:
            skipped[reason] += 1
            continue

        name = t["theorem_name"]
        slug = re.sub(r"\W+", "_", name).strip("_")[:80]
        problem_path, ref_path = PROBLEMS_DIR / f"{slug}.lean", REFERENCES_DIR / f"{slug}.lean"
        problem_path.write_text(f"{preamble.strip()}\n\n{statement.strip()}\n", encoding="utf-8")
        ref_path.write_text(solution, encoding="utf-8")
        found.append({
            "id": t["theorem_id"],
            "name": name,
            "title": t.get("theorem_title"),
            "environment": t.get("env_display_name"),
            "mathlib_rev": t.get("mathlib_rev"),
            "tags": t.get("tags"),
            "statement_nl": t.get("natural_language_statement"),
            "reference_lines": len(solution.strip().splitlines()),
            "problem": problem_path.relative_to(PROJECT_DIR).as_posix(),
            "reference": ref_path.relative_to(PROJECT_DIR).as_posix(),
        })
        print(f"  candidate: {name} (reference proof: {found[-1]['reference_lines']} lines)")

    print(f"\nScanned {scanned} theorems. Skipped: {dict(skipped)}")

    if args.verify:
        print("\nChecking candidates locally (close VS Code's Lean server first)...")
        for c in found:
            p = check(PROJECT_DIR / c["problem"])
            r = check(PROJECT_DIR / c["reference"])
            # The problem should compile with only the `sorry`; the reference should be a clean proof
            c["problem_ok"] = p["compiled"] and p["sorry"] and not p["bad_axioms"]
            c["reference_ok"] = r["solved"]

    with open(PROBLEMS_DIR / "candidates.jsonl", "w", encoding="utf-8") as f:
        for c in found:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(found)} candidates written to Problems/ and References/ (see Problems/candidates.jsonl)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--explore", action="store_true", help="save raw API responses and stop")
    parser.add_argument("--status", default="Proved", help="theorem status meaning solved")
    parser.add_argument("--want", type=int, default=15, help="candidates to collect")
    parser.add_argument("--max-theorems", type=int, default=3000, help="theorems to scan at most")
    parser.add_argument("--max-ref-lines", type=int, default=200, help="longest reference proof to accept")
    parser.add_argument("--max-submissions", type=int, default=5, help="accepted proofs to try per theorem")
    parser.add_argument("--verify", action="store_true", help="compile each candidate locally")
    args = parser.parse_args()

    client = Client(load_api_key())
    explore(client, args.status) if args.explore else find(client, args)


if __name__ == "__main__":
    main()
