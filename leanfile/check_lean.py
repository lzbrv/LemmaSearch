import subprocess

def check(path):
    result = subprocess.run(
        ["lake", "env", "lean", path],
        capture_output=True, text=True, timeout=600,
    )
    output = result.stdout + result.stderr
    compiled = result.returncode == 0
    has_sorry = "declaration uses 'sorry'" in output
    print(f"{path}: compiled={compiled}, sorry={has_sorry}, solved={compiled and not has_sorry}")
    if output.strip():
        print("  ", output.strip()[:300])

for f in ["Leanfile/Good.lean", "Leanfile/Wrong.lean", "Leanfile/Sorry.lean"]:
    check(f)