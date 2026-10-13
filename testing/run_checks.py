"""Run every check:  python testing/run_checks.py   (add a word to filter, -v for full output)."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHECKS = Path(__file__).resolve().parent / "checks"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "-v" in sys.argv
    scripts = sorted(p for p in CHECKS.glob("verify_*.py") if not args or args[0] in p.name)
    failed = []
    for script in scripts:
        run = subprocess.run([sys.executable, str(script)], cwd=REPO, capture_output=True, text=True)
        output = run.stdout + run.stderr
        ok = run.returncode == 0
        print(f"{'✅' if ok else '❌'} {script.stem}")
        if verbose or not ok:
            print("\n".join("     " + line for line in output.splitlines()[-40:]))
        if not ok:
            failed.append(script.stem)
    print(f"\n{len(scripts) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
