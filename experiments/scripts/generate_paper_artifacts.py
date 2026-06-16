"""Generate all paper artifacts from experiment results.

Runs the validity suite, stress sweep, and web_ephemeral sweep,
then outputs JSON data for figure/table generation.

Usage:
    python experiments/scripts/generate_paper_artifacts.py
    python experiments/scripts/generate_paper_artifacts.py --skip-runs
    python experiments/scripts/generate_paper_artifacts.py --seeds 0-9
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    paper_dir = repo_root / "paper"
    paper_data = paper_dir / "data"
    scripts_dir = repo_root / "experiments" / "scripts"

    paper_data.mkdir(parents=True, exist_ok=True)

    validity_out = paper_data / "validity_suite.json"
    sweep_out = paper_data / "stress_sweep_validity.json"
    web_ephemeral_out = paper_data / "web_ephemeral_sweep.json"

    python = sys.executable

    parser = argparse.ArgumentParser(description="Generate paper artifacts")
    parser.add_argument(
        "--skip-runs", action="store_true",
        help="Skip running experiments, use existing data",
    )
    parser.add_argument("--seeds", default="0-9")
    args = parser.parse_args()

    if not args.skip_runs:
        # 1. Run validity suite (multi-seed)
        print("[1/3] Running validity suite...")
        subprocess.check_call(
            [
                python,
                str(scripts_dir / "run_validity_suite.py"),
                "--seeds", args.seeds,
                "--out", str(validity_out),
                "--quiet",
            ],
            cwd=str(repo_root),
        )
        print(f"  -> {validity_out}")

        # 2. Run stress sweep
        print("[2/3] Running validity stress sweep...")
        subprocess.check_call(
            [
                python,
                str(scripts_dir / "run_stress_sweep.py"),
                "--suite", "validity",
                "--seeds", args.seeds,
                "--out", str(sweep_out),
                "--quiet",
            ],
            cwd=str(repo_root),
        )
        print(f"  -> {sweep_out}")

        # 3. Run web_ephemeral sweep (integrity prototype)
        print("[3/3] Running web_ephemeral sweep...")
        subprocess.check_call(
            [
                python,
                str(scripts_dir / "run_web_ephemeral_sweep.py"),
                "--seed", "0",
                "--clock-start-unix", "1700000000",
                "--out", str(web_ephemeral_out),
                "--quiet",
            ],
            cwd=str(repo_root),
        )
        print(f"  -> {web_ephemeral_out}")

    print("\n[OK] Paper data generated:")
    for f in [validity_out, sweep_out, web_ephemeral_out]:
        status = "exists" if f.exists() else "missing"
        print(f"  {f.name}: {status}")


if __name__ == "__main__":
    main()
