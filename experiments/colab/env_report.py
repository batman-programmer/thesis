"""Environment / version report for the BWSN-1 PPO pipeline (read-only).

Prints the ACTUAL installed versions of every dependency the project needs, the
Python build/architecture, and whether the RL stack (torch / SB3 / gymnasium) is
present. It changes nothing and installs nothing. Run IDENTICALLY on the laptop
and on Colab so the two fingerprints can be compared.

    .venv/Scripts/python.exe experiments/colab/env_report.py      # laptop
    python experiments/colab/env_report.py                        # Colab

The authoritative integration gate remains ``experiments/ppo/verify_env.py``
(this script is a lightweight version snapshot, not a hydraulic check).
"""

from __future__ import annotations

import importlib.metadata as md
import platform
import sys

REQUIRED = [
    # (importlib name, role)
    ("wntr", "hydraulic engine (EPANET 2.2) — FROZEN pin 1.5.0"),
    ("numpy", "numeric core — frozen 2.5.2"),
    ("scipy", "scientific — frozen 1.18.1"),
    ("pandas", "tabular — frozen 3.0.5"),
    ("matplotlib", "plotting — frozen 3.11.1"),
    ("networkx", "graph — frozen 3.6.1"),
    ("gymnasium", "RL env API — pin 1.4.0"),
    ("stable-baselines3", "PPO — pin 2.9.0"),
    ("torch", "NN backend — Colab preinstalled CUDA build"),
    ("pyyaml", "config serialisation — pin 6.0.3"),
    ("epyt", "EPANET 2.3 — present but NOT used in the frozen path"),
]


def _ver(name: str) -> str:
    try:
        return md.version(name)
    except Exception:
        return "NOT INSTALLED"


def main() -> int:
    print("=== BWSN-1 PPO environment report ===")
    print(f"python    : {platform.python_version()} ({platform.python_implementation()})")
    print(f"platform  : {platform.platform()}")
    print(f"machine   : {platform.machine()}  64bit={sys.maxsize > 2**32}")
    print(f"executable: {sys.executable}")
    print()
    rl_missing = []
    for name, role in REQUIRED:
        v = _ver(name)
        flag = ""
        if name in ("gymnasium", "stable-baselines3", "torch") and v == "NOT INSTALLED":
            rl_missing.append(name)
            flag = "   <-- RL stack"
        print(f"{name:20s} {v:14s} {role}{flag}")
    print()
    if rl_missing:
        print(f"RL stack NOT installed: {', '.join(rl_missing)} "
              f"(expected on the laptop; required on Colab).")
    else:
        print("RL stack present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
