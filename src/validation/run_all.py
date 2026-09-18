"""Phase 5 driver: run every gate in order and collect the verdicts.

Usage (from the repository root):

    .venv/Scripts/python.exe src/validation/run_all.py

Each gate module is a standalone script that writes one JSON artefact into
``results/phase5/``. This driver runs them in dependency order in separate
processes, so a failure in one gate cannot corrupt another gate's interpreter
state, and then reads the artefacts back to print the consolidated verdict
table that section 17 of ``docs/phase5_bwsn_preflight.md`` reports.

Nothing here tunes, searches, optimises or trains. Every gate is deterministic:
no random seed is used anywhere in phase 5, so a rerun reproduces the artefacts
bit-for-bit apart from the timestamps in ``env``.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RESULTS = REPO / "results" / "phase5"

# module, artefact it writes, gates it decides
STAGES: list[tuple[str, str, str]] = [
    ("g0_integrity.py", "g0_integrity.json", "G0"),
    ("g1_baseline.py", "g1_g2_g11_baseline.json", "G1, G2, G11"),
    ("g3_pump_speed.py", "g3_pump_speed.json", "G3"),
    ("g4_g5_prv.py", "g4_g5_prv.json", "G4, G5"),
    ("g6_g7_g8_leak_pda.py", "g6_g7_g8_leak_pda.json", "G6, G7, G8"),
    ("g9_g10_full.py", "g9_g10_full.json", "G9, G10"),
    ("g12_realizability.py", "g12_realizability.json", "G12"),
]


def run_stage(module: str) -> dict:
    """Run one gate module in a fresh interpreter and time it."""
    t0 = time.time()
    proc = subprocess.run([sys.executable, str(HERE / module)],
                          capture_output=True, text=True, cwd=str(REPO))
    dt = time.time() - t0
    tail = [ln for ln in proc.stdout.splitlines() if "=" in ln and ln.isupper()]
    return {"module": module, "returncode": proc.returncode,
            "seconds": round(dt, 1), "verdict_lines": tail[-6:],
            "stderr_tail": proc.stderr.splitlines()[-5:] if proc.stderr else []}


def collect() -> dict:
    """Read the verdict block out of every artefact that exists.

    Two artefact shapes exist and both are accepted: a single-gate module writes
    one string under ``verdict``, a multi-gate module writes a name -> verdict
    mapping under ``verdicts``. Normalising here keeps the consolidated table
    complete instead of silently dropping the single-gate modules.
    """
    out = {}
    for _, artefact, _ in STAGES:
        path = RESULTS / artefact
        if not path.exists():
            out[artefact] = {"present": False}
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        verdicts = dict(payload.get("verdicts", {}))
        if not verdicts and isinstance(payload.get("verdict"), str):
            verdicts = {payload.get("gate", artefact): payload["verdict"]}
        out[artefact] = {"present": True,
                         "verdicts": verdicts,
                         "env_python": payload.get("env", {}).get("python"),
                         "env_wntr": payload.get("env", {}).get("wntr")}
    return out


def main() -> int:
    print("=" * 88)
    print("PHASE 5 - BWSN-1 PRE-FLIGHT VALIDATION: full gate sequence")
    print("=" * 88)
    runs = []
    for module, artefact, gates in STAGES:
        print(f"\n>>> {module}  (gates {gates})")
        r = run_stage(module)
        runs.append(r)
        status = "ok" if r["returncode"] == 0 else f"FAILED rc={r['returncode']}"
        print(f"    {status} in {r['seconds']} s")
        for ln in r["verdict_lines"]:
            print(f"    {ln}")
        for ln in r["stderr_tail"]:
            print(f"    stderr: {ln}")
    print("\n" + "=" * 88)
    print("CONSOLIDATED VERDICTS")
    print("=" * 88)
    got = collect()
    for _, artefact, _ in STAGES:
        d = got[artefact]
        if not d["present"]:
            print(f"  {artefact:<32} MISSING - gate not run")
            continue
        for name, verdict in d["verdicts"].items():
            print(f"  {name:<52} {verdict}")
    bad = [r["module"] for r in runs if r["returncode"] != 0]
    print()
    print(f"  modules run: {len(runs)}, non-zero exit: {len(bad)}"
          + (f" -> {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
